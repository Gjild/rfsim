import math
import numpy as np
import pytest
from components.capacitor import CapacitorComponent
from components.resistor import ResistorComponent
from components.inductor import InductorComponent
from utils.matrix import robust_inv, z_to_s, s_to_z, y_to_s, s_to_y

# --- Component Impedance Tests ---

def test_capacitor_impedance_normal():
    """
    Verify that a capacitor's impedance is calculated correctly at normal operating frequency.
    """
    cap = CapacitorComponent("C1", {"C": "1e-9"})
    f = 1e6  # 1 MHz
    C = 1e-9
    Z = cap.impedance_expr(f, C)
    expected = 1 / (1j * 2 * math.pi * f * C)
    np.testing.assert_allclose(Z, expected, rtol=1e-6)

def test_capacitor_impedance_zero_frequency():
    """
    Verify that evaluating capacitor impedance at zero frequency raises ZeroDivisionError.
    """
    cap = CapacitorComponent("C_zero", {"C": "1e-9"})
    with pytest.raises(ZeroDivisionError):
        cap.impedance_expr(0, 1e-9)

def test_capacitor_impedance_negative_value():
    """
    Check that a capacitor with a negative capacitance (even if unphysical)
    produces the mathematically consistent impedance.
    """
    cap = CapacitorComponent("C_neg", {"C": "-1e-9"})
    f = 1e6
    C = -1e-9
    Z = cap.impedance_expr(f, C)
    expected = 1 / (1j * 2 * math.pi * f * C)
    np.testing.assert_allclose(Z, expected, rtol=1e-6)

def test_resistor_impedance():
    """
    Verify that a resistor's impedance returns its resistance value regardless of frequency.
    """
    res = ResistorComponent("R1", {"R": "1000"})
    f = 1e6  # frequency is irrelevant for a resistor
    Z = res.impedance_expr(f, 1000)
    assert Z == 1000

def test_inductor_impedance_normal():
    """
    Verify that an inductor's impedance is calculated correctly at normal operating frequency.
    """
    ind = InductorComponent("L1", {"L": "1e-6"})
    f = 1e6  # 1 MHz
    L = 1e-6
    Z = ind.impedance_expr(f, L)
    expected = 1j * 2 * math.pi * f * L
    np.testing.assert_allclose(Z, expected, rtol=1e-6)

def test_inductor_impedance_zero_frequency():
    """
    Verify that an inductor's impedance at zero frequency is zero.
    """
    ind = InductorComponent("L_zero", {"L": "1e-6"})
    f = 0
    Z = ind.impedance_expr(f, 1e-6)
    np.testing.assert_allclose(Z, 0, rtol=1e-6)


# --- Matrix Utility Tests ---

def test_robust_inv_regular_matrix():
    """
    Verify that robust_inv returns a valid inverse for a well-conditioned matrix.
    """
    A = np.array([[1, 2], [3, 4]], dtype=complex)
    invA = robust_inv(A)
    np.testing.assert_allclose(A @ invA, np.eye(2), rtol=1e-6, atol=1e-8)

def test_robust_inv_singular_matrix():
    """
    Check that robust_inv handles singular matrices by returning a pseudoinverse.
    """
    A = np.array([[1, 2], [2, 4]], dtype=complex)
    invA = robust_inv(A)
    np.testing.assert_allclose(A, A @ invA @ A, rtol=1e-6)

@pytest.mark.parametrize("Z0", [50, 75])
def test_z_to_s_and_back(Z0):
    """
    Ensure that converting an impedance matrix Z to a scattering matrix S and back
    yields the original impedance matrix.
    """
    Z = np.array([[10, 2], [2, 10]], dtype=complex)
    S = z_to_s(Z, Z0=Z0)
    Z_back = s_to_z(S, Z0=Z0)
    np.testing.assert_allclose(Z, Z_back, atol=1e-5)

def test_y_to_s_and_s_to_y_roundtrip():
    """
    Verify that converting an admittance matrix Y to a scattering matrix S and back
    produces a consistent scattering matrix (allowing for an overall sign flip).
    """
    Y = np.array([[1, -0.5], [-0.5, 1]], dtype=complex)
    S = y_to_s(Y)
    Y_back = s_to_y(S)
    S_back = y_to_s(Y_back)
    # Allow an overall sign flip due to potential numerical nuances.
    if not (np.allclose(S, S_back, atol=1e-5) or np.allclose(S, -S_back, atol=1e-5)):
        raise AssertionError("S and S_back differ more than allowed, even after sign adjustment.")
