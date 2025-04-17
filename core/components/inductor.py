# core/components/inductor.py
"""
Inductor component plugin for RFSim v2.
Two-port inductor with admittance Y = 1/(j*2πf*L).
"""
import numpy as np
from typing import Dict, Any, List

from core.components.base import Component
from core.exceptions import ParameterError
from core.components.plugin_loader import ComponentFactory


class InductorComponent(Component):
    """
    Two-port inductor component.

    Parameters (in params dict):
      L: inductance in Henries (float)

    Ports:
      '1', '2'
    """
    type_name = "inductor"

    def __init__(self, comp_id: str, params: Dict[str, Any]):
        super().__init__(comp_id, params)

    @property
    def ports(self) -> List[str]:
        return ["1", "2"]

    def get_ymatrix(self, freq: float, params: Dict[str, float]) -> np.ndarray:
        # Expect 'L' to be in resolved params
        if "L" not in params:
            raise ParameterError(f"Inductor '{self.id}' missing parameter 'L'.")
        L_val = params["L"]
        if freq == 0:
            # At DC, inductor is short → infinite admittance
            Y = 1e12
        else:
            # Admittance of inductor: Y = 1/(j*2*pi*f*L)
            Y = 1 / (1j * 2 * np.pi * freq * L_val)
        # Y-matrix for series element
        return np.array([[ Y, -Y],
                         [-Y,  Y]], dtype=complex)

# Register plugin
ComponentFactory.register(InductorComponent)
