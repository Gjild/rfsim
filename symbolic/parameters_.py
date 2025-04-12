"""
symbolic/parameters.py

This module provides functions for compiling and resolving symbolic parameters,
handling dependencies, and merging parameter dictionaries for the Modified Nodal Analysis
RF simulator.
"""

import logging
import re
import threading
from collections import defaultdict, deque
from typing import Any, Dict, Tuple, Union

import pint
import sympy

from core.exceptions import ParameterError

# Initialize a Pint unit registry.
ureg = pint.UnitRegistry()

# Global lambda cache and lock for thread-safe expression compilation.
_LAMBDA_CACHE: Dict[str, Tuple[sympy.Expr, Any]] = {}
_LAMBDA_CACHE_LOCK = threading.Lock()


def compile_expr(expr: Union[str, sympy.Expr]) -> Tuple[sympy.Expr, Any]:
    """
    Compiles a symbolic expression (given as a string or sympy.Expr) into a sympy.Expr
    and its corresponding lambda function for numerical evaluation.
    """
    expr_key = str(expr)
    with _LAMBDA_CACHE_LOCK:
        if expr_key in _LAMBDA_CACHE:
            return _LAMBDA_CACHE[expr_key]

    try:
        sym_expr = sympy.sympify(expr)
        symbols = tuple(sorted(sym_expr.free_symbols, key=lambda s: str(s)))
        func = sympy.lambdify(symbols, sym_expr, "numpy")
        with _LAMBDA_CACHE_LOCK:
            _LAMBDA_CACHE[expr_key] = (sym_expr, func)
        return sym_expr, func
    except Exception as e:
        logging.error(f"Could not compile expression '{expr}': {e}")
        raise ParameterError(f"Could not compile expression '{expr}': {e}")


def resolve_parameters(expr: Union[str, sympy.Expr], param_dict: Dict[str, Any]) -> float:
    """
    Resolve a parameter expression to its float value.

    If the expression is a string that includes unit symbols (e.g., "ohm", "F", etc.),
    attempt to parse it with Pint. Otherwise, compile and evaluate the symbolic expression
    using values in param_dict.

    Parameters:
        expr: The parameter expression (str or sympy.Expr).
        param_dict: Dictionary mapping parameter names to their numeric values.

    Returns:
        The evaluated float value.

    Raises:
        ParameterError: When the expression cannot be compiled or a parameter is missing.
    """
    if isinstance(expr, str):
        # Try to detect and parse units.
        for unit_keyword in ("ohm", "F", "nF", "pF", "H", "s", "S"):
            if unit_keyword in expr:
                try:
                    quantity = ureg.Quantity(expr)
                    return quantity.to_base_units().magnitude
                except Exception:
                    # Fall back to symbolic evaluation if unit parsing fails.
                    break

    # Use symbolic resolution.
    try:
        sym_expr, func = compile_expr(expr)
        # Prepare substitution list based on sorted free symbols.
        subs_values = []
        for symbol in sorted(sym_expr.free_symbols, key=lambda s: str(s)):
            name = str(symbol)
            if name in param_dict:
                subs_values.append(param_dict[name])
            else:
                raise ParameterError(f"Parameter '{name}' not found in the provided dictionary.")
        return float(func(*subs_values))
    except Exception as e:
        logging.error(f"Error evaluating expression '{expr}' with parameters {param_dict}: {e}")
        raise ParameterError(f"Error resolving '{expr}': {e}")


def clear_lambda_cache() -> None:
    """Clears the internal expression lambda cache."""
    with _LAMBDA_CACHE_LOCK:
        _LAMBDA_CACHE.clear()


def merge_params(*dicts: Dict[str, Any], conflict_strategy: str = 'override',
                 log_level: int = logging.WARNING) -> Dict[str, Any]:
    """
    Merge multiple parameter dictionaries based on a specified conflict resolution strategy.

    Supported strategies:
        - 'override': Use the new value, logging the override.
        - 'keep': Retain the existing value.
        - 'raise': Raise an exception on conflict.
        - 'combine': Combine lists or merge dictionaries; otherwise override.

    Parameters:
        dicts: Parameter dictionaries to merge.
        conflict_strategy: Strategy to resolve conflicts ('override', 'keep', 'raise', 'combine').
        log_level: Logging level for conflict messages.

    Returns:
        A single merged dictionary of parameters.
    """
    allowed_strategies = {'override', 'keep', 'raise', 'combine'}
    if conflict_strategy not in allowed_strategies:
        raise ValueError(f"Unknown conflict_strategy '{conflict_strategy}'. Allowed values are: {allowed_strategies}")

    def _merge_value(existing: Any, new: Any) -> Any:
        if existing == new:
            return existing
        if conflict_strategy == 'override':
            logging.log(log_level, f"Parameter conflict: '{existing}' overridden by '{new}'.")
            return new
        elif conflict_strategy == 'keep':
            logging.debug(f"Parameter conflict: keeping '{existing}' and ignoring '{new}'.")
            return existing
        elif conflict_strategy == 'raise':
            raise Exception(f"Parameter conflict: cannot merge '{existing}' with '{new}'.")
        elif conflict_strategy == 'combine':
            if isinstance(existing, list) and isinstance(new, list):
                combined = existing + new
                logging.log(log_level, f"Parameter conflict: combining lists {existing} and {new} -> {combined}.")
                return combined
            elif isinstance(existing, dict) and isinstance(new, dict):
                return merge_params(existing, new, conflict_strategy='combine', log_level=log_level)
            else:
                logging.log(log_level, f"Parameter conflict: overriding '{existing}' with '{new}'.")
                return new

    result: Dict[str, Any] = {}
    for d in dicts:
        for key, value in d.items():
            result[key] = _merge_value(result[key], value) if key in result else value
    return result


def is_number(s: str) -> bool:
    """Check if a string can be converted to a float."""
    try:
        float(s)
        return True
    except ValueError:
        return False


def resolve_all_parameters(param_dict: Dict[str, str]) -> Dict[str, float]:
    """
    Resolve all symbolic parameters, respecting inter-parameter dependencies.

    This function creates a dependency graph by tokenizing expressions,
    then performs a topological sort to determine an evaluation order.
    Circular dependencies raise an exception.

    Parameters:
        param_dict: Dictionary mapping parameter names to their expressions.

    Returns:
        Dictionary of parameter names to their evaluated float values.

    Raises:
        Exception: When circular dependencies are detected.
    """
    # Build dependency graphs.
    dependency_graph = {key: set() for key in param_dict}
    dependents = {key: set() for key in param_dict}
    token_pattern = re.compile(r'\b([a-zA-Z_]\w*)\b')
    
    for key, expr in param_dict.items():
        if isinstance(expr, str):
            tokens = token_pattern.findall(expr)
            for token in tokens:
                # Only add dependency if token is not a number and is a parameter.
                if token in param_dict and not is_number(token):
                    dependency_graph[key].add(token)
                    dependents[token].add(key)
    
    # Topologically sort the parameters using Kahn's algorithm.
    sorted_keys = []
    queue = deque([k for k, deps in dependency_graph.items() if not deps])
    while queue:
        current = queue.popleft()
        sorted_keys.append(current)
        for dep in dependents[current]:
            dependency_graph[dep].discard(current)
            if not dependency_graph[dep]:
                queue.append(dep)
    
    if len(sorted_keys) != len(param_dict):
        raise Exception("Circular dependency detected in parameters!")
    
    # Evaluate parameters in sorted order.
    resolved: Dict[str, float] = {}
    for key in sorted_keys:
        resolved[key] = resolve_parameters(param_dict[key], resolved)
    return resolved
