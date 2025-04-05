# components/symmetric_impedance_mixin.py
from typing import Any
import numpy as np
import logging

def robust_inv(matrix: np.ndarray, reg: float = 1e-9) -> np.ndarray:
    """
    Compute the inverse of a matrix with added regularization for numerical stability.
    
    Parameters:
        matrix: The matrix to invert.
        reg: Regularization term to add to the diagonal.
    
    Returns:
        The inverse (or pseudoinverse) of the regularized matrix.
    """
    I = np.eye(matrix.shape[0], dtype=matrix.dtype)
    try:
        return np.linalg.inv(matrix + reg * I)
    except np.linalg.LinAlgError:
        logging.warning("robust_inv: singular matrix encountered; using pseudoinverse with regularization.")
        return np.linalg.pinv(matrix + reg * I)

class TwoPortSymmetricImpedanceMixin:
    """
    Mixin for two-port components that assume a symmetric, reciprocal impedance structure.
    
    The default implementation constructs a 2x2 impedance matrix of the form:
    
        [[Z, -Z],
         [-Z, Z]]
    
    where Z is the computed impedance. This mixin is appropriate only when the component's
    behavior is symmetric and reciprocal. More generalized implementations should override
    this method.
    """
    def _build_two_port_impedance(self, impedance: complex) -> np.ndarray:
        return np.array([[impedance, -impedance],
                         [-impedance, impedance]], dtype=complex)
