import numpy as np
import pytest
from components.resistor import ResistorComponent
from components.capacitor import CapacitorComponent
from components.inductor import InductorComponent
from components.transmission_line import TransmissionLineComponent
from core.topology.node import Node
from core.exceptions import RFSimError

# Dummy node for attaching ports.
dummy_node = Node("dummy")

@pytest.mark.parametrize("ComponentClass, param_key, default_value", [
    (ResistorComponent, "R", 1000),
    (CapacitorComponent, "C", 1e-9),
    (InductorComponent, "L", 1e-6),
])
def test_two_port_components_get_zmatrix(ComponentClass, param_key, default_value):
    comp = ComponentClass("test")
    for port in comp.ports:
        port.connected_node = dummy_node
    # Evaluate at 1 GHz.
    Z = comp.get_zmatrix(1e9, {})
    assert Z.shape == (2, 2)
    # Instead of checking that one off-diagonal equals the negative of the other,
    # check that the sum of each row is approximately zero.
    np.testing.assert_allclose(Z[0, 0] + Z[0, 1], 0, atol=1e-3)
    np.testing.assert_allclose(Z[1, 0] + Z[1, 1], 0, atol=1e-3)

def test_transmission_line_get_zmatrix():
    comp = TransmissionLineComponent("TL1", params={"Z0": "50", "length": "0.1", "beta": "2*pi/0.3"})
    for port in comp.ports:
        port.connected_node = dummy_node
    Z = comp.get_zmatrix(1e9, {})
    assert Z.shape == (2, 2)
    # For a lossless TL, the magnitudes of the off-diagonals should be similar.
    np.testing.assert_allclose(np.abs(Z[0, 1]), np.abs(Z[1, 0]), rtol=1e-2)

def test_component_factory():
    from components.factory import get_component_class
    Cls = get_component_class("resistor")
    assert Cls.__name__ == "ResistorComponent"
    # Expect RFSimError now.
    with pytest.raises(RFSimError):
        get_component_class("nonexistent")
