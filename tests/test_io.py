import os
import yaml
from inout.yaml_parser import parse_netlist

def test_yaml_parser(tmp_path):
    netlist = {
        "components": [
            {"id": "R1", "type": "resistor", "params": {"R": "R0"}, "ports": ["1", "2"]}
        ],
        "connections": [
            {"port": "R1.1", "node": "n1"},
            {"port": "R1.2", "node": "n2"}
        ]
    }
    file_path = tmp_path / "netlist.yml"
    with open(file_path, "w") as f:
        yaml.dump(netlist, f)
    circuit = parse_netlist(str(file_path))
    # Now that components are successfully created, we expect one component.
    assert len(circuit.components) == 1
    comp = circuit.components[0]
    # Verify that each port is connected to a node.
    for port in comp.ports:
        assert port.connected_node is not None
