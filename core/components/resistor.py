# core/components/resistor.py
"""
Resistor component plugin for RFSim v2.
Defines a two-port resistor with conductance G = 1/R.
"""
import numpy as np
from typing import Dict, Any, List

from core.components.base import Component
from core.exceptions import ParameterError
from core.components.plugin_loader import ComponentFactory


class ResistorComponent(Component):
    """
    Two-port resistor component.

    Parameters (in params dict):
      R: resistance in Ohms (float)

    Ports:
      '1', '2'
    """
    type_name = "resistor"

    def __init__(self, comp_id: str, params: Dict[str, Any]):
        super().__init__(comp_id, params)

    @property
    def ports(self) -> List[str]:
        return ["1", "2"]

    def get_ymatrix(self, freq: float, params: Dict[str, float]) -> np.ndarray:
        # Expect 'R' to be in resolved params
        if "R" not in params:
            raise ParameterError(f"Resistor '{self.id}' missing parameter 'R'.")
        R = params["R"]
        if R == 0:
            raise ParameterError(f"Resistor '{self.id}' has zero resistance => infinite conductance.")
        G = 1.0 / R
        # Y-matrix for series resistor between port1 and port2
        # [[+G, -G], [-G, +G]]
        return np.array([[ G, -G],
                         [-G,  G]], dtype=complex)


# Register plugin
ComponentFactory.register(ResistorComponent)
