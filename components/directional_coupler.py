# components/directional_coupler.py
import numpy as np
from core.behavior.component import Component
from symbolic.utils import merge_params
import math

class DirectionalCouplerComponent(Component):
    """
    A 4-port directional coupler.

    Port assignments:
      1: Input
      2: Through port
      3: Coupled port
      4: Isolated port

    S-matrix (ideal, lossless) elements are defined as:
      S[0,1] = S[1,0] = sqrt(1 - k^2) * A
      S[0,2] = S[2,0] = 1j * k * A
      S[1,3] = S[3,1] = 1j * k * A
      S[2,3] = S[3,2] = sqrt(1 - k^2) * A
    with k derived from 'coupling_dB' and A from 'loss_dB'.

    Parameters:
      coupling_dB: Coupling in dB (default "10").
      loss_dB: Overall insertion loss in dB (default "0").
    """
    type_name = "directional_coupler"

    def __init__(self, id: str, params: dict = None) -> None:
        from core.topology.port import Port
        ports = [Port("1", 0, None), Port("2", 1, None),
                 Port("3", 2, None), Port("4", 3, None)]
        default_params = {"coupling_dB": "10", "loss_dB": "0"}
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)
    
    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        try:
            coupling_dB = float(merged["coupling_dB"])
            loss_dB = float(merged["loss_dB"])
        except ValueError as e:
            raise ValueError("Invalid parameter in directional coupler: " + str(e))
        # Convert coupling from dB to amplitude.
        k = 10 ** (-coupling_dB / 20.0)
        if not (0 <= k <= 1):
            raise ValueError("Coupling factor out of bounds, check coupling_dB parameter.")
        main_amp = math.sqrt(1 - k**2)
        A = 10 ** (-loss_dB / 20.0)
        S = np.zeros((4, 4), dtype=complex)
        S[0,1] = main_amp * A  # input -> through
        S[0,2] = 1j * k * A    # input -> coupled
        S[1,0] = main_amp * A  # through -> input
        S[1,3] = 1j * k * A    # through -> isolated
        S[2,0] = 1j * k * A    # coupled -> input
        S[2,3] = main_amp * A  # coupled -> isolated
        S[3,1] = 1j * k * A    # isolated -> through
        S[3,2] = main_amp * A  # isolated -> coupled
        return S
