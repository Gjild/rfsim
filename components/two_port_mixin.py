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

class SeriesTwoPortZMixin:
    """
    Submatrix builder for a device that is physically from one node to another (typical two-port).
    Returns [[Z, -Z], [-Z, Z]].
    """
    def _build_two_port_impedance(self, Z: complex) -> np.ndarray:
        return np.array([[Z, -Z],
                         [-Z, Z]], dtype=complex)


class ShuntTwoPortZMixin:
    """
    Submatrix builder for a device that is physically from node to ground 
    (or equivalently '1-port' in many circuit formalisms, but represented 
     here as 2-ports where the 2nd is ground).
    Returns [[Z, 0], [0, Z]].
    """
    def _build_two_port_impedance(self, Z: complex) -> np.ndarray:
        return np.array([[Z, 0],
                         [0, Z]], dtype=complex)
    

class SeriesTwoPortYMNAStamp:
    """
    Admittance submatrix builder for a two-port device that is physically in series
    from one node to the other. The standard MNA Y-stamp is:
        [[+Y,  -Y],
         [ -Y, +Y]]
    """
    def build_two_port_admittance(self, Y: complex) -> np.ndarray:
        return np.array([[+Y, -Y],
                         [-Y, +Y]], dtype=complex)


class ShuntTwoPortYMNAStamp:
    """
    Admittance submatrix for a device from node to ground. The standard MNA stamp:
        [[+Y, 0],
         [ 0, +Y]]
    (Though typically a 1-port to ground is just Y on the node’s diagonal.)
    """
    def build_two_port_admittance(self, Y: complex) -> np.ndarray:
        return np.array([[Y, 0],
                         [0, Y]], dtype=complex)