# core/components/subcircuit.py
"""
Subcircuit component plugin for RFSim v2.
Encapsulates a nested netlist as a multi-port component via its interface mapping.
"""
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

from core.components.base import Component
from core.exceptions import ParameterError
from core.components.plugin_loader import ComponentFactory
from core.inout.netlist import load_netlist
from core.topology.netlist_graph import NetlistGraph
from core.stamping.matrix_builder import MatrixBuilder
from core.stamping.static_pkg import StaticPackage
from core.parameters.resolver import resolve as _resolve_params
from core.numeric.context import NumericContext


class SubcircuitComponent(Component):
    """
    Hierarchical subcircuit component.

    Params dict must contain:
      - file: Path to nested netlist YAML.
      - mapping: Dict mapping external port names to internal net names.

    Ports are the keys of the mapping.
    """
    type_name = "subcircuit"

    def __init__(self, comp_id: str, params: Dict[str, Any]) -> None:
        super().__init__(comp_id, params)
        # Validate params
        try:
            file_path = params["file"]
            interface_map = params["mapping"]
        except KeyError as e:
            raise ParameterError(
                f"Subcircuit '{comp_id}' requires 'file' and 'mapping' in params; missing {e.args[0]}"
            )
        # ------------------------------------------------------------
        # 1) Load & freeze the nested circuit
        # ------------------------------------------------------------
        self.nested_model = load_netlist(Path(file_path))
        self.interface_map: Dict[str, str] = interface_map
        self._ports: List[str] = list(interface_map.keys())

        # ------------------------------------------------------------
        # 2) Compile the immutable topology once
        # ------------------------------------------------------------
        graph = NetlistGraph.from_circuit(self.nested_model)
        builder = MatrixBuilder(graph, self.nested_model, tol=1e-9)
        self._static_pkg: StaticPackage = builder.export_static()   # picklable
        # (discard the heavy builder instance – we can resurrect it on demand)



    @property
    def ports(self) -> List[str]:
        return self._ports

    def get_ymatrix(self, freq: float, params: Dict[str, float]) -> np.ndarray:
        """
        Build the nested circuit, reduce it to the interface nets,
        and return its multi‑port admittance matrix.
        """
        # --------------------------------------------------------
        # 1) Resolve *all* parameters visible to the subcircuit
        #    (outer numeric values + nested expressions)
        # --------------------------------------------------------
        exprs: Dict[str, object] = dict(params)                    # outer already numeric
        exprs.update(self.nested_model.global_parameters)          # may still be strings
        for comp in self.nested_model.components:                  #  + per‑component
            exprs.update(comp.params)
        resolved = _resolve_params(exprs)

        ctx = NumericContext(freq, resolved)

        # --------------------------------------------------------
        # 2) Assemble Y using the cached topology
        # --------------------------------------------------------
        builder = MatrixBuilder.from_static(self._static_pkg,
                                            self.nested_model,
                                            tol=1e-9, sparse=True)
        Y_global, node_index, _ = builder.build_global_Y(self.nested_model, ctx)

        Yg = Y_global.toarray()

        # --------------------------------------------------------
        # 3) Pull out the sub‑matrix defined by interface mapping
        # --------------------------------------------------------
        try:
            idxs = [node_index[self.interface_map[p]] for p in self._ports]
        except KeyError as missing:
            raise ParameterError(
                f"Subcircuit '{self.id}': internal net '{missing.args[0]}' not found"
            ) from None

        return Yg[np.ix_(idxs, idxs)]


# Register the subcircuit component
ComponentFactory.register(SubcircuitComponent)
