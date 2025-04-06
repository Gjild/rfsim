import numpy as np
import pytest
from core.topology.circuit import Circuit
from components.resistor import ResistorComponent

def test_sweep_single_point(basic_circuit):
    from evaluation.sweep import sweep
    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6], "points": 1, "scale": "linear"}
        ]
    }
    result = sweep(basic_circuit, config)
    assert result.results, "Expected at least one sweep result."
    for key, S in result.results.items():
        assert S.shape[0] == S.shape[1]

def test_sweep_multi_parameter(basic_circuit):
    from evaluation.sweep import sweep
    basic_circuit.parameters["dummy"] = "1"
    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6], "points": 1, "scale": "linear"},
            {"param": "dummy", "values": [1, 2, 3]}
        ]
    }
    result = sweep(basic_circuit, config)
    assert len(result.results) == 3

def test_sweep_large_batch(complex_circuit):
    from evaluation.sweep import sweep
    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6 + 1e5], "points": 500, "scale": "linear"}
        ]
    }
    result = sweep(complex_circuit, config)
    assert len(result.results) == 500

def test_sweep_error_propagation(basic_circuit):
    # Force an error in one sweep point by assigning an invalid parameter.
    basic_circuit.parameters["dummy"] = "invalid"
    config = {
        "sweep": [
            {"param": "f", "range": [1e6, 1e6], "points": 1, "scale": "linear"},
            {"param": "dummy", "values": ["invalid"]}
        ]
    }
    from evaluation.sweep import sweep
    result = sweep(basic_circuit, config)
    # At least one error should be reported.
    assert result.errors, "Expected error propagation during sweep."
