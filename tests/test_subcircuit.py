import pytest
import numpy as np
from core.subcircuit.subcircuit import Subcircuit
from core.topology.circuit import Circuit
from core.topology.node import Node
from core.exceptions import SubcircuitMappingError

class DummyCircuit(Circuit):
    def __init__(self):
        super().__init__()
        for n in ["n1", "n2", "n3", "n4"]:
            self.topology_manager.nodes[n] = Node(n)
    def assemble_global_ymatrix(self, freq, params):
        Y_global = np.array([
            [ 2, -1,  0, -1],
            [-1,  3, -1, -1],
            [ 0, -1,  2, -1],
            [-1, -1, -1,  3]
        ], dtype=complex)
        mapping = {"n1": 0, "n2": 1, "n3": 2, "n4": 3}
        return Y_global, mapping
    def clone(self):
        new_circuit = DummyCircuit()
        new_circuit.parameters = self.parameters.copy()
        new_circuit.components = [comp.clone() for comp in self.components]
        new_circuit.topology_manager.nodes = self.topology_manager.nodes.copy()
        new_circuit.topology_manager.graph = self.topology_manager.graph.copy()
        new_circuit.external_ports = self.external_ports.copy() if self.external_ports else None
        return new_circuit

def test_flatten_subcircuit_success():
    dummy = DummyCircuit()
    interface_port_map = {"p1": "n1", "p2": "n4"}
    subckt = Subcircuit("SC1", dummy, interface_port_map)
    flat = subckt.flatten()
    assert "p1" in flat.topology_manager.nodes
    assert "p2" in flat.topology_manager.nodes
    assert "n1" not in flat.topology_manager.nodes

def test_flatten_subcircuit_failure():
    dummy = DummyCircuit()
    interface_port_map = {"p1": "nonexistent", "p2": "n4"}
    subckt = Subcircuit("SC2", dummy, interface_port_map)
    with pytest.raises(SubcircuitMappingError, match="Internal node 'nonexistent' for external port 'p1' not found."):
        subckt.flatten()
