"""
Module for flattening a subcircuit into an equivalent flat Circuit.
This utility handles:
  - Cloning the internal circuit.
  - Remapping internal nodes to external interface names.
  - Updating component port connections and the underlying graph.
  
Assumptions:
  - The subcircuit has an attribute `circuit` (the internal circuit)
    and an `interface_port_map` that maps external port names to internal node names.
  - The Circuit class has a clone() method and stores its node information in
    its topology manager (i.e. `circuit.topology_manager.nodes` and `circuit.topology_manager.graph`).
"""

import networkx as nx
from core.topology.circuit import Circuit
from core.exceptions import SubcircuitMappingError

def flatten_subcircuit(subcircuit) -> Circuit:
    """
    Flatten a subcircuit into an equivalent flat Circuit.
    
    The function performs the following steps:
      1. Clone the internal circuit.
      2. For each external interface defined in subcircuit.interface_port_map:
         - Check that the internal node exists.
         - Rename the node in the cloned circuit to the external name.
         - Update the topology manager's nodes dictionary.
         - Relabel the internal graph using networkx.relabel_nodes.
         - Update all component port connections that point to the renamed node.
    
    Args:
        subcircuit: An instance of Subcircuit.
    
    Returns:
        A new Circuit instance representing the flattened subcircuit.
    
    Raises:
        SubcircuitMappingError: If any external interface mapping references a non-existent internal node.
    """
    flat_circuit: Circuit = subcircuit.circuit.clone()
    tm = flat_circuit.topology_manager
    # If a required node is missing in the clone, retrieve it from the original
    original_nodes = subcircuit.circuit.topology_manager.nodes
    for ext_port, internal_node in subcircuit.interface_port_map.items():
        if internal_node not in tm.nodes:
            if internal_node in original_nodes:
                tm.nodes[internal_node] = original_nodes[internal_node]
            else:
                raise SubcircuitMappingError(
                    f"Internal node '{internal_node}' for external port '{ext_port}' not found."
                )
        # Now, rename the node and update the topology
        node = tm.nodes[internal_node]
        old_name = node.name
        node.name = ext_port
        tm.nodes[ext_port] = node
        del tm.nodes[old_name]
        if tm.graph.has_node(old_name):
            tm.graph = nx.relabel_nodes(tm.graph, {old_name: ext_port})
        for comp in flat_circuit.components:
            for port in comp.ports:
                if port.connected_node and port.connected_node.name == old_name:
                    port.connected_node = node
    return flat_circuit
