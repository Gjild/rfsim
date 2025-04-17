# core/stamping/factors.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence
import numpy as np

@dataclass
class YFactorCache:
    """
    Pre‑factorisation data that can be reused across sweep points as long as
    the topology & frequency stay unchanged.
    """
    ext_idx: Sequence[int]             # external‑port node indices
    int_idx: Sequence[int]             # internal‑node indices
    solver_ii: "callable[[np.ndarray], np.ndarray]"  # solves Y_ii * x = b

    def solve_internal(self, rhs: np.ndarray) -> np.ndarray:
        """Convenience wrapper so callers need not touch solver_ii directly."""
        return self.solver_ii(rhs)
