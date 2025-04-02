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
# Optional: you can configure Pint further if needed.

# Global lambda cache and lock for thread-safety.
_LAMBDA_CACHE: Dict[str, Tuple[sympy.Expr, Any]] = {}
_LAMBDA_CACHE_LOCK = threading.Lock()

def compile_expr(expr: Union[str, sympy.Expr]) -> Tuple[sympy.Expr, Any]:
    """
    Compile a symbolic expression using sympy.lambdify and cache the result.
    
    Args:
        expr: Expression in string or sympy.Expr form.
    
    Returns:
        A tuple (sym_expr, func) where 'sym_expr' is the sympy expression and
        'func' is a lambda function for numerical evaluation.
    
    Raises:
        ParameterError: If the expression cannot be compiled.
    """
    expr_key = str(expr)
    with _LAMBDA_CACHE_LOCK:
        if expr_key in _LAMBDA_CACHE:
            return _LAMBDA_CACHE[expr_key]
    try:
        sym_expr = sympy.sympify(expr)
        # Sort free symbols by name for consistency.
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
    Resolve a symbolic expression using caching and compiled lambdified functions.
    
    Supports robust unit handling using Pint. If the expression is a simple numeric value with a unit,
    it is parsed via Pint.
    
    Args:
        expr: The expression to resolve (string or sympy.Expr).
        param_dict: Dictionary of parameter values.
    
    Returns:
        The numerical value of the expression.
    
    Raises:
        ParameterError: On failure to resolve.
    """
    try:
        # Attempt to parse as a simple quantity using Pint.
        if isinstance(expr, str):
            try:
                quantity = ureg.Quantity(expr)
                return quantity.to_base_units().magnitude
            except Exception:
                pass  # Fall back to symbolic resolution if Pint cannot parse it.
        
        # Compile (or fetch from cache) the expression.
        sym_expr, func = compile_expr(expr)
        symbols = sorted(sym_expr.free_symbols, key=lambda s: str(s))
        subs_list = []
        for s in symbols:
            sname = str(s)
            # Look up the parameter value; support for unit suffixes can be enhanced further.
            if sname in param_dict:
                subs_list.append(param_dict[sname])
            else:
                # Optionally, check if the symbol (with a unit appended) exists in param_dict.
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
    """
    Invalidate the cached lambda functions. This can be called when the simulation context changes.
    """
    with _LAMBDA_CACHE_LOCK:
        _LAMBDA_CACHE.clear()

import logging
from typing import Any, Dict

def merge_params(*dicts: Dict[str, Any], conflict_strategy: str = 'override', log_level: int = logging.WARNING) -> Dict[str, Any]:
    """
    Merge several parameter dictionaries with conflict resolution.
    Later dictionaries override earlier ones by default.
    
    The conflict_strategy parameter can be one of:
      - 'override': Always override the earlier value with the later one (default).
      - 'keep': Retain the earlier value and ignore subsequent conflicts.
      - 'raise': Raise an exception if a conflict is detected.
      - 'combine': If both values are lists, combine them; if both are dicts, merge recursively; otherwise, override.
    
    Args:
        *dicts: Parameter dictionaries to merge.
        conflict_strategy: Strategy to resolve conflicts: 'override', 'keep', 'raise', or 'combine'.
        log_level: Logging level for conflict messages.
    
    Returns:
        A new dictionary containing the merged parameters.
    
    Raises:
        ValueError: If conflict_strategy is not one of the allowed values.
        Exception: If conflict_strategy is 'raise' and a conflict is detected.
    """
    allowed_strategies = {'override', 'keep', 'raise', 'combine'}
    if conflict_strategy not in allowed_strategies:
        raise ValueError(f"Unknown conflict_strategy '{conflict_strategy}'. Allowed values are: {allowed_strategies}")
    
    def _merge_value(existing: Any, new: Any) -> Any:
        # If the values are the same, return one of them.
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
            # If both values are lists, concatenate them.
            if isinstance(existing, list) and isinstance(new, list):
                combined = existing + new
                logging.log(log_level, f"Parameter conflict: combining lists {existing} and {new} -> {combined}.")
                return combined
            # If both are dictionaries, merge recursively.
            elif isinstance(existing, dict) and isinstance(new, dict):
                return merge_params(existing, new, conflict_strategy='combine', log_level=log_level)
            else:
                # Otherwise, default to overriding.
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
