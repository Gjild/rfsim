import dearpygui.dearpygui as dpg
import numpy as np

dpg.create_context()

# ---------- Constants ----------
CIRCLE_RES, REACTANCE_RES, UNIT_CIRCLE_CLIP = 500, 2000, 0.999
RESISTANCE_VALUES, REACTANCE_VALUES = [0.2, 0.5, 1, 2, 5], [0.2, 0.5, 1, 2, 5]
frequencies = np.linspace(1e9, 10e9, 100)
gamma = 0.5 * np.exp(1j * 2 * np.pi * frequencies / 1e10)
x_vals, y_vals = gamma.real.tolist(), gamma.imag.tolist()

# ---------- Theme ----------
with dpg.theme() as gray_theme:
    with dpg.theme_component(dpg.mvLineSeries):
        dpg.add_theme_color(dpg.mvPlotCol_Line, (150, 150, 150, 255), category=dpg.mvThemeCat_Plots)

# ---------- Grid Generators ----------
def generate_resistance_circle(r):
    theta = np.linspace(-np.pi, np.pi, CIRCLE_RES)
    c, rad = r / (1 + r), 1 / (1 + r)
    x, y = c + rad * np.cos(theta), rad * np.sin(theta)
    mask = x**2 + y**2 <= UNIT_CIRCLE_CLIP
    return [(x[i], y[i]) for i in range(len(x)) if mask[i]]

def generate_reactance_arcs(xval):
    arcs, radius = [], 1 / xval
    theta = np.linspace(-np.pi, np.pi, REACTANCE_RES)
    for s in [+1, -1]:
        x = 1 + radius * np.cos(theta)
        y = s * radius + radius * np.sin(theta)
        mask, current = (x**2 + y**2 <= UNIT_CIRCLE_CLIP), []
        for i, m in enumerate(mask):
            if m: current.append((x[i], y[i]))
            elif current: arcs.append(current) if len(current) >= 10 else None; current = []
        if current and len(current) >= 10: arcs.append(current)
    return arcs

# ---------- Drawing ----------
def draw_grid():
    for r in RESISTANCE_VALUES:
        pts = generate_resistance_circle(r)
        if len(pts) >= 2:
            dpg.bind_item_theme(dpg.add_line_series(*zip(*pts), parent="y_axis"), gray_theme)
    for x in REACTANCE_VALUES:
        for arc in generate_reactance_arcs(x):
            dpg.bind_item_theme(dpg.add_line_series(*zip(*arc), parent="y_axis"), gray_theme)

def update_tooltip():
    if dpg.is_item_hovered("smith_plot"):
        x, y = dpg.get_plot_mouse_pos()
        dpg.set_value("hover_info", f"Γ = {x:.3f} + j{y:.3f}")

# ---------- UI ----------
with dpg.window(label="Smith Chart", tag="smith_window", width=800, height=700):
    dpg.add_button(label="Reset Zoom", callback=lambda: [dpg.set_axis_limits("x_axis", -1.1, 1.1), dpg.set_axis_limits("y_axis", -1.1, 1.1)])
    with dpg.plot(label="Smith Chart", width=600, height=600, equal_aspects=True, tag="smith_plot"):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Re", tag="x_axis", no_gridlines=True)
        dpg.add_plot_axis(dpg.mvYAxis, label="Im", tag="y_axis", no_gridlines=True)
        dpg.bind_item_theme(dpg.add_line_series(np.cos(np.linspace(0, 2*np.pi, CIRCLE_RES)), 
                                                np.sin(np.linspace(0, 2*np.pi, CIRCLE_RES)), 
                                                parent="y_axis"), gray_theme)
        dpg.add_line_series(x_vals, y_vals, label="S11 Trace", parent="y_axis")
        draw_grid()
        with dpg.tooltip(parent="y_axis"):
            dpg.add_text("", tag="hover_info")
    dpg.set_axis_limits("x_axis", -1.1, 1.1)
    dpg.set_axis_limits("y_axis", -1.1, 1.1)

# ---------- App Lifecycle ----------
with dpg.handler_registry():
    dpg.add_mouse_move_handler(callback=lambda _: update_tooltip())

dpg.set_primary_window("smith_window", True)
dpg.create_viewport(title='RFSim Smith Chart', width=800, height=700)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
