import pytest
from core.topology_manager import TopologyManager
from core.topology.node import Node
from core.topology.port import Port
from core.exceptions import RFSimError

def test_add_and_remove_node():
    tm = TopologyManager()
    tm.add_node("n1")
    assert "n1" in tm.nodes
    tm.remove_node("n1")
    assert "n1" not in tm.nodes

def test_duplicate_node_error():
    tm = TopologyManager()
    tm.add_node("n1")
    with pytest.raises(RFSimError, match="Node 'n1' already exists."):
        tm.add_node("n1")

def test_update_topology_for_port():
    tm = TopologyManager()
    node = Node("n_test")
    port = Port("1", 0, connected_node=node)
    tm.update_topology_for_port("C1", port)
    assert "n_test" in tm.nodes
    # Check that the graph has an edge with a 'port' attribute.
    edges = list(tm.graph.edges(data=True))
    assert any("port" in data for (_, _, data) in edges)

def test_disconnect_port_effect():
    tm = TopologyManager()
    node = Node("n_test")
    port = Port("1", 0, connected_node=node)
    tm.update_topology_for_port("C1", port)
    tm.disconnect_port("C1", port)
    assert port.connected_node is None
