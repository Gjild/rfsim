# components/transformer.py
import numpy as np
from core.behavior.component import TwoPortComponent
from symbolic.utils import merge_params

class TransformerComponent(TwoPortComponent):
    """
    An ideal transformer modeled as a two-port network.

    Parameters:
      turns_ratio: The transformer turns ratio (n). The voltage transformation is n:1 (default "1").
    """
    type_name = "transformer"

    def __init__(self, id: str, params: dict = None) -> None:
        from core.topology.port import Port
        ports = [Port("1", 0, None), Port("2", 1, None)]
        default_params = {"turns_ratio": "1"}
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_zmatrix(self, freq: float, params: dict) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        try:
            n = float(merged["turns_ratio"])
        except ValueError as e:
            raise ValueError("Invalid turns_ratio in transformer: " + str(e))
        Z0 = 50  # Reference impedance.
        # Define the Z-matrix for an ideal transformer.
        Z = np.array([[0, Z0/n],
                      [n*Z0, 0]], dtype=complex)
        return Z

    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        Z = self.get_zmatrix(freq, params)
        from utils.matrix import z_to_s
        return z_to_s(Z, Z0=Z0)
