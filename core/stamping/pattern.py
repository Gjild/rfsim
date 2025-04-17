from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Sequence
import numpy as np

@dataclass
class StampPattern:
    """
    Immutable COO pattern (row, col) plus slices telling where the data of
    each component lives inside the final `data` vector.

    The pattern depends *only* on topology, never on numeric values.
    """
    rows: np.ndarray          # int32
    cols: np.ndarray          # int32
    slices: Sequence[slice]   # len == n_components

    @property
    def nnz(self):            # number of non‑zeros
        return self.rows.size
