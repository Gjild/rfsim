# utils/linops.py
from __future__ import annotations
import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
import scipy.sparse.linalg as sla

class LinearOperator:
    """
    Wraps either a dense or sparse factorisation and exposes a .solve(b) method.
    """
    __slots__ = ("_solve",)

    def __init__(self, A: "sp.spmatrix|np.ndarray", assume_posdef=False):
        if sp.issparse(A):
            fac = sla.splu(A.tocsc())
            self._solve = fac.solve                        # SuperLU solve
        else:
            if assume_posdef:
                c, lower = la.cho_factor(A, lower=True)    # dense Cholesky
                self._solve = lambda b: la.cho_solve((c, lower), b)
            else:
                lu, piv = la.lu_factor(A)                  # dense LU
                self._solve = lambda b: la.lu_solve((lu, piv), b)
    
    def __call__(self, rhs):
        return self._solve(rhs)

    def solve(self, rhs: "np.ndarray") -> "np.ndarray":
        return self._solve(rhs)
