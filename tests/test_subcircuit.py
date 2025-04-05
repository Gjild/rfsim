# tests/test_subcircuit.py
import pytest
import numpy as np
from core.subcircuit.subcircuit import Subcircuit
from core.topology.circuit import Circuit
from core.topology.port import Port
from core.topology.node import Node
from core.exceptions import SubcircuitMappingError
from core.behavior.component import Component

# A dummy component for internal testing.
class DummyComponent(Component):
    def __init__(self, comp_id):
        # Create two ports connected to nodes "n1" and "n2"
        node1 = Node("n1")
        node2 = Node("n2")
        ports = [Port("out1", 0, node1), Port("out2", 1, node2)]
        super().__init__(comp_id, ports)
        self._type_name = "dummy"
    
    def get_smatrix(self, freq, params, Z0=50):
        # Return a fixed S-matrix.
        return np.array([[0.1, 0.2], [0.3, 0.4]])
    
    def get_zmatrix(self, freq, params):
        I = np.eye(2)
        S = self.get_smatrix(freq, params, Z0=50)
        epsilon = 1e-6
        return 50 * (I + S) @ np.linalg.inv((I - S) + epsilon * I)

def create_dummy_internal_circuit():
    circuit = Circuit()
    dummy = DummyComponent("dummy")
    circuit.add_component(dummy)
    # Register the nodes used in DummyComponent.
    circuit.topology_manager.nodes["n1"] = dummy.ports[0].connected_node
    circuit.topology_manager.nodes["n2"] = dummy.ports[1].connected_node
    return circuit

def test_subcircuit_get_smatrix():
    internal_circuit = create_dummy_internal_circuit()
    # Define a valid interface mapping.
    interface_map = {"external1": "n1", "external2": "n2"}
    subckt = Subcircuit("sub1", internal_circuit, interface_map)
    
    S = subckt.get_smatrix(1e9, {})
    assert S.shape == (2, 2)
    # Check that the S-matrix elements are finite.
    np.testing.assert_allclose(np.isfinite(S), True)

def test_subcircuit_get_smatrix_invalid_mapping():
    internal_circuit = create_dummy_internal_circuit()
    # Map one external port to a non-existent internal node.
    interface_map = {"external1": "n3", "external2": "n2"}
    subckt = Subcircuit("sub1", internal_circuit, interface_map)
    with pytest.raises(SubcircuitMappingError):
        subckt.get_smatrix(1e9, {})

def test_subcircuit_flatten():
    internal_circuit = create_dummy_internal_circuit()
    interface_map = {"ext1": "n1", "ext2": "n2"}
    subckt = Subcircuit("sub1", internal_circuit, interface_map)
    flat = subckt.flatten()
    # Verify that the flattened circuit has nodes renamed to external port names.
    assert "ext1" in flat.topology_manager.nodes
    assert "ext2" in flat.topology_manager.nodes
    # Check that the flattened circuit retains the same number of components.
    assert len(flat.components) == len(internal_circuit.components)
    # Optionally, verify that components connected to the interface nodes now point to the renamed nodes.

