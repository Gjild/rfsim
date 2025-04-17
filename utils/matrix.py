# utils/matrix.py
import numpy as np
import scipy.sparse as sp
from utils.linops import LinearOperator

def y_to_s(Y: "np.ndarray|sp.spmatrix", Z0, reg: float = 1e-12):
    """Convert Y‑matrix to S‑matrix without ever forming an explicit inverse."""
    N = Y.shape[0]
    Z0_vec = (np.full(N, Z0) if np.isscalar(Z0) else np.asarray(Z0)).astype(np.complex128)

    Y0 = np.diag(1.0 / Z0_vec)
    D  = np.diag(np.sqrt(Z0_vec.real))
    Dinv = np.diag(1.0 / np.sqrt(Z0_vec.real))

    M = Y0 + Y
    if sp.issparse(M):
        M = M + reg * sp.eye(N, dtype=M.dtype)           # light regularisation
    else:
        np.fill_diagonal(M, M.diagonal() + reg)

    solver = LinearOperator(M, assume_posdef=False)      # LU solve
    RHS = (Y0 - Y)
    X = solver.solve(RHS)                                # (Y0+Y)^{-1}(Y0-Y)
    return D @ X @ Dinv