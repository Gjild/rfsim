import numpy as np
from components.single_impedance_component import SingleImpedanceComponent

class CapacitorComponent(SingleImpedanceComponent):
    type_name = "capacitor"
    default_params = {"C": "1e-9"}
    param_key = "C"

    def impedance_expr(self, f: float, C: float) -> complex:
        """
        Compute the impedance of a capacitor at a given frequency.
        
        :param f: Frequency in Hz.
        :param C: Capacitance in Farads.
        :return: The impedance as a complex number.
        """
        return 1 / (1j * 2 * np.pi * f * C)
