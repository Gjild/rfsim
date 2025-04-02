import os
import yaml
import pytest
import tempfile

from core.topology.circuit import Circuit, EvaluationContext, EvaluationResult
from core.topology.node import Node
from components.factory import get_component_class
from symbolic.parameters import merge_params
import numpy as np

# For tests requiring a dummy component, we define one as a proper subclass of Component.
from core.behavior.component import Component
from core.topology.port import Port

class DummyComponent(Component):
    def __init__(self, comp_id="D1"):
        # Create two ports; nodes will be assigned externally.
        from core.topology.port import Port
        self.id = comp_id
        self.ports = [Port("1", 0, None), Port("2", 1, None)]
        self.params = {}
        self._type_name = "dummy"
    
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
    # YAML dict should include the component type.
    yaml_dict = empty_circuit.to_yaml_dict()
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

def test_add_and_remove_node(empty_circuit):
    empty_circuit.add_node("n1", label="Input")
    assert "n1" in empty_circuit.nodes
    empty_circuit.remove_node("n1")
    assert "n1" not in empty_circuit.nodes

def test_connect_disconnect_port(empty_circuit):
    empty_circuit.add_component("R1", "resistor", {"R": "1000"})
    comp = empty_circuit.components[0]
    for port in comp.ports:
        assert port.connected_node is None
    empty_circuit.connect_port("R1", "1", "n1")
    empty_circuit.connect_port("R1", "2", "n2")
    assert comp.ports[0].connected_node.name == "n1"
    assert comp.ports[1].connected_node.name == "n2"
    empty_circuit.disconnect_port("R1", "1")
    assert comp.ports[0].connected_node is None

def test_validate_on_change(empty_circuit):
    empty_circuit.validate_on_change(True)
    empty_circuit.add_node("n1")
    empty_circuit.add_component("R1", "resistor", {"R": "1000"})
    # Both ports of R1 are still unconnected.
    with pytest.raises(Exception) as excinfo:
        empty_circuit.validate_now()
    assert "Floating port" in str(excinfo.value)
    empty_circuit.validate_on_change(False)

def test_transaction(empty_circuit):
    empty_circuit.validate_on_change(True)
    # In a transaction, validation is deferred until exit.
    with pytest.raises(Exception):
        with empty_circuit.transaction():
            empty_circuit.add_node("n1")
            empty_circuit.add_component("R1", "resistor", {"R": "1000"})
            empty_circuit.connect_port("R1", "1", "n1")
            # Port "2" remains unconnected, so final validation should fail.
    empty_circuit.validate_on_change(False)

def test_yaml_serialization(empty_circuit, tmp_path):
    empty_circuit.parameters = {"scale": 1.0}
    empty_circuit.add_component("R1", "resistor", {"R": "1000 * scale"})
    empty_circuit.add_component("C1", "capacitor", {"C": "1n"})
    empty_circuit.connect_port("R1", "1", "in")
    empty_circuit.connect_port("R1", "2", "n1")
    empty_circuit.connect_port("C1", "1", "n1")
    empty_circuit.connect_port("C1", "2", "out")
    netlist_dict = empty_circuit.to_yaml_dict()
    assert "parameters" in netlist_dict
    assert "components" in netlist_dict
    assert "connections" in netlist_dict
    yaml_file = tmp_path / "netlist_out.yml"
    empty_circuit.to_yaml_file(str(yaml_file))
    with open(yaml_file, "r") as f:
        loaded = yaml.safe_load(f)
    assert loaded["parameters"] == empty_circuit.parameters
    assert len(loaded["components"]) == len(empty_circuit.components)

def test_full_lifecycle(tmp_path):
    # Write an initial netlist YAML.
    initial_netlist = {
        "parameters": {"scale": 1.0},
        "components": [
            {"id": "R1", "type": "resistor", "params": {"R": "1000 * scale"}, "ports": ["1", "2"]},
            {"id": "C1", "type": "capacitor", "params": {"C": "1n"}, "ports": ["2", "3"]}
        ],
        "connections": [
            {"port": "R1.1", "node": "in"},
            {"port": "R1.2", "node": "n1"},
            {"port": "C1.1", "node": "n1"},
            {"port": "C1.2", "node": "out"}
        ]
    }
    init_file = tmp_path / "init_netlist.yml"
    with open(init_file, "w") as f:
        yaml.dump(initial_netlist, f)
    from inout.yaml_parser import parse_netlist
    circuit = parse_netlist(str(init_file))
    # Mutate: update R1, replace C1, add node, reconnect.
    circuit.update_component_params("R1", {"R": "2000 * scale"})
    circuit.replace_component_type("C1", "transmission_line", {"Z0": "50", "length": "0.05", "beta": "2*pi/0.3"})
    circuit.add_node("extra")
    circuit.connect_port("R1", "1", "extra")
    circuit.remove_node("in", force=True)
    yaml_dict = circuit.to_yaml_dict()
    new_file = tmp_path / "modified_netlist.yml"
    circuit.to_yaml_file(str(new_file))
    circuit2 = parse_netlist(str(new_file))
    result = circuit2.evaluate(1e6, {"scale": 1.0})
    assert result.s_matrix.shape[0] > 0

def test_global_zmatrix_assembly():
    # Create a circuit and add nodes manually.
    circuit = Circuit()
    from core.topology.node import Node
    circuit.nodes["n1"] = Node("n1")
    circuit.nodes["n2"] = Node("n2")
    # Create a dummy component that subclasses Component.
    class DummyComponent(Component):
        def __init__(self, comp_id="D1"):
            from core.topology.port import Port
            self.id = comp_id
            self.ports = [Port("1", 0, circuit.nodes["n1"]),
                          Port("2", 1, circuit.nodes["n2"])]
            self.params = {}
            self._type_name = "dummy"
        def get_smatrix(self, freq, params, Z0=50):
            return np.array([[1+1j, -1j], [-1j, 2+1j]], dtype=complex)
        def get_zmatrix(self, freq, params):
            I = np.eye(2)
            epsilon = 1e-6
            S = self.get_smatrix(freq, params, Z0=50)
            return 50 * (I + S) @ np.linalg.inv((I - S)+epsilon*I)
    dummy = DummyComponent()
    circuit.add_component(dummy)
    Z_global, node_index = circuit.assemble_global_zmatrix(1e9, {})
    assert Z_global.shape == (2, 2)
    # Check that the diagonal entries are greater than 50 (termination added).
    assert np.all(np.abs(np.diag(Z_global)) > 50)

