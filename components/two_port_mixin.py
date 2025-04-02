# components/two_port_mixin.py
from typing import Any
import numpy as np
import logging

def robust_inv(matrix: np.ndarray, Z0: float, use_fallback: bool = True) -> np.ndarray:
    """
    Compute the inverse of a matrix with fallback to pseudoinverse if singular.
    
    Args:
        matrix: The matrix to invert.
        Z0: A scaling factor used in the caller (for context in error messages).
        use_fallback: If True, use np.linalg.pinv() on failure.
        
    Returns:
        The inverse (or pseudoinverse) of the matrix.
    """
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        logging.warning("robust_inv: singular matrix encountered; using pseudoinverse. This may affect numerical accuracy.")
        return np.linalg.pinv(matrix)

class TwoPortImpedanceMixin:
    def _build_two_port_impedance(self, impedance: complex) -> np.ndarray:
        """
        Construct a 2x2 impedance matrix for a two-port component.
        
        Args:
            impedance: The computed impedance value (or scalar impedance factor).
        
        Returns:
            A 2x2 numpy array with the impedance structure:
                [[Z, -Z],
                 [-Z, Z]]
        """
        return np.array([[impedance, -impedance],
                         [-impedance, impedance]], dtype=complex)
