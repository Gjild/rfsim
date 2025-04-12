import time
import numpy as np
import pytest
from evaluation.sweep import sweep, SweepResult
from core.topology.circuit import Circuit
from components.resistor import ResistorComponent
from core.exceptions import RFSimError

@pytest.fixture
def perf_circuit():
    """
    Fixture for creating a simple circuit for performance and concurrency testing.
    """
    circuit = Circuit()
    resistor = ResistorComponent("R1", {"R": "1000"})
    circuit.add_component(resistor)
    from core.topology.node import Node
    from core.topology.port import Port  # Import Port for external ports
    # Connect resistor ports to two distinct nodes.
    node1 = Node("n1")
    node2 = Node("n2")
    resistor.ports[0].connected_node = node1
    resistor.ports[1].connected_node = node2
    # Register nodes with the topology manager.
    circuit.topology_manager.nodes[node1.name] = node1
    circuit.topology_manager.nodes[node2.name] = node2
    # Set external_ports as a dictionary mapping node names to Port objects.
    circuit.external_ports = {
        "n1": Port("n1", index=0, connected_node=node1, impedance=50),
        "n2": Port("n2", index=0, connected_node=node2, impedance=50)
    }
    return circuit

def test_parallel_sweep_performance(perf_circuit):
    """
    Test that a parallel sweep of many points completes within an acceptable time.
    This test simulates a high-load scenario and verifies that:
      - All sweep points are processed.
      - The overall execution time is within limits.
    """
    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6 + 1e5], "points": 1000, "scale": "linear"}
        ]
    }
    start_time = time.time()
    result = sweep(perf_circuit, config)
    elapsed = time.time() - start_time

    # Check that all 1000 sweep points have results.
    assert len(result.results) == 1000, f"Expected 1000 sweep results, got {len(result.results)}"
    # Set an upper threshold (e.g., 10 seconds) for acceptable performance.
    assert elapsed < 10, f"Sweep took too long: {elapsed:.2f} seconds"

def test_parallel_sweep_error_propagation(perf_circuit):
    """
    Test that errors in a parallel sweep are captured per sweep point.
    We simulate errors by injecting an invalid parameter for a fraction of the sweep.
    The evaluation should record errors without stopping the overall process.
    """
    # Modify the circuit so that one sweep point will trigger an error.
    # For example, set an invalid parameter value in the circuit's parameters.
    perf_circuit.parameters["dummy"] = "invalid"

    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6], "points": 1, "scale": "linear"},
            {"param": "dummy", "values": ["invalid", 1]}  # This will cause one point to error.
        ]
    }
    result = sweep(perf_circuit, config)
    # We expect at least one error among the sweep points.
    assert result.errors, "Expected at least one error to be recorded in sweep evaluation"
    # Verify that valid points still yield an S-matrix of the expected shape.
    for key, eval in result.results.items():
        if eval is not None:
            S = eval.s_matrix
            assert S.shape == (2, 2), f"Expected 2x2 S-matrix, got {S.shape}"

def test_concurrency_stability(perf_circuit):
    """
    Test the stability of concurrent sweep evaluations by repeating the sweep multiple times.
    This helps to ensure that parallel execution does not introduce intermittent errors or state corruption.
    """
    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6 + 5000], "points": 50, "scale": "linear"}
        ]
    }
    num_runs = 5
    results = []
    for _ in range(num_runs):
        result = sweep(perf_circuit, config)
        results.append(result)
    
    # Verify that each run produces 50 valid sweep results.
    for idx, result in enumerate(results):
        assert len(result.results) == 50, f"Run {idx}: Expected 50 results, got {len(result.results)}"
        for key, eval in result.results.items():
            if eval.s_matrix is not None:
                assert eval.s_matrix.shape == (2, 2), f"Run {idx}: Expected 2x2 S-matrix, got {eval.s_matrix.shape}"
