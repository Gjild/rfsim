# components/single_impedance_component.py
import numpy as np
from core.behavior.component import TwoPortComponent
from core.topology.port import Port
from symbolic.parameters import merge_params, resolve_parameters
from components.two_port_mixin import TwoPortImpedanceMixin

class SingleImpedanceComponent(TwoPortComponent, TwoPortImpedanceMixin):
    # Class-level attributes for derived classes to override.
    type_name: str = "undefined"
    default_params: dict = {}
    param_key: str = "X"  # e.g., "R", "C", or "L"
    impedance_expr = None  # Function f(freq, value) -> impedance

    def __init__(self, id: str, params: dict = None) -> None:
        ports = [Port("1", 0, None), Port("2", 1, None)]
        all_params = merge_params(self.default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_zmatrix(self, freq: float, params: dict) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        # Retrieve the value for the parameter (R, C, or L)
        value = resolve_parameters(merged[self.param_key], merged)
        if self.impedance_expr is None:
            raise NotImplementedError("Impedance expression not defined for this component.")
        # Calculate impedance using the provided lambda expression.
        Z = self.impedance_expr(freq, value)
        return self._build_two_port_impedance(Z)
    