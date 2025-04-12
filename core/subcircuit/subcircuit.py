"""
core/subcircuit/subcircuit.py

This module defines the Subcircuit component, which encapsulates a hierarchical circuit.
It supports operations for obtaining S- and Z-parameters and flattening the subcircuit
into an equivalent flat Circuit.
"""

import numpy as np
import networkx as nx

from core.behavior.component import Component
from core.topology.port import Port
from core.topology.circuit import Circuit
from core.exceptions import SubcircuitMappingError
from symbolic.utils import merge_params
from utils.matrix import y_to_s, s_to_z  # Imported at module-level if no circular dependencies
from core.flattening_engine import flatten_subcircuit
from typing import Any, Dict


class Subcircuit(Component):
    def __init__(self, 
                 id: Any, 
                 circuit: Circuit, 
                 interface_port_map: Dict[str, str], 
                 params: Dict[str, Any] = None) -> None:
        """
        Initialize the Subcircuit component that encapsulates a hierarchical circuit.

        Parameters:
            id: Unique identifier for the subcircuit.
            circuit: The internal Circuit instance representing the subcircuit.
            interface_port_map: Mapping of external port names to internal node names.
            params: Optional dictionary of subcircuit parameters.
        """
        super().__init__(id, ports=[], params=params)
        self.circuit = circuit
        self.interface_port_map = interface_port_map

        # Create external ports using the keys of the interface mapping.
        self.ports = [
            Port(name=ext, index=i, connected_node=None)
            for i, ext in enumerate(interface_port_map.keys())
        ]

    def get_smatrix(self, freq: float, params: Dict[str, Any], Z0: float = 50) -> np.ndarray:
        """
        Compute the subcircuit's S-parameter matrix for a given frequency and parameters.

        Parameters:
            freq: The frequency at which to evaluate the matrix.
            params: Dictionary of parameter overrides.
            Z0: The reference impedance (default: 50 ohm).

        Returns:
            The S-matrix as an np.ndarray.

        Raises:
            SubcircuitMappingError: If an external port maps to an undefined internal node.
        """
        merged_params = merge_params(self.params, params)

        # Assemble the internal circuit's global admittance matrix.
        Y_global, node_index = self.circuit.assemble_global_ymatrix(freq, merged_params)

        # Map each external port to its corresponding internal node index.
        try:
            indices = [node_index[self.interface_port_map[ext_port]]
                       for ext_port in self.interface_port_map]
        except KeyError as e:
            raise SubcircuitMappingError(
                f"Internal node '{e.args[0]}' for external port mapping not found."
            ) from e

        # Extract the submatrix corresponding to the interface nodes and convert to S-parameters.
        sub_Y = Y_global[np.ix_(indices, indices)]
        return y_to_s(sub_Y, Z0)

    def get_zmatrix(self, freq: float, params: Dict[str, Any]) -> np.ndarray:
        """
        Compute the subcircuit's Z-parameter matrix for a given frequency and parameters.

        Parameters:
            freq: The frequency at which to evaluate the matrix.
            params: Dictionary of parameter overrides.

        Returns:
            The Z-matrix as an np.ndarray.
        """
        S = self.get_smatrix(freq, params, Z0=50)
        return s_to_z(S, Z0=50)

    def flatten(self) -> Circuit:
        """
        Flatten the subcircuit into an equivalent flat Circuit representation.

        Returns:
            A flat Circuit object that is electrically equivalent to the subcircuit.
        """
        return flatten_subcircuit(self)
