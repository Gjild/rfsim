import numpy as np
from core.behavior.component import TwoPortComponent
from core.topology.port import Port
from symbolic.utils import merge_params
from symbolic.evaluator import resolve_all_parameters
from components.two_port_mixin import TwoPortSymmetricImpedanceMixin

class SingleImpedanceComponent(TwoPortComponent, TwoPortSymmetricImpedanceMixin):
    """
    Base class for components that have a single impedance parameter (like resistor, capacitor, inductor).
    """
    type_name: str = "undefined"
    default_params: dict = {}
    param_key: str = "X"  # e.g., "R", "C", or "L"

    def __init__(self, id: str, params: dict = None) -> None:
        ports = [Port("1", 0, None), Port("2", 1, None)]
        all_params = merge_params(self.default_params, params or {})
        super().__init__(id, ports, all_params)

    def impedance_expr(self, freq: float, value: float) -> complex:
        """
        Calculate the impedance based on frequency and the given parameter value.
        This method should be overridden by subclasses.
        
        :param freq: Frequency in Hz.
        :param value: The parameter value.
        :return: The computed impedance as a complex number.
        """
        raise NotImplementedError("Impedance expression not implemented for this component.")

    def get_zmatrix(self, freq: float, params: dict) -> np.ndarray:
        merged = merge_params(self.params, params or {})
        # Fully resolve all parameters from the merged dictionary.
        resolved = resolve_all_parameters(merged)
        # Retrieve the value for the parameter (e.g., "R", "C", or "L")
        value = resolved[self.param_key]
        Z = self.impedance_expr(freq, value)
        return self._build_two_port_impedance(Z)

