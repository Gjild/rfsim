# utils/matrix.py
import numpy as np
import logging

NUMERICAL_FALLBACK_WARNING = True

def z_to_s(Z, Z0=50):
    I = np.eye(Z.shape[0], dtype=complex)
    try:
        inv_matrix = np.linalg.inv(Z + Z0 * I)
    except np.linalg.LinAlgError:
        if NUMERICAL_FALLBACK_WARNING:
            logging.warning("z_to_s: singular matrix encountered; using pseudoinverse.")
        inv_matrix = np.linalg.pinv(Z + Z0 * I)
    return (Z - Z0 * I) @ inv_matrix

def s_to_z(S, Z0=50):
    I = np.eye(S.shape[0], dtype=complex)
    try:
        inv_matrix = np.linalg.inv(I - S)
    except np.linalg.LinAlgError:
        if NUMERICAL_FALLBACK_WARNING:
            logging.warning("s_to_z: singular matrix encountered; using pseudoinverse.")
        inv_matrix = np.linalg.pinv(I - S)
    return Z0 * (I + S) @ inv_matrix

# --- New functions for frontend expressions ---

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
    return np.real(val)

def imag(val):
    return np.imag(val)

def log10(val):
    return np.log10(val)

def log(val):
    return np.log(val)

def unwrap_phase(phases):
    """Unwrap a sequence of phase values (e.g. over frequency)."""
    return np.unwrap(phases)

def conjugate(val):
    return np.conj(val)
