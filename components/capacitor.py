# components/capacitor.py
import numpy as np
from components.single_impedance_component import SingleImpedanceComponent

class CapacitorComponent(SingleImpedanceComponent):
    type_name = "capacitor"
    default_params = {"C": "1e-9"}
    param_key = "C"
    impedance_expr = staticmethod(lambda f, C: 1/(1j * 2 * np.pi * f * C))
