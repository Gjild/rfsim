# ui/frontend.py
import threading
import time
import os
import hashlib
import difflib
from ruamel.yaml import YAML
from utils import matrix as mat
from inout.yaml_parser import parse_netlist
from evaluation.sweep import sweep
import dearpygui.dearpygui as dpg
import numpy as np

# ---------- Safe Evaluation Context ----------
SAFE_EVAL_CONTEXT = {
    "np": np,
    "z_to_s": mat.z_to_s,
    "s_to_z": mat.s_to_z,
    "db": mat.db,
    "mag": mat.mag,
    "phase": mat.phase,
    "real": mat.real,
    "imag": mat.imag,
    "log10": mat.log10,
    "log": mat.log,
    "unwrap": mat.unwrap_phase,
    "conj": mat.conjugate,
    "abs": abs,
    "round": round,
}

def _hash_file(path):
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

# ---------- Global State Manager ----------
class StateManager:
    def __init__(self):
        self.netlist_path = ""
        self.sweep_config_path = ""
        self.simulation_running = False
        self.simulation_progress = 0.0
        self.simulation_results = None
        self.logs = []
        # For each plot tab, store its type, a unique tab tag, and a list of trace expressions.
        self.plot_tabs = {}
        self._last_netlist_hash = None
        self._last_sweep_hash = None
        self.yaml_editor_text = ""
        self.yaml_editor_original = ""

    def add_log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")

    def needs_simulation(self):
        netlist_hash = _hash_file(self.netlist_path)
        sweep_hash = _hash_file(self.sweep_config_path)
        if (netlist_hash != self._last_netlist_hash) or (sweep_hash != self._last_sweep_hash):
            self._last_netlist_hash = netlist_hash
            self._last_sweep_hash = sweep_hash
            return True
        return False

state = StateManager()

# ---------- Plot Evaluation Helpers ----------
def _evaluate_expression(expr):
    """Evaluate an expression that returns a numeric value (for rectangular plots)."""
    x_data, y_data = [], []
    safe_globals = {"__builtins__": {}, **SAFE_EVAL_CONTEXT}
    if state.simulation_results is None:
        state.add_log("No simulation results available.")
        return None, None
    for (freq, _), s_matrix in state.simulation_results.results.items():
        try:
            Z = mat.s_to_z(s_matrix)
            y_val = eval(expr, safe_globals, {"Z": Z, "freq": freq})
            x_data.append(freq)
            y_data.append(y_val)
        except Exception as e:
            state.add_log(f"Eval failed at {freq:.3e} Hz: {e}")
            return None, None
    return x_data, y_data

def _evaluate_complex_expression(expr):
    """Evaluate an expression that returns a complex value (for Smith charts)."""
    x_data, y_data = [], []
    safe_globals = {"__builtins__": {}, **SAFE_EVAL_CONTEXT}
    if state.simulation_results is None:
        state.add_log("No simulation results available.")
        return None, None
    for (freq, _), s_matrix in state.simulation_results.results.items():
        try:
            Z = mat.s_to_z(s_matrix)
            val = eval(expr, safe_globals, {"Z": Z, "freq": freq})
            x_data.append(val.real)
            y_data.append(val.imag)
        except Exception as e:
            state.add_log(f"Complex eval failed at {freq:.3e} Hz: {e}")
            return None, None
    return x_data, y_data

# ---------- Global Smith Chart Constants & Grid Generators ----------
CIRCLE_RES = 500
REACTANCE_RES = 2000
UNIT_CIRCLE_CLIP = 0.999
RESISTANCE_VALUES = [0.2, 0.5, 1, 2, 5]
REACTANCE_VALUES = [0.2, 0.5, 1, 2, 5]

def generate_resistance_circle(r):
    theta = np.linspace(-np.pi, np.pi, CIRCLE_RES)
    c, rad = r / (1 + r), 1 / (1 + r)
    x = c + rad * np.cos(theta)
    y = rad * np.sin(theta)
    mask = x**2 + y**2 <= UNIT_CIRCLE_CLIP
    return [(x[i], y[i]) for i in range(len(x)) if mask[i]]

def generate_reactance_arcs(xval):
    arcs, radius = [], 1 / xval
    theta = np.linspace(-np.pi, np.pi, REACTANCE_RES)
    for s in [+1, -1]:
        x = 1 + radius * np.cos(theta)
        y = s * radius + radius * np.sin(theta)
        mask = x**2 + y**2 <= UNIT_CIRCLE_CLIP
        current = []
        for i, m in enumerate(mask):
            if m:
                current.append((x[i], y[i]))
            elif current:
                if len(current) >= 10:
                    arcs.append(current)
                current = []
        if current and len(current) >= 10:
            arcs.append(current)
    return arcs

def draw_smith_grid(plot_id, theme):
    # Draw resistance circles.
    for r in RESISTANCE_VALUES:
        pts = generate_resistance_circle(r)
        if len(pts) >= 2:
            x, y = zip(*pts)
            tag = f"grid_res_circle_{plot_id}_{r}"
            dpg.add_line_series(x, y, parent=f"y_axis_{plot_id}", tag=tag)
            dpg.bind_item_theme(tag, theme)
    # Draw reactance arcs.
    for x_val in REACTANCE_VALUES:
        arcs = generate_reactance_arcs(x_val)
        for i, arc in enumerate(arcs):
            if len(arc) >= 2:
                x, y = zip(*arc)
                tag = f"grid_react_arc_{plot_id}_{x_val}_{i}"
                dpg.add_line_series(x, y, parent=f"y_axis_{plot_id}", tag=tag)
                dpg.bind_item_theme(tag, theme)

# ---------- Trace List Management ----------
def _update_trace_list(plot_id):
    """Rebuild the trace list UI for the given plot tab."""
    list_tag = f"trace_list_{plot_id}"
    if dpg.does_item_exist(list_tag):
        dpg.delete_item(list_tag, children_only=True)
    # Create a group for each trace in the tab.
    for idx, expr in enumerate(state.plot_tabs[plot_id]["traces"]):
        with dpg.group(horizontal=True, parent=list_tag):
            input_tag = f"trace_input_{plot_id}_{idx}"
            dpg.add_input_text(label="", default_value=expr, width=250, tag=input_tag)
            dpg.add_button(label="Update", user_data=(plot_id, idx), callback=update_trace_callback)
            dpg.add_button(label="Remove", user_data=(plot_id, idx), callback=remove_trace_callback)

def update_trace_callback(sender, app_data, user_data):
    plot_id, idx = user_data
    input_tag = f"trace_input_{plot_id}_{idx}"
    new_expr = dpg.get_value(input_tag).strip()
    if not new_expr:
        state.add_log("Updated expression is empty.")
        return
    old_expr = state.plot_tabs[plot_id]["traces"][idx]
    if new_expr == old_expr:
        state.add_log("Expression unchanged.")
        return
    # Remove the old line series.
    if state.plot_tabs[plot_id]["type"] == "rectangular":
        old_tag = f"trace_{plot_id}_{hash(old_expr)}"
        if dpg.does_item_exist(old_tag):
            dpg.delete_item(old_tag)
        state.plot_tabs[plot_id]["traces"][idx] = new_expr
        add_trace_to_rectangular_plot(plot_id, new_expr)
    elif state.plot_tabs[plot_id]["type"] == "smith":
        old_tag = f"smith_trace_{plot_id}_{hash(old_expr)}"
        if dpg.does_item_exist(old_tag):
            dpg.delete_item(old_tag)
        state.plot_tabs[plot_id]["traces"][idx] = new_expr
        add_trace_to_smith_plot(plot_id, new_expr)
    state.add_log(f"Updated trace in plot {plot_id} at index {idx}.")
    _update_trace_list(plot_id)

def remove_trace_callback(sender, app_data, user_data):
    plot_id, idx = user_data
    expr = state.plot_tabs[plot_id]["traces"][idx]
    if state.plot_tabs[plot_id]["type"] == "rectangular":
        tag = f"trace_{plot_id}_{hash(expr)}"
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
    elif state.plot_tabs[plot_id]["type"] == "smith":
        tag = f"smith_trace_{plot_id}_{hash(expr)}"
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
    del state.plot_tabs[plot_id]["traces"][idx]
    state.add_log(f"Removed trace from plot {plot_id} at index {idx}.")
    _update_trace_list(plot_id)

# ---------- Plot Tab Management ----------
def add_new_plot_tab(plot_type, initial_expression=None):
    # Create a unique plot id.
    plot_id = str(int(time.time() * 1000))
    tab_tag = f"tab_{plot_id}"
    if plot_type.lower() == "rectangular":
        with dpg.tab(label="Rectangular Plot", tag=tab_tag, parent="results_tab_bar"):
            # Input for new trace.
            input_tag = f"expression_input_{plot_id}"
            dpg.add_input_text(label="Plot Expression", default_value="abs(z_to_s(Z)[1, 0])", tag=input_tag, width=300)
            dpg.add_button(label="Add Trace", user_data=plot_id, callback=plot_expression_callback)
            # Container for the trace list placed above the plot.
            with dpg.child_window(label="Trace List", tag=f"trace_list_{plot_id}", autosize_x=False, autosize_y=False):
                pass
            # Plot widget.
            with dpg.child_window(tag=f"plot_container_{plot_id}", autosize_x=True, autosize_y=True):
                with dpg.plot(label="Rectangular Plot", height=400, width=400, tag=f"plot_{plot_id}"):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency (Hz)", tag=f"x_axis_{plot_id}")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Y Axis", tag=f"y_axis_{plot_id}")
        state.plot_tabs[plot_id] = {"type": "rectangular", "traces": [] if initial_expression is None else [initial_expression], "tab_tag": tab_tag}
        if initial_expression is not None:
            add_trace_to_rectangular_plot(plot_id, initial_expression)
            _update_trace_list(plot_id)
    elif plot_type.lower() == "smith":
        with dpg.tab(label="Smith Chart", tag=tab_tag, parent="results_tab_bar"):
            # Reset zoom button.
            dpg.add_button(label="Reset Zoom", user_data=plot_id, callback=reset_zoom_callback)
            # Input for new trace.
            with dpg.group(horizontal=True):
                dpg.add_input_text(label="Expression", tag=f"smith_expr_input_{plot_id}", default_value="s_matrix[0, 0]")
                dpg.add_button(label="Add Trace", user_data=plot_id, callback=smith_expression_callback)
            # Container for the trace list placed above the plot.
            with dpg.child_window(label="Trace List", tag=f"trace_list_{plot_id}", autosize_x=True, autosize_y=False):
                pass
            # Plot widget.
            with dpg.child_window(tag=f"plot_container_{plot_id}", autosize_x=True, autosize_y=True):
                with dpg.plot(label="Smith Chart", width=600, height=600, equal_aspects=True, tag=f"plot_{plot_id}"):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="Re", tag=f"x_axis_{plot_id}", no_gridlines=True)
                    dpg.add_plot_axis(dpg.mvYAxis, label="Im", tag=f"y_axis_{plot_id}", no_gridlines=True)
                    # Draw unit circle with grey theme.
                    dpg.bind_item_theme(
                        dpg.add_line_series(np.cos(np.linspace(0, 2*np.pi, CIRCLE_RES)),
                                            np.sin(np.linspace(0, 2*np.pi, CIRCLE_RES)),
                                            parent=f"y_axis_{plot_id}"),
                        GRAY_THEME
                    )
                    # Draw grid lines (resistance and reactance).
                    draw_smith_grid(plot_id, GRAY_THEME)
        state.plot_tabs[plot_id] = {"type": "smith", "traces": [], "tab_tag": tab_tag}
    state.add_log(f"Added new {plot_type} plot tab with id {plot_id}")

def add_new_plot_tab_callback(sender, app_data, user_data):
    plot_type = dpg.get_value("new_plot_type").lower()  # "Rectangular" or "Smith"
    add_new_plot_tab(plot_type)

# ---------- Rectangular Plot Trace Functions ----------
def add_trace_to_rectangular_plot(plot_id, expr):
    tag = f"trace_{plot_id}_{hash(expr)}"
    x_data, y_data = _evaluate_expression(expr)
    if x_data is None:
        return
    dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
    dpg.fit_axis_data(f"y_axis_{plot_id}")
    state.add_log(f"Added trace '{expr}' to plot {plot_id}")

def plot_expression_callback(sender, app_data, plot_id):
    input_tag = f"expression_input_{plot_id}"
    expr = dpg.get_value(input_tag).strip()
    if not expr:
        state.add_log("Empty expression.")
        return
    if expr in state.plot_tabs[plot_id]["traces"]:
        state.add_log(f"Expression already plotted in plot {plot_id}: {expr}")
        return
    state.plot_tabs[plot_id]["traces"].append(expr)
    add_trace_to_rectangular_plot(plot_id, expr)
    _update_trace_list(plot_id)

def update_rectangular_plot(plot_id):
    for expr in state.plot_tabs[plot_id]["traces"]:
        tag = f"trace_{plot_id}_{hash(expr)}"
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
        x_data, y_data = _evaluate_expression(expr)
        if x_data is None:
            continue
        dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
    dpg.fit_axis_data(f"y_axis_{plot_id}")
    state.add_log(f"Updated rectangular plot {plot_id}")

# ---------- Smith Chart Trace Functions ----------
def add_trace_to_smith_plot(plot_id, expr):
    tag = f"smith_trace_{plot_id}_{hash(expr)}"
    x_data, y_data = _evaluate_complex_expression(expr)
    if x_data is None:
        return
    dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
    dpg.fit_axis_data(f"y_axis_{plot_id}")
    state.add_log(f"Added smith trace '{expr}' to plot {plot_id}")

def smith_expression_callback(sender, app_data, plot_id):
    input_tag = f"smith_expr_input_{plot_id}"
    expr = dpg.get_value(input_tag).strip()
    if not expr:
        state.add_log("Empty smith expression.")
        return
    if expr in state.plot_tabs[plot_id]["traces"]:
        state.add_log(f"Expression already plotted in smith chart {plot_id}: {expr}")
        return
    state.plot_tabs[plot_id]["traces"].append(expr)
    add_trace_to_smith_plot(plot_id, expr)
    _update_trace_list(plot_id)

def update_smith_chart(plot_id):
    # Update each smith trace.
    for expr in state.plot_tabs[plot_id]["traces"]:
        tag = f"smith_trace_{plot_id}_{hash(expr)}"
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
        x_data, y_data = _evaluate_complex_expression(expr)
        if x_data is None:
            continue
        dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
    dpg.fit_axis_data(f"y_axis_{plot_id}")
    state.add_log(f"Updated Smith chart plot {plot_id}")

def reset_zoom_callback(sender, app_data, plot_id):
    dpg.set_axis_limits(f"x_axis_{plot_id}", -1.1, 1.1)
    dpg.set_axis_limits(f"y_axis_{plot_id}", -1.1, 1.1)
    state.add_log(f"Reset zoom for Smith chart plot {plot_id}")

def update_smith_tooltips():
    for plot_id, info in state.plot_tabs.items():
        if info["type"] == "smith":
            tag = f"hover_info_{plot_id}"
            if dpg.does_item_exist(tag) and dpg.is_item_hovered(f"plot_{plot_id}"):
                x, y = dpg.get_plot_mouse_pos()
                dpg.set_value(tag, f"Γ = {x:.3f} + j{y:.3f}")

# ---------- Simulation Thread ----------
def simulation_thread():
    state.simulation_results = None
    state.simulation_running = True
    state.simulation_progress = 0.0
    state.add_log("Simulation started.")
    try:
        yaml = YAML()
        if not os.path.exists(state.netlist_path):
            raise FileNotFoundError(f"Netlist file not found: {state.netlist_path}")
        if not os.path.exists(state.sweep_config_path):
            raise FileNotFoundError(f"Sweep config file not found: {state.sweep_config_path}")

        if not state.needs_simulation():
            state.add_log("Input files unchanged, skipping re-simulation.")
            return

        state.add_log("Loading netlist...")
        circuit = parse_netlist(state.netlist_path)
        circuit.validate(verbose=True)
        state.add_log("Netlist loaded and validated.")

        state.add_log("Loading sweep configuration...")
        with open(state.sweep_config_path, 'r') as f:
            sweep_config_data = yaml.load(f)
        state.add_log("Sweep configuration loaded.")

        state.add_log("Running simulation sweep...")
        result = sweep(circuit, sweep_config_data)
        state.simulation_results = result
        state.add_log("Simulation completed successfully.")

        # Update each plot tab.
        for plot_id, info in state.plot_tabs.items():
            if info["type"] == "rectangular":
                update_rectangular_plot(plot_id)
            elif info["type"] == "smith":
                update_smith_chart(plot_id)

    except Exception as e:
        state.add_log("Simulation failed: " + str(e))
    finally:
        state.simulation_running = False
        state.simulation_progress = 1.0
        time.sleep(0.2)

# ---------- File and UI Callbacks ----------
def open_netlist_file_dialog_callback():
    dpg.configure_item("netlist_file_dialog", show=True)

def open_sweep_file_dialog_callback():
    dpg.configure_item("sweep_file_dialog", show=True)

def netlist_file_selected_callback(sender, app_data, user_data):
    state.netlist_path = app_data["file_path_name"]
    dpg.set_value("netlist_path_display", state.netlist_path)
    state.add_log(f"Netlist file set to: {state.netlist_path}")
    with open(state.netlist_path, 'r') as f:
        state.yaml_editor_text = f.read()
        state.yaml_editor_original = state.yaml_editor_text
        dpg.set_value("yaml_editor", state.yaml_editor_text)
        update_diff_preview()

def sweep_file_selected_callback(sender, app_data, user_data):
    state.sweep_config_path = app_data["file_path_name"]
    dpg.set_value("sweep_path_display", state.sweep_config_path)
    state.add_log(f"Sweep config file set to: {state.sweep_config_path}")

def run_simulation_callback():
    if not state.netlist_path or not state.sweep_config_path:
        state.add_log("Error: Please select both netlist and sweep config files.")
        return
    if state.simulation_running:
        state.add_log("Simulation is already running.")
        return
    sim_thread = threading.Thread(target=simulation_thread, daemon=True)
    sim_thread.start()

def update_ui_callback():
    dpg.set_value("progress_bar_tag", state.simulation_progress)
    dpg.set_value("log_text_tag", "\n".join(state.logs[-100:]))
    dpg.set_y_scroll("log_child", 10000)
    update_smith_tooltips()

def update_diff_preview():
    new_text = dpg.get_value("yaml_editor")
    diff = list(difflib.unified_diff(
        state.yaml_editor_original.splitlines(),
        new_text.splitlines(),
        fromfile="original",
        tofile="edited",
        lineterm=""
    ))
    dpg.set_value("yaml_diff", "\n".join(diff))

def apply_yaml_edits_callback():
    new_text = dpg.get_value("yaml_editor")
    with open(state.netlist_path, 'w') as f:
        f.write(new_text)
    state.yaml_editor_text = new_text
    state.yaml_editor_original = new_text
    state.add_log("Netlist YAML updated from editor.")
    update_diff_preview()

# ---------- Global Grey Theme for Smith Chart ----------
GRAY_THEME = None

# ---------- UI Creation ----------
def create_ui():
    global GRAY_THEME
    # Create the grey theme once.
    with dpg.theme() as gray_theme:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (150, 150, 150, 255), category=dpg.mvThemeCat_Plots)
    GRAY_THEME = gray_theme

    with dpg.window(label="Simulation Control", pos=[10, 10], width=400, height=200):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Browse Netlist", callback=open_netlist_file_dialog_callback)
            dpg.add_input_text(label="", readonly=True, width=250, tag="netlist_path_display")
        with dpg.group(horizontal=True):
            dpg.add_button(label="Browse Sweep Config", callback=open_sweep_file_dialog_callback)
            dpg.add_input_text(label="", readonly=True, width=250, tag="sweep_path_display")
        dpg.add_button(label="Run Simulation", callback=run_simulation_callback)
        dpg.add_progress_bar(default_value=0.0, tag="progress_bar_tag", width=300)

    with dpg.window(label="Log Console", pos=[10, 220], width=400, height=200):
        with dpg.child_window(tag="log_child", autosize_x=True, autosize_y=True):
            dpg.add_input_text(multiline=True, readonly=True, tag="log_text_tag", width=-1, height=200)

    with dpg.window(label="Results Viewer", pos=[420, 10], width=420, height=430):
        dpg.add_combo(("Rectangular", "Smith"), label="Plot Type", tag="new_plot_type", default_value="Rectangular")
        dpg.add_button(label="Add New Plot", callback=add_new_plot_tab_callback)
        with dpg.tab_bar(tag="results_tab_bar"):
            pass

    with dpg.window(label="Netlist Editor", pos=[850, 10], width=420, height=450):
        dpg.add_input_text(tag="yaml_editor", multiline=True, width=-1, height=200, default_value="", callback=update_diff_preview)
        dpg.add_button(label="Apply YAML Edits", callback=apply_yaml_edits_callback)
        dpg.add_text("Unsaved Changes Preview:")
        dpg.add_input_text(tag="yaml_diff", multiline=True, readonly=True, width=-1, height=180)

    with dpg.file_dialog(directory_selector=False, show=False, callback=netlist_file_selected_callback,
                         tag="netlist_file_dialog", width=600, height=400):
        dpg.add_file_extension("YAML Files (*.yaml){.yaml}")
        dpg.add_file_extension("YML Files (*.yml){.yml}")

    with dpg.file_dialog(directory_selector=False, show=False, callback=sweep_file_selected_callback,
                         tag="sweep_file_dialog", width=600, height=400):
        dpg.add_file_extension("YAML Files (*.yaml){.yaml}")
        dpg.add_file_extension("YML Files (*.yml){.yml}")

# ---------- Main Application Loop ----------
def main():
    dpg.create_context()
    create_ui()
    dpg.create_viewport(title="RFSim Frontend", width=1300, height=520)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    while dpg.is_dearpygui_running():
        update_ui_callback()
        dpg.render_dearpygui_frame()
    dpg.destroy_context()

if __name__ == "__main__":
    main()
