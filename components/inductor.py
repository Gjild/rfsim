import numpy as np
from components.single_impedance_component import SingleImpedanceComponent

class InductorComponent(SingleImpedanceComponent):
    type_name = "inductor"
    default_params = {"L": "1e-6"}
    param_key = "L"

    def impedance_expr(self, f: float, L: float) -> complex:
        """
        Compute the impedance of an inductor.
        
        :param f: Frequency in Hz.
        :param L: Inductance in Henries.
        :return: The impedance as a complex number.
        """
        return 1j * 2 * np.pi * f * L
