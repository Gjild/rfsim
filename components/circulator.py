# components/circulator.py
import numpy as np
from core.behavior.component import Component
from symbolic.utils import merge_params

class CirculatorComponent(Component):
    """
    A 3-port circulator that routes signals in a cyclic order.

    By default (direction 'clockwise'):
      - Port 1 -> Port 2
      - Port 2 -> Port 3
      - Port 3 -> Port 1

    Parameters:
      phase: The phase shift (in radians) applied to the transmission path (default "0").
      loss_dB: Insertion loss in dB (default "0").
      direction: Circulation order; either "clockwise" (default) or "counterclockwise".
                 In "counterclockwise" mode:
                     Port 1 -> Port 3, Port 3 -> Port 2, Port 2 -> Port 1.
    """
    type_name = "circulator"

    def __init__(self, id: str, params: dict = None) -> None:
        from core.topology.port import Port
        # Define three ports.
        ports = [Port("1", 0, None), Port("2", 1, None), Port("3", 2, None)]
        # Set default parameters.
        default_params = {
            "phase": "0",            # Phase shift in radians.
            "loss_dB": "0",          # Insertion loss (dB).
            "direction": "clockwise" # Circulation direction: "clockwise" or "counterclockwise".
        }
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        # Merge default and runtime parameters.
        merged = merge_params(self.params, params or {})
        try:
            phase = float(merged["phase"])
            loss_dB = float(merged["loss_dB"])
        except ValueError as e:
            raise ValueError("Invalid numeric parameter in circulator: " + str(e))
        direction = merged["direction"].lower()
        
        # Convert loss from dB to amplitude.
        amplitude = 10 ** (-loss_dB / 20.0)
        # Compute the transmission coefficient (apply phase shift).
        T = amplitude * np.exp(-1j * phase)
        
        # Initialize a 3x3 S-matrix with zeros.
        S = np.zeros((3, 3), dtype=complex)
        
        if direction == "clockwise":
            # Set the cyclic routing: port 1->2, 2->3, 3->1.
            S[0, 1] = T
            S[1, 2] = T
            S[2, 0] = T
        elif direction == "counterclockwise":
            # Reverse circulation: port 1->3, 3->2, 2->1.
            S[0, 2] = T
            S[2, 1] = T
            S[1, 0] = T
        else:
            raise ValueError("Invalid 'direction' parameter; must be 'clockwise' or 'counterclockwise'.")
        
        return S
