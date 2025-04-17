# core/topology/netlist_graph.py
"""
NetlistGraph for RFSim v2: captures circuit connectivity strictly in terms of nets (nodes).
Provides stable index mapping for matrix assembly.
Supports both static models with raw connection specs and live Circuit instances.
"""
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field


@dataclass
class PortConnection:
    """
    Represents a single port-to-net mapping.
    """
    component_id: str
    port_name: str
    net_name: str


class NetlistGraph:
    """
    Represents the connectivity graph of a circuit at the net (node) level.
    Nodes are net names; edges are implicit via PortConnection records.
    """
    def __init__(self):
        # Set of all net names in the circuit
        self._nets: Set[str] = set()
        # List of all port-to-net assignments
        self._connections: List[PortConnection] = []
        # Cached mapping from net name to matrix index
        self._node_index: Optional[Dict[str, int]] = None

    @classmethod
    def from_circuit(cls, circuit) -> "NetlistGraph":
        """
        Build a NetlistGraph from:
          - A CircuitModel: use its `connections` list.
          - A live Circuit: inspect each Component's ports for connected_node.
        """
        graph = cls()
        # Static model with raw connections
        if hasattr(circuit, 'connections') and isinstance(circuit.connections, list):
            for conn in circuit.connections:
                graph.add_connection(conn.component_id, conn.port_name, conn.net_name)
            return graph

        # Live Circuit: inspect ports connected_node
        for comp in circuit.components:
            for port in comp.ports:
                node = getattr(port, 'connected_node', None)
                if node is not None:
                    graph.add_connection(comp.id, port.name, node.name)
        return graph

    def add_connection(self, component_id: str, port_name: str, net_name: str) -> None:
        """
        Record that component.port is tied to net_name.
        Resets cached index mapping.
        """
        self._nets.add(net_name)
        self._connections.append(PortConnection(component_id, port_name, net_name))
        self._node_index = None

    def remove_connection(self, component_id: str, port_name: str, net_name: str) -> None:
        """
        Remove a specific port-to-net connection, if present.
        """
        to_remove = PortConnection(component_id, port_name, net_name)
        try:
            self._connections.remove(to_remove)
        except ValueError:
            raise KeyError(f"Connection {to_remove} not found in NetlistGraph.")
        # Rebuild net list from remaining connections
        self._nets = {c.net_name for c in self._connections}
        self._node_index = None

    def nodes(self) -> List[str]:
        """
        Return a sorted list of net names.
        """
        return sorted(self._nets)

    def connections(self) -> List[PortConnection]:
        """
        Return the recorded port-to-net assignments.
        """
        return list(self._connections)

    def node_index(self, ground_net: Optional[str] = None) -> Dict[str, int]:
        """
        Return a mapping from net name to integer index for matrix axes.
        If ground_net is given and present, it will be assigned index 0.
        Caches the result until connections change.
        """
        if self._node_index is not None:
            return self._node_index

        nets = list(self._nets)
        if ground_net and ground_net in nets:
            nets.remove(ground_net)
            nets = [ground_net] + nets
        else:
            nets.sort()

        self._node_index = {net: idx for idx, net in enumerate(nets)}
        return self._node_index

    def dimension(self) -> int:
        """
        Number of distinct nets in the circuit.
        """
        return len(self._nets)

    def __repr__(self) -> str:
        return (
            f"<NetlistGraph nets={len(self._nets)} connections={len(self._connections)}>"
        )
