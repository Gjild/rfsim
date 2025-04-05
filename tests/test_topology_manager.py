import pytest
from core.topology.circuit import Circuit
from components.resistor import ResistorComponent

def test_add_component_without_connection():
    circuit = Circuit()
    # Create a resistor; its ports are unconnected.
    resistor = ResistorComponent("R1", params={"R": "1000"})
    circuit.add_component(resistor)
    # The component is registered.
    assert len(circuit.components) == 1
    # Topology remains empty since no port is connected.
    assert len(circuit.topology_manager.nodes) == 0
    assert len(circuit.topology_manager.graph.nodes) == 0
    assert len(circuit.topology_manager.graph.edges) == 0

def test_connect_port_updates_topology():
    circuit = Circuit()
    resistor = ResistorComponent("R1", params={"R": "1000"})
    circuit.add_component(resistor)
    # Connect port "1" to node "n1".
    circuit.connect_port("R1", "1", "n1")
    # Verify that node "n1" is now registered.
    assert "n1" in circuit.topology_manager.nodes
    # Verify that the graph contains node "n1".
    assert circuit.topology_manager.graph.has_node("n1")
    # An edge should exist between the component and node "n1".
    assert circuit.topology_manager.graph.has_edge("R1", "n1")
    # Verify that the resistor's port "1" now points to node "n1".
    port1 = next(p for p in resistor.ports if p.name == "1")
    assert port1.connected_node is not None
    assert port1.connected_node.name == "n1"

def test_multiple_port_connections():
    circuit = Circuit()
    resistor = ResistorComponent("R1", params={"R": "1000"})
    circuit.add_component(resistor)
    # Connect both ports to different nodes.
    circuit.connect_port("R1", "1", "n1")
    circuit.connect_port("R1", "2", "n2")
    # Verify that both nodes exist.
    assert "n1" in circuit.topology_manager.nodes
    assert "n2" in circuit.topology_manager.nodes
    # Verify graph edges exist for both connections.
    assert circuit.topology_manager.graph.has_edge("R1", "n1")
    assert circuit.topology_manager.graph.has_edge("R1", "n2")
    # Check that the ports are connected appropriately.
    port1 = next(p for p in resistor.ports if p.name == "1")
    port2 = next(p for p in resistor.ports if p.name == "2")
    assert port1.connected_node.name == "n1"
    assert port2.connected_node.name == "n2"
