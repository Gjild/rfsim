import pytest
from core.topology.circuit import Circuit
from core.topology.node import Node
from components.resistor import ResistorComponent
from components.capacitor import CapacitorComponent
from components.inductor import InductorComponent

@pytest.fixture
def basic_circuit():
    circuit = Circuit()
    resistor = ResistorComponent("R1", {"R": "1000"})
    circuit.add_component(resistor)
    node1 = Node("n1")
    node2 = Node("n2")
    resistor.ports[0].connected_node = node1
    resistor.ports[1].connected_node = node2
    circuit.topology_manager.nodes["n1"] = node1
    circuit.topology_manager.nodes["n2"] = node2
    circuit.external_ports = ["n1", "n2"]
    return circuit

@pytest.fixture
def complex_circuit():
    circuit = Circuit()
    # Create nodes
    nodes = {n: Node(n) for n in ["n1", "n2", "n3", "n4"]}
    for n in nodes.values():
        circuit.topology_manager.nodes[n.name] = n

    # Add a resistor between n1 and n2.
    r1 = ResistorComponent("R1", {"R": "1000"})
    r1.ports[0].connected_node = nodes["n1"]
    r1.ports[1].connected_node = nodes["n2"]
    circuit.add_component(r1)

    # Add a capacitor between n2 and n3.
    c1 = CapacitorComponent("C1", {"C": "1e-9"})
    c1.ports[0].connected_node = nodes["n2"]
    c1.ports[1].connected_node = nodes["n3"]
    circuit.add_component(c1)

    # Add an inductor between n3 and n4.
    l1 = InductorComponent("L1", {"L": "1e-6"})
    l1.ports[0].connected_node = nodes["n3"]
    l1.ports[1].connected_node = nodes["n4"]
    circuit.add_component(l1)

    # Connect another resistor between n1 and n3 to create an alternative path.
    r2 = ResistorComponent("R2", {"R": "500"})
    r2.ports[0].connected_node = nodes["n1"]
    r2.ports[1].connected_node = nodes["n3"]
    circuit.add_component(r2)

    circuit.external_ports = ["n1", "n4"]
    return circuit

@pytest.fixture
def dummy_logger(caplog):
    caplog.set_level("DEBUG")
    return caplog
