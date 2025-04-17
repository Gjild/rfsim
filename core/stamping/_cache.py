# core/stamping/_cache.py  – NEW small helper

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import scipy.sparse as sp
from typing import Tuple

@dataclass
class LUEntry:
    pattern_key: bytes            # fingerprint of indices / indptr / shape
    data_key   : int              # 64‑bit hash of numeric data
    solver     : "LinearOperator" # ready .solve()

def sparsity_fingerprint(M: sp.csc_matrix) -> bytes:
    """Return an order‑independent fingerprint of the sparsity pattern only."""
    import hashlib, pickle
    h = hashlib.blake2b(digest_size=16)
    h.update(pickle.dumps((M.indices.tobytes(), M.indptr.tobytes(), M.shape)))
    return h.digest()

def data_checksum(M: sp.csc_matrix) -> int:
    """Cheap numeric checksum (64‑bit xor) insensitive to permutations."""
    # view bytes as uint64 chunks
    arr64 = M.data.view(np.uint64, copy=False)
    return int(np.bitwise_xor.reduce(arr64, dtype=np.uint64))
