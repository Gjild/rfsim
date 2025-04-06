import pytest
from components.factory import get_component_class, register_component
from core.exceptions import RFSimError
from components.capacitor import CapacitorComponent
from core.topology.port import Port  # New import at top


def test_get_component_class_valid():
    cls = get_component_class("capacitor")
    assert cls is CapacitorComponent

def test_get_component_class_invalid_type():
    with pytest.raises(RFSimError, match="Unknown component type"):
        get_component_class("nonexistent")

def test_get_component_class_non_string():
    with pytest.raises(RFSimError, match="Component type name must be a string"):
        get_component_class(123)

def test_register_component_invalid():
    with pytest.raises(RFSimError, match="Registered component must be a subclass of Component"):
        register_component("test", int)

def test_register_component_custom():
    from core.behavior.component import Component
    class DummyComponent(Component):
        type_name = "dummy"
        def get_smatrix(self, freq, params, Z0=50):
            import numpy as np
            return np.array([[0]])
    register_component("dummy", DummyComponent)
    cls = get_component_class("dummy")
    assert cls is DummyComponent

def test_dynamic_component_integration():
    from core.topology.circuit import Circuit
    from core.behavior.component import Component
    import numpy as np
    class DummyComponent(Component):
        type_name = "dummy2"
        def get_smatrix(self, freq, params, Z0=50):
            return np.array([[1, 0], [0, 1]])
    register_component("dummy2", DummyComponent)
    circuit = Circuit()
    # Create two dummy ports for the component.
    dummy = DummyComponent("D1", ports=[Port("1", 0, None), Port("2", 1, None)], params={})
    circuit.add_component(dummy)
    from core.topology.node import Node
    dummy.ports[0].connected_node = Node("n1")
    dummy.ports[1].connected_node = Node("n2")
    circuit.topology_manager.nodes["n1"] = dummy.ports[0].connected_node
    circuit.topology_manager.nodes["n2"] = dummy.ports[1].connected_node
    S = dummy.get_smatrix(1e6, {})
    np.testing.assert_array_equal(S, np.array([[1, 0], [0, 1]]))
