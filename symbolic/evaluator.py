# symbolic/evaluator.py
from typing import Dict, Union
import sympy
from typing import Dict
from symbolic.expressions import compile_expr
from symbolic.dependency_resolver import build_dependency_graph, topological_sort
from symbolic.units import parse_quantity

def evaluate_parameter(expr: Union[str, sympy.Expr], resolved: Dict[str, float]) -> float:
    """
    Evaluate a single parameter expression using any previously resolved parameters.
    
    If the expression represents a simple quantity (using units), it is converted via the units module.
    Otherwise, the expression is compiled and evaluated.
    
    :param expr: The parameter expression as a string or sympy.Expr.
    :param resolved: A dictionary of already resolved parameter values.
    :return: The evaluated parameter value as a float.
    :raises Exception: If a symbol in the expression is not found in 'resolved'.
    """
    # If the expression is a string, try to parse it as a quantity first.
    if isinstance(expr, str):
        try:
            return parse_quantity(expr)
        except Exception:
            pass  # Not a quantity; continue with symbolic evaluation.
    
    sym_expr, func = compile_expr(expr)
    symbols = sorted(sym_expr.free_symbols, key=lambda s: str(s))
    values = []
    for s in symbols:
        sname = str(s)
        if sname in resolved:
            values.append(resolved[sname])
        else:
            raise Exception(f"Parameter '{sname}' not found in the resolved dictionary.")
    result = func(*values)
    try:
        # Try to convert directly to float.
        return float(result)
    except Exception:
        # If result is symbolic, evaluate numerically.
        return float(result.evalf())

def resolve_all_parameters(param_dict: Dict[str, str]) -> Dict[str, float]:
    """
    Resolve all symbolic parameters considering dependencies.
    
    :param param_dict: A dictionary of parameter names and their expressions.
    :return: A dictionary mapping parameter names to their evaluated float values.
    :raises Exception: If circular dependencies are detected.
    """
    graph = build_dependency_graph(param_dict)
    sorted_keys = topological_sort(graph)
    resolved = {}
    for key in sorted_keys:
        resolved[key] = evaluate_parameter(param_dict[key], resolved)
    return resolved
