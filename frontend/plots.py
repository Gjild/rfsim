# frontend/plots.py
import numpy as np
import dearpygui.dearpygui as dpg
from typing import List, Tuple
from utils.expr_eval import safe_eval_expr
from utils.tags import TagRegistry
from states import StateManager

# Configuration constants.
CIRCLE_RES = 500
REACTANCE_RES = 2000
UNIT_CIRCLE_CLIP = 0.999
RESISTANCE_VALUES = [0.2, 0.5, 1, 2, 5]
REACTANCE_VALUES = [0.2, 0.5, 1, 2, 5]
DEFAULT_RECT_EXPR = "abs(z_to_s(Z)[1, 0])"
DEFAULT_SMITH_EXPR = "s_matrix[0, 0]"

class PlotManager:
    """
    Handles creation, updating, and drawing of plots and traces.
    """
    def __init__(self, state: StateManager, ui_controller: 'UIController') -> None:
        self.state = state
        self.ui_controller = ui_controller

    def generate_resistance_circle(self, r: float) -> List[Tuple[float, float]]:
        theta = np.linspace(-np.pi, np.pi, CIRCLE_RES)
        c = r / (1 + r)
        rad = 1 / (1 + r)
        x = c + rad * np.cos(theta)
        y = rad * np.sin(theta)
        mask = x**2 + y**2 <= UNIT_CIRCLE_CLIP
        return [(x[i], y[i]) for i in range(len(x)) if mask[i]]

    def generate_reactance_arcs(self, xval: float) -> List[List[Tuple[float, float]]]:
        arcs = []
        radius = 1 / xval
        theta = np.linspace(-np.pi, np.pi, REACTANCE_RES)
        for s in [+1, -1]:
            x = 1 + radius * np.cos(theta)
            y = s * radius + radius * np.sin(theta)
            mask = x**2 + y**2 <= UNIT_CIRCLE_CLIP
            current_arc = []
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

    def draw_smith_grid(self, plot_id: str, theme: int) -> None:
        # Draw resistance circles.
        for r in RESISTANCE_VALUES:
            pts = self.generate_resistance_circle(r)
            if len(pts) >= 2:
                x, y = zip(*pts)
                tag = TagRegistry.generate_tag("grid_res_circle", plot_id, identifier=str(r))
                dpg.add_line_series(x, y, parent=f"y_axis_{plot_id}", tag=tag)
                dpg.bind_item_theme(tag, theme)
        # Draw reactance arcs.
        for x_val in REACTANCE_VALUES:
            arcs = self.generate_reactance_arcs(x_val)
            for i, arc in enumerate(arcs):
                if len(arc) >= 2:
                    x, y = zip(*arc)
                    tag = TagRegistry.generate_tag("grid_react_arc", plot_id, identifier=f"{x_val}_{i}")
                    dpg.add_line_series(x, y, parent=f"y_axis_{plot_id}", tag=tag)
                    dpg.bind_item_theme(tag, theme)

    def add_trace(self, plot_id: str, expr: str, is_complex: bool) -> None:
        tag_prefix = "smith_trace" if is_complex else "trace"
        tag = TagRegistry.generate_tag(tag_prefix, plot_id, identifier=expr)
        result = safe_eval_expr(expr, self.state.simulation_results, is_complex=is_complex, logger_func=self.state.add_log)
        if result is None:
            return
        x_data, y_data = result
        dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
        dpg.fit_axis_data(f"y_axis_{plot_id}")
        kind = "Smith" if is_complex else "rectangular"
        self.state.add_log(f"Added {kind} trace '{expr}' to plot {plot_id}")

    def update_rectangular_plot(self, plot_id: str) -> None:
        for expr in self.state.plot_tabs[plot_id].traces:
            tag = TagRegistry.generate_tag("trace", plot_id, identifier=expr)
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
        for expr in self.state.plot_tabs[plot_id].traces:
            tag = TagRegistry.generate_tag("smith_trace", plot_id, identifier=expr)
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
        dpg.set_axis_limits(f"x_axis_{plot_id}", -1.1, 1.1)
        dpg.set_axis_limits(f"y_axis_{plot_id}", -1.1, 1.1)
        self.state.add_log(f"Reset zoom for Smith chart plot {plot_id}")
