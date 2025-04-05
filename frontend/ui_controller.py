# frontend/ui_controller.py
import time
from typing import Any, Tuple, Optional

import dearpygui.dearpygui as dpg

from frontend.states import StateManager, PlotTab
from frontend.plots import PlotManager, DEFAULT_RECT_EXPR, DEFAULT_SMITH_EXPR
from frontend.sim import SimulationController
from utils.tags import TagRegistry

# UI layout constants.
FILE_DIALOG_WIDTH = 600
FILE_DIALOG_HEIGHT = 400
MIN_SMITH_SIZE = 100
SMITH_MARGIN = 20

class UIController:
    """
    Manages the Dear PyGui UI including callbacks, layout creation,
    and periodic updates.
    """
    def __init__(self, state: StateManager) -> None:
        self.state = state
        self.gray_theme: Optional[int] = None
        self.plot_manager = PlotManager(state, self)
        self.simulation_controller = SimulationController(state, self)

    # --- Callback Functions ---
    def rename_plot_callback(self, sender: str, app_data: str, user_data: str) -> None:
        plot_id = user_data
        new_name = app_data.strip()
        if new_name:
            if plot_id in self.state.plot_tabs:
                self.state.plot_tabs[plot_id].name = new_name
                dpg.set_item_label(self.state.plot_tabs[plot_id].tab_tag, new_name)
                self.state.add_log(f"Renamed plot {plot_id} to '{new_name}'")
        else:
            self.state.add_log("Plot name cannot be empty.")

    def update_trace_callback(self, sender: str, app_data: Any, user_data: Tuple[str, int]) -> None:
        plot_id, idx = user_data
        input_tag = f"trace_input_{plot_id}_{idx}"
        new_expr = dpg.get_value(input_tag).strip()
        if not new_expr:
            self.state.add_log("Updated expression is empty.")
            return
        old_expr = self.state.plot_tabs[plot_id].traces[idx]
        if new_expr == old_expr:
            self.state.add_log("Expression unchanged.")
            return

        tag_prefix = "smith_trace" if self.state.plot_tabs[plot_id].type == "smith" else "trace"
        old_tag = TagRegistry.generate_tag(tag_prefix, plot_id, identifier=old_expr)
        if dpg.does_item_exist(old_tag):
            dpg.delete_item(old_tag)
        self.state.update_plot_trace(plot_id, idx, new_expr)
        self.plot_manager.add_trace(plot_id, new_expr, is_complex=(self.state.plot_tabs[plot_id].type == "smith"))
        self.state.add_log(f"Updated trace in plot {plot_id} at index {idx}.")
        self._update_trace_list(plot_id)

    def remove_trace_callback(self, sender: str, app_data: Any, user_data: Tuple[str, int]) -> None:
        plot_id, idx = user_data
        expr = self.state.plot_tabs[plot_id].traces[idx]
        tag_prefix = "smith_trace" if self.state.plot_tabs[plot_id].type == "smith" else "trace"
        tag = TagRegistry.generate_tag(tag_prefix, plot_id, identifier=expr)
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
        self.state.remove_plot_trace(plot_id, idx)
        self.state.add_log(f"Removed trace from plot {plot_id} at index {idx}.")
        self._update_trace_list(plot_id)

    def _update_trace_list(self, plot_id: str) -> None:
        list_tag = f"trace_list_{plot_id}"
        if dpg.does_item_exist(list_tag):
            dpg.delete_item(list_tag, children_only=True)
        with dpg.group(parent=list_tag):
            for idx, expr in enumerate(self.state.plot_tabs[plot_id].traces):
                with dpg.group(horizontal=True):
                    input_tag = f"trace_input_{plot_id}_{idx}"
                    dpg.add_input_text(label="", default_value=expr, width=250, tag=input_tag)
                    dpg.add_button(label="Update", user_data=(plot_id, idx), callback=self.update_trace_callback)
                    dpg.add_button(label="Remove", user_data=(plot_id, idx), callback=self.remove_trace_callback)

    def plot_expression_callback(self, sender: str, app_data: Any, plot_id: str) -> None:
        input_tag = f"expression_input_{plot_id}"
        expr = dpg.get_value(input_tag).strip()
        if not expr:
            self.state.add_log("Empty expression.")
            return
        if expr in self.state.plot_tabs[plot_id].traces:
            self.state.add_log(f"Expression already plotted in plot {plot_id}: {expr}")
            return
        self.state.add_plot_trace(plot_id, expr)
        self.plot_manager.add_trace(plot_id, expr, is_complex=False)
        self._update_trace_list(plot_id)

    def smith_expression_callback(self, sender: str, app_data: Any, plot_id: str) -> None:
        input_tag = f"smith_expr_input_{plot_id}"
        expr = dpg.get_value(input_tag).strip()
        if not expr:
            self.state.add_log("Empty smith expression.")
            return
        if expr in self.state.plot_tabs[plot_id].traces:
            self.state.add_log(f"Expression already plotted in smith chart {plot_id}: {expr}")
            return
        self.state.add_plot_trace(plot_id, expr)
        self.plot_manager.add_trace(plot_id, expr, is_complex=True)
        self._update_trace_list(plot_id)

    def netlist_file_selected_callback(self, sender: str, app_data: dict, user_data: Any) -> None:
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

    def sweep_file_selected_callback(self, sender: str, app_data: dict, user_data: Any) -> None:
        self.state.sweep_config_path = app_data["file_path_name"]
        dpg.set_value("sweep_path_display", self.state.sweep_config_path)
        self.state.add_log(f"Sweep config file set to: {self.state.sweep_config_path}")

    def update_diff_preview(self) -> None:
        new_text = dpg.get_value("yaml_editor")
        import difflib
        diff = list(difflib.unified_diff(
            self.state.yaml_editor_original.splitlines(),
            new_text.splitlines(),
            fromfile="original",
            tofile="edited",
            lineterm=""
        ))
        dpg.set_value("yaml_diff", "\n".join(diff))

    def apply_yaml_edits_callback(self) -> None:
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
        for plot_id, plot_tab in self.state.plot_tabs.items():
            if plot_tab.type == "smith":
                tag = f"hover_info_{plot_id}"
                if dpg.does_item_exist(tag) and dpg.is_item_hovered(f"plot_{plot_id}"):
                    x, y = dpg.get_plot_mouse_pos()
                    dpg.set_value(tag, f"Γ = {x:.3f} + j{y:.3f}")

    def update_ui(self) -> None:
        dpg.set_value("progress_bar_tag", self.state.simulation_progress)
        dpg.set_value("log_text_tag", "\n".join(self.state.logs[-100:]))
        dpg.set_y_scroll("log_child", 10000)
        self.update_smith_tooltips()
        for plot_id, plot_tab in self.state.plot_tabs.items():
            if plot_tab.type == "smith":
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

    # --- UI Layout Creation ---
    def create_sidebar(self) -> None:
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
        with dpg.child_window(tag="main_work_area", autosize_x=True, autosize_y=True, border=True):
            with dpg.group():
                with dpg.group(horizontal=True):
                    dpg.add_combo(("Rectangular", "Smith"), tag="new_plot_type", default_value="Rectangular", width=150)
                    dpg.add_button(label="Add New Plot", callback=self.add_new_plot_tab_callback)
                with dpg.tab_bar(tag="results_tab_bar"):
                    pass

    def create_log_console(self) -> None:
        with dpg.child_window(tag="log_console", height=140, autosize_x=True, border=True):
            dpg.add_text("Log Console")
            with dpg.child_window(tag="log_child", autosize_x=True, autosize_y=True):
                dpg.add_input_text(multiline=True, readonly=True, tag="log_text_tag", width=-1, height=120)

    def create_file_dialogs(self) -> None:
        with dpg.file_dialog(directory_selector=False, show=False, callback=self.netlist_file_selected_callback,
                             tag="netlist_file_dialog", width=FILE_DIALOG_WIDTH, height=FILE_DIALOG_HEIGHT):
            dpg.add_file_extension("YAML Files (*.yaml){.yaml}")
            dpg.add_file_extension("YML Files (*.yml){.yml}")
        with dpg.file_dialog(directory_selector=False, show=False, callback=self.sweep_file_selected_callback,
                             tag="sweep_file_dialog", width=FILE_DIALOG_WIDTH, height=FILE_DIALOG_HEIGHT):
            dpg.add_file_extension("YAML Files (*.yaml){.yaml}")
            dpg.add_file_extension("YML Files (*.yml){.yml}")

    def open_netlist_file_dialog(self) -> None:
        dpg.configure_item("netlist_file_dialog", show=True)

    def open_sweep_file_dialog(self) -> None:
        dpg.configure_item("sweep_file_dialog", show=True)

    def add_new_plot_tab_callback(self, sender: str, app_data: Any) -> None:
        plot_type = dpg.get_value("new_plot_type").lower()
        self.add_new_plot_tab(plot_type)

    def add_new_plot_tab(self, plot_type: str, initial_expression: Optional[str] = None) -> None:
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
        self.state.plot_tabs[plot_id] = PlotTab(id=plot_id, name=plot_name, type=plot_type, tab_tag=tab_tag)
        if plot_type == "rectangular" and initial_expression is not None:
            self.plot_manager.add_trace(plot_id, initial_expression, is_complex=False)
            self._update_trace_list(plot_id)
        self.state.add_log(f"Added new {plot_type} plot tab with id {plot_id}")

    def create_ui(self) -> None:
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
