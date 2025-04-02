# components/capacitor.py
import numpy as np
from core.behavior.component import TwoPortComponent
from core.topology.port import Port
from symbolic.parameters import resolve_parameters, merge_params
from components.two_port_mixin import TwoPortImpedanceMixin

class CapacitorComponent(TwoPortComponent, TwoPortImpedanceMixin):
    def __init__(self, id: str, params: dict = None) -> None:
        ports = [
            Port(name="1", index=0, connected_node=None),
            Port(name="2", index=1, connected_node=None)
        ]
        default_params = {"C": "1e-9"}
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)
    
    def get_zmatrix(self, freq: float, params: dict) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        C_value = resolve_parameters(self.params.get("C", "1e-9"), merged)
        # Calculate capacitive impedance: Z = 1/(j2πfC)
        Z = 1 / (1j * 2 * np.pi * freq * C_value)
        return self._build_two_port_impedance(Z)