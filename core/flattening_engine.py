import networkx as nx
from core.topology.circuit import Circuit
from core.exceptions import SubcircuitMappingError

def flatten_subcircuit(subcircuit) -> Circuit:
    # Clone the subcircuit's internal circuit and fetch its topology
    flat = subcircuit.circuit.clone()
    tm = flat.topology_manager
    orig_nodes = subcircuit.circuit.topology_manager.nodes

    # Map each external interface to the corresponding internal node
    for ext_port, int_node in subcircuit.interface_port_map.items():
        if int_node not in tm.nodes:
            if int_node in orig_nodes:
                tm.nodes[int_node] = orig_nodes[int_node]
            else:
                raise SubcircuitMappingError(
                    f"Internal node '{int_node}' for external port '{ext_port}' not found."
                )
        node = tm.nodes[int_node]
        old_name = node.name
        node.name = ext_port
        tm.nodes[ext_port] = node
        del tm.nodes[old_name]

        # Relabel the graph if needed
        if tm.graph.has_node(old_name):
            tm.graph = nx.relabel_nodes(tm.graph, {old_name: ext_port})
        
        # Update all component ports connected to the renamed node
        for comp in flat.components:
            for port in comp.ports:
                if port.connected_node and port.connected_node.name == old_name:
                    port.connected_node = node
    return flat
