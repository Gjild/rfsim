import pytest
import math
from symbolic.parameters_ import resolve_all_parameters

@pytest.mark.xfail(reason="Resolution with units and functions returns unexpected value.")
def test_symbolic_with_units_and_functions():
    params = {
        "R": "1000 * ohm",
        "C": "1e-9",
        "tau": "R * C",
        "omega": "2 * pi * 1e6",
        "Xc": "1 / (omega * C)"
    }
    resolved = resolve_all_parameters(params)
    assert abs(resolved["tau"] - 1e-6) < 1e-9
    expected_Xc = 1 / (2 * math.pi * 1e6 * 1e-9)
    assert abs(resolved["Xc"] - expected_Xc) < 1e-6

def test_advanced_symbolic_expression():
    params = {
        "pi": "3.141592653589793",
        "theta": "pi / 3",
        "cos_val": "cos(theta)",
        "sin_val": "sin(theta)",
        "tan_val": "sin(theta) / cos(theta)"
    }
    resolved = resolve_all_parameters(params)
    expected_cos = math.cos(math.pi/3)
    expected_sin = math.sin(math.pi/3)
    expected_tan = math.tan(math.pi/3)
    assert abs(resolved["cos_val"] - expected_cos) < 1e-6
    assert abs(resolved["sin_val"] - expected_sin) < 1e-6
    assert abs(resolved["tan_val"] - expected_tan) < 1e-6

def test_error_in_symbolic_expression():
    params = {"a_val": "2", "b_val": "a_val + c_val"}
    with pytest.raises(Exception, match="not found"):
        resolve_all_parameters(params)
