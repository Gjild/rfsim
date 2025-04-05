# components/inductor.py
import numpy as np
from components.single_impedance_component import SingleImpedanceComponent

class InductorComponent(SingleImpedanceComponent):
    type_name = "inductor"
    default_params = {"L": "1e-6"}
    param_key = "L"
    impedance_expr = staticmethod(lambda f, L: 1j * 2 * np.pi * f * L)
