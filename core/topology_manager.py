# core/topology_manager.py
import networkx as nx
from core.topology.node import Node
from core.topology.port import Port
from core.exceptions import RFSimError

class TopologyManager:
    """
    Manages nodes, ports, and the underlying network graph for a circuit.
    """
    def __init__(self):
        self.nodes = {}  # Dictionary: node name -> Node instance
        self.graph = nx.MultiGraph()

    def add_node(self, node_name: str, **attrs) -> None:
        """
        Add a new node to the topology.
        """
        if node_name in self.nodes:
            raise RFSimError(f"Node '{node_name}' already exists.")
        new_node = Node(node_name, **attrs)
        self.nodes[node_name] = new_node
        self.graph.add_node(node_name, node=new_node)

    def remove_node(self, node_name: str, force: bool = False) -> None:
        """
        Remove a node from the topology.
        """
        if node_name not in self.nodes:
            raise RFSimError(f"Node '{node_name}' does not exist.")
        # Optionally, one can check for connections before removal.
        del self.nodes[node_name]
        if self.graph.has_node(node_name):
            self.graph.remove_node(node_name)

    def register_external_port(self, comp_id: str, port: Port) -> None:
        """
        Register an external port with the topology.
        The port must have a connected node (a Node instance) assigned.
        """
        if port.connected_node is None:
            raise RFSimError(f"Cannot register external port {port}: no node connected.")
        node_name = port.connected_node.name
        # Add the node if it is not already present.
        if node_name not in self.nodes:
            self.add_node(node_name)
        # Add an edge from the component (comp_id) to the node,
        # storing the full Port object as part of the edge data.
        self.graph.add_edge(comp_id, node_name, port=port)

    def update_topology_for_port(self, comp_id: str, port: Port) -> None:
        """
        Update the topology for a specific port.
        This ensures that the port's connected node is registered and that the edge between
        the component and the node is current.
        """
        if port.connected_node is None:
            raise RFSimError(f"Port {port} is not connected to any node.")
        node_name = port.connected_node.name
        if node_name not in self.nodes:
            self.add_node(node_name)
        # Ensure the node exists in the graph.
        if not self.graph.has_node(node_name):
            self.graph.add_node(node_name, node=port.connected_node)
        # Add an edge from the component ID to the node with the full Port object.
        self.graph.add_edge(comp_id, node_name, port=port)

    def connect_port(self, comp_id: str, port: Port, node_name: str) -> None:
        """
        Connect a port to a node by name.
        """
        if node_name not in self.nodes:
            from core.topology.node import Node
            self.add_node(node_name)
        port.connected_node = self.nodes[node_name]
        self.update_topology_for_port(comp_id, port)

    def disconnect_port(self, comp_id: str, port: Port) -> None:
        """
        Disconnect a port from its node.
        """
        port.connected_node = None
        # Note: For simplicity, we leave the graph unchanged. A full rebuild might be needed.
