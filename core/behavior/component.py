# core/behavior/component.py
from abc import ABC, abstractmethod
import numpy as np

class Component(ABC):
    def __init__(self, comp_id, ports, params=None):
        self.id = comp_id
        self.ports = ports  # List of Port objects
        self.params = params or {}

    @abstractmethod
    def get_smatrix(self, freq, params, Z0=None) -> np.ndarray:
        """Return the S-matrix of the component."""
        pass

    def get_matrix(self, freq, params, Z0=50):
        # Backwards-compatible alias.
        return self.get_smatrix(freq, params, Z0)

    @property
    def type_name(self) -> str:
        """Return the original type name (e.g., 'resistor', 'capacitor')."""
        return getattr(self, "_type_name", "unknown")

    def to_yaml_dict(self) -> dict:
        # If _type_name is missing, infer it from the class name.
        type_name = getattr(self, "_type_name", None)
        if type_name is None:
            type_name = self.__class__.__name__.replace("Component", "").lower()
            self._type_name = type_name
        return {
            "id": self.id,
            "type": type_name,
            "params": self.params,
            "ports": [p.name for p in self.ports]
        }

    def __repr__(self):
        return f"<Component {self.id} ({self.type_name}): ports={self.ports}, params={self.params}>"

# New abstract subclass for two-port components that provides common S/Z conversion.
class TwoPortComponent(Component):
    def get_smatrix(self, freq, params, Z0=50):
        from utils.matrix import z_to_s  # use our unified conversion function
        Z = self.get_zmatrix(freq, params)
        return z_to_s(Z, Z0)

    def get_matrix(self, freq, params, Z0=50):
        return self.get_smatrix(freq, params, Z0)
