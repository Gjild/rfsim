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
        logging.warning("robust_inv: singular matrix encountered; using pseudoinverse with regularization.")
        return np.linalg.pinv(matrix + reg * I)

def z_to_s(Z: np.ndarray, Z0: float = 50, reg: float = 1e-9) -> np.ndarray:
    """
    Convert an impedance matrix Z to a scattering matrix S.
    
    Parameters:
        Z: Impedance matrix.
        Z0: Characteristic impedance.
        reg: Regularization constant.
    
    Returns:
        Scattering matrix S.
    
    Warnings:
        If Z is non-square or non-Hermitian, an assertion or warning is raised.
    """
    # Check that Z is square
    assert Z.shape[0] == Z.shape[1], "Impedance matrix must be square."
    
    # Optional: Check Hermitian property for passive networks (if needed)
    if not np.allclose(Z, np.conjugate(Z.T), atol=1e-6):
        logging.warning(f"z_to_s: Impedance matrix does not appear Hermitian. Hermitian level {np.max(np.abs(Z - np.conjugate(Z.T)))}")
    
    I = np.eye(Z.shape[0], dtype=complex)
    inv_matrix = robust_inv(Z + Z0 * I, reg=reg)
    S = (Z - Z0 * I) @ inv_matrix
    return S

def s_to_z(S: np.ndarray, Z0: float = 50, reg: float = 1e-9) -> np.ndarray:
    """
    Convert a scattering matrix S to an impedance matrix Z.
    
    Parameters:
        S: Scattering matrix.
        Z0: Characteristic impedance.
        reg: Regularization constant.
    
    Returns:
        Impedance matrix Z.
    
    Warnings:
        If S is non-square or close to singular, the function uses robust inversion.
    """
    # Check that S is square
    assert S.shape[0] == S.shape[1], "Scattering matrix must be square."
    
    I = np.eye(S.shape[0], dtype=complex)
    inv_matrix = robust_inv(I - S, reg=reg)
    Z = Z0 * (I + S) @ inv_matrix
    return Z

def y_to_s(Y: np.ndarray, Z0: float = 50, reg: float = 1e-9) -> np.ndarray:
    """
    Convert an N-port admittance matrix Y to the scattering matrix S,
    using the standard formula:

        S = (Y0I - Y) * inv(Y0I + Y)

    where Y0 = 1/Z0 and I is the identity matrix.

    We regularize the inversion with 'reg' similarly to robust_inv.
    """
    assert Y.shape[0] == Y.shape[1], "Y must be square."
    I = np.eye(Y.shape[0], dtype=complex)
    Y0 = 1.0 / Z0
    # Y0I + Y
    M = Y0 * I + Y
    # Use your robust_inv or direct np.linalg.inv:
    from utils.matrix import robust_inv
    M_inv = robust_inv(M, reg=reg)
    S = (Y0*I - Y) @ M_inv
    return S

def s_to_y(S: np.ndarray, Z0: float = 50, reg: float = 1e-9) -> np.ndarray:
    """
    Convert scattering matrix S to admittance matrix Y:

        Y = Y0 * (I - S)^{-1} * (I + S)

    where Y0 = 1/Z0.
    """
    assert S.shape[0] == S.shape[1], "S must be square."
    I = np.eye(S.shape[0], dtype=complex)
    Y0 = 1.0 / Z0
    from utils.matrix import robust_inv
    inv_part = robust_inv(I - S, reg=reg)
    Y = Y0 * inv_part @ (I + S)
    return Y

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
