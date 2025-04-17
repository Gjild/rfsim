# core/stamping/_worker.py
from __future__ import annotations
from typing import Dict, Any, Tuple

import numpy as np
from utils.matrix import y_to_s

from core.numeric.context import NumericContext
from core.parameters.resolver import resolve as _resolve_params
from core.stamping.static_pkg import StaticPackage   # only a dataclass – safe


def evaluate_point(
    args: Tuple[
        StaticPackage,            # static topology
        Any,                      # circuit model
        Dict[str, str],           # raw_global_param_expr
        float,                    # frequency
        Dict[str, Any],           # sweep_local_overrides
        float,                    # tol
        bool                      # sparse flag
    ]
) -> Tuple[Dict[str, Any], str]:
    static_pkg, circuit, raw_globals, freq, local_overrides, tol, sparse = args

    # -------------------------------------------------------------- #
    # 1) Resolve all parameters *once* for this sweep point
    # -------------------------------------------------------------- #
    exprs: Dict[str, Any] = dict(raw_globals)
    for comp in circuit.components:
        exprs.update(comp.params)
    exprs.update(local_overrides)

    try:
        resolved = _resolve_params(exprs)
    except Exception as e:
        return (
            {'frequency': freq, 'parameters': local_overrides, 's_matrix': None},
            f"Param resolution error at f={freq}: {e}"
        )

    ctx = NumericContext(freq, resolved)

    # -------------------------------------------------------------- #
    # 2) Numeric assembly & S conversion
    #    (import MatrixBuilder *here* to avoid circular‑import at top level)
    # -------------------------------------------------------------- #
    try:
        from core.stamping.matrix_builder import MatrixBuilder   # local import
        builder = MatrixBuilder.from_static(static_pkg, circuit,
                                            tol=tol, sparse=sparse)

        Y_global, _, yfac = builder.build_global_Y(circuit, ctx)

        # --- external‑port reduction ------------------------------------
        ext_specs = list(circuit.external_ports.values())
        Z0 = [spec.impedance.get_impedance(freq, resolved) for spec in ext_specs]

        if yfac:                          # internal nodes present
            Y_ee = Y_global[np.ix_(yfac.ext_idx, yfac.ext_idx)].toarray()
            Y_ei = Y_global[np.ix_(yfac.ext_idx, yfac.int_idx)]
            Y_ie = Y_global[np.ix_(yfac.int_idx, yfac.ext_idx)]
            Y_eff = Y_ee - Y_ei @ yfac.solve_internal(Y_ie.toarray())
        else:                             # no internals
            Y_eff = Y_global.toarray()

        S = y_to_s(Y_eff, Z0=Z0, reg=tol)

        return (
            {'frequency': freq,
             'parameters': local_overrides,
             's_matrix'  : S},            # ← success: return the S‑matrix
            ""
        )

    except Exception as e:
        return (
            {'frequency': freq, 'parameters': local_overrides, 's_matrix': None},
            f"Evaluation error at f={freq}: {e}"
        )
