import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import numpy as np

from core.topology.port import Port


class Component(ABC):
    """
    Abstract base class for RF circuit components.
    Subclasses should override `type_name` and implement get_smatrix().
    """
    type_name: str = "undefined"  # Override in subclasses

    def __init__(self, comp_id: str, ports: List[Port], params: Dict[str, Any] = None) -> None:
        """
        Initialize the component.
        
        Args:
            comp_id: Unique identifier for the component.
            ports: List of Port instances connected to the component.
            params: Optional dictionary of component parameters.
        """
        self.id = comp_id
        self.ports = ports  # Expected to be a list of Port objects
        self.params = params or {}

    @abstractmethod
    def get_smatrix(self, freq: float, params: Dict[str, Any], Z0: float = 50) -> np.ndarray:
        """
        Compute and return the S-matrix for the component at the given frequency.
        
        Args:
            freq: Frequency at which to evaluate the matrix.
            params: Parameter dictionary for the evaluation.
            Z0: Reference impedance.
            
        Returns:
            A NumPy ndarray representing the S-matrix.
        """
        pass

    def get_matrix(self, freq: float, params: Dict[str, Any], Z0: float = 50) -> np.ndarray:
        """Alias for get_smatrix to maintain a consistent interface."""
        return self.get_smatrix(freq, params, Z0)

    def to_yaml_dict(self) -> dict:
        """
        Serialize the component for YAML output.
        
        Returns:
            A dictionary with keys 'id', 'type', 'params', and 'ports'.
        """
        return {
            "id": self.id,
            "type": self.type_name,
            "params": self.params,
            "ports": [port.name for port in self.ports]
        }

    def __repr__(self) -> str:
        return f"<Component {self.id} ({self.type_name}): ports={self.ports}, params={self.params}>"

    def clone(self) -> "Component":
        """
        Create a shallow clone of this component.
        
        Clones ports preserving their properties (including the connected node),
        and attempts to reinitialize the component by passing the copied parameters
        if supported.
        
        Returns:
            A new instance of the component with duplicated ports and parameters.
        """
        # Clone ports using a list comprehension.
        cloned_ports = [
            Port(port.name, port.index, port.connected_node, port.impedance)
            for port in self.ports
        ]

        # Use introspection to determine supported arguments in __init__
        init_sig = inspect.signature(self.__class__.__init__)
        init_kwargs = {}
        if "params" in init_sig.parameters:
            init_kwargs["params"] = self.params.copy()

        # If the __init__ expects ports, you could also add them.
        # Currently, we assume ports are set post initialization.
        new_instance = self.__class__(self.id, cloned_ports, **init_kwargs) if "ports" in init_sig.parameters \
            else self.__class__(self.id, **init_kwargs)
        new_instance.ports = cloned_ports
        return new_instance


class TwoPortComponent(Component):
    """
    Abstract subclass for two-port components with built-in S/Z parameter conversion.
    """
    
    def get_smatrix(self, freq: float, params: Dict[str, Any], Z0: float = 50) -> np.ndarray:
        """
        Compute the S-matrix by first computing the Z-matrix and converting it.
        
        Note: This method assumes that a get_zmatrix() method is implemented
        by the subclass.
        """
        from utils.matrix import z_to_s  # Unified conversion function
        Z = self.get_zmatrix(freq, params)
        return z_to_s(Z, Z0)

    def get_matrix(self, freq: float, params: Dict[str, Any], Z0: float = 50) -> np.ndarray:
        """Return the S-matrix using the standard get_smatrix interface."""
        return self.get_smatrix(freq, params, Z0)
