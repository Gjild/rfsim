# components/transmission_line.py

import numpy as np
from core.behavior.component import TwoPortComponent
from symbolic.evaluator import resolve_all_parameters
from symbolic.utils import merge_params
from utils.matrix import robust_inv, s_to_y

class TransmissionLineComponent(TwoPortComponent):
    type_name = "transmission_line"

    def __init__(self, id: str, params: dict = None) -> None:
        from core.topology.port import Port
        ports = [Port("1", 0, None), Port("2", 1, None)]
        default_params = {
            "Z0": "50",
            "length": "0.1",
            "beta": "2*pi/0.3"
        }
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        """
        Same as your existing method, returning a 2x2 S-parameter for the line.
        """
        merged = merge_params(self.params, params or {})
        resolved = resolve_all_parameters(merged)
        Z0_value = resolved["Z0"]
        length = resolved["length"]
        beta = resolved["beta"]

        theta = beta * length
        T = np.exp(-1j * theta)
        S = np.array([[0, T], [T, 0]], dtype=complex)
        return S

    def get_ymatrix(self, freq: float, params: dict) -> np.ndarray:
        """
        Convert the TLine’s S-parameters to Y-parameters for MNA stamping.
        """
        S = self.get_smatrix(freq, params, Z0=50)
        from utils.matrix import s_to_y
        Y = s_to_y(S, Z0=50)
        return Y
