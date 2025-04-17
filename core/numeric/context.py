# core/numeric/context.py
from __future__ import annotations
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Tuple


@dataclass(frozen=True, slots=True)
class NumericContext:
    """
    Immutable <frequency, parameter‑set> bundle.

    * Hashable → can be used as a cache key.
    * Picklable → ships cheaply to worker processes.
    * Read‑only → components cannot mutate shared state.
    """
    freq: float
    _items: Tuple[Tuple[str, float], ...]          # sorted for stable hash

    def __init__(self, freq: float, params: Mapping[str, float]):
        object.__setattr__(self, "freq", float(freq))
        # store as tuple‑of‑tuples so hashing is O(1)
        object.__setattr__(self, "_items", tuple(sorted(params.items())))

    # ------------------------------------------------------------------
    # Convenience read‑only mapping interface
    # ------------------------------------------------------------------
    @property
    def params(self) -> Mapping[str, float]:
        return MappingProxyType(dict(self._items))

    def __getitem__(self, key: str) -> float:           # dict‑like access
        return dict(self._items)[key]
