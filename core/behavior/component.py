import numpy as np
from abc import ABC, abstractmethod
from core.topology.port import Port
import inspect

class Component(ABC):
    type_name: str = "undefined"  # All subclasses override this as needed

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

    def to_yaml_dict(self) -> dict:
        """
        Convert the component to a dictionary suitable for YAML serialization.

        Returns:
            A dictionary with keys: id, type, params, ports.
        """
        return {
            "id": self.id,
            "type": self.type_name,
            "params": self.params,
            "ports": [p.name for p in self.ports]
        }

    def __repr__(self):
        return f"<Component {self.id} ({self.type_name}): ports={self.ports}, params={self.params}>"

    def clone(self):
        """
        Create a shallow clone of the component.
        Ports are cloned with the same properties, preserving the connected_node reference.
        """
        new_ports = []
        for port in self.ports:
            # Update from port.Z0 (legacy) to port.impedance in the new design.
            new_port = Port(port.name, port.index, port.connected_node, port.impedance)
            new_ports.append(new_port)
        # Use type introspection to create a new instance.
        sig = inspect.signature(self.__class__.__init__)
        if 'params' in sig.parameters:
            try:
                new_comp = self.__class__(self.id, params=self.params.copy())
            except TypeError:
                new_comp = self.__class__(self.id)
        else:
            new_comp = self.__class__(self.id)
        new_comp.ports = new_ports
        return new_comp

# New abstract subclass for two-port components that provides common S/Z conversion.
class TwoPortComponent(Component):
    def get_smatrix(self, freq, params, Z0=50):
        from utils.matrix import z_to_s  # use our unified conversion function
        Z = self.get_zmatrix(freq, params)
        return z_to_s(Z, Z0)

    def get_matrix(self, freq, params, Z0=50):
        return self.get_smatrix(freq, params, Z0)
