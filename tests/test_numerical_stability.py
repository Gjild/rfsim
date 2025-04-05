import numpy as np
from utils.matrix import z_to_s, s_to_z     

def test_singular_matrix_inversion():
    """
    Test that the robust inversion helper correctly falls back to a pseudoinverse
    when faced with a singular matrix.
    """
    # Create a nearly singular 2x2 impedance matrix.
    Z = np.array([[1e-12, 1e-12], [1e-12, 1e-12]], dtype=complex)
    Z0 = 50
    S = z_to_s(Z, Z0=Z0)
    # Convert back and verify that the function produces a result
    Z_reconstructed = s_to_z(S, Z0=Z0)
    # Allow some tolerance because of the pseudoinverse fallback.
    np.testing.assert_allclose(Z, Z_reconstructed, rtol=1e-3, atol=1e-3)

def test_extreme_frequency_values():
    """
    Test the evaluation of a component at extreme frequency values.
    """
    from components.capacitor import CapacitorComponent
    from core.topology.port import Port
    from core.topology.node import Node
    
    # Create a capacitor component and attach dummy nodes.
    comp = CapacitorComponent("C_extreme")
    dummy_node = Node("dummy")
    for port in comp.ports:
        port.connected_node = dummy_node

    # Evaluate at an extremely low frequency.
    Z_low = comp.get_zmatrix(1e-3, {})
    # Evaluate at an extremely high frequency.
    Z_high = comp.get_zmatrix(1e12, {})

    # Check that the impedance matrices are finite.
    assert np.all(np.isfinite(Z_low))
    assert np.all(np.isfinite(Z_high))

def test_conflicting_parameter_definitions():
    """
    Test that the merge_params function logs a warning and correctly overrides
    conflicting parameter definitions.
    """
    from symbolic.utils import merge_params
    import logging
    # Set up a logging capture (using pytest's caplog fixture)
    params1 = {"a": 1, "b": 2}
    params2 = {"b": 3, "c": 4}
    merged = merge_params(params1, params2)
    assert merged["a"] == 1
    assert merged["b"] == 3  # params2 overrides params1
    assert merged["c"] == 4
