# core/subcircuit/subcircuit.py
import numpy as np
import networkx as nx
from core.behavior.component import Component
from core.topology.port import Port
from symbolic.utils import merge_params
from core.exceptions import SubcircuitMappingError
from core.topology.circuit import Circuit
from core.flattening_engine import flatten_subcircuit

class Subcircuit(Component):
    def __init__(self, id, circuit, interface_port_map: dict, params=None):
        """
        Subcircuit component that encapsulates a hierarchical circuit.
        """
        super().__init__(id, ports=[], params=params)
        self.circuit = circuit
        self.interface_port_map = interface_port_map
        # Create external ports using the keys of the interface mapping.
        self.ports = [Port(name=ext, index=i, connected_node=None)
                      for i, ext in enumerate(interface_port_map.keys())]
    
    def get_smatrix(self, freq, params, Z0=50):
        merged_params = merge_params(self.params, params)
        # Assemble the internal circuit's global impedance matrix.
        Z_global, node_index = self.circuit.assemble_global_zmatrix(freq, merged_params)
        # Build indices for external ports based on the interface mapping.
        indices = []
        for ext_port, internal_node in self.interface_port_map.items():
            if internal_node not in node_index:
                raise SubcircuitMappingError(
                    f"Internal node '{internal_node}' for external port '{ext_port}' not found."
                )
            indices.append(node_index[internal_node])
        # Extract the submatrix corresponding to the interface nodes.
        sub_Z = Z_global[np.ix_(indices, indices)]
        from utils.matrix import z_to_s
        S = z_to_s(sub_Z, Z0)
        return S

    def get_zmatrix(self, freq, params):
        from utils.matrix import s_to_z
        S = self.get_smatrix(freq, params, Z0=50)
        return s_to_z(S, Z0=50)
    
    def flatten(self) -> Circuit:
        """
        Flatten the subcircuit into an equivalent flat Circuit.
        Delegates the flattening process to the flattening engine.
        """
        return flatten_subcircuit(self)
