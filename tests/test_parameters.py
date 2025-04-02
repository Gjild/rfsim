import pytest
import sympy
from symbolic.parameters import merge_params, resolve_parameters

def test_merge_params():
    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 3, "c": 4}
    merged = merge_params(dict1, dict2)
    assert merged["a"] == 1
    assert merged["b"] == 3  # dict2 overrides dict1
    assert merged["c"] == 4

def test_resolve_parameters_numeric():
    expr = "2 * x + 1"
    param_dict = {"x": 3}
    value = resolve_parameters(expr, param_dict)
    assert value == 7.0

def test_resolve_parameters_symbolic():
    expr = sympy.sympify("2 * x + 1")
    param_dict = {"x": 4}
    value = resolve_parameters(expr, param_dict)
    assert value == 9.0
