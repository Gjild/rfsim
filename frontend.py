#!/usr/bin/env python
"""
RFSim Frontend with Dear PyGui (Revised Version)

This version separates configuration, utilities, state management,
simulation, plotting, and UI control into distinct sections for better
maintainability. Type annotations, improved error handling, and clearer
naming conventions have been added.
"""

import threading
import time
import os
import hashlib
import difflib
import numpy as np
import logging
from ruamel.yaml import YAML
import dearpygui.dearpygui as dpg
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils import matrix as mat
from inout.yaml_parser import parse_netlist
from evaluation.sweep import sweep

# =============================================================================
# Configuration & Constants
# =============================================================================

# Plot resolution and grid settings
CIRCLE_RES: int = 500
REACTANCE_RES: int = 2000
UNIT_CIRCLE_CLIP: float = 0.999
RESISTANCE_VALUES: List[float] = [0.2, 0.5, 1, 2, 5]
REACTANCE_VALUES: List[float] = [0.2, 0.5, 1, 2, 5]

# Default expressions for traces
DEFAULT_RECT_EXPR: str = "abs(z_to_s(Z)[1, 0])"
DEFAULT_SMITH_EXPR: str = "s_matrix[0, 0]"

# File dialog dimensions
FILE_DIALOG_WIDTH: int = 600
FILE_DIALOG_HEIGHT: int = 400

# Smith chart size limits
MIN_SMITH_SIZE: int = 100
SMITH_MARGIN: int = 20

# Safe evaluation context for user-supplied expressions
SAFE_EVAL_CONTEXT: Dict[str, Any] = {
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

# =============================================================================
# Logging Setup
# =============================================================================

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# =============================================================================
# Utility Functions
# =============================================================================

def _hash_file(path: str) -> Optional[str]:
    """Compute SHA-256 hash of file contents."""
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def generate_tag(prefix: str, plot_id: str, expr: Optional[str] = None, suffix: Optional[str] = None) -> str:
    """Generate a unique tag for UI items based on a prefix, plot ID, and optionally an expression or suffix."""
    if expr is not None:
        return f"{prefix}_{plot_id}_{hash(expr)}"
    elif suffix is not None:
        return f"{prefix}_{plot_id}_{suffix}"
    else:
        return f"{prefix}_{plot_id}"


def safe_eval_expr(expr: str,
                   simulation_results: Any,
                   is_complex: bool = False,
                   logger_func: Optional[Callable[[str], None]] = None
                   ) -> Optional[Tuple[List[float], List[float]]]:
    """
    Safely evaluate a user-supplied expression using a restricted context.
    
    Returns:
        Tuple containing x_data and y_data lists if successful, or None on failure.
    """
    safe_globals = {"__builtins__": {}, **SAFE_EVAL_CONTEXT}
    x_data: List[float] = []
    y_data: List[float] = []
    
    if simulation_results is None:
        if logger_func:
            logger_func("No simulation results available.")
        return None

    for (freq, _), s_matrix in simulation_results.results.items():
        try:
            # Convert S-parameters to Z-parameters
            Z = mat.s_to_z(s_matrix)
            if is_complex:
                val = eval(expr, safe_globals, {"Z": Z, "freq": freq, "s_matrix": s_matrix})
                x_data.append(val.real)
                y_data.append(val.imag)
            else:
                y_val = eval(expr, safe_globals, {"Z": Z, "freq": freq, "s_matrix": s_matrix})
                x_data.append(freq)
                y_data.append(y_val)
        except Exception as e:
            error_type = "Complex eval" if is_complex else "Eval"
            if logger_func:
                logger_func(f"{error_type} failed at {freq:.3e} Hz: {e}")
            return None
    return x_data, y_data

# =============================================================================
# State Management
# =============================================================================

class StateManager:
    """
    Maintains application state such as file paths, simulation status, logs, and plot metadata.
    """
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.netlist_path: str = ""
        self.sweep_config_path: str = ""
        self.simulation_running: bool = False
        self.simulation_progress: float = 0.0
        self.simulation_results: Any = None
        self.logs: List[str] = []
        # Mapping plot_id -> metadata dictionary
        self.plot_tabs: Dict[str, Dict[str, Any]] = {}
        self._last_netlist_hash: Optional[str] = None
        self._last_sweep_hash: Optional[str] = None
        self.yaml_editor_text: str = ""
        self.yaml_editor_original: str = ""

    def add_log(self, message: str) -> None:
        """Add a log message with a timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        with self.lock:
            self.logs.append(log_message)
        logger.info(message)

    def needs_simulation(self) -> bool:
        """
        Determine if a new simulation is needed based on whether the input files have changed.
        """
        netlist_hash = _hash_file(self.netlist_path)
        sweep_hash = _hash_file(self.sweep_config_path)
        if (netlist_hash != self._last_netlist_hash) or (sweep_hash != self._last_sweep_hash):
            self._last_netlist_hash = netlist_hash
            self._last_sweep_hash = sweep_hash
            return True
        return False

    def set_plot_name(self, plot_id: str, new_name: str) -> None:
        """Rename a plot tab both in state and in the UI."""
        if plot_id in self.plot_tabs:
            self.plot_tabs[plot_id]["name"] = new_name
            dpg.set_item_label(self.plot_tabs[plot_id]["tab_tag"], new_name)
            self.add_log(f"Renamed plot {plot_id} to '{new_name}'")


# =============================================================================
# Simulation Control
# =============================================================================

class SimulationController:
    """
    Controls the simulation process including loading input files, running the sweep,
    and updating the UI after simulation.
    """
    def __init__(self, state: StateManager, ui_controller: 'UIController') -> None:
        self.state = state
        self.ui_controller = ui_controller
        self.yaml_parser = YAML()

    def run_simulation(self) -> None:
        """Run the simulation sweep in a thread-safe manner and update plots upon completion."""
        self.state.simulation_results = None
        self.state.simulation_running = True
        self.state.simulation_progress = 0.0
        self.state.add_log("Simulation started.")
        try:
            if not os.path.exists(self.state.netlist_path):
                raise FileNotFoundError(f"Netlist file not found: {self.state.netlist_path}")
            if not os.path.exists(self.state.sweep_config_path):
                raise FileNotFoundError(f"Sweep config file not found: {self.state.sweep_config_path}")

            if not self.state.needs_simulation():
                self.state.add_log("Input files unchanged, skipping re-simulation.")
                return

            self.state.add_log("Loading netlist...")
            circuit = parse_netlist(self.state.netlist_path)
            circuit.validate(verbose=True)
            self.state.add_log("Netlist loaded and validated.")

            self.state.add_log("Loading sweep configuration...")
            with open(self.state.sweep_config_path, 'r') as f:
                sweep_config_data = self.yaml_parser.load(f)
            self.state.add_log("Sweep configuration loaded.")

            self.state.add_log("Running simulation sweep...")
            result = sweep(circuit, sweep_config_data)
            self.state.simulation_results = result
            self.state.add_log("Simulation completed successfully.")

            # Update plots based on their type.
            for plot_id, info in self.state.plot_tabs.items():
                if info["type"] == "rectangular":
                    self.ui_controller.plot_manager.update_rectangular_plot(plot_id)
                elif info["type"] == "smith":
                    self.ui_controller.plot_manager.update_smith_chart(plot_id)
        except Exception as e:
            self.state.add_log("Simulation failed: " + str(e))
        finally:
            self.state.simulation_running = False
            self.state.simulation_progress = 1.0
            time.sleep(0.2)  # Allow UI updates to process

    def start(self) -> None:
        """Start the simulation in a separate daemon thread."""
        sim_thread = threading.Thread(target=self.run_simulation, daemon=True)
        sim_thread.start()

# =============================================================================
# Plot Management
# =============================================================================

class PlotManager:
    """
    Handles the creation, updating, and drawing of plots and traces.
    """
    def __init__(self, state: StateManager, ui_controller: 'UIController') -> None:
        self.state = state
        self.ui_controller = ui_controller

    def generate_resistance_circle(self, r: float) -> List[Tuple[float, float]]:
        """Generate a resistance circle for the Smith chart."""
        theta = np.linspace(-np.pi, np.pi, CIRCLE_RES)
        c = r / (1 + r)
        rad = 1 / (1 + r)
        x = c + rad * np.cos(theta)
        y = rad * np.sin(theta)
        mask = x**2 + y**2 <= UNIT_CIRCLE_CLIP
        return [(x[i], y[i]) for i in range(len(x)) if mask[i]]

    def generate_reactance_arcs(self, xval: float) -> List[List[Tuple[float, float]]]:
        """Generate reactance arcs for the Smith chart."""
        arcs: List[List[Tuple[float, float]]] = []
        radius = 1 / xval
        theta = np.linspace(-np.pi, np.pi, REACTANCE_RES)
        for s in [+1, -1]:
            x = 1 + radius * np.cos(theta)
            y = s * radius + radius * np.sin(theta)
            mask = x**2 + y**2 <= UNIT_CIRCLE_CLIP
            current_arc: List[Tuple[float, float]] = []
            for i, valid in enumerate(mask):
                if valid:
                    current_arc.append((x[i], y[i]))
                elif current_arc:
                    if len(current_arc) >= 10:
                        arcs.append(current_arc)
                    current_arc = []
            if current_arc and len(current_arc) >= 10:
                arcs.append(current_arc)
        return arcs

    def draw_smith_grid(self, plot_id: str, theme: Any) -> None:
        """Draw the resistance circles and reactance arcs on the Smith chart grid."""
        # Draw resistance circles.
        for r in RESISTANCE_VALUES:
            pts = self.generate_resistance_circle(r)
            if len(pts) >= 2:
                x, y = zip(*pts)
                tag = generate_tag("grid_res_circle", plot_id, suffix=str(r))
                dpg.add_line_series(x, y, parent=f"y_axis_{plot_id}", tag=tag)
                dpg.bind_item_theme(tag, theme)
        # Draw reactance arcs.
        for x_val in REACTANCE_VALUES:
            arcs = self.generate_reactance_arcs(x_val)
            for i, arc in enumerate(arcs):
                if len(arc) >= 2:
                    x, y = zip(*arc)
                    tag = generate_tag("grid_react_arc", plot_id, suffix=f"{x_val}_{i}")
                    dpg.add_line_series(x, y, parent=f"y_axis_{plot_id}", tag=tag)
                    dpg.bind_item_theme(tag, theme)

    def add_trace(self, plot_id: str, expr: str, is_complex: bool) -> None:
        """
        Add a new trace to a plot, evaluating its data using safe_eval_expr.
        """
        tag_prefix = "smith_trace" if is_complex else "trace"
        tag = generate_tag(tag_prefix, plot_id, expr=expr)
        result = safe_eval_expr(expr, self.state.simulation_results, is_complex=is_complex, logger_func=self.state.add_log)
        if result is None:
            return
        x_data, y_data = result
        dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
        dpg.fit_axis_data(f"y_axis_{plot_id}")
        kind = "Smith" if is_complex else "rectangular"
        self.state.add_log(f"Added {kind} trace '{expr}' to plot {plot_id}")

    def update_rectangular_plot(self, plot_id: str) -> None:
        """Update all traces in a rectangular plot based on simulation results."""
        for expr in self.state.plot_tabs[plot_id]["traces"]:
            tag = generate_tag("trace", plot_id, expr=expr)
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            result = safe_eval_expr(expr, self.state.simulation_results, is_complex=False, logger_func=self.state.add_log)
            if result is None:
                continue
            x_data, y_data = result
            dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
        dpg.fit_axis_data(f"y_axis_{plot_id}")
        self.state.add_log(f"Updated rectangular plot {plot_id}")

    def update_smith_chart(self, plot_id: str) -> None:
        """Update all traces in a Smith chart based on simulation results."""
        for expr in self.state.plot_tabs[plot_id]["traces"]:
            tag = generate_tag("smith_trace", plot_id, expr=expr)
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            result = safe_eval_expr(expr, self.state.simulation_results, is_complex=True, logger_func=self.state.add_log)
            if result is None:
                continue
            x_data, y_data = result
            dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
        dpg.fit_axis_data(f"y_axis_{plot_id}")
        self.state.add_log(f"Updated Smith chart plot {plot_id}")

    def reset_zoom(self, plot_id: str) -> None:
        """Reset the zoom level for a Smith chart plot."""
        dpg.set_axis_limits(f"x_axis_{plot_id}", -1.1, 1.1)
        dpg.set_axis_limits(f"y_axis_{plot_id}", -1.1, 1.1)
        self.state.add_log(f"Reset zoom for Smith chart plot {plot_id}")

# =============================================================================
# UI Controller
# =============================================================================

class UIController:
    """
    Manages the Dear PyGui UI including callbacks, layout, and periodic updates.
    """
    def __init__(self, state: StateManager) -> None:
        self.state = state
        self.gray_theme: Optional[int] = None
        self.plot_manager = PlotManager(state, self)
        self.simulation_controller = SimulationController(state, self)

    # ---------------------------
    # Callback Functions
    # ---------------------------

    def rename_plot_callback(self, sender: str, app_data: str, user_data: str) -> None:
        """Callback to rename a plot based on user input."""
        plot_id = user_data
        new_name = app_data.strip()
        if new_name:
            self.state.set_plot_name(plot_id, new_name)
        else:
            self.state.add_log("Plot name cannot be empty.")

    def update_trace_callback(self, sender: str, app_data: Any, user_data: Tuple[str, int]) -> None:
        """Callback to update an existing trace with a new expression."""
        plot_id, idx = user_data
        input_tag = f"trace_input_{plot_id}_{idx}"
        new_expr = dpg.get_value(input_tag).strip()
        if not new_expr:
            self.state.add_log("Updated expression is empty.")
            return
        old_expr = self.state.plot_tabs[plot_id]["traces"][idx]
        if new_expr == old_expr:
            self.state.add_log("Expression unchanged.")
            return

        # Remove old trace and add the new one.
        if self.state.plot_tabs[plot_id]["type"] == "rectangular":
            tag = generate_tag("trace", plot_id, expr=old_expr)
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            self.state.plot_tabs[plot_id]["traces"][idx] = new_expr
            self.plot_manager.add_trace(plot_id, new_expr, is_complex=False)
        elif self.state.plot_tabs[plot_id]["type"] == "smith":
            tag = generate_tag("smith_trace", plot_id, expr=old_expr)
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            self.state.plot_tabs[plot_id]["traces"][idx] = new_expr
            self.plot_manager.add_trace(plot_id, new_expr, is_complex=True)
        self.state.add_log(f"Updated trace in plot {plot_id} at index {idx}.")
        self._update_trace_list(plot_id)

    def remove_trace_callback(self, sender: str, app_data: Any, user_data: Tuple[str, int]) -> None:
        """Callback to remove a trace from a plot."""
        plot_id, idx = user_data
        expr = self.state.plot_tabs[plot_id]["traces"][idx]
        tag_prefix = "smith_trace" if self.state.plot_tabs[plot_id]["type"] == "smith" else "trace"
        tag = generate_tag(tag_prefix, plot_id, expr=expr)
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
        del self.state.plot_tabs[plot_id]["traces"][idx]
        self.state.add_log(f"Removed trace from plot {plot_id} at index {idx}.")
        self._update_trace_list(plot_id)

    def _update_trace_list(self, plot_id: str) -> None:
        """
        Refresh the list of trace input fields in the UI for a given plot.
        This method recreates the trace list UI elements.
        """
        list_tag = f"trace_list_{plot_id}"
        if dpg.does_item_exist(list_tag):
            dpg.delete_item(list_tag, children_only=True)
        with dpg.group(parent=list_tag):
            for idx, expr in enumerate(self.state.plot_tabs[plot_id]["traces"]):
                with dpg.group(horizontal=True):
                    input_tag = f"trace_input_{plot_id}_{idx}"
                    dpg.add_input_text(label="", default_value=expr, width=250, tag=input_tag)
                    dpg.add_button(label="Update", user_data=(plot_id, idx), callback=self.update_trace_callback)
                    dpg.add_button(label="Remove", user_data=(plot_id, idx), callback=self.remove_trace_callback)

    def plot_expression_callback(self, sender: str, app_data: Any, plot_id: str) -> None:
        """Callback to add a new rectangular trace to a plot."""
        input_tag = f"expression_input_{plot_id}"
        expr = dpg.get_value(input_tag).strip()
        if not expr:
            self.state.add_log("Empty expression.")
            return
        if expr in self.state.plot_tabs[plot_id]["traces"]:
            self.state.add_log(f"Expression already plotted in plot {plot_id}: {expr}")
            return
        self.state.plot_tabs[plot_id]["traces"].append(expr)
        self.plot_manager.add_trace(plot_id, expr, is_complex=False)
        self._update_trace_list(plot_id)

    def smith_expression_callback(self, sender: str, app_data: Any, plot_id: str) -> None:
        """Callback to add a new Smith chart trace to a plot."""
        input_tag = f"smith_expr_input_{plot_id}"
        expr = dpg.get_value(input_tag).strip()
        if not expr:
            self.state.add_log("Empty smith expression.")
            return
        if expr in self.state.plot_tabs[plot_id]["traces"]:
            self.state.add_log(f"Expression already plotted in smith chart {plot_id}: {expr}")
            return
        self.state.plot_tabs[plot_id]["traces"].append(expr)
        self.plot_manager.add_trace(plot_id, expr, is_complex=True)
        self._update_trace_list(plot_id)

    def netlist_file_selected_callback(self, sender: str, app_data: Dict[str, Any], user_data: Any) -> None:
        """Callback when a netlist file is selected."""
        self.state.netlist_path = app_data["file_path_name"]
        dpg.set_value("netlist_path_display", self.state.netlist_path)
        self.state.add_log(f"Netlist file set to: {self.state.netlist_path}")
        try:
            with open(self.state.netlist_path, 'r') as f:
                self.state.yaml_editor_text = f.read()
                self.state.yaml_editor_original = self.state.yaml_editor_text
                dpg.set_value("yaml_editor", self.state.yaml_editor_text)
                self.update_diff_preview()
        except Exception as e:
            self.state.add_log(f"Failed to load netlist file: {e}")

    def sweep_file_selected_callback(self, sender: str, app_data: Dict[str, Any], user_data: Any) -> None:
        """Callback when a sweep configuration file is selected."""
        self.state.sweep_config_path = app_data["file_path_name"]
        dpg.set_value("sweep_path_display", self.state.sweep_config_path)
        self.state.add_log(f"Sweep config file set to: {self.state.sweep_config_path}")

    def update_diff_preview(self) -> None:
        """Update the diff preview for the YAML editor."""
        new_text = dpg.get_value("yaml_editor")
        diff = list(difflib.unified_diff(
            self.state.yaml_editor_original.splitlines(),
            new_text.splitlines(),
            fromfile="original",
            tofile="edited",
            lineterm=""
        ))
        dpg.set_value("yaml_diff", "\n".join(diff))

    def apply_yaml_edits_callback(self) -> None:
        """Apply the changes made in the YAML editor to the netlist file."""
        new_text = dpg.get_value("yaml_editor")
        try:
            with open(self.state.netlist_path, 'w') as f:
                f.write(new_text)
            self.state.yaml_editor_text = new_text
            self.state.yaml_editor_original = new_text
            self.state.add_log("Netlist YAML updated from editor.")
            self.update_diff_preview()
        except Exception as e:
            self.state.add_log(f"Failed to apply YAML edits: {e}")

    def update_smith_tooltips(self) -> None:
        """Update the hover tooltip for Smith charts to show the current mouse position."""
        for plot_id, info in self.state.plot_tabs.items():
            if info["type"] == "smith":
                tag = f"hover_info_{plot_id}"
                if dpg.does_item_exist(tag) and dpg.is_item_hovered(f"plot_{plot_id}"):
                    x, y = dpg.get_plot_mouse_pos()
                    dpg.set_value(tag, f"Γ = {x:.3f} + j{y:.3f}")

    def update_ui(self) -> None:
        """Periodically update UI elements such as progress bar, log console, and Smith chart sizes."""
        dpg.set_value("progress_bar_tag", self.state.simulation_progress)
        dpg.set_value("log_text_tag", "\n".join(self.state.logs[-100:]))
        dpg.set_y_scroll("log_child", 10000)
        self.update_smith_tooltips()
        # Dynamically adjust Smith chart sizes.
        for plot_id, info in self.state.plot_tabs.items():
            if info["type"] == "smith":
                try:
                    container_width, container_height = dpg.get_item_rect_size(f"plot_container_{plot_id}")
                    size = max(min(container_width, container_height) - SMITH_MARGIN, MIN_SMITH_SIZE)
                    dpg.set_item_width(f"plot_{plot_id}", size)
                    dpg.set_item_height(f"plot_{plot_id}", size)
                    pad = max(0, (container_width - size) // 2)
                    dpg.set_item_width(f"smith_left_spacer_{plot_id}", pad)
                    dpg.set_item_width(f"smith_right_spacer_{plot_id}", pad)
                except Exception:
                    pass

    # ---------------------------
    # UI Layout Creation
    # ---------------------------

    def create_sidebar(self) -> None:
        """Create the sidebar UI elements for simulation control and YAML editing."""
        with dpg.child_window(tag="sidebar", width=380, autosize_y=True, border=True):
            with dpg.collapsing_header(label="Simulation Control", default_open=True):
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Browse Netlist", callback=lambda s, a: self.open_netlist_file_dialog())
                    dpg.add_input_text(label="", readonly=True, width=250, tag="netlist_path_display")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Browse Sweep Config", callback=lambda s, a: self.open_sweep_file_dialog())
                    dpg.add_input_text(label="", readonly=True, width=250, tag="sweep_path_display")
                dpg.add_button(label="Run Simulation", callback=lambda s, a: self.simulation_controller.start())
                dpg.add_progress_bar(default_value=0.0, tag="progress_bar_tag", width=300)
            with dpg.collapsing_header(label="Netlist Editor", default_open=True):
                dpg.add_input_text(tag="yaml_editor", multiline=True, width=-1, height=200,
                                   default_value="", callback=lambda s, a: self.update_diff_preview())
                dpg.add_button(label="Apply YAML Edits", callback=lambda s, a: self.apply_yaml_edits_callback())
                dpg.add_text("Unsaved Changes Preview:")
                dpg.add_input_text(tag="yaml_diff", multiline=True, readonly=True, width=-1, height=180)

    def create_main_work_area(self) -> None:
        """Create the main work area for adding and viewing plots."""
        with dpg.child_window(tag="main_work_area", autosize_x=True, autosize_y=True, border=True):
            with dpg.group():
                with dpg.group(horizontal=True):
                    dpg.add_combo(("Rectangular", "Smith"), tag="new_plot_type", default_value="Rectangular", width=150)
                    dpg.add_button(label="Add New Plot", callback=self.add_new_plot_tab_callback)
                with dpg.tab_bar(tag="results_tab_bar"):
                    pass

    def create_log_console(self) -> None:
        """Create the log console UI elements."""
        with dpg.child_window(tag="log_console", height=140, autosize_x=True, border=True):
            dpg.add_text("Log Console")
            with dpg.child_window(tag="log_child", autosize_x=True, autosize_y=True):
                dpg.add_input_text(multiline=True, readonly=True, tag="log_text_tag", width=-1, height=120)

    def create_file_dialogs(self) -> None:
        """Create file dialogs for netlist and sweep config selection."""
        with dpg.file_dialog(directory_selector=False, show=False, callback=self.netlist_file_selected_callback,
                             tag="netlist_file_dialog", width=FILE_DIALOG_WIDTH, height=FILE_DIALOG_HEIGHT):
            dpg.add_file_extension("YAML Files (*.yaml){.yaml}")
            dpg.add_file_extension("YML Files (*.yml){.yml}")
        with dpg.file_dialog(directory_selector=False, show=False, callback=self.sweep_file_selected_callback,
                             tag="sweep_file_dialog", width=FILE_DIALOG_WIDTH, height=FILE_DIALOG_HEIGHT):
            dpg.add_file_extension("YAML Files (*.yaml){.yaml}")
            dpg.add_file_extension("YML Files (*.yml){.yml}")

    def open_netlist_file_dialog(self) -> None:
        """Open the netlist file dialog."""
        dpg.configure_item("netlist_file_dialog", show=True)

    def open_sweep_file_dialog(self) -> None:
        """Open the sweep config file dialog."""
        dpg.configure_item("sweep_file_dialog", show=True)

    def add_new_plot_tab_callback(self, sender: str, app_data: Any) -> None:
        """Callback to add a new plot tab based on the selected plot type."""
        plot_type = dpg.get_value("new_plot_type").lower()
        self.add_new_plot_tab(plot_type)

    def add_new_plot_tab(self, plot_type: str, initial_expression: Optional[str] = None) -> None:
        """Create and initialize a new plot tab."""
        plot_id = str(int(time.time() * 1000))
        tab_tag = f"tab_{plot_id}"
        plot_name = "Rectangular Plot" if plot_type == "rectangular" else "Smith Chart"

        with dpg.tab(label=plot_name, tag=tab_tag, parent="results_tab_bar"):
            if plot_type == "smith":
                dpg.add_button(label="Reset Zoom", user_data=plot_id,
                               callback=lambda s, a, u=plot_id: self.plot_manager.reset_zoom(u))
            with dpg.group(horizontal=True):
                with dpg.group():
                    dpg.add_input_text(
                        label="Plot Name",
                        default_value=plot_name,
                        user_data=plot_id,
                        callback=self.rename_plot_callback,
                        tag=f"plot_name_input_{plot_id}",
                        width=250
                    )
                    with dpg.group(horizontal=True):
                        if plot_type == "rectangular":
                            dpg.add_button(label="Add Trace", user_data=plot_id, callback=lambda s, a, u=plot_id: self.plot_expression_callback(s, a, u))
                            dpg.add_input_text(
                                label="Plot Expression",
                                default_value=DEFAULT_RECT_EXPR,
                                tag=f"expression_input_{plot_id}",
                                width=300
                            )
                        elif plot_type == "smith":
                            dpg.add_button(label="Add Trace", user_data=plot_id, callback=lambda s, a, u=plot_id: self.smith_expression_callback(s, a, u))
                            dpg.add_input_text(
                                label="Expression",
                                default_value=DEFAULT_SMITH_EXPR,
                                tag=f"smith_expr_input_{plot_id}",
                                width=300
                            )
                with dpg.group(tag=f"trace_list_group_{plot_id}"):
                    with dpg.child_window(tag=f"trace_list_{plot_id}", autosize_x=True, height=120):
                        pass

            if plot_type == "rectangular":
                with dpg.child_window(tag=f"plot_container_{plot_id}", autosize_x=True, autosize_y=True):
                    with dpg.plot(label="Rectangular Plot", tag=f"plot_{plot_id}", height=-1, width=-1):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency (Hz)", tag=f"x_axis_{plot_id}")
                        dpg.add_plot_axis(dpg.mvYAxis, label="Y Axis", tag=f"y_axis_{plot_id}")
            elif plot_type == "smith":
                with dpg.child_window(tag=f"plot_container_{plot_id}", autosize_x=True, autosize_y=True):
                    with dpg.group(horizontal=True, tag=f"smith_wrapper_{plot_id}"):
                        dpg.add_spacer(tag=f"smith_left_spacer_{plot_id}", width=0)
                        with dpg.group(tag=f"smith_chart_group_{plot_id}"):
                            with dpg.plot(label="Smith Chart", tag=f"plot_{plot_id}", equal_aspects=True, height=400, width=400):
                                dpg.add_plot_legend()
                                dpg.add_plot_axis(dpg.mvXAxis, label="Re", tag=f"x_axis_{plot_id}", no_gridlines=True)
                                dpg.add_plot_axis(dpg.mvYAxis, label="Im", tag=f"y_axis_{plot_id}", no_gridlines=True)
                            self.plot_manager.draw_smith_grid(plot_id, self.gray_theme)
                        dpg.add_spacer(tag=f"smith_right_spacer_{plot_id}", width=0)

        # Save plot tab metadata in state.
        self.state.plot_tabs[plot_id] = {
            "type": plot_type,
            "traces": [] if initial_expression is None else [initial_expression],
            "tab_tag": tab_tag,
            "name": plot_name
        }
        # If an initial expression was provided for a rectangular plot, add it immediately.
        if plot_type == "rectangular" and initial_expression is not None:
            self.plot_manager.add_trace(plot_id, initial_expression, is_complex=False)
            self._update_trace_list(plot_id)
        self.state.add_log(f"Added new {plot_type} plot tab with id {plot_id}")

    def create_ui(self) -> None:
        """Assemble the full UI layout."""
        # Create a consistent grey theme for plots.
        with dpg.theme() as self.gray_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (150, 150, 150, 255), category=dpg.mvThemeCat_Plots)
        with dpg.window(tag="root_window", label="RFSim UI", no_title_bar=True, no_resize=True, no_move=True, no_close=True):
            dpg.set_primary_window("root_window", True)
            with dpg.group(horizontal=True):
                self.create_sidebar()
                self.create_main_work_area()
            self.create_log_console()
        self.create_file_dialogs()

    def main_loop(self) -> None:
        """Initialize the Dear PyGui context and run the main UI loop."""
        dpg.create_context()
        self.create_ui()
        dpg.create_viewport(title="RFSim Frontend", width=1400, height=800)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        while dpg.is_dearpygui_running():
            vp_width, vp_height = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
            dpg.set_item_width("root_window", vp_width)
            dpg.set_item_height("root_window", vp_height - 10)
            self.update_ui()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()

# =============================================================================
# Main Application Entry Point
# =============================================================================

def main() -> None:
    state = StateManager()
    ui_controller = UIController(state)
    ui_controller.main_loop()


if __name__ == "__main__":
    main()
