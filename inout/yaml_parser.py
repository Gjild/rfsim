# inout/yaml_parser.py
import yaml
import logging
from typing import Dict, Any
from cerberus import Validator
from core.topology.circuit import Circuit
from components.factory import get_component_class
from symbolic.parameters import merge_params, resolve_all_parameters
from core.exceptions import RFSimError
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Define a schema for the netlist.
NETLIST_SCHEMA: Dict[str, Any] = {
    'parameters': {'type': 'dict', 'required': False},
    # New schema entry for external ports.
    'external_ports': {
        'type': 'list',
        'required': False,
        'schema': {'type': 'string'}
    },
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

# Define a schema for the sweep configuration.
SWEEP_SCHEMA: Dict[str, Any] = {
    'sweep': {
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'param': {'type': 'string', 'required': True},
                # For frequency sweep, expect a range (list of 2 numbers) and points.
                'range': {'type': 'list', 'required': False, 'minlength': 2, 'maxlength': 2, 'schema': {'type': 'number'}},
                'points': {'type': 'integer', 'required': False},
                'scale': {'type': 'string', 'required': False, 'allowed': ['linear', 'log']},
                # For non-frequency parameters, we expect a list of values.
                'values': {'type': 'list', 'required': False}
            }
        }
    }
}

def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the YAML data against a given schema.
    
    Args:
        data: The YAML data as a dictionary.
        schema: The Cerberus schema definition.
    
    Returns:
        The validated document.
    
    Raises:
        RFSimError: If validation fails.
    """
    validator = Validator(schema)
    if not validator.validate(data):
        errors = validator.errors
        logger.error("YAML schema validation errors: %s", errors)
        raise RFSimError("YAML schema validation failed: " + str(errors))
    return validator.document

def parse_netlist(yaml_file: str) -> Circuit:
    """
    Parse the YAML netlist and return a Circuit object.
    
    Args:
        yaml_file: Path to the YAML netlist file.
    
    Returns:
        An instance of Circuit populated with components, connections, and external ports (if defined).
    
    Raises:
        RFSimError: On validation or connection errors.
    """
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    data = validate_schema(data, NETLIST_SCHEMA)
    
    circuit = Circuit()
    if "parameters" in data:
        # Resolve all parameters considering dependencies.
        circuit.parameters = resolve_all_parameters(data["parameters"])
    
    # Store external ports if provided.
    if "external_ports" in data:
        circuit.external_ports = data["external_ports"]
    else:
        circuit.external_ports = None

    # Component creation remains as before.
    for comp in data.get("components", []):
        comp_id = comp.get("id")
        comp_type = comp.get("type")
        comp_params = comp.get("params", {})
        if not comp_id or not comp_type:
            logger.error("Component entry missing 'id' or 'type'; skipping.")
            continue
        comp_params = merge_params(circuit.parameters, comp_params)
        try:
            ComponentClass = get_component_class(comp_type)
            component = ComponentClass(comp_id, comp_params)
            component._type_name = comp_type.lower()
        except Exception as e:
            logger.error("Error creating component '%s' of type '%s': %s", comp_id, comp_type, e)
            continue
        circuit.add_component(component)
    
    # Connection processing remains unchanged.
    for conn in data.get("connections", []):
        port_ref = conn.get("port")
        node_name = conn.get("node")
        if not port_ref or not node_name:
            logger.error("Connection entry missing 'port' or 'node'; skipping.")
            continue
        if "." not in port_ref:
            logger.error("Invalid port reference '%s'; must be in 'ComponentID.PortName' format.", port_ref)
            continue
        comp_id, port_name = port_ref.split(".")
        try:
            circuit.connect_port(comp_id, port_name, node_name)
        except RFSimError as e:
            logger.error("Error connecting '%s' to node '%s': %s", port_ref, node_name, e)
    
    return circuit

def parse_sweep_config(yaml_file: str) -> Dict[str, Any]:
    """
    Parse and validate the sweep configuration YAML file.
    """
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    data = validate_schema(data, SWEEP_SCHEMA)
    return data
