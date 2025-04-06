import pytest
import numpy as np
from core.topology.circuit import Circuit
from core.topology.node import Node
from core.exceptions import RFSimError
from components.resistor import ResistorComponent

def test_self_loop_node():
    circuit = Circuit()
    resistor = ResistorComponent("R_self", {"R": "500"})
    circuit.add_component(resistor)
    node = Node("n_self")
    # Connect both ports to the same node.
    resistor.ports[0].connected_node = node
    resistor.ports[1].connected_node = node
    # Register the node in the topology manager.
    circuit.topology_manager.nodes["n_self"] = node
    with pytest.raises(RFSimError, match="Graph inconsistency: Registered node 'n_self' missing"):
        circuit.validate(verbose=False)

def test_duplicate_node_entries():
    from core.topology.node import Node  # Import once at the top of the function.
    circuit = Circuit()
    node = Node("shared")
    # Add two components that share the same node.
    for comp_id, resistance in [("R1", "1000"), ("R2", "2000")]:
        resistor = ResistorComponent(comp_id, {"R": resistance})
        resistor.ports[0].connected_node = node
        # For the second port, create a new node.
        resistor.ports[1].connected_node = Node(comp_id + "_n")
        circuit.add_component(resistor)
        circuit.topology_manager.nodes[node.name] = node
    circuit.validate(verbose=False)

def test_valid_topology():
    """
    Test a simple, valid topology where a single resistor connects two distinct nodes.
    This test verifies that the circuit validation passes without raising any errors.
    """
    circuit = Circuit()
    node1 = Node("n1")
    node2 = Node("n2")
    resistor = ResistorComponent("R1", {"R": "1000"})
    resistor.ports[0].connected_node = node1
    resistor.ports[1].connected_node = node2
    circuit.add_component(resistor)
    # Ensure that nodes are registered with the topology manager.
    circuit.topology_manager.nodes[node1.name] = node1
    circuit.topology_manager.nodes[node2.name] = node2

    # Expect validation to pass since the circuit is properly connected.
    circuit.validate(verbose=False)

def test_self_loop_topology():
    """
    Test for self-loop error where both ports of a component are connected to the same node.
    Such configurations can lead to an invalid network graph.
    """
    circuit = Circuit()
    node = Node("n_self")
    resistor = ResistorComponent("R_self", {"R": "500"})
    resistor.ports[0].connected_node = node
    resistor.ports[1].connected_node = node
    circuit.add_component(resistor)
    circuit.topology_manager.nodes[node.name] = node

    # Expect an RFSimError due to self-connection or graph inconsistency.
    with pytest.raises(RFSimError):
        circuit.validate(verbose=False)

def test_disconnected_graph():
    """
    Test for a circuit with two disconnected subgraphs.
    Even though individual components may be valid, the overall circuit graph must be fully connected.
    """
    circuit = Circuit()
    # Create two disjoint resistor components.
    node1 = Node("n1")
    node2 = Node("n2")
    node3 = Node("n3")
    node4 = Node("n4")
    r1 = ResistorComponent("R1", {"R": "1000"})
    r1.ports[0].connected_node = node1
    r1.ports[1].connected_node = node2
    r2 = ResistorComponent("R2", {"R": "2000"})
    r2.ports[0].connected_node = node3
    r2.ports[1].connected_node = node4
    circuit.add_component(r1)
    circuit.add_component(r2)
    # Register nodes with the topology manager.
    for n in (node1, node2, node3, node4):
        circuit.topology_manager.nodes[n.name] = n

    # Expect an error due to the overall circuit graph being disconnected.
    with pytest.raises(RFSimError):
        circuit.validate(verbose=False)

def test_duplicate_node_entries_improvement():
    """
    Test a scenario where multiple components share a common node.
    Verify that the topology manager correctly handles shared nodes and that validation passes.
    """
    circuit = Circuit()
    # Create a shared node.
    shared_node = Node("shared")
    # Two resistors share the same first node.
    r1 = ResistorComponent("R1", {"R": "1000"})
    r2 = ResistorComponent("R2", {"R": "2000"})
    r1.ports[0].connected_node = shared_node
    r1.ports[1].connected_node = Node("R1_n2")
    r2.ports[0].connected_node = shared_node
    r2.ports[1].connected_node = Node("R2_n2")
    circuit.add_component(r1)
    circuit.add_component(r2)
    # Register the shared node and the unique nodes.
    circuit.topology_manager.nodes[shared_node.name] = shared_node
    circuit.topology_manager.nodes[r1.ports[1].connected_node.name] = r1.ports[1].connected_node
    circuit.topology_manager.nodes[r2.ports[1].connected_node.name] = r2.ports[1].connected_node

    # Validation should pass as all nodes are connected within a single graph.
    circuit.validate(verbose=False)

def test_integration_with_topology_manager_updates():
    """
    Test that connecting and disconnecting ports via the topology manager
    properly updates the circuit's topology, and that these changes are reflected during validation.
    """
    circuit = Circuit()
    resistor = ResistorComponent("R_int", {"R": "1500"})
    circuit.add_component(resistor)
    # Initially, connect one port and leave the other floating.
    circuit.connect_port("R_int", "1", "n1")
    # Do not connect the second port, so validation should fail.
    with pytest.raises(RFSimError):
        circuit.validate(verbose=False)
    
    # Now connect the second port.
    circuit.connect_port("R_int", "2", "n2")
    # Manually register nodes if necessary.
    if "n1" not in circuit.topology_manager.nodes:
        circuit.topology_manager.nodes["n1"] = Node("n1")
    if "n2" not in circuit.topology_manager.nodes:
        circuit.topology_manager.nodes["n2"] = Node("n2")
    
    # With both ports connected, validation should now pass.
    circuit.validate(verbose=False)
