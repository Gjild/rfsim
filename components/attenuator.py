
#components/attenuator.py
import numpy as np
from core.behavior.component import TwoPortComponent
from core.topology.port import Port
from symbolic.utils import merge_params


class AttenuatorComponent(TwoPortComponent):
    """
    Two-port attenuator that reduces signal amplitude by a specified attenuation (in dB).

    Attributes:
        type_name (str): The component type name.
    """

    type_name = "attenuator"

    def __init__(self, id: str, params: dict = None) -> None:
        default_params = {"att_dB": "3"}
        all_params = merge_params(default_params, params or {})
        ports = [Port("1", 0, None), Port("2", 1, None)]
        super().__init__(id, ports, all_params)

    def get_smatrix(self, freq: float, params: dict, Z0: float = 50) -> np.ndarray:
        # Merge component-level parameters with new overrides.
        merged = merge_params(self.params, params or {})
        try:
            att_dB = float(merged["att_dB"])
        except ValueError as e:
            raise ValueError(f"Invalid attenuation value '{merged.get('att_dB', None)}': {e}")

        # Convert attenuation in dB to amplitude (voltage) scaling factor.
        amplitude = 10 ** (-att_dB / 20.0)

        # Return the matched two-port S-matrix with pure transmission.
        S = np.array([[0, amplitude],
                      [amplitude, 0]], dtype=complex)
        return S
