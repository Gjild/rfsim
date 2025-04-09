import ast
import hashlib
import os
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

# Import the updated matrix conversion functions.
from utils import matrix as mat

# Global safe namespace that doesn’t include the per‑point conversion functions.
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
    # Note: We leave out s_to_z and z_to_s; they are provided per evaluation point.
}

def validate_expr(expr: str) -> bool:
    """
    Validate the expression using AST to ensure it contains only safe nodes.
    (In production consider whitelisting a set of allowed node types for more security.)
    """
    try:
        node = ast.parse(expr, mode="eval")
        for subnode in ast.walk(node):
            # Reject any import-related nodes.
            if isinstance(subnode, (ast.Import, ast.ImportFrom)):
                return False
            # Optionally, add further checks against disallowed nodes (e.g. exec or other dynamic calls).
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
    
    Returns a tuple (x_data, y_data) if successful or None on failure.

    This function builds a local evaluation dictionary for each simulation point so that
    conversion functions (s_to_z, z_to_s) use the appropriate per-port impedance vector.
    """
    if not validate_expr(expr):
        if logger_func:
            logger_func("Expression validation failed.")
        return None
    
    if simulation_results is None:
        if logger_func:
            logger_func("No simulation results available.")
        return None

    x_data: List[float] = []
    y_data: List[float] = []
    
    # Iterate over each evaluated sweep point.
    # simulation_results.results is expected to be a dict with keys like (freq, params).
    for (freq, _), result in simulation_results.results.items():
        S = result.s_matrix
        
        # Get the per-point reference impedance vector from the result stats.
        # If not found, fall back to a scalar default of 50.
        Z0 = result.stats.get('ref_impedance_vector', 50)
        
        # Build a local evaluation context that includes dynamic variables and conversion wrappers.
        local_context = {
            "freq": freq,
            "S": S,
            "Z0": Z0,
            # Provide a lambda that uses the per-point impedance vector.
            "s_to_z": lambda S: mat.s_to_z(S, Z0=Z0),
            "z_to_s": lambda Z: mat.z_to_s(Z, Z0=Z0)
        }
        #try:
        #    # Convert the current s_matrix to an impedance matrix using the per-point conversion.
        #    local_context["S"] = S
        #except Exception as e:
        #    if logger_func:
        #        logger_func(f"Conversion to impedance failed at {freq:.3e} Hz: {e}")
        #    return None
        
        try:
            # Evaluate the user expression within the safe globals and the local context.
            val = eval(expr, SAFE_EVAL_CONTEXT, local_context)
            if is_complex:
                # For complex expressions we return separate real and imaginary parts.
                x_data.append(val.real)
                y_data.append(val.imag)
            else:
                x_data.append(freq)
                y_data.append(val)
        except Exception as e:
            msg_type = "Complex eval" if is_complex else "Eval"
            if logger_func:
                logger_func(f"{msg_type} failed at {freq:.3e} Hz: {e}")
            return None
    return x_data, y_data
