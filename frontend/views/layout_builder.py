# frontend/views/layout_builder.py
import dearpygui.dearpygui as dpg
from frontend.utils.constants import FILE_DIALOG_WIDTH, FILE_DIALOG_HEIGHT, SMITH_MARGIN, MIN_SMITH_SIZE
from frontend.models.state import PlotType

class LayoutBuilder:
    """
    Responsible for building and updating the UI layout.
    """
    def __init__(self, controller) -> None:
        self.controller = controller

    def build_ui(self) -> None:
        with dpg.theme() as self.controller.gray_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (150, 150, 150, 255), category=dpg.mvThemeCat_Plots)
        with dpg.window(tag="root_window", label="RFSim UI", no_title_bar=True, no_resize=True, no_move=True, no_close=True):
            dpg.set_primary_window("root_window", True)
            with dpg.group(horizontal=True):
                self._build_sidebar()
                self._build_main_work_area()
            self._build_log_console()
        self._build_file_dialogs()

    def _build_sidebar(self) -> None:
        with dpg.child_window(tag="sidebar", width=380, autosize_y=True, border=True):
            with dpg.collapsing_header(label="Simulation Control", default_open=True):
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Browse Netlist", callback=lambda s, a: self.controller.open_netlist_file_dialog())
                    dpg.add_input_text(label="", readonly=True, width=250, tag="netlist_path_display")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Browse Sweep Config", callback=lambda s, a: self.controller.open_sweep_file_dialog())
                    dpg.add_input_text(label="", readonly=True, width=250, tag="sweep_path_display")
                dpg.add_button(label="Run Simulation", callback=lambda s, a: self.controller.simulation_controller.start())
                dpg.add_progress_bar(default_value=0.0, tag="progress_bar_tag", width=300)
            with dpg.collapsing_header(label="Netlist Editor", default_open=True):
                dpg.add_input_text(tag="yaml_editor", multiline=True, width=-1, height=200, callback=lambda s, a: self.controller.update_diff_preview())
                dpg.add_button(label="Apply YAML Edits", callback=lambda s, a: self.controller.apply_yaml_edits())
                dpg.add_text("Unsaved Changes Preview:")
                dpg.add_input_text(tag="yaml_diff", multiline=True, readonly=True, width=-1, height=180)

    def _build_main_work_area(self) -> None:
        with dpg.child_window(tag="main_work_area", autosize_x=True, autosize_y=True, border=True):
            with dpg.group():
                with dpg.group(horizontal=True):
                    dpg.add_combo(("Rectangular", "Smith"), tag="new_plot_type", default_value="Rectangular", width=150)
                    # Convert the string value to a PlotType enum before passing it on.
                    dpg.add_button(
                        label="Add New Plot",
                        callback=lambda s, a: self.controller.add_new_plot_tab(self._get_plot_type())
                    )
                with dpg.tab_bar(tag="results_tab_bar"):
                    pass

    def _build_log_console(self) -> None:
        with dpg.child_window(tag="log_console", height=140, autosize_x=True, border=True):
            dpg.add_text("Log Console")
            with dpg.child_window(tag="log_child", autosize_x=True, autosize_y=True):
                dpg.add_input_text(multiline=True, readonly=True, tag="log_text_tag", width=-1, height=120)

    def _build_file_dialogs(self) -> None:
        with dpg.file_dialog(
            directory_selector=False, show=False,
            callback=self.controller.netlist_file_selected,
            tag="netlist_file_dialog", width=FILE_DIALOG_WIDTH, height=FILE_DIALOG_HEIGHT
        ):
            dpg.add_file_extension("YAML Files (*.yaml){.yaml}")
            dpg.add_file_extension("YML Files (*.yml){.yml}")
        with dpg.file_dialog(
            directory_selector=False, show=False,
            callback=self.controller.sweep_file_selected,
            tag="sweep_file_dialog", width=FILE_DIALOG_WIDTH, height=FILE_DIALOG_HEIGHT
        ):
            dpg.add_file_extension("YAML Files (*.yaml){.yaml}")
            dpg.add_file_extension("YML Files (*.yml){.yml}")

    def _get_plot_type(self) -> PlotType:
        """
        Converts the combo-box selection (a string) into a PlotType enum.
        """
        value = dpg.get_value("new_plot_type").lower()
        if value == "rectangular":
            return PlotType.RECTANGULAR
        elif value == "smith":
            return PlotType.SMITH
        else:
            # Fallback default.
            return PlotType.RECTANGULAR

    def update_ui(self) -> None:
        dpg.set_value("progress_bar_tag", self.controller.state.simulation_status.progress)
        dpg.set_value("log_text_tag", "\n".join(self.controller.state.logs[-100:]))
        dpg.set_y_scroll("log_child", 10000)
        # Update smith chart dimensions if applicable.
        for plot_id, plot_tab in self.controller.state.plot_tabs.items():
            if plot_tab.type.name.lower() == "smith":
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
