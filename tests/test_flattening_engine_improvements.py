import pytest
import numpy as np
from core.topology.circuit import Circuit
from core.topology.node import Node
from core.subcircuit.subcircuit import Subcircuit
from core.exceptions import SubcircuitMappingError
from core.flattening_engine import flatten_subcircuit

# Create a dummy circuit that simulates an internal circuit for a subcircuit.
class DummyCircuit(Circuit):
    def __init__(self):
        super().__init__()
        # Create internal nodes: n1, n2, n3.
        for name in ["n1", "n2", "n3"]:
            self.topology_manager.nodes[name] = Node(name)
    
    def assemble_global_ymatrix(self, freq, params):
        # Provide a fixed Y matrix and mapping for testing purposes.
        Y = np.array([
            [ 3, -1, -1],
            [-1,  3, -1],
            [-1, -1,  3]
        ], dtype=complex)
        mapping = {"n1": 0, "n2": 1, "n3": 2}
        return Y, mapping

def test_flatten_subcircuit_success():
    """
    Test that flattening a subcircuit correctly renames internal nodes
    according to the provided interface_port_map.
    
    In this test, the dummy circuit has internal nodes "n1", "n2", "n3".
    The interface_port_map maps:
      - "p1" to "n1"
      - "p2" to "n3"
    After flattening, the new circuit should have nodes "p1" and "p2", and "n1" should no longer exist.
    """
    dummy = DummyCircuit()
    interface_port_map = {"p1": "n1", "p2": "n3"}
    subckt = Subcircuit("SC1", dummy, interface_port_map)
    flat_circuit = flatten_subcircuit(subckt)
    
    # Verify that the new external nodes have been correctly set.
    topology_nodes = flat_circuit.topology_manager.nodes
    assert "p1" in topology_nodes, "Expected external node 'p1' in flattened circuit"
    assert "p2" in topology_nodes, "Expected external node 'p2' in flattened circuit"
    # The original node "n1" should have been renamed.
    assert "n1" not in topology_nodes, "Original internal node 'n1' should have been replaced"

def test_flatten_subcircuit_failure():
    """
    Test that flattening fails when the interface_port_map references a non-existent internal node.
    
    Here, the mapping contains an invalid reference: "p1" is mapped to "nonexistent".
    The flattening process should raise a SubcircuitMappingError.
    """
    dummy = DummyCircuit()
    interface_port_map = {"p1": "nonexistent", "p2": "n3"}
    subckt = Subcircuit("SC2", dummy, interface_port_map)
    
    with pytest.raises(SubcircuitMappingError):
        flatten_subcircuit(subckt)
