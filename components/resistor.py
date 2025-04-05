# components/resistor.py
import numpy as np
from components.single_impedance_component import SingleImpedanceComponent

class ResistorComponent(SingleImpedanceComponent):
    type_name = "resistor"
    default_params = {"R": "1000"}
    param_key = "R"
    impedance_expr = staticmethod(lambda f, R: R)
