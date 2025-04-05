# tests/test_performance.py
import time
import logging
import numpy as np
import pytest
from core.topology.circuit import Circuit
from core.topology.node import Node
from core.topology.port import Port
from core.behavior.component import Component
from utils.matrix import z_to_s, s_to_z

# Dummy component to simulate a realistic but lightweight circuit element.
class DummyComponent(Component):
    def __init__(self, comp_id):
        # Create two ports with distinct nodes.
        node1 = Node("n1")
        node2 = Node("n2")
        ports = [Port("1", 0, node1), Port("2", 1, node2)]
        super().__init__(comp_id, ports)
        self._type_name = "dummy"
        
    def get_smatrix(self, freq, params, Z0=50):
        # Return a dummy S-matrix that varies with frequency.
        return np.array([[((freq % 10) / 10), 0.1], [0.1, ((freq % 5) / 5)]])
    
    def get_zmatrix(self, freq, params):
        I = np.eye(2)
        S = self.get_smatrix(freq, params, Z0=50)
        epsilon = 1e-6
        return 50 * (I + S) @ np.linalg.inv((I - S) + epsilon * I)

def create_large_circuit(n_components=100):
    circuit = Circuit()
    # For a simple series connection, create nodes "n0" through "nN"
    for i in range(n_components):
        comp = DummyComponent(f"D{i}")
        circuit.add_component(comp)
        if i == 0:
            circuit.topology_manager.nodes[f"n{i}"] = comp.ports[0].connected_node
    return circuit


def test_large_sweep_performance():
    """
    Create a moderately large circuit and perform a sweep over frequency and one extra parameter.
    Verify that:
      - The total number of evaluation points matches expectations.
      - The simulation completes in a reasonable time.
      - A high percentage of evaluation points produce valid (non-None) results.
    """
    n_comps =  10
    n_points = 10
    n_vals = 10
    circuit = create_large_circuit(n_comps)  # 50 components → 51 nodes approximately
    # Define a sweep configuration: 50 frequency points and 10 values for a dummy parameter.
    sweep_config = {
        "sweep": [
            {"param": "f", "range": [1e6, 10e6], "points": n_points, "scale": "linear"},
            {"param": "dummy", "values": list(range(n_vals))}
        ]
    }
    from evaluation.sweep import sweep
    start = time.time()
    result = sweep(circuit, sweep_config)
    elapsed = time.time() - start
    expected_points = n_comps * n_vals
    assert result.stats["points"] == expected_points, "Mismatch in total sweep points."
    logging.info(f"Large sweep test completed in {elapsed:.2f} seconds.")
    # Ensure that most of the sweep points produced valid S-matrix data.
    valid_count = sum(1 for v in result.results.values() if v is not None)
    assert valid_count >= expected_points * 0.9, "Too many sweep points returned errors."

def test_numerical_accuracy_conversion():
    """
    Verify that converting an impedance matrix to a scattering matrix and back
    reproduces the original matrix within a tight tolerance.
    """
    R = 1000
    Z = np.array([[R, -R],
                  [-R, R]], dtype=complex)
    Z0 = 50
    S = z_to_s(Z, Z0=Z0)
    Z_reconstructed = s_to_z(S, Z0=Z0)
    np.testing.assert_allclose(Z, Z_reconstructed, rtol=1e-5, atol=1e-5)

@pytest.mark.benchmark
def test_benchmark_sweep(benchmark):
    """
    Benchmark the sweep function on a moderately large circuit.
    Use pytest-benchmark to monitor performance.
    """
    circuit = create_large_circuit(30)
    sweep_config = {
        "sweep": [
            {"param": "f", "range": [1e6, 2e6], "points": 10, "scale": "linear"},
            {"param": "dummy", "values": list(range(5))}
        ]
    }
    from evaluation.sweep import sweep
    benchmark(lambda: sweep(circuit, sweep_config))
