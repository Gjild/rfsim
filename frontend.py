import threading
import time
import os
import hashlib
import difflib
from ruamel.yaml import YAML
from inout.yaml_parser import parse_netlist
from evaluation.sweep import sweep
import dearpygui.dearpygui as dpg
import numpy as np
from utils import matrix as mat

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


class StateManager:
    def __init__(self):
        self.netlist_path = ""
        self.sweep_config_path = ""
        self.simulation_running = False
        self.simulation_progress = 0.0
        self.simulation_results = None
        self.logs = []
        self.plots = {}
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


def _evaluate_expression(expr):
    x_data, y_data = [], []
    safe_globals = {"__builtins__": {}, **SAFE_EVAL_CONTEXT}
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


def _replot_expression(expr):
    tag = state.plots.get(expr)
    if tag and dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    x_data, y_data = _evaluate_expression(expr)
    if x_data is None:
        return
    tag = f"plot_{hash(expr)}"
    dpg.add_line_series(x_data, y_data, label=expr, parent="results_y_axis", tag=tag)
    state.plots[expr] = tag
    dpg.fit_axis_data("results_y_axis")
    _update_expression_list()


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

        for expr in list(state.plots.keys()):
            _replot_expression(expr)

    except Exception as e:
        state.add_log("Simulation failed: " + str(e))
    finally:
        state.simulation_running = False
        state.simulation_progress = 1.0
        time.sleep(0.2)


def plot_expression_callback():
    if not state.simulation_results:
        state.add_log("No simulation results to plot.")
        return

    expr = dpg.get_value("expression_input").strip()
    if not expr:
        state.add_log("Empty expression.")
        return
    if expr in state.plots:
        state.add_log(f"Expression already plotted: {expr}")
        return

    x_data, y_data = _evaluate_expression(expr)
    if x_data is None:
        return

    tag = f"plot_{hash(expr)}"
    dpg.add_line_series(x_data, y_data, label=expr, parent="results_y_axis", tag=tag)
    state.plots[expr] = tag
    dpg.fit_axis_data("results_y_axis")
    _update_expression_list()


def _update_expression_list():
    if dpg.does_item_exist("expression_list"):
        dpg.delete_item("expression_list", children_only=True)

    for expr in list(state.plots.keys()):
        with dpg.group(horizontal=True, parent="expression_list"):
            dpg.add_text(expr, tag=f"expr_text_{hash(expr)}")
            dpg.add_button(label="Remove", width=60, user_data=expr, callback=_remove_expression)


def _remove_expression(sender, app_data, user_data):
    expr = user_data
    tag = state.plots.get(expr)
    if tag and dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    state.plots.pop(expr, None)
    state.add_log(f"Removed: {expr}")
    _update_expression_list()


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


def create_ui():
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
        with dpg.group(horizontal=True):
            dpg.add_input_text(label="Plot Expression", default_value="abs(z_to_s(Z)[1, 0])", tag="expression_input", width=300)
            dpg.add_button(label="Plot", callback=plot_expression_callback)
        dpg.add_text("Plotted Expressions:")
        with dpg.child_window(tag="expression_list", height=60, width=-1):
            pass
        with dpg.child_window(tag="results_child", autosize_x=True, autosize_y=True):
            with dpg.plot(label="Expression Plot", height=-1, width=-1):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Frequency (Hz)")
                dpg.add_plot_axis(dpg.mvYAxis, label="Y Axis (Expression Result)", tag="results_y_axis")

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
