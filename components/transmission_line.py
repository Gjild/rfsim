# components/transmission_line.py
import numpy as np
from core.behavior.component import TwoPortComponent
from core.topology.port import Port
from symbolic.parameters import resolve_parameters, merge_params
from components.two_port_mixin import robust_inv

class TransmissionLineComponent(TwoPortComponent):
    type_name = "transmission_line"  # Added class attribute for robust identification

    def __init__(self, id: str, params: dict = None) -> None:
        ports = [
            Port(name="1", index=0, connected_node=None),
            Port(name="2", index=1, connected_node=None)
        ]
        default_params = {
            "Z0": "50",
            "length": "0.1",      # in meters
            "beta": "2*pi/0.3"     # assume wavelength 0.3 m for simplicity
        }
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_zmatrix(self, freq: float, params: dict) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        Z0_value = resolve_parameters(self.params.get("Z0", "50"), merged)
        length = resolve_parameters(self.params.get("length", "0.1"), merged)
        beta = resolve_parameters(self.params.get("beta", "2*pi/0.3"), merged)
        theta = beta * length
        T = np.exp(-1j * theta)
        S_matrix = np.array([[0, T], [T, 0]], dtype=complex)
        I = np.eye(2, dtype=complex)
        # Use the robust inversion helper for numerical stability.
        inv_term = robust_inv(I - S_matrix, Z0=Z0_value)
        Z = Z0_value * (I + S_matrix) @ inv_term
        return Z
