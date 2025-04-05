import yaml
import pytest
from core.topology.circuit import Circuit
import numpy as np

# Import the serializer functions.
from core.circuit_serializer import to_yaml_dict, to_yaml_file

# For tests requiring a dummy component, we define one as a proper subclass of Component.
from core.behavior.component import Component
from core.topology.port import Port

class DummyComponent(Component):
    type_name = "dummy"
    
    def __init__(self, comp_id="D1"):
        # Create two ports; nodes will be assigned externally.
        self.id = comp_id
        self.ports = [Port("1", 0, None), Port("2", 1, None)]
        self.params = {}
    
    def get_smatrix(self, freq, params, Z0=50):
        # Return a fixed S-matrix for testing.
        return np.array([[1+1j, -1j],
                         [-1j, 2+1j]], dtype=complex)
    
    def get_zmatrix(self, freq, params):
        I = np.eye(2)
        epsilon = 1e-6
        S = self.get_smatrix(freq, params, Z0=50)
        return 50 * (I + S) @ np.linalg.inv((I - S) + epsilon * I)

#############################
# Begin tests for the editor API
#############################

@pytest.fixture
def empty_circuit():
    # Create a fresh circuit with default context.
    return Circuit()

def test_add_component(empty_circuit):
    empty_circuit.add_component("R1", "resistor", {"R": "1000"})
    assert len(empty_circuit.components) == 1
    comp = empty_circuit.components[0]
    assert comp.id == "R1"
    assert comp.type_name == "resistor"
    # Use the serializer to generate the YAML dict.
    yaml_dict = to_yaml_dict(empty_circuit)
    assert "components" in yaml_dict
    assert yaml_dict["components"][0]["type"] == "resistor"

def test_remove_component(empty_circuit):
    empty_circuit.add_component("R1", "resistor", {"R": "1000"})
    empty_circuit.remove_component("R1")
    assert len(empty_circuit.components) == 0

def test_update_component_params(empty_circuit):
    empty_circuit.add_component("R1", "resistor", {"R": "1000"})
    empty_circuit.update_component_params("R1", {"R": "2000"})
    comp = empty_circuit.components[0]
    assert comp.params["R"] == "2000"

def test_replace_component_type(empty_circuit):
    empty_circuit.add_component("X1", "resistor", {"R": "1000"})
    empty_circuit.replace_component_type("X1", "capacitor", {"C": "1n"})
    comp = next((c for c in empty_circuit.components if c.id == "X1"), None)
    assert comp is not None
    assert comp.type_name == "capacitor"

def test_connect_disconnect_port(empty_circuit):
    empty_circuit.add_component("R1", "resistor", {"R": "1000"})
    comp = empty_circuit.components[0]
    # Initially, no ports are connected.
    for port in comp.ports:
        assert port.connected_node is None
    empty_circuit.connect_port("R1", "1", "n1")
    empty_circuit.connect_port("R1", "2", "n2")
    assert comp.ports[0].connected_node.name == "n1"
    assert comp.ports[1].connected_node.name == "n2"
    empty_circuit.disconnect_port("R1", "1")
    assert comp.ports[0].connected_node is None

def test_yaml_serialization(empty_circuit, tmp_path):
    empty_circuit.parameters = {"scale": 1.0}
    empty_circuit.add_component("R1", "resistor", {"R": "1000 * scale"})
    empty_circuit.add_component("C1", "capacitor", {"C": "1n"})
    empty_circuit.connect_port("R1", "1", "in")
    empty_circuit.connect_port("R1", "2", "n1")
    empty_circuit.connect_port("C1", "1", "n1")
    empty_circuit.connect_port("C1", "2", "out")
    netlist_dict = to_yaml_dict(empty_circuit)
    assert "parameters" in netlist_dict
    assert "components" in netlist_dict
    assert "connections" in netlist_dict
    yaml_file = tmp_path / "netlist_out.yml"
    to_yaml_file(empty_circuit, str(yaml_file))
    with open(yaml_file, "r") as f:
        loaded = yaml.safe_load(f)
    assert loaded["parameters"] == empty_circuit.parameters
    assert len(loaded["components"]) == len(empty_circuit.components)
