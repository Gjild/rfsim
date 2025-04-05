# utils/matrix.py
import numpy as np
import logging

NUMERICAL_FALLBACK_WARNING = True

def robust_inv(matrix: np.ndarray, reg: float = 1e-9) -> np.ndarray:
    """
    Compute the inverse of a matrix with added regularization for numerical stability.
    
    This function attempts to invert the matrix after adding a small regularization term
    (reg * I) to the diagonal. This helps mitigate numerical issues when the matrix is 
    near-singular. If inversion still fails, it falls back to computing the pseudoinverse.
    
    Args:
        matrix: The matrix to invert.
        reg: Regularization constant added to the diagonal (default: 1e-9).
    
    Returns:
        The inverse (or pseudoinverse) of the regularized matrix.
    
    Note:
        While regularization improves stability, it may introduce slight deviations 
        from the true inverse. In scenarios near resonance or with highly ill-conditioned
        matrices, users should interpret results with caution.
    """
    I = np.eye(matrix.shape[0], dtype=matrix.dtype)
    try:
        return np.linalg.inv(matrix + reg * I)
    except np.linalg.LinAlgError:
        logging.warning("robust_inv: singular matrix encountered; using pseudoinverse.")
        return np.linalg.pinv(matrix + reg * I)

def z_to_s(Z, Z0=50, reg: float = 1e-9):
    """
    Convert an impedance matrix (Z) to a scattering matrix (S) using regularized inversion.
    
    This function first computes a regularized inverse of (Z + Z0*I) to reduce numerical 
    instability when Z is ill-conditioned. It then applies the standard conversion formula:
    
        S = (Z - Z0*I) @ inv(Z + Z0*I)
    
    Args:
        Z: The impedance matrix.
        Z0: The characteristic impedance (default: 50).
        reg: Regularization constant (default: 1e-9).
    
    Returns:
        The scattering matrix corresponding to the given impedance matrix.
    
    Limitations:
        Near resonance or when Z is extremely ill-conditioned, the regularization may 
        affect numerical accuracy. Adjust the `reg` parameter if needed.
    """
    I = np.eye(Z.shape[0], dtype=complex)
    inv_matrix = robust_inv(Z + Z0 * I, reg=reg)
    return (Z - Z0 * I) @ inv_matrix

def s_to_z(S, Z0=50, reg: float = 1e-9):
    """
    Convert a scattering matrix (S) to an impedance matrix (Z) using regularized inversion.
    
    The conversion uses the formula:
    
        Z = Z0 * (I + S) @ inv(I - S)
    
    where the inversion of (I - S) is performed with regularization to improve stability.
    
    Args:
        S: The scattering matrix.
        Z0: The characteristic impedance (default: 50).
        reg: Regularization constant (default: 1e-9).
    
    Returns:
        The impedance matrix corresponding to the scattering matrix.
    
    Limitations:
        When S is very close to I, the matrix (I - S) can be nearly singular.
        The regularization parameter helps, but caution is advised in such cases.
    """
    I = np.eye(S.shape[0], dtype=complex)
    inv_matrix = robust_inv(I - S, reg=reg)
    return Z0 * (I + S) @ inv_matrix

def db(val):
    """Convert linear magnitude to dB."""
    return 20 * np.log10(np.abs(val))

def mag(val):
    """Return magnitude."""
    return np.abs(val)

def phase(val, deg=True):
    """Return phase of a complex number (in degrees by default)."""
    angle = np.angle(val)
    return np.degrees(angle) if deg else angle

def real(val):
    """Return the real part of a value."""
    return np.real(val)

def imag(val):
    """Return the imaginary part of a value."""
    return np.imag(val)

def log10(val):
    """Return the base-10 logarithm."""
    return np.log10(val)

def log(val):
    """Return the natural logarithm."""
    return np.log(val)

def unwrap_phase(phases):
    """Unwrap a sequence of phase values (e.g. over frequency)."""
    return np.unwrap(phases)

def conjugate(val):
    """Return the complex conjugate of a value."""
    return np.conj(val)
