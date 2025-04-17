# core/parameters/resolver.py
"""
Parameter resolver for RFSim v2.
Safely resolves symbolic parameter expressions into numeric values,
honoring physical units and inter-parameter dependencies using sympy and Pint.
"""

from typing import Dict, Union, Set, List
import sympy as sp
import re
from pint import UnitRegistry

from core.exceptions import ParameterError
from core.safe_math import parse_expr

# Unit handling
ureg = UnitRegistry()

# Regex to detect numeric literals with unit suffixes like "2.2pF"
_NUM_UNIT_PATTERN = re.compile(
    r"""^\s*                # optional leading whitespace
        [-+]?\d+(?:\.\d*)?  # digits with optional decimal
        (?:[eE][-+]?\d+)?   # optional exponent
        \s*                 # optional space
        [a-zA-ZµΩ]+         # at least one letter (unit incl. SI‑prefix)
        \s*$                # optional trailing ws, then EOS
    """, re.VERBOSE
)


def _build_dependency_graph(param_dict: Dict[str, Union[str, sp.Expr]]) -> Dict[str, Set[str]]:
    """
    Build a dependency graph mapping each parameter to the set of other
    parameters it depends on.
    Also converts string expressions to sympy.Expr or float as needed.
    """
    graph: Dict[str, Set[str]] = {}
    for key, expr in param_dict.items():
        deps: Set[str] = set()

        # Case: plain float/int — no dependencies
        if isinstance(expr, (float, int)):
            graph[key] = deps
            continue

        # Case: string — try unit first
        if isinstance(expr, str):
            try:
                # Try interpreting as a unit-bearing value (e.g., "1pF")
                qty = ureg.Quantity(expr)
                param_dict[key] = float(qty.to_base_units().magnitude)
                graph[key] = deps
                continue
            except Exception:
                pass  # Not a unit — treat as symbolic

            try:
                expr = parse_expr(expr)
                param_dict[key] = expr  # Cache parsed expression
            except Exception as e:
                raise ParameterError(f"Failed to parse expression for '{key}': {e}")

        # Case: non-numeric, non-expr
        elif not isinstance(expr, sp.Expr):
            raise ParameterError(f"Unsupported type for parameter '{key}': {type(expr)}")

        # Case: sympy.Expr — extract dependencies
        if isinstance(expr, sp.Expr):
            for sym in expr.free_symbols:
                name = str(sym)
                if name != key and name in param_dict:
                    deps.add(name)

        graph[key] = deps

    return graph


def _topological_sort(graph: Dict[str, Set[str]]) -> List[str]:
    """
    Perform Kahn's algorithm to topologically sort the dependency graph.
    Raises ParameterError on cycles.
    """
    in_degree: Dict[str, int] = {node: 0 for node in graph}
    reverse_map: Dict[str, Set[str]] = {node: set() for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            in_degree[node] += 1
            reverse_map.setdefault(dep, set()).add(node)

    queue: List[str] = [n for n, deg in in_degree.items() if deg == 0]
    sorted_list: List[str] = []

    while queue:
        n = queue.pop(0)
        sorted_list.append(n)
        for dependent in reverse_map.get(n, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(sorted_list) != len(graph):
        cycle_candidates = [k for k, deg in in_degree.items() if deg > 0]
        raise ParameterError(f"Circular dependency among: {', '.join(cycle_candidates)}")

    return sorted_list


def resolve(param_dict: Dict[str, Union[str, sp.Expr]]) -> Dict[str, float]:
    """
    Resolve all parameters in `param_dict` to numeric float values.
    Strings are parsed using sympy, units are handled with Pint.

    Args:
        param_dict: Mapping from parameter name to expression string or sympy.Expr

    Returns:
        Dictionary mapping parameter name to evaluated float value.

    Raises:
        ParameterError: If expression parsing or evaluation fails.
    """
    graph = _build_dependency_graph(param_dict)
    order = _topological_sort(graph)

    resolved: Dict[str, float] = {}
    for key in order:
        expr = param_dict[key]

        # Case: literal float or int
        if isinstance(expr, (int, float)):
            resolved[key] = float(expr)
            continue

        # Case: expression with unit (e.g., "1pF")
        if isinstance(expr, str) and _NUM_UNIT_PATTERN.match(expr):
            try:
                qty = ureg.Quantity(expr)
                resolved[key] = float(qty.to_base_units().magnitude)
                continue
            except Exception as e:
                raise ParameterError(f"Unit parse error for '{key}': {e}")

        # Case: parsed sympy expression
        if isinstance(expr, sp.Expr):
            try:
                val = expr.evalf(subs=resolved)
                resolved[key] = float(val)
                continue
            except Exception as e:
                raise ParameterError(f"Evaluation failed for '{key}': {e}")

        # Catch-all fallback
        raise ParameterError(f"Unhandled parameter type for '{key}': {type(expr)}")

    return resolved
