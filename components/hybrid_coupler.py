# components/hybrid_coupler.py
import numpy as np
from core.behavior.component import Component
from symbolic.utils import merge_params

class HybridCouplerComponent(Component):
    """
    A 4-port ideal 90-degree hybrid coupler (branch-line coupler).

    The ideal S-matrix (without loss) is:
      [[ 0,          j/√2,       1/√2,       0      ],
       [ j/√2,       0,          0,          1/√2   ],
       [ 1/√2,       0,          0,          j/√2   ],
       [ 0,          1/√2,       j/√2,       0      ]]

    Parameters:
      loss_dB: Overall insertion loss in dB (default "0").
    """
    type_name = "hybrid_coupler"

    def __init__(self, id: str, params: dict = None) -> None:
        from core.topology.port import Port
        # Define four ports.
        ports = [Port("1", 0, None), Port("2", 1, None),
                 Port("3", 2, None), Port("4", 3, None)]
        default_params = {"loss_dB": "0"}
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        try:
            loss_dB = float(merged["loss_dB"])
        except ValueError as e:
            raise ValueError("Invalid loss value: " + str(e))
        # Overall amplitude scaling.
        A = 10 ** (-loss_dB / 20.0)
        factor = A / np.sqrt(2)
        j = 1j
        S = np.array([
            [0,       j * factor, factor,      0],
            [j * factor, 0,       0,       factor],
            [factor,    0,       0,       j * factor],
            [0,       factor,  j * factor,  0]
        ], dtype=complex)
        return S
