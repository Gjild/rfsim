# components/attenuator.py
import numpy as np
from core.behavior.component import TwoPortComponent
from symbolic.utils import merge_params

class AttenuatorComponent(TwoPortComponent):
    """
    A two-port attenuator that reduces signal amplitude by a specified attenuation (in dB).

    Parameters:
      att_dB: The attenuation in dB (default "3").
    """
    type_name = "attenuator"

    def __init__(self, id: str, params: dict = None) -> None:
        from core.topology.port import Port
        ports = [Port("1", 0, None), Port("2", 1, None)]
        default_params = {"att_dB": "3"}
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        try:
            att_dB = float(merged["att_dB"])
        except ValueError as e:
            raise ValueError("Invalid attenuation value: " + str(e))
        # Convert attenuation dB to amplitude factor.
        amplitude = 10 ** (-att_dB / 20.0)
        # Matched two-port S-matrix: no reflections, pure transmission.
        S = np.array([[0, amplitude],
                      [amplitude, 0]], dtype=complex)
        return S
