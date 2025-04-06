import numpy as np
import pytest
from components.capacitor import CapacitorComponent
from components.inductor import InductorComponent
from components.resistor import ResistorComponent

@pytest.mark.parametrize("cap_value", ["1e-9", 1e-9])
def test_capacitor_impedance(cap_value):
    cap = CapacitorComponent("C1", {"C": str(cap_value)})
    f = 1e6  # 1 MHz
    Z = cap.impedance_expr(f, float(cap_value))
    expected = 1 / (1j * 2 * np.pi * f * float(cap_value))
    np.testing.assert_almost_equal(Z, expected, decimal=6)

def test_capacitor_zero_frequency():
    cap = CapacitorComponent("C_zero", {"C": "1e-9"})
    with pytest.raises(ZeroDivisionError, match="division by zero"):
        cap.impedance_expr(0, 1e-9)

def test_capacitor_negative_value():
    cap = CapacitorComponent("C_neg", {"C": "-1e-9"})
    f = 1e6
    Z = cap.impedance_expr(f, -1e-9)
    expected = 1 / (1j * 2 * np.pi * f * (-1e-9))
    np.testing.assert_almost_equal(Z, expected, decimal=6)

def test_resistor_impedance():
    res = ResistorComponent("R1", {"R": "1000"})
    f = 1e6  # frequency ignored
    Z = res.impedance_expr(f, 1000)
    assert Z == 1000

def test_inductor_impedance():
    ind = InductorComponent("L1", {"L": "1e-6"})
    f = 1e6
    Z = ind.impedance_expr(f, 1e-6)
    expected = 1j * 2 * np.pi * f * 1e-6
    np.testing.assert_almost_equal(Z, expected, decimal=6)

def test_inductor_zero_frequency():
    ind = InductorComponent("L_zero", {"L": "1e-6"})
    # At f=0, impedance should be 0.
    Z = ind.impedance_expr(0, 1e-6)
    np.testing.assert_almost_equal(Z, 0, decimal=6)

# New: Test with malformed parameter inputs.
def test_capacitor_invalid_param():
    cap = CapacitorComponent("C_invalid", {"C": "not_a_number"})
    with pytest.raises(ValueError):
        # Assuming that a float conversion or parameter resolution would raise ValueError.
        cap.impedance_expr(1e6, float("not_a_number"))
