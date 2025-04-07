# components/phase_shifter.py
import numpy as np
from core.behavior.component import TwoPortComponent
from symbolic.utils import merge_params

class PhaseShifterComponent(TwoPortComponent):
    """
    A two-port phase shifter component.
    
    Parameters:
      phase: The phase shift in radians (default "0").
      loss_dB: Insertion loss in decibels (default "0" dB).
    
    The S-matrix for a lossless ideal phase shifter is:
        [[0, T],
         [T, 0]]
    where T = exp(-j*phase). An insertion loss (in dB) is applied as an amplitude scaling.
    """
    type_name = "phase_shifter"

    def __init__(self, id: str, params: dict = None) -> None:
        from core.topology.port import Port
        # Define two ports for a two-port device.
        ports = [Port("1", 0, None), Port("2", 1, None)]
        # Set default parameters.
        default_params = {
            "phase": "0",      # Phase shift (in radians)
            "loss_dB": "0"     # Insertion loss in dB
        }
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        # Merge component defaults with runtime parameters.
        merged = merge_params(self.params, params or {})
        # Convert parameters to numerical values.
        phase = float(merged["phase"])
        loss_dB = float(merged["loss_dB"])
        # Convert loss from dB to an amplitude factor.
        amplitude = 10 ** (-loss_dB / 20.0)
        # Calculate the transmission coefficient.
        T = amplitude * np.exp(-1j * phase)
        # Construct the S-matrix (assumes no reflection).
        S = np.array([[0, T],
                      [T, 0]], dtype=complex)
        return S
