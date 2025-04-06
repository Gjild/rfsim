import numpy as np
import scipy.interpolate as interp
from core.behavior.component import TwoPortComponent
from symbolic.utils import merge_params
from inout.touchstone_parser import read_touchstone_file

class TouchstoneComponent(TwoPortComponent):
    type_name = "touchstone"
    default_params = {"filename": "default.s2p"}

    def __init__(self, id: str, params: dict = None) -> None:
        # Initialize as a two-port device.
        super().__init__(id, ports=[], params=params)
        from core.topology.port import Port
        # Define the two ports.
        self.ports = [Port("1", 0, None), Port("2", 1, None)]
        # Merge user-provided parameters with defaults.
        self.params = merge_params(self.default_params, self.params)
        # Touchstone data will be loaded once.
        self.touchstone_data = None
        self.load_data()

    def load_data(self) -> None:
        """
        Load the touchstone data using the inout parser.
        """
        filename = self.params.get("filename", self.default_params["filename"])
        self.touchstone_data = read_touchstone_file(filename)

    def get_smatrix(self, freq: float, params: dict, Z0=50) -> np.ndarray:
        """
        Interpolate the S-parameter data from the touchstone file for a given frequency.
        """
        if self.touchstone_data is None:
            self.load_data()

        freq_data = self.touchstone_data["freq"]
        S_data = self.touchstone_data["S"]

        # Extract S-parameter elements.
        S11 = np.array([S[0, 0] for S in S_data])
        S12 = np.array([S[0, 1] for S in S_data])
        S21 = np.array([S[1, 0] for S in S_data])
        S22 = np.array([S[1, 1] for S in S_data])

        # Create interpolation functions with linear interpolation (and extrapolation).
        interp_S11 = interp.interp1d(freq_data, S11, kind="linear", fill_value="extrapolate")
        interp_S12 = interp.interp1d(freq_data, S12, kind="linear", fill_value="extrapolate")
        interp_S21 = interp.interp1d(freq_data, S21, kind="linear", fill_value="extrapolate")
        interp_S22 = interp.interp1d(freq_data, S22, kind="linear", fill_value="extrapolate")

        S_interp = np.array([
            [interp_S11(freq), interp_S12(freq)],
            [interp_S21(freq), interp_S22(freq)]
        ], dtype=complex)
        return S_interp

    def get_zmatrix(self, freq: float, params: dict):
        """
        Optionally provide the impedance matrix by converting the interpolated S-matrix.
        """
        from utils.matrix import s_to_z
        S = self.get_smatrix(freq, params)
        return s_to_z(S, Z0=50)
