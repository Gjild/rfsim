import pytest
import yaml
from inout.yaml_parser import parse_netlist, parse_sweep_config, validate_schema
from core.exceptions import RFSimError

def test_parse_netlist_valid(tmp_path):
    netlist_content = """
parameters:
  scale: 1.0
external_ports:
  - name: p1
    impedance:
      type: fixed
      value: "50"
  - name: p2
    impedance:
      type: fixed
      value: "50"
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: p1
  - port: R1.2
    node: p2
"""
    file = tmp_path / "netlist.yaml"
    file.write_text(netlist_content)
    circuit = parse_netlist(str(file))
    assert len(circuit.components) == 1
    assert sorted(circuit.external_ports.keys()) == ["p1", "p2"]

def test_parse_sweep_config_valid(tmp_path):
    sweep_content = """
sweep:
  - param: f
    range: [1000000, 10000000]
    points: 10
    scale: linear
  - param: scale
    values: [1.0, 2.0]
"""
    file = tmp_path / "sweep.yaml"
    file.write_text(sweep_content)
    config = parse_sweep_config(str(file))
    assert "sweep" in config
    assert len(config["sweep"]) == 2

def test_parse_netlist_missing_keys(tmp_path):
    bad_netlist = """
components:
  - id: R1
    params:
      R: "1000"
    ports: ["1", "2"]
"""
    file = tmp_path / "bad_netlist.yaml"
    file.write_text(bad_netlist)
    with pytest.raises(RFSimError):
        parse_netlist(str(file))

def test_parse_yaml_invalid_format(tmp_path):
    bad_yaml = """
parameters: [not, a, dict]
external_ports: "p1, p2"
"""
    file = tmp_path / "bad_format.yaml"
    file.write_text(bad_yaml)
    with pytest.raises(Exception):
        parse_netlist(str(file))

# --- Netlist YAML Parsing Tests ---

def test_parse_valid_netlist(tmp_path):
    """
    Verify that a well-formed netlist YAML file is parsed into a Circuit with the expected properties.
    """
    netlist_content = """
parameters:
  scale: 1.0
external_ports:
  - name: p1
    impedance:
      type: fixed
      value: "50"
  - name: p2
    impedance:
      type: fixed
      value: "50" 
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: p1
  - port: R1.2
    node: p2
"""
    netlist_file = tmp_path / "netlist.yaml"
    netlist_file.write_text(netlist_content)
    
    # Parse netlist and verify that it produces a Circuit with one component and correct external ports.
    circuit = parse_netlist(str(netlist_file))
    assert len(circuit.components) == 1, "Expected one component in the parsed circuit"
    assert sorted(circuit.external_ports.keys()) == ["p1", "p2"], "External ports do not match the YAML configuration"

def test_parse_netlist_missing_required_keys(tmp_path):
    """
    Verify that a netlist YAML missing required keys (like type or id for a component) raises an exception.
    """
    incomplete_netlist = """
parameters:
  scale: 1.0
components:
  - id: R1
    params:
      R: "1000"
    ports: ["1", "2"]
"""
    netlist_file = tmp_path / "bad_netlist.yaml"
    netlist_file.write_text(incomplete_netlist)
    
    with pytest.raises(RFSimError):
        parse_netlist(str(netlist_file))

def test_parse_netlist_invalid_format(tmp_path):
    """
    Ensure that an improperly formatted YAML file (e.g., wrong types for parameters) fails validation.
    """
    bad_netlist_content = """
parameters: [not, a, dict]
external_ports: "p1, p2"
components:
  - id: R1
    type: resistor
    ports: ["1", "2"]
"""
    netlist_file = tmp_path / "bad_format_netlist.yaml"
    netlist_file.write_text(bad_netlist_content)
    
    with pytest.raises(Exception):
        # Expecting an exception from either YAML parsing or schema validation.
        parse_netlist(str(netlist_file))

# --- Sweep YAML Parsing Tests ---

def test_parse_valid_sweep_config(tmp_path):
    """
    Test that a valid sweep configuration YAML is parsed correctly into a dictionary with the proper structure.
    """
    sweep_content = """
sweep:
  - param: f
    range: [1e6, 1e7]
    points: 10
    scale: linear
  - param: scale
    values: [1, 2, 3]
"""
    sweep_file = tmp_path / "sweep.yaml"
    sweep_file.write_text(sweep_content)
    
    config = parse_sweep_config(str(sweep_file))
    assert "sweep" in config, "Parsed sweep config should contain a 'sweep' key"
    assert len(config["sweep"]) == 2, "Expected two sweep entries in the configuration"

def test_parse_sweep_config_invalid_entries(tmp_path):
    """
    Test that a sweep configuration with invalid entries (e.g., misspelt 'ranged' for frequency sweep)
    triggers validation errors.
    """
    bad_sweep_content = """
sweep:
  - param: f
    ranged: [1e6, 1e7]
    scale: linear
"""
    sweep_file = tmp_path / "bad_sweep.yaml"
    sweep_file.write_text(bad_sweep_content)
    
    with pytest.raises(RFSimError):
        parse_sweep_config(str(sweep_file))

def test_validate_schema_with_extra_keys(tmp_path):
    """
    Test that the schema validation fails when extra keys are present.
    """
    extra_keys_content = """
parameters:
  scale: 1.0
external_ports:
  - p1
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: p1
# An extra key not defined in the schema should trigger a validation error
extra_info: "This should cause a validation error"
"""
    data = yaml.safe_load(extra_keys_content)
    schema = {
        'parameters': {'type': 'dict', 'required': False},
        'external_ports': {'type': 'list', 'required': False, 'schema': {'type': 'string'}},
        'components': {
            'type': 'list',
            'required': True,
            'schema': {
                'type': 'dict',
                'schema': {
                    'id': {'type': 'string', 'required': True},
                    'type': {'type': 'string', 'required': True},
                    'params': {'type': 'dict', 'required': False},
                    'ports': {'type': 'list', 'required': True, 'schema': {'type': 'string'}}
                }
            }
        },
        'connections': {
            'type': 'list',
            'required': False,
            'schema': {
                'type': 'dict',
                'schema': {
                    'port': {'type': 'string', 'required': True},
                    'node': {'type': 'string', 'required': True}
                }
            }
        }
    }
    
    with pytest.raises(RFSimError, match="failed"):
        validate_schema(data, schema)
