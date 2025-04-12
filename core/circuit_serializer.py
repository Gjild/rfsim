# core/circuit_serializer.py
import yaml

def to_yaml_dict(circuit) -> dict:
    """
    Convert the circuit to a dictionary suitable for YAML serialization.
    
    Args:
        circuit: The Circuit object.
        
    Returns:
        A dictionary containing parameters, components, and connection definitions.
    """
    return {
        "parameters": circuit.parameters,
        "components": [comp.to_yaml_dict() for comp in circuit.components],
        "connections": [
            {"port": f"{comp.id}.{port.name}", "node": port.connected_node.name}
            for comp in circuit.components for port in comp.ports if port.connected_node
        ],
    }

def to_yaml_file(circuit, path: str) -> None:
    """
    Write the circuit's YAML representation to a file.
    
    Args:
        circuit: The Circuit object.
        path: The file path where the YAML should be written.
    """
    with open(path, "w") as f:
        yaml.dump(to_yaml_dict(circuit), f)
