import numpy as np
from core.behavior.component import Component
from symbolic.utils import merge_params

class CirculatorComponent(Component):
    """
    A 3-port circulator that routes signals in a cyclic order.

    Default (clockwise) behavior:
      - Port 1 -> Port 2
      - Port 2 -> Port 3
      - Port 3 -> Port 1

    Parameters:
      phase: Phase shift (radians) applied to the transmission path (default "0").
      loss_dB: Insertion loss in dB (default "0").
      direction: Circulation order; "clockwise" (default) or "counterclockwise".
                 In counterclockwise mode:
                     Port 1 -> Port 3, Port 3 -> Port 2, Port 2 -> Port 1.
    """
    type_name = "circulator"

    def __init__(self, id: str, params: dict = None) -> None:
        # Import Port locally to avoid potential circular dependencies.
        from core.topology.port import Port
        # Define three ports (Port numbers as strings with corresponding indices).
        ports = [Port("1", 0, None), Port("2", 1, None), Port("3", 2, None)]
        default_params = {
            "phase": "0",            # Phase shift in radians.
            "loss_dB": "0",          # Insertion loss in dB.
            "direction": "clockwise" # Circulation direction.
        }
        # Merge default and provided parameters.
        all_params = merge_params(default_params, params or {})
        super().__init__(id, ports, all_params)

    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        """
        Compute the 3x3 scattering matrix for the circulator.

        Parameters:
            freq : Frequency (unused in this component, but typically provided for consistency)
            params : Runtime parameters which override instance parameters.
            Z0 : Characteristic impedance (default 50).

        Returns:
            S : The 3x3 scattering matrix as a numpy.ndarray.
        """
        merged = merge_params(self.params, params or {})
        try:
            phase = float(merged["phase"])
            loss_dB = float(merged["loss_dB"])
        except ValueError as e:
            raise ValueError("Invalid numeric parameter in circulator: " + str(e))

        direction = merged["direction"].lower()
        # Convert loss from dB to amplitude and apply phase shift.
        T = 10 ** (-loss_dB / 20.0) * np.exp(-1j * phase)

        # Initialize a 3x3 S-matrix with zeros.
        S = np.zeros((3, 3), dtype=complex)

        # Define routing mappings.
        routing = {
            "clockwise": [(0, 1), (1, 2), (2, 0)],
            "counterclockwise": [(0, 2), (2, 1), (1, 0)]
        }

        if direction not in routing:
            raise ValueError("Invalid 'direction' parameter; must be 'clockwise' or 'counterclockwise'.")

        for src, dst in routing[direction]:
            S[dst, src] = T  # Note: S-matrix convention may vary by indexing.

        return S
