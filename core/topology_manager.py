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
        self.nodes = {}  # Map of node name to Node instance
        self.graph = nx.MultiGraph()

    def add_node(self, node_name: str, **attrs) -> None:
        if node_name in self.nodes:
            raise RFSimError(f"Node '{node_name}' already exists.")
        node = Node(node_name, **attrs)
        self.nodes[node_name] = node
        self.graph.add_node(node_name, node=node)

    def remove_node(self, node_name: str, force: bool = False) -> None:
        if node_name not in self.nodes:
            raise RFSimError(f"Node '{node_name}' does not exist.")
        del self.nodes[node_name]
        if self.graph.has_node(node_name):
            self.graph.remove_node(node_name)

    def register_external_port(self, comp_id: str, port: Port) -> None:
        if not port.connected_node:
            raise RFSimError(f"Cannot register external port {port}: no node connected.")
        node_name = port.connected_node.name
        if node_name not in self.nodes:
            self.add_node(node_name)
        self.graph.add_edge(comp_id, node_name, port=port)

    def update_topology_for_port(self, comp_id: str, port: Port) -> None:
        if not port.connected_node:
            raise RFSimError(f"Port {port} is not connected to any node.")
        node_name = port.connected_node.name
        if node_name not in self.nodes:
            self.add_node(node_name)
        if not self.graph.has_node(node_name):
            self.graph.add_node(node_name, node=port.connected_node)
        self.graph.add_edge(comp_id, node_name, port=port)

    def connect_port(self, comp_id: str, port: Port, node_name: str) -> None:
        if node_name not in self.nodes:
            self.add_node(node_name)
        port.connected_node = self.nodes[node_name]
        self.update_topology_for_port(comp_id, port)

    def disconnect_port(self, comp_id: str, port: Port) -> None:
        port.connected_node = None
        # The graph remains unchanged; a full rebuild would be required for cleanup.
