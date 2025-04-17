# core/stamping/matrix_builder.py
"""
Assemble the global admittance matrix, run parameter/frequency sweeps in parallel,
reduce to external ports, and convert to scattering parameters.
"""
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from itertools import product
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import scipy.sparse as sp

from core.topology.netlist_graph import NetlistGraph
from core.exceptions import RFSimError
from utils.matrix import y_to_s
from utils.linops import LinearOperator
from core.stamping.factors import YFactorCache
from core.stamping.pattern import StampPattern
from core.stamping.static_pkg import StaticPackage
from core.parameters.resolver import resolve as _resolve_params
from core.numeric.context import NumericContext
from core.stamping._cache import LUEntry, sparsity_fingerprint, data_checksum

# pattern_key -> LUEntry  (only one entry per pattern kept to bound memory)
_LU_FACTOR_CACHE: dict[bytes, LUEntry] = {}

def _choose_ground(graph: NetlistGraph) -> str | None:
    """
    Return the first net whose name equals 'gnd' (case‑insensitive).
    If none exists, return None (no row/col will be eliminated).
    """
    return next((n for n in graph.nodes() if n.lower() == "gnd"), None)

def _eliminate_reference(
    Y: sp.csr_matrix,
    node_index: Dict[str, int],
    ref_name: str = "gnd",
) -> Tuple[sp.csr_matrix, Dict[str, int]]:
    """
    Drop the ground row/col from Y and return a *new* node‑index map that no
    longer contains `ref_name`.

    Args
    ----
    Y : csr_matrix
        Full admittance matrix with ground row/col still present.
    node_index : {net: idx}
        Mapping that **includes** ref_name.
    ref_name : str
        Net name (case‑insensitive) to treat as reference.

    Returns
    -------
    Y_red : csr_matrix
        (N‑1, N‑1) matrix with ref row/col removed.
    index_red : {net: new_idx}
        Same mapping but without ref_name, indices packed.
    """
    # locate reference (may not exist)
    g = next((n for n in node_index if n.lower() == ref_name.lower()), None)
    if g is None:
        return Y, node_index           # nothing to do

    gidx = node_index[g]
    keep: List[int] = [i for i in range(Y.shape[0]) if i != gidx]
    Y_red = Y[keep][:, keep]           # csr slicing keeps sparsity

    # rebuild index map
    index_red: Dict[str, int] = {}
    for net, idx in node_index.items():
        if net == g:
            continue
        index_red[net] = idx - (1 if idx > gidx else 0)
    return Y_red, index_red

@dataclass
class SweepResult:
    """
    Results of a parameter/frequency sweep.

    Attributes:
        entries: List of {frequency, parameters, s_matrix} dicts.
        errors: List of error messages.
    """
    entries: List[Dict[str, Any]]
    errors: List[str]

class MatrixBuilder:
    def __init__(self, graph: NetlistGraph, circuit, tol: float = 1e-9, sparse: bool = True):
        self.graph   = graph
        self.circuit = circuit
        self.tol     = tol
        self.sparse  = sparse

        # ---------------------------------------------------------------
        # Decide reference node *first*
        # ---------------------------------------------------------------
        self._ground_net = _choose_ground(self.graph)

        # ---------------------------------------------------------------
        # Build structural pattern (needs self._ground_net)
        # ---------------------------------------------------------------
        self._pattern = self._compile_pattern()

        # ---------------------------------------------------------------
        # Immutable topology meta‑data
        # ---------------------------------------------------------------
        self._shape = (self.graph.dimension(), self.graph.dimension())
        node_index_full = self.graph.node_index(ground_net=self._ground_net)

        # rebuild index map without ground
        _, node_index = _eliminate_reference(
            sp.csr_matrix(self._shape, dtype=np.complex128),  # dummy, 0× pattern
            node_index_full,
            ref_name=self._ground_net or "gnd"
        )
        self._node_index = node_index

        ext_specs = list(self.circuit.external_ports.values())
        self._ext_idx = [node_index[s.net_name] for s in ext_specs if s.net_name in node_index]
        all_idx = set(range(len(node_index)))
        self._int_idx = list(all_idx - set(self._ext_idx))

    def export_static(self) -> StaticPackage:
        return StaticPackage(
            rows=self._pattern.rows,
            cols=self._pattern.cols,
            slices=self._pattern.slices,
            shape=self._shape,
            ext_idx=self._ext_idx,
            int_idx=self._int_idx,
            node_index=self._node_index,
            graph=self.graph,
            ground_net=self._ground_net
        )
    
    @classmethod
    def from_static(cls, static: StaticPackage, circuit, tol=1e-9, sparse=True):
        self = cls.__new__(cls)
        # shallow attributes
        self.graph    = static.graph
        self.circuit  = circuit
        self.tol      = tol
        self.sparse   = sparse
        # plug in the cached pieces
        self._pattern = StampPattern(static.rows, static.cols, static.slices)
        self._shape   = static.shape
        self._ext_idx = static.ext_idx
        self._int_idx = static.int_idx
        self._node_index = static.node_index
        self._ground_net = static.ground_net
        return self

    def _compile_pattern(self) -> StampPattern:
        """
        Build the immutable (rows, cols) pattern once per netlist **without**
        resolving parameters or evaluating component Y‑matrices.
        """
        rows: List[int]   = []
        cols: List[int]   = []
        slices: List[slice] = []

        # 1) Net‑name → matrix‑index map (ground, if present, is index 0)
        node_index = self.graph.node_index(ground_net=self._ground_net)

        # 2) Fast lookup: (component_id, port_name) ➔ net_index
        conn_lookup: Dict[Tuple[str, str], int] = {
            (c.component_id, c.port_name): node_index[c.net_name]
            for c in self.graph.connections()
        }

        cursor = 0
        for comp in self.circuit.components:
            # Net indices in *declared* port order
            nets = [conn_lookup[(comp.id, pname)] for pname in comp.ports]
            n = comp.n_ports                      # cheap: len(comp.ports)

            # Full Kronecker grid for a dense n×n sub‑matrix
            for i in range(n):
                rows.extend([nets[i]] * n)        # row i repeated n times
                cols.extend(nets)                 # all columns for that row

            # Reserve slice [cursor : cursor+n²) for this component’s data
            slices.append(slice(cursor, cursor + n * n))
            cursor += n * n

        return StampPattern(
            rows=np.asarray(rows, dtype=np.int32),
            cols=np.asarray(cols, dtype=np.int32),
            slices=slices,
        )
    
    def build_global_Y(self, circuit, ctx: "NumericContext") -> Tuple[sp.csr_matrix, Dict[str, int], YFactorCache | None]:
        """
        Assemble the global admittance matrix using the precompiled pattern.

        Returns
        -------
        Y_global : csr_matrix          # global admittance (ref node removed)
        node_index : Dict[str, int]    # net -> matrix index (no gnd)
        factor_cache : YFactorCache or None
            For reuse in Schur reduction.
        """
        from core.stamping.factors import YFactorCache
        from core.stamping.matrix_builder import _eliminate_reference  # assumes local helper

        # 1) Evaluate numeric Y-matrices per component and fill in global data
        data = np.empty(self._pattern.nnz, dtype=np.complex128)

        for comp, slc in zip(self.circuit.components, self._pattern.slices):
            Yk = comp.get_ymatrix(ctx.freq, ctx.params)     # ctx is the NumericContext
            data[slc] = Yk.reshape(comp.n_ports ** 2)

        # 2) Build sparse matrix using precompiled pattern (rows/cols never change)
        node_index_full = self.graph.node_index(ground_net=self._ground_net)

        dim = len(node_index_full)
        Y_csr = sp.coo_matrix(
            (data, (self._pattern.rows, self._pattern.cols)),
            shape=(dim, dim)
        ).tocsr()

        # 3) Eliminate ground row/col, update node_index
        Y_csr, node_index = _eliminate_reference(Y_csr, node_index_full, ref_name=self._ground_net or "gnd")

        # 4) Build reusable LU cache for Schur reduction
        ext_specs = list(circuit.external_ports.values())
        ext_idx = [node_index[s.net_name] for s in ext_specs if s.net_name in node_index]

        all_indices = set(range(Y_csr.shape[0]))
        int_idx = list(all_indices - set(ext_idx))

        factor_cache = None
        if int_idx:
            Y_ii = Y_csr[np.ix_(int_idx, int_idx)].tocsc()

            patt_key = sparsity_fingerprint(Y_ii)
            dat_key  = data_checksum(Y_ii)

            entry = _LU_FACTOR_CACHE.get(patt_key)
            if entry is None or entry.data_key != dat_key:
                from utils.linops import LinearOperator
                solver = LinearOperator(Y_ii, assume_posdef=False)
                _LU_FACTOR_CACHE[patt_key] = LUEntry(patt_key, dat_key, solver)
            else:
                solver = entry.solver

            factor_cache = YFactorCache(ext_idx=ext_idx,
                                        int_idx=int_idx,
                                        solver_ii=solver)

        return Y_csr, node_index, factor_cache

    def sweep(
        self,
        circuit,
        sweep_config: Any,
        resolved_globals: Dict[str, float]
    ) -> SweepResult:
        """
        Execute the parameter/frequency sweep in parallel.
        """
        static_pkg = self.export_static()
        # Prepare frequency list & param grid
        freq_list: List[float] = []
        param_sweeps: Dict[str, List[Any]] = {}
        for entry in sweep_config.sweep:
            if entry.param == 'f':
                if entry.range is None or entry.points is None:
                    raise RFSimError("Frequency sweep entry requires 'range' and 'points'.")
                start, end = entry.range
                freq_list = list(np.logspace(np.log10(start), np.log10(end), entry.points)) if entry.scale == 'log' else list(np.linspace(start, end, entry.points))
            else:
                if entry.values is None:
                    raise RFSimError(f"Parameter sweep for '{entry.param}' requires 'values'.")
                param_sweeps[entry.param] = entry.values

        keys = list(param_sweeps.keys())
        from itertools import product
        value_combinations = list(product(*(param_sweeps[k] for k in keys))) if keys else [()]

        # Build tasks
        tasks: List[Tuple] = []
        for freq in freq_list:
            for vals in value_combinations:
                local_params = dict(zip(keys, vals))
                tasks.append((static_pkg, circuit, circuit.global_parameters, freq, local_params, self.tol, self.sparse))

        results: List[Dict[str, Any]] = []
        errors: List[str] = []

        # Run in parallel
        from concurrent.futures import ProcessPoolExecutor
        from core.stamping._worker import evaluate_point as _evaluate_point
        with ProcessPoolExecutor() as executor:
            for entry, error in executor.map(_evaluate_point, tasks):
                results.append(entry)
                if error:
                    errors.append(error)

        return SweepResult(entries=results, errors=errors)
