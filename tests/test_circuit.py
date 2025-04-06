import pytest
from core.topology.circuit import Circuit
from components.resistor import ResistorComponent
from core.exceptions import RFSimError

def test_add_and_remove_component():
    circuit = Circuit()
    resistor = ResistorComponent("R1", {"R": "1000"})
    circuit.add_component(resistor)
    assert len(circuit.components) == 1
    circuit.remove_component("R1")
    assert len(circuit.components) == 0

def test_update_component_params():
    circuit = Circuit()
    resistor = ResistorComponent("R1", {"R": "1000"})
    circuit.add_component(resistor)
    circuit.update_component_params("R1", {"R": "2000"})
    assert resistor.params["R"] == "2000"

def test_invalid_remove_component():
    circuit = Circuit()
    with pytest.raises(RFSimError, match="Component 'NON_EXISTENT' not found."):
        circuit.remove_component("NON_EXISTENT")

def test_connect_disconnect_port():
    circuit = Circuit()
    resistor = ResistorComponent("R1", {"R": "1000"})
    circuit.add_component(resistor)
    circuit.connect_port("R1", "1", "n1")
    assert resistor.ports[0].connected_node.name == "n1"
    circuit.disconnect_port("R1", "1")
    assert resistor.ports[0].connected_node is None

def test_topology_inconsistency(basic_circuit, dummy_logger):
    # Disconnect one port so that it becomes floating.
    basic_circuit.components[0].ports[0].connected_node = None
    with pytest.raises(RFSimError, match="Floating port"):
        basic_circuit.validate(verbose=False)

def test_duplicate_node_connection(complex_circuit):
    # Validate that sharing a node does not corrupt the graph.
    assert "n2" in complex_circuit.topology_manager.nodes
    complex_circuit.validate(verbose=False)
