# inout/yaml_parser.py
import yaml
import logging
from typing import Dict, Any
from cerberus import Validator
from core.topology.circuit import Circuit
from components.factory import get_component_class
from symbolic.utils import merge_params
from symbolic.evaluator import resolve_all_parameters
from core.exceptions import RFSimError
from utils.logging_config import get_logger
from ports.impedance_factory import create_impedance_model_from_config
from core.topology.port import Port



logger = get_logger(__name__)

# Define a schema for the netlist.
NETLIST_SCHEMA: Dict[str, Any] = {
    'parameters': {
        'type': 'dict',
        'required': False,
    },
    'external_ports': {
        'type': 'list',
        'required': False,
        'schema': {
            'type': 'dict',
            'schema': {
                'name': {
                    'type': 'string',
                    'required': True,
                },
                'impedance': {
                    'type': 'dict',
                    'required': True,
                    'schema': {
                        'type': {
                            'type': 'string',
                            'required': True,
                            'allowed': ['fixed', 'freq_dep', 's1p'],  # Extend as needed.
                        },
                        # For the "fixed" type, a "value" is expected.
                        'value': {
                            'type': 'string',
                            'required': False,
                        },
                        # For frequency-dependent impedances, a "function" key is required.
                        'function': {
                            'type': 'string',
                            'required': False,
                        },
                    }
                },
            }
        }
    },
    'components': {
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {
                    'type': 'string',
                    'required': True,
                },
                'type': {
                    'type': 'string',
                    'required': True,
                },
                'params': {
                    'type': 'dict',
                    'required': False,
                },
                'ports': {
                    'type': 'list',
                    'required': True,
                    'schema': {
                        'type': 'string'
                    },
                },
            },
        },
    },
    'connections': {
        'type': 'list',
        'required': False,
        'schema': {
            'type': 'dict',
            'schema': {
                'port': {
                    'type': 'string',
                    'required': True,
                },
                'node': {
                    'type': 'string',
                    'required': True,
                },
            },
        },
    },
}

SWEEP_SCHEMA = {
    'sweep': {
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'param': {'type': 'string', 'required': True},
                'range': {
                    'type': 'list',
                    'minlength': 2,
                    'maxlength': 2,
                    'schema': {'type': 'number', 'coerce': float},
                    'required': False
                },
                'points': {'type': 'integer', 'required': False},
                'scale': {
                    'type': 'string',
                    'allowed': ['linear', 'log'],
                    'required': False
                },
                'values': {'type': 'list', 'required': False}
            },
        },
    },
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
        # Fully resolve all parameters considering dependencies.
        circuit.parameters = resolve_all_parameters(data["parameters"])
    
        external_ports_data = data.get("external_ports", None)
        external_ports = {}
        if external_ports_data:
            for entry in external_ports_data:
                # entry is expected to be a dictionary.
                name = entry.get("name")
                impedance_spec = entry.get("impedance", {"type": "fixed", "value": "50"})
                port_obj = Port(name, index=0, impedance=create_impedance_model_from_config(impedance_spec))
                external_ports[name] = port_obj
            circuit.external_ports = external_ports
        else:
            circuit.external_ports = {}
    
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
            # Removed instance-level type assignment; type_name is now a class attribute.
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

    # -------------------------------------------
    # (1) Mark the "gnd" node (if it exists) as ground.
    # -------------------------------------------
    if "gnd" in circuit.topology_manager.nodes:
        node_obj = circuit.topology_manager.nodes["gnd"]
        node_obj.is_ground = True
    
    return circuit

def parse_sweep_config(yaml_file: str) -> Dict[str, Any]:
    """
    Parse and validate the sweep configuration YAML file.
    """
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    data = validate_schema(data, SWEEP_SCHEMA)
    return data
