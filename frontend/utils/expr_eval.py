import ast
import hashlib
import os
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

# Import the updated matrix conversion functions.
from utils import matrix as mat

# The original safe globals, now without our conversion functions re‑bound.
SAFE_EVAL_CONTEXT: Dict[str, Any] = {
    "np": np,
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
    # We leave out s_to_z and z_to_s here—they will be re‑bound below.
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
    
    This version also re-binds the conversion functions (s_to_z, z_to_s) so that they
    use the proper per-port impedance vector stored in simulation_results.stats.
    """
    if not validate_expr(expr):
        if logger_func:
            logger_func("Expression validation failed.")
        return None
    
    if simulation_results is None:
        if logger_func:
            logger_func("No simulation results available.")
        return None

    # Retrieve the reference impedance vector from simulation results stats.
    # If not found, fall back to a scalar default (50).
    ref_impedance = simulation_results.stats.get("ref_impedance_vector", 50)
    print(list(simulation_results.results.keys()))

    # Build a safe globals dictionary. Here, we override our conversion functions
    # using lambda wrappers that capture the 'ref_impedance' value.
    safe_globals: Dict[str, Any] = {"__builtins__": {}}
    safe_globals.update(SAFE_EVAL_CONTEXT)
    safe_globals["s_to_z"] = lambda S: mat.s_to_z(S, Z0=ref_impedance)
    safe_globals["z_to_s"] = lambda Z: mat.z_to_s(Z, Z0=ref_impedance)
    # You may also add similar wrappers for s_to_y or y_to_s if needed.
    
    x_data: List[float] = []
    y_data: List[float] = []
    
    # Loop over each evaluated sweep point.
    # simulation_results.results is expected to be a dict where keys are (freq, params) tuples.
    for (freq, _), result in simulation_results.results.items:
        s_matrix = result.results.items()
        try:
            # Using the overridden s_to_z conversion; now Z will be computed using the
            # correct (per-port) impedance values.
            print(s_matrix.stats)
            Z = safe_globals["s_to_z"](s_matrix)
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
