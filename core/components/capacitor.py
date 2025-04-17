# core/components/capacitor.py
"""
Capacitor component plugin for RFSim v2.
Two-port capacitor with admittance Y = j*2πf*C.
"""
import numpy as np
from typing import Dict, Any, List

from core.components.base import Component
from core.exceptions import ParameterError
from core.components.plugin_loader import ComponentFactory


class CapacitorComponent(Component):
    """
    Two-port capacitor component.

    Parameters (in params dict):
      C: capacitance in Farads (float)

    Ports:
      '1', '2'
    """
    type_name = "capacitor"

    def __init__(self, comp_id: str, params: Dict[str, Any]):
        super().__init__(comp_id, params)

    @property
    def ports(self) -> List[str]:
        return ["1", "2"]

    def get_ymatrix(self, freq: float, params: Dict[str, float]) -> np.ndarray:
        # Expect 'C' to be in resolved params
        if "C" not in params:
            raise ParameterError(f"Capacitor '{self.id}' missing parameter 'C'.")
        C_val = params["C"]
        # Admittance of capacitor: Y = j*2*pi*f*C
        Y = 1j * 2 * np.pi * freq * C_val
        # Y-matrix for series element: [[+Y, -Y], [-Y, +Y]]
        return np.array([[ Y, -Y],
                         [-Y,  Y]], dtype=complex)

# Register plugin
ComponentFactory.register(CapacitorComponent)