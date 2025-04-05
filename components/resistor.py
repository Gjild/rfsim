import numpy as np
from components.single_impedance_component import SingleImpedanceComponent

class ResistorComponent(SingleImpedanceComponent):
    type_name = "resistor"
    default_params = {"R": "1000"}
    param_key = "R"

    def impedance_expr(self, f: float, R: float) -> complex:
        """
        Compute the impedance of a resistor.
        
        :param f: Frequency in Hz (unused for resistor).
        :param R: Resistance in Ohms.
        :return: The impedance as a complex number.
        """
        return R
