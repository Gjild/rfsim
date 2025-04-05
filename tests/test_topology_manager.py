# tests/test_topology_manager.py
import pytest
import networkx as nx
from core.topology.circuit import Circuit
from components.resistor import ResistorComponent

def test_add_component_without_connection():
    circuit = Circuit()
    # Create a resistor component (its ports are unconnected by default)
    resistor = ResistorComponent("R1", params={"R": "1000"})
    circuit.add_component(resistor)
    # The component is registered
    assert len(circuit.components) == 1
    # No ports are connected so the topology should remain empty.
    assert len(circuit.nodes) == 0
    assert len(circuit.graph.nodes) == 0
    assert len(circuit.graph.edges) == 0

def test_connect_port_updates_topology():
    circuit = Circuit()
    resistor = ResistorComponent("R1", params={"R": "1000"})
    circuit.add_component(resistor)
    # Connect port "1" to node "n1"
    circuit.connect_port("R1", "1", "n1")
    # Verify that the node "n1" is created and registered.
    assert "n1" in circuit.nodes
    # The graph should contain node "n1"
    assert circuit.graph.has_node("n1")
    # An edge should exist between the component and node "n1"
    assert circuit.graph.has_edge("R1", "n1")
    # Verify that the resistor's port "1" now points to node "n1"
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
    assert "n1" in circuit.nodes
    assert "n2" in circuit.nodes
    # Verify graph edges exist for both connections.
    assert circuit.graph.has_edge("R1", "n1")
    assert circuit.graph.has_edge("R1", "n2")
    # Check that the ports are connected appropriately.
    port1 = next(p for p in resistor.ports if p.name == "1")
    port2 = next(p for p in resistor.ports if p.name == "2")
    assert port1.connected_node.name == "n1"
    assert port2.connected_node.name == "n2"
