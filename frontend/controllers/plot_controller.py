# frontend/controllers/plot_controller.py
import numpy as np
import dearpygui.dearpygui as dpg
from typing import List, Tuple
from frontend.utils.expr_eval import safe_eval_expr
from frontend.utils.tag_factory import TagFactory
from frontend.models.state import StateManager, PlotType
from frontend.utils.constants import CIRCLE_RES, REACTANCE_RES, UNIT_CIRCLE_CLIP, RESISTANCE_VALUES, REACTANCE_VALUES

class PlotController:
    """
    Handles plot generation, trace addition, and updating plots.
    """
    def __init__(self, state: StateManager) -> None:
        self.state = state

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
                tag = TagFactory.generate_tag("grid_res_circle", plot_id, identifier=str(r))
                dpg.add_line_series(x, y, parent=f"y_axis_{plot_id}", tag=tag)
                dpg.bind_item_theme(tag, theme)
        # Draw reactance arcs.
        for x_val in RESISTANCE_VALUES:
            arcs = self.generate_reactance_arcs(x_val)
            for i, arc in enumerate(arcs):
                if len(arc) >= 2:
                    x, y = zip(*arc)
                    tag = TagFactory.generate_tag("grid_react_arc", plot_id, identifier=f"{x_val}_{i}")
                    dpg.add_line_series(x, y, parent=f"y_axis_{plot_id}", tag=tag)
                    dpg.bind_item_theme(tag, theme)

    def add_trace(self, plot_id: str, expr: str, is_complex: bool) -> None:
        tag_prefix = "smith_trace" if is_complex else "trace"
        tag = TagFactory.generate_tag(tag_prefix, plot_id, identifier=expr)
        result = safe_eval_expr(expr, self.state.simulation_results, is_complex=is_complex, logger_func=self.state.add_log)
        if result is None:
            return
        x_data, y_data = result
        dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
        dpg.fit_axis_data(f"y_axis_{plot_id}")
        kind = "Smith" if is_complex else "rectangular"
        self.state.add_log(f"Added {kind} trace '{expr}' to plot {plot_id}")

    def update_plot(self, plot_id: str, plot_type: PlotType) -> None:
        tag_prefix = "smith_trace" if plot_type == PlotType.SMITH else "trace"
        for expr in self.state.plot_tabs[plot_id].traces:
            tag = TagFactory.generate_tag(tag_prefix, plot_id, identifier=expr)
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            is_complex = (plot_type == PlotType.SMITH)
            result = safe_eval_expr(expr, self.state.simulation_results, is_complex=is_complex, logger_func=self.state.add_log)
            if result is None:
                continue
            x_data, y_data = result
            dpg.add_line_series(x_data, y_data, label=expr, parent=f"y_axis_{plot_id}", tag=tag)
        dpg.fit_axis_data(f"y_axis_{plot_id}")
        self.state.add_log(f"Updated plot {plot_id}")
    
    def reset_zoom(self, plot_id: str) -> None:
        dpg.set_axis_limits(f"x_axis_{plot_id}", -1.1, 1.1)
        dpg.set_axis_limits(f"y_axis_{plot_id}", -1.1, 1.1)
        self.state.add_log(f"Reset zoom for Smith chart plot {plot_id}")
