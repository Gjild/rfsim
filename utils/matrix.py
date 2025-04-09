# utils/matrix.py
import numpy as np
import logging

NUMERICAL_FALLBACK_WARNING = True

def robust_inv(matrix: np.ndarray, reg: float = 1e-9) -> np.ndarray:
    """
    Compute the inverse of a matrix with regularization. Uses Cholesky decomposition
    if the matrix is Hermitian.
    """
    I = np.eye(matrix.shape[0], dtype=matrix.dtype)
    try:
        if np.allclose(matrix, np.conjugate(matrix.T), atol=1e-6):
            # Try Cholesky decomposition for Hermitian matrices.
            L = np.linalg.cholesky(matrix + reg * I)
            invL = np.linalg.inv(L)
            return invL.T @ invL
        else:
            return np.linalg.inv(matrix + reg * I)
    except np.linalg.LinAlgError:
        logging.warning("robust_inv: singular matrix encountered; using pseudoinverse with regularization.")
        return np.linalg.pinv(matrix + reg * I)
    

def z_to_s(Z: np.ndarray, Z0, reg: float = 1e-9) -> np.ndarray:
    """
    Convert an impedance matrix Z to a scattering matrix S, handling nonuniform port impedances.

    Parameters:
      Z : np.ndarray
          An NxN impedance matrix.
      Z0 : scalar or array-like
          The reference impedance(s) for each port. Can be a scalar (all ports identical)
          or an array-like of length N.
      reg : float
          Regularization term for numerical stability.

    Returns:
      S : np.ndarray
          The scattering matrix, computed as:
              S = D^{-1} (Z - Z0_diag) inv(Z + Z0_diag) D,
          with D = diag(sqrt(Z0_vec)) and Z0_diag = diag(Z0_vec).
    """
    N = Z.shape[0]
    # Create reference impedance vector.
    if np.isscalar(Z0):
        Z0_vec = np.array([Z0] * N)
    else:
        Z0_vec = np.array(Z0)
    if len(Z0_vec) != N:
        raise ValueError(f"Impedance vector length {len(Z0_vec)} does not match number of ports {N}.")

    Z0_diag = np.diag(Z0_vec)
    D = np.diag(np.sqrt(np.real(Z0_vec)))
    D_inv = np.diag(1.0/np.sqrt(np.real(Z0_vec)))

    M = Z + Z0_diag
    M_inv = robust_inv(M, reg=reg)
    S = D_inv @ (Z - Z0_diag) @ M_inv @ D
    return S

def s_to_z(S: np.ndarray, Z0, reg: float = 1e-9) -> np.ndarray:
    """
    Convert a scattering matrix S to an impedance matrix Z, handling nonuniform port impedances.

    Parameters:
      S : np.ndarray
          An NxN scattering matrix.
      Z0 : scalar or array-like
          The reference impedance(s) for each port.
      reg : float
          Regularization term for numerical stability.

    Returns:
      Z : np.ndarray
          The impedance matrix, computed as:
              Z = D @ (I + S') @ inv(I - S') @ D,
          where S' = D^{-1} S D and D = diag(sqrt(Z0_vec)).
    """
    N = S.shape[0]
    if np.isscalar(Z0):
        Z0_vec = np.array([Z0] * N)
    else:
        Z0_vec = np.array(Z0)
    if len(Z0_vec) != N:
        raise ValueError(f"Impedance vector length {len(Z0_vec)} does not match number of ports {N}.")

    D = np.diag(np.sqrt(np.real(Z0_vec)))
    D_inv = np.diag(1.0/np.sqrt(np.real(Z0_vec)))
    S_prime = D_inv @ S @ D
    I = np.eye(N, dtype=complex)
    inv_I_minus_S = robust_inv(I - S_prime, reg=reg)
    # Compute Z using the derived relation:
    Z = D @ ((I + S_prime) @ inv_I_minus_S) @ D
    return Z

def y_to_s(Y: np.ndarray, Z0, reg: float = 1e-9) -> np.ndarray:
    """
    Convert an admittance matrix Y to a scattering matrix S for nonuniform port impedances.
    
    Parameters:
      Y: np.ndarray
         The NxN admittance matrix.
      Z0: scalar or array-like
         The reference impedance for each port. Can be a scalar (all ports identical)
         or an array-like of length N.
      reg: float
         Regularization term for numerical stability.
    
    Returns:
      S: np.ndarray
         The resulting scattering matrix.
    """
    N = Y.shape[0]
    # Create the reference impedance vector.
    if np.isscalar(Z0):
        Z0_vec = np.array([Z0] * N)
    else:
        Z0_vec = np.array(Z0)
    if len(Z0_vec) != N:
        raise ValueError(f"Impedance vector length {len(Z0_vec)} does not match number of ports {N}.")
    Z0_real = np.array([np.real(z) for z in Z0_vec])

    # Y0 is the diagonal matrix of the port admittances.
    Y0 = np.diag(1.0 / Z0_real)
    
    # Create scaling matrices for normalization.
    D = np.diag(1.0/np.sqrt(Z0_real))
    D_inv = np.diag(np.sqrt(Z0_real))
    
    # Form the sum Y0 + Y and regularize if needed.
    M = Y0 + Y
    cond_M = np.linalg.cond(M)
    if cond_M > 1e6:
        reg = max(reg, cond_M * 1e-12)
        logging.warning(f"High condition number in (Y0+Y): {cond_M:.2e}; using reg={reg}")
    
    try:
        M_inv = robust_inv(M, reg=reg)
    except Exception as e:
        raise ValueError(f"Failed to invert (Y0+Y) matrix: {e}")
    
    # The proper conversion when Z0 is nonuniform:
    S = D @ ((Y0 - Y) @ M_inv) @ D_inv
    return S

def s_to_y(S: np.ndarray, Z0, reg: float = 1e-9) -> np.ndarray:
    """
    Convert a scattering matrix S to an admittance matrix Y, handling nonuniform port impedances.

    Parameters:
      S : np.ndarray
          An NxN scattering matrix.
      Z0 : scalar or array-like
          The reference impedance(s) for each port.
      reg : float
          Regularization term for numerical stability.

    Returns:
      Y : np.ndarray
          The admittance matrix, computed as:
              Y = Y0_diag @ (I - S') @ inv(I + S'),
          where S' = D^{-1} S D, Y0_diag = diag(1/Z0_vec),
          and D = diag(sqrt(Z0_vec)).
    """
    N = S.shape[0]
    if np.isscalar(Z0):
        Z0_vec = np.array([Z0] * N)
    else:
        Z0_vec = np.array(Z0)
    if len(Z0_vec) != N:
        raise ValueError(f"Impedance vector length {len(Z0_vec)} does not match number of ports {N}.")

    D = np.diag(np.sqrt(np.real(Z0_vec)))
    D_inv = np.diag(1.0/np.sqrt(np.real(Z0_vec)))
    S_prime = D_inv @ S @ D
    I = np.eye(N, dtype=complex)
    inv_I_plus_S = robust_inv(I + S_prime, reg=reg)
    Y0_diag = np.diag(1.0 / Z0_vec)
    Y = Y0_diag @ (I - S_prime) @ inv_I_plus_S
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
