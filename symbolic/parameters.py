# symbolic/parameters.py
from typing import Any, Dict, Tuple, Union
import sympy
import logging
import re
from core.exceptions import ParameterError
import pint
import threading

# Initialize a Pint unit registry.
ureg = pint.UnitRegistry()

# Global lambda cache and lock for thread-safety.
_LAMBDA_CACHE: Dict[str, Tuple[sympy.Expr, Any]] = {}
_LAMBDA_CACHE_LOCK = threading.Lock()

def compile_expr(expr: Union[str, sympy.Expr]) -> Tuple[sympy.Expr, Any]:
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
    try:
        if isinstance(expr, str):
            try:
                quantity = ureg.Quantity(expr)
                return quantity.to_base_units().magnitude
            except Exception:
                pass
        sym_expr, func = compile_expr(expr)
        symbols = sorted(sym_expr.free_symbols, key=lambda s: str(s))
        subs_list = []
        for s in symbols:
            sname = str(s)
            if sname in param_dict:
                subs_list.append(param_dict[sname])
            else:
                found = False
                for key in param_dict:
                    if sname == key:
                        subs_list.append(param_dict[key])
                        found = True
                        break
                if not found:
                    raise ParameterError(f"Parameter '{sname}' not found in the provided dictionary.")
        value = float(func(*subs_list))
        return value
    except Exception as e:
        logging.error(f"Error evaluating expression '{expr}' with parameters {param_dict}: {e}")
        raise ParameterError(f"Error resolving '{expr}': {e}")

def clear_lambda_cache() -> None:
    with _LAMBDA_CACHE_LOCK:
        _LAMBDA_CACHE.clear()

from typing import Any, Dict
def merge_params(*dicts: Dict[str, Any], conflict_strategy: str = 'override', log_level: int = logging.WARNING) -> Dict[str, Any]:
    allowed_strategies = {'override', 'keep', 'raise', 'combine'}
    if conflict_strategy not in allowed_strategies:
        raise ValueError(f"Unknown conflict_strategy '{conflict_strategy}'. Allowed values are: {allowed_strategies}")
    
    def _merge_value(existing: Any, new: Any) -> Any:
        if existing == new:
            return existing
        if conflict_strategy == 'override':
            logging.log(log_level, f"Parameter conflict: existing value '{existing}' overridden by '{new}'.")
            return new
        elif conflict_strategy == 'keep':
            logging.debug(f"Parameter conflict: keeping existing value '{existing}', ignoring new value '{new}'.")
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
            if key in result:
                result[key] = _merge_value(result[key], value)
            else:
                result[key] = value
    return result

def is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False

def resolve_all_parameters(param_dict: Dict[str, str]) -> Dict[str, float]:
    """
    Resolve all symbolic parameters taking dependencies into account.
    This function builds a dependency graph by examining the tokens in each expression,
    then performs a topological sort to resolve parameters in order.
    """
    from collections import defaultdict, deque

    # Build dependency graph: keys map to a set of parameter names they depend on.
    dependency_graph = {key: set() for key in param_dict}
    dependents = {key: set() for key in param_dict}
    token_pattern = re.compile(r'\b([a-zA-Z_]\w*)\b')
    
    for key, expr in param_dict.items():
        if isinstance(expr, str):
            tokens = token_pattern.findall(expr)
            # Only add tokens that are parameters (and not pure numbers)
            for token in tokens:
                if token in param_dict and not is_number(token):
                    dependency_graph[key].add(token)
                    dependents[token].add(key)
    
    # Topological sort using Kahn's algorithm.
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
    
    resolved = {}
    for key in sorted_keys:
        resolved[key] = resolve_parameters(param_dict[key], resolved)
    return resolved
