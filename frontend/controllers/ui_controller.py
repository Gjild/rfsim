# frontend/controllers/ui_controller.py
import time
import dearpygui.dearpygui as dpg
from typing import Any, Optional
from frontend.models.state import StateManager, PlotTab, PlotType
from frontend.controllers.simulation_controller import SimulationController
from frontend.controllers.plot_controller import PlotController
from frontend.views.layout_builder import LayoutBuilder
from frontend.utils.constants import DEFAULT_RECT_EXPR, DEFAULT_SMITH_EXPR
from frontend.utils.tag_factory import TagFactory

class UIController:
    """
    Coordinates UI events and delegates actions to appropriate controllers.
    """
    def __init__(self, state: StateManager) -> None:
        self.state = state
        self.layout_builder = LayoutBuilder(self)
        self.plot_controller = PlotController(state)
        self.simulation_controller = SimulationController(state, self.refresh_plots)
        self.gray_theme: Optional[int] = None

    def refresh_plots(self) -> None:
        # Refresh all plot tabs based on their type.
        for plot_id, plot_tab in self.state.plot_tabs.items():
            if plot_tab.type == PlotType.RECTANGULAR:
                self.plot_controller.update_plot(plot_id, PlotType.RECTANGULAR)
            elif plot_tab.type == PlotType.SMITH:
                self.plot_controller.update_plot(plot_id, PlotType.SMITH)

    def run(self) -> None:
        dpg.create_context()
        self.layout_builder.build_ui()
        dpg.create_viewport(title="RFSim Frontend", width=1400, height=800)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        while dpg.is_dearpygui_running():
            vp_width, vp_height = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
            dpg.set_item_width("root_window", vp_width)
            dpg.set_item_height("root_window", vp_height - 10)
            self.layout_builder.update_ui()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()

    # Callback implementations:

    def rename_plot(self, sender: str, app_data: str, plot_id: str) -> None:
        new_name = app_data.strip()
        if new_name and plot_id in self.state.plot_tabs:
            self.state.plot_tabs[plot_id].name = new_name
            dpg.set_item_label(self.state.plot_tabs[plot_id].tab_tag, new_name)
            self.state.add_log(f"Renamed plot {plot_id} to '{new_name}'")
        else:
            self.state.add_log("Plot name cannot be empty.")

    def update_trace(self, sender: str, app_data: Any, user_data: tuple) -> None:
        plot_id, idx = user_data
        input_tag = TagFactory.get_trace_input_tag(plot_id, idx)
        new_expr = dpg.get_value(input_tag).strip()
        if not new_expr:
            self.state.add_log("Updated expression is empty.")
            return
        old_expr = self.state.plot_tabs[plot_id].traces[idx]
        if new_expr == old_expr:
            self.state.add_log("Expression unchanged.")
            return

        tag_prefix = "smith_trace" if self.state.plot_tabs[plot_id].type == PlotType.SMITH else "trace"
        old_tag = TagFactory.generate_tag(tag_prefix, plot_id, identifier=old_expr)
        if dpg.does_item_exist(old_tag):
            dpg.delete_item(old_tag)
        self.state.update_plot_trace(plot_id, idx, new_expr)
        is_complex = (self.state.plot_tabs[plot_id].type == PlotType.SMITH)
        self.plot_controller.add_trace(plot_id, new_expr, is_complex=is_complex)
        self.state.add_log(f"Updated trace in plot {plot_id} at index {idx}.")
        self._refresh_trace_list(plot_id)

    def remove_trace(self, sender: str, app_data: Any, user_data: tuple) -> None:
        plot_id, idx = user_data
        expr = self.state.plot_tabs[plot_id].traces[idx]
        tag_prefix = "smith_trace" if self.state.plot_tabs[plot_id].type == PlotType.SMITH else "trace"
        tag = TagFactory.generate_tag(tag_prefix, plot_id, identifier=expr)
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
        self.state.remove_plot_trace(plot_id, idx)
        self.state.add_log(f"Removed trace from plot {plot_id} at index {idx}.")
        self._refresh_trace_list(plot_id)

    def _refresh_trace_list(self, plot_id: str) -> None:
        list_tag = f"trace_list_{plot_id}"
        if dpg.does_item_exist(list_tag):
            dpg.delete_item(list_tag, children_only=True)
        with dpg.group(parent=list_tag):
            for idx, expr in enumerate(self.state.plot_tabs[plot_id].traces):
                with dpg.group(horizontal=True):
                    input_tag = TagFactory.get_trace_input_tag(plot_id, idx)
                    dpg.add_input_text(label="", default_value=expr, width=250, tag=input_tag)
                    dpg.add_button(label="Update", user_data=(plot_id, idx), callback=self.update_trace)
                    dpg.add_button(label="Remove", user_data=(plot_id, idx), callback=self.remove_trace)

    def add_new_plot_tab(self, plot_type: PlotType, initial_expression: Optional[str] = None) -> None:
        plot_id = str(int(time.time() * 1000))
        tab_tag = f"tab_{plot_id}"
        plot_name = "Rectangular Plot" if plot_type == PlotType.RECTANGULAR else "Smith Chart"
        with dpg.tab(label=plot_name, tag=tab_tag, parent="results_tab_bar"):
            if plot_type == PlotType.SMITH:
                dpg.add_button(label="Reset Zoom", user_data=plot_id,
                               callback=lambda s, a, u=plot_id: self.plot_controller.reset_zoom(u))
            with dpg.group(horizontal=True):
                with dpg.group():
                    dpg.add_input_text(
                        label="Plot Name",
                        default_value=plot_name,
                        user_data=plot_id,
                        callback=lambda s, a, u=plot_id: self.rename_plot(s, a, u),
                        tag=f"plot_name_input_{plot_id}",
                        width=250
                    )
                    with dpg.group(horizontal=True):
                        if plot_type == PlotType.RECTANGULAR:
                            dpg.add_button(label="Add Trace", user_data=plot_id, callback=lambda s, a, u=plot_id: self.add_plot_trace(u, False))
                            dpg.add_input_text(
                                label="Plot Expression",
                                default_value=DEFAULT_RECT_EXPR,
                                tag=f"expression_input_{plot_id}",
                                width=300
                            )
                        elif plot_type == PlotType.SMITH:
                            dpg.add_button(label="Add Trace", user_data=plot_id, callback=lambda s, a, u=plot_id: self.add_plot_trace(u, True))
                            dpg.add_input_text(
                                label="Expression",
                                default_value=DEFAULT_SMITH_EXPR,
                                tag=f"smith_expr_input_{plot_id}",
                                width=300
                            )
                with dpg.group(tag=f"trace_list_group_{plot_id}"):
                    with dpg.child_window(tag=f"trace_list_{plot_id}", autosize_x=True, height=120):
                        pass
            if plot_type == PlotType.RECTANGULAR:
                with dpg.child_window(tag=f"plot_container_{plot_id}", autosize_x=True, autosize_y=True):
                    with dpg.plot(label="Rectangular Plot", tag=f"plot_{plot_id}", height=-1, width=-1):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency (Hz)", tag=f"x_axis_{plot_id}")
                        dpg.add_plot_axis(dpg.mvYAxis, label="Y Axis", tag=f"y_axis_{plot_id}")
            elif plot_type == PlotType.SMITH:
                with dpg.child_window(tag=f"plot_container_{plot_id}", autosize_x=True, autosize_y=True):
                    with dpg.group(horizontal=True, tag=f"smith_wrapper_{plot_id}"):
                        dpg.add_spacer(tag=f"smith_left_spacer_{plot_id}", width=0)
                        with dpg.group(tag=f"smith_chart_group_{plot_id}"):
                            with dpg.plot(label="Smith Chart", tag=f"plot_{plot_id}", equal_aspects=True, height=400, width=400):
                                dpg.add_plot_legend()
                                dpg.add_plot_axis(dpg.mvXAxis, label="Re", tag=f"x_axis_{plot_id}", no_gridlines=True)
                                dpg.add_plot_axis(dpg.mvYAxis, label="Im", tag=f"y_axis_{plot_id}", no_gridlines=True)
                            self.plot_controller.draw_smith_grid(plot_id, self.gray_theme)
                        dpg.add_spacer(tag=f"smith_right_spacer_{plot_id}", width=0)
        self.state.plot_tabs[plot_id] = PlotTab(id=plot_id, name=plot_name, type=plot_type, tab_tag=tab_tag)
        if plot_type == PlotType.RECTANGULAR and initial_expression is not None:
            self.plot_controller.add_trace(plot_id, initial_expression, is_complex=False)
            self._refresh_trace_list(plot_id)
        self.state.add_log(f"Added new {plot_type.value} plot tab with id {plot_id}")

    def add_plot_trace(self, plot_id: str, is_smith: bool) -> None:
        input_tag = f"smith_expr_input_{plot_id}" if is_smith else f"expression_input_{plot_id}"
        expr = dpg.get_value(input_tag).strip()
        if not expr:
            self.state.add_log("Empty expression.")
            return
        if expr in self.state.plot_tabs[plot_id].traces:
            self.state.add_log(f"Expression already plotted in plot {plot_id}: {expr}")
            return
        self.state.add_plot_trace(plot_id, expr)
        self.plot_controller.add_trace(plot_id, expr, is_complex=is_smith)
        self._refresh_trace_list(plot_id)

    def netlist_file_selected(self, sender: str, app_data: dict, user_data: Any) -> None:
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

    def sweep_file_selected(self, sender: str, app_data: dict, user_data: Any) -> None:
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

    def apply_yaml_edits(self) -> None:
        new_text = dpg.get_value("yaml_editor")
        try:
            # Backup the current file.
            with open(self.state.netlist_path + ".bak", 'w') as f:
                f.write(self.state.yaml_editor_original)
            with open(self.state.netlist_path, 'w') as f:
                f.write(new_text)
            self.state.yaml_editor_text = new_text
            self.state.yaml_editor_original = new_text
            self.state.add_log("Netlist YAML updated from editor.")
            self.update_diff_preview()
        except Exception as e:
            self.state.add_log(f"Failed to apply YAML edits: {e}")

    def open_netlist_file_dialog(self) -> None:
        dpg.configure_item("netlist_file_dialog", show=True)

    def open_sweep_file_dialog(self) -> None:
        dpg.configure_item("sweep_file_dialog", show=True)
