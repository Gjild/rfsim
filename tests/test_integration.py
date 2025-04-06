import os
import tempfile
import yaml
import numpy as np
import pytest
from inout.yaml_parser import parse_netlist, parse_sweep_config
from evaluation.sweep import sweep
from core.topology.circuit import Circuit
from core.exceptions import RFSimError
from core.circuit_serializer import to_yaml_dict  # New import


def test_full_integration_yaml_roundtrip(tmp_path):
    netlist_content = """
parameters:
  scale: 1.0
external_ports:
  - p1
  - p2
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
  - id: C1
    type: capacitor
    params:
      C: "1e-9"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: p1
  - port: R1.2
    node: n1
  - port: C1.1
    node: n1
  - port: C1.2
    node: p2
"""
    sweep_content = """
sweep:
  - param: f
    range: [1000000, 1000000]
    points: 1
    scale: linear
"""
    netlist_file = tmp_path / "netlist.yaml"
    sweep_file = tmp_path / "sweep.yaml"
    netlist_file.write_text(netlist_content)
    sweep_file.write_text(sweep_content)

    circuit = parse_netlist(str(netlist_file))
    sweep_config = parse_sweep_config(str(sweep_file))

    circuit.validate(verbose=False)
    result = sweep(circuit, sweep_config)
    assert result.results, "Expected sweep results."
    for key, S in result.results.items():
        assert S.shape == (2, 2)

    circuit_dict = to_yaml_dict(circuit)  # Use the serializer
    import yaml
    new_yaml = yaml.dump(circuit_dict)
    new_data = yaml.safe_load(new_yaml)
    assert "components" in new_data and "connections" in new_data

def test_full_integration_with_multiple_sweep_params(tmp_path):
    netlist_content = """
parameters:
  scale: 1.0
external_ports:
  - n1
  - n2
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: n1
  - port: R1.2
    node: n2
"""
    sweep_content = """
sweep:
  - param: f
    range: [1000000, 2000000]
    points: 3
    scale: linear
  - param: scale
    values: [1, 2]
"""
    netlist_file = tmp_path / "netlist.yaml"
    sweep_file = tmp_path / "sweep.yaml"
    netlist_file.write_text(netlist_content)
    sweep_file.write_text(sweep_content)

    circuit = parse_netlist(str(netlist_file))
    sweep_config = parse_sweep_config(str(sweep_file))
    
    circuit.validate(verbose=False)
    result = sweep(circuit, sweep_config)
    # 3 frequency points x 2 scale values = 6 results expected.
    assert len(result.results) == 6


def test_yaml_roundtrip_integration(tmp_path):
    """
    Integration test that parses a netlist YAML, validates the circuit, performs a sweep,
    and serializes the circuit back to YAML.
    
    This test verifies:
      - The circuit is correctly built from YAML.
      - Validation passes for a correctly connected circuit.
      - The sweep function produces the expected S-matrix shapes.
      - The circuit can be re-serialized to a valid YAML structure.
    """
    netlist_content = """
parameters:
  scale: 1.0
external_ports:
  - p1
  - p2
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
  - id: C1
    type: capacitor
    params:
      C: "1e-9"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: p1
  - port: R1.2
    node: n1
  - port: C1.1
    node: n1
  - port: C1.2
    node: p2
"""
    sweep_content = """
sweep:
  - param: f
    range: [1e6, 1e6]
    points: 1
    scale: linear
"""
    netlist_file = tmp_path / "netlist.yaml"
    sweep_file = tmp_path / "sweep.yaml"
    netlist_file.write_text(netlist_content)
    sweep_file.write_text(sweep_content)
    
    # Parse YAML files into circuit and sweep configuration.
    circuit = parse_netlist(str(netlist_file))
    sweep_config = parse_sweep_config(str(sweep_file))
    
    # Validate the circuit topology.
    circuit.validate(verbose=False)
    
    # Run the sweep evaluation.
    result = sweep(circuit, sweep_config)
    
    # Ensure at least one sweep result is produced and it has the expected shape.
    assert result.results, "Expected at least one sweep result."
    for key, S in result.results.items():
        assert S.shape == (2, 2), f"Expected 2x2 S-matrix, got shape {S.shape}"
    
    # Test YAML serialization roundtrip.
    circuit_dict = to_yaml_dict(circuit)
    new_yaml = yaml.dump(circuit_dict)
    new_data = yaml.safe_load(new_yaml)
    assert "components" in new_data, "Serialized YAML missing 'components' key"
    assert "connections" in new_data, "Serialized YAML missing 'connections' key"

def test_invalid_netlist_yaml(tmp_path):
    """
    Test that providing a malformed YAML netlist causes an appropriate exception.
    
    This test feeds an invalid YAML structure to the parser and expects it to fail,
    ensuring that improper configurations are caught early.
    """
    bad_netlist_content = """
parameters: [not, a, dict]
external_ports: "p1, p2"
components:
  - id: R1
    type: resistor
    ports: ["1", "2"]
"""
    bad_file = tmp_path / "bad_netlist.yaml"
    bad_file.write_text(bad_netlist_content)
    with pytest.raises(Exception):
        parse_netlist(str(bad_file))

def test_integration_multi_param_sweep(tmp_path):
    """
    Integration test that validates multi-parameter sweep behavior.
    
    This test sets up a netlist with a resistor and defines a sweep with two parameters:
    - Frequency ('f') over 3 points.
    - A dummy parameter ('scale') with two values.
    The expected outcome is 3 x 2 = 6 sweep results.
    """
    netlist_content = """
parameters:
  scale: 1.0
external_ports:
  - n1
  - n2
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: n1
  - port: R1.2
    node: n2
"""
    sweep_content = """
sweep:
  - param: f
    range: [1e6, 2e6]
    points: 3
    scale: linear
  - param: scale
    values: [1, 2]
"""
    netlist_file = tmp_path / "netlist.yaml"
    sweep_file = tmp_path / "sweep.yaml"
    netlist_file.write_text(netlist_content)
    sweep_file.write_text(sweep_content)
    
    circuit = parse_netlist(str(netlist_file))
    sweep_config = parse_sweep_config(str(sweep_file))
    
    circuit.validate(verbose=False)
    result = sweep(circuit, sweep_config)
    
    # Expect 3 frequency points x 2 scale values = 6 results.
    assert len(result.results) == 6, f"Expected 6 sweep results, got {len(result.results)}"

def test_sweep_error_propagation(tmp_path):
    """
    Test that errors in sweep evaluation are properly captured and reported.
    
    This test forces an error by providing an invalid value for a non-frequency parameter.
    The evaluation should record an error without crashing the overall sweep process.
    """
    netlist_content = """
parameters:
  scale: 1.0
external_ports:
  - n1
  - n2
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: n1
  - port: R1.2
    node: n2
"""
    sweep_content = """
sweep:
  - param: f
    range: [1e6, 1e6]
    points: 1
    scale: linear
  - param: dummy
    values: ["invalid"]
"""
    netlist_file = tmp_path / "netlist.yaml"
    sweep_file = tmp_path / "sweep.yaml"
    netlist_file.write_text(netlist_content)
    sweep_file.write_text(sweep_content)
    
    circuit = parse_netlist(str(netlist_file))
    sweep_config = parse_sweep_config(str(sweep_file))
    
    circuit.validate(verbose=False)
    result = sweep(circuit, sweep_config)
    
    assert result.errors, "Expected errors in sweep evaluation due to invalid parameter input"