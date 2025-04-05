# core/behavior/component.py
import numpy as np
from abc import ABC, abstractmethod
from core.topology.port import Port
import inspect

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
        return self.get_smatrix(freq, params, Z0)

    @property
    def type_name(self) -> str:
        return getattr(self, "_type_name", "unknown")

    def to_yaml_dict(self) -> dict:
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

    def clone(self):
        """
        Create a shallow clone of the component.
        Ports are cloned with the same properties, preserving the connected_node reference
        (which will later be updated by the Circuit clone).
        """
        new_ports = []
        for port in self.ports:
            new_port = Port(port.name, port.index, port.connected_node, port.Z0)
            new_ports.append(new_port)
            
        # Inspect the subclass __init__ to decide whether to pass "params".
        sig = inspect.signature(self.__class__.__init__)
        if 'params' in sig.parameters:
            try:
                new_comp = self.__class__(self.id, params=self.params.copy())
            except TypeError:
                new_comp = self.__class__(self.id)
        else:
            new_comp = self.__class__(self.id)
            
        new_comp.ports = new_ports
        if hasattr(self, "_type_name"):
            new_comp._type_name = self._type_name
        return new_comp

# New abstract subclass for two-port components that provides common S/Z conversion.
class TwoPortComponent(Component):
    def get_smatrix(self, freq, params, Z0=50):
        from utils.matrix import z_to_s  # use our unified conversion function
        Z = self.get_zmatrix(freq, params)
        return z_to_s(Z, Z0)

    def get_matrix(self, freq, params, Z0=50):
        return self.get_smatrix(freq, params, Z0)
