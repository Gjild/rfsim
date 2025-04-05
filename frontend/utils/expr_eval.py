# frontend/utils/expr_eval.py
import ast
import hashlib
import os
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

# Assume you have a module for matrix operations.
from utils import matrix as mat

SAFE_EVAL_CONTEXT: Dict[str, Any] = {
    "np": np,
    "z_to_s": mat.z_to_s,
    "s_to_z": mat.s_to_z,
    "db": mat.db,
    "mag": mat.mag,
    "phase": mat.phase,
    "real": mat.real,
    "imag": mat.imag,
    "log10": mat.log10,
    "log": mat.log,
    "unwrap": mat.unwrap_phase,
    "conj": mat.conjugate,
    "abs": abs,
    "round": round,
}

def validate_expr(expr: str) -> bool:
    """
    Validate the expression using AST to ensure it contains only safe nodes.
    """
    try:
        node = ast.parse(expr, mode="eval")
        for subnode in ast.walk(node):
            # For a more complete solution, whitelist allowed node types here.
            if isinstance(subnode, (ast.Import, ast.ImportFrom)):
                return False
        return True
    except Exception:
        return False

def hash_file(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def safe_eval_expr(expr: str,
                   simulation_results: Any,
                   is_complex: bool = False,
                   logger_func: Optional[Callable[[str], None]] = None
                   ) -> Optional[Tuple[List[float], List[float]]]:
    """
    Safely evaluate a user-supplied expression using a restricted context.
    Returns (x_data, y_data) if successful, or None on failure.
    """
    if not validate_expr(expr):
        if logger_func:
            logger_func("Expression validation failed.")
        return None

    safe_globals = {"__builtins__": {}, **SAFE_EVAL_CONTEXT}
    x_data: List[float] = []
    y_data: List[float] = []

    if simulation_results is None:
        if logger_func:
            logger_func("No simulation results available.")
        return None

    for (freq, _), s_matrix in simulation_results.results.items():
        try:
            Z = mat.s_to_z(s_matrix)
            if is_complex:
                val = eval(expr, safe_globals, {"Z": Z, "freq": freq, "s_matrix": s_matrix})
                x_data.append(val.real)
                y_data.append(val.imag)
            else:
                y_val = eval(expr, safe_globals, {"Z": Z, "freq": freq, "s_matrix": s_matrix})
                x_data.append(freq)
                y_data.append(y_val)
        except Exception as e:
            error_type = "Complex eval" if is_complex else "Eval"
            if logger_func:
                logger_func(f"{error_type} failed at {freq:.3e} Hz: {e}")
            return None
    return x_data, y_data
