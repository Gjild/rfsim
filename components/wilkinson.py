# components/wilkinson_divider.py
import numpy as np
from core.behavior.component import Component
from symbolic.utils import merge_params

class WilkinsonDividerComponent(Component):
    """
    A simplified ideal 3-port Wilkinson divider/combiner.

    In this ideal model, the input (port 1) is split equally between the two outputs (ports 2 and 3).
    The S-matrix is defined as:
       S[0,1] = S[0,2] = T
       S[1,0] = S[2,0] = T
    with T = (10^(-loss_dB/20)) / √2.

    Parameters:
      loss_dB: Insertion loss in dB (default "0").
    """
    type_name = "wilkinson_divider"

    def __init__(self, id: str, params: dict = None) -> None:
        from core.topology.port import Port
        # Port 1: input, Ports 2 & 3: outputs.
        ports = [Port("1", 0, None), Port("2", 1, None), Port("3", 2, None)]
        default_params = {"loss_dB": "0"}
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)
    
    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        try:
            loss_dB = float(merged["loss_dB"])
        except ValueError as e:
            raise ValueError("Invalid loss parameter in Wilkinson divider: " + str(e))
        A = 10 ** (-loss_dB / 20.0)
        T = A / np.sqrt(2)
        S = np.zeros((3, 3), dtype=complex)
        S[0,1] = T
        S[0,2] = T
        S[1,0] = T
        S[2,0] = T
        return S
