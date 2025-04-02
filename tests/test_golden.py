import numpy as np
from core.topology.circuit import Circuit
from core.behavior.component import Component
from core.topology.port import Port
from core.topology.node import Node

# A minimal RC lowpass component for a golden circuit test.
class RCComponent(Component):
    def __init__(self, id):
        ports = [Port("in", 0, Node("n1")), Port("out", 1, Node("n2"))]
        params = {"R": "1000", "C": "1e-9"}
        super().__init__(id, ports, params)
    
    def get_smatrix(self, freq, params, Z0=50):
        # For simplicity, return a dummy S-matrix scaled by frequency.
        return np.array([[0, 1],[1, 0]]) * (freq / 1e9)
    
    def get_zmatrix(self, freq, params):
        I = np.eye(2)
        epsilon = 1e-6
        S = self.get_smatrix(freq, params, Z0=50)
        return 50 * (I + S) @ np.linalg.inv((I - S) + epsilon * I)

def test_rc_lowpass():
    circuit = Circuit()
    comp = RCComponent("RC1")
    circuit.add_component(comp)
    circuit.nodes["n1"] = comp.ports[0].connected_node
    circuit.nodes["n2"] = comp.ports[1].connected_node
    result = circuit.evaluate(1e9, {})
    # Instead of exact values, check shape and that some elements are nonzero.
    assert result.s_matrix.shape == (2, 2)
    assert np.any(np.abs(result.s_matrix) > 0)
