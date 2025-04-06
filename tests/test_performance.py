import time
import numpy as np
import pytest
from evaluation.sweep import sweep
from core.topology.circuit import Circuit
from components.resistor import ResistorComponent

@pytest.fixture
def perf_circuit():
    circuit = Circuit()
    resistor = ResistorComponent("R1", {"R": "1000"})
    circuit.add_component(resistor)
    from core.topology.node import Node
    node1 = Node("n1")
    node2 = Node("n2")
    resistor.ports[0].connected_node = node1
    resistor.ports[1].connected_node = node2
    circuit.topology_manager.nodes["n1"] = node1
    circuit.topology_manager.nodes["n2"] = node2
    circuit.external_ports = ["n1", "n2"]
    return circuit

def test_sweep_performance(perf_circuit):
    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6 + 1e5], "points": 1000, "scale": "linear"}
        ]
    }
    start = time.time()
    result = sweep(perf_circuit, config)
    elapsed = time.time() - start
    assert elapsed < 10, f"Sweep took too long: {elapsed} seconds"
    assert len(result.results) == 1000

@pytest.mark.skip(reason="Local benchmark only.")
def test_sweep_benchmark(benchmark, perf_circuit):
    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6 + 1e5], "points": 500, "scale": "linear"}
        ]
    }
    benchmark(lambda: sweep(perf_circuit, config))
