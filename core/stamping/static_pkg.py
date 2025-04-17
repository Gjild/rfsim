from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence, Dict
import numpy as np
from core.topology.netlist_graph import NetlistGraph


@dataclass(frozen=True)
class StaticPackage:
    """
    All objects that depend **only** on the netlist topology, never on
    numeric parameters or frequency.  Pickle‑safe by design.
    """
    rows: np.ndarray            # int32, pattern of COO row indices
    cols: np.ndarray            # int32, pattern of COO col indices
    slices: Sequence[slice]     # slice per component (same order)
    shape: tuple[int, int]      # matrix dimension
    ext_idx: Sequence[int]      # external‑port rows/cols after gnd drop
    int_idx: Sequence[int]      # internal node rows/cols
    node_index: Dict[str, int]  # net → row/col
    graph: NetlistGraph
    ground_net: str | None      # chosen reference (None ⇒ no ground row/col)
