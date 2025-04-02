import numpy as np
import pytest
from components.resistor import ResistorComponent

class DummyNode:
    def __init__(self, name):
        self.name = name

def test_resistor_component_get_matrix():
    # Create a resistor with a symbolic parameter R set to "2000"
    resistor = ResistorComponent("R1", params={"R": "2000"})
    # Manually attach dummy nodes.
    for port in resistor.ports:
        port.connected_node = DummyNode("dummy")
    # Evaluate the S-matrix at 1 GHz.
    s_matrix = resistor.get_matrix(1e9, {})
    assert isinstance(s_matrix, np.ndarray)
    assert s_matrix.shape == (2, 2)
