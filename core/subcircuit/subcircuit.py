# core/subcircuit/subcircuit.py
import numpy as np
import networkx as nx
from core.behavior.component import Component
from core.topology.port import Port
from symbolic.parameters import merge_params
from core.exceptions import SubcircuitMappingError
from core.topology.circuit import Circuit

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
        # Convert the submatrix to an S-matrix.
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
        
        This method clones the internal circuit using a custom clone mechanism,
        then renames the nodes corresponding to the external interface.
        
        Returns:
            A new Circuit instance representing the flattened subcircuit.
            
        Raises:
            SubcircuitMappingError: If any external interface mapping references a non-existent internal node.
        """
        # Use the custom clone method instead of a deep copy.
        flat_circuit: Circuit = self.circuit.clone()

        # Remap nodes: for each external port, rename the corresponding internal node.
        for ext_port, internal_node in self.interface_port_map.items():
            if internal_node not in flat_circuit.nodes:
                raise SubcircuitMappingError(
                    f"Internal node '{internal_node}' for external port '{ext_port}' not found."
                )
            # Retrieve and rename the node.
            node = flat_circuit.nodes[internal_node]
            old_name = node.name
            node.name = ext_port
            # Update the circuit's node dictionary.
            flat_circuit.nodes[ext_port] = node
            del flat_circuit.nodes[old_name]
            # Update the graph: relabel the internal node to the external port name.
            if flat_circuit.graph.has_node(old_name):
                flat_circuit.graph = nx.relabel_nodes(flat_circuit.graph, {old_name: ext_port})
            # Update port connections in all components.
            for comp in flat_circuit.components:
                for port in comp.ports:
                    if port.connected_node and port.connected_node.name == old_name:
                        port.connected_node = node

        return flat_circuit
