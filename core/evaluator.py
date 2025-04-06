# core/evaluator.py
import numpy as np
import networkx as nx
import logging
import scipy.sparse as sp

class EvaluationResult:
    def __init__(self, s_matrix, port_order, node_mapping, errors=None, stats=None):
        self.s_matrix = s_matrix
        self.port_order = port_order
        self.node_mapping = node_mapping
        self.errors = errors if errors is not None else []
        self.stats = stats if stats is not None else {}

    def __repr__(self):
        return (f"<EvaluationResult: s_matrix shape={self.s_matrix.shape if self.s_matrix is not None else None}, "
                f"ports={self.port_order}, errors={self.errors}, stats={self.stats}>")

class EvaluationContext:
    def __init__(self, Z0=50, backend="Z"):
        self.Z0 = Z0
        self.backend = backend  # Either "Z" or "S"

    def __repr__(self):
        return f"<EvaluationContext Z0={self.Z0}, backend={self.backend}>"

class Evaluator:
    """
    Encapsulates circuit evaluation strategies.
    """
    def __init__(self, context: EvaluationContext):
        self.context = context

    def assemble_global_ymatrix(self, circuit, freq, params):
        """
        Assemble the global nodal Y matrix for the circuit.
        Then we can do node reduction, etc.

        Returns:
            Y_global: (n x n) complex array (admittance)
            node_index: dict mapping node name -> row/col index
        """
        node_names = list(circuit.topology_manager.nodes.keys())
        n = len(node_names)
        node_index = {node: i for i, node in enumerate(node_names)}

        # Accumulate sparse matrix data.
        rows = []
        cols = []
        data = []

        for comp in circuit.components:
            try:
                Y_comp = comp.get_ymatrix(freq, params)
            except AttributeError:
                try:
                    S = comp.get_smatrix(freq, params, Z0=self.context.Z0)
                    from utils.matrix import s_to_y
                    Y_comp = s_to_y(S, Z0=self.context.Z0)
                except Exception as e:
                    logging.error(f"Component {comp.id} conversion failure: {e}")
                    continue

            # Map component ports to circuit node indices.
            port_nodes = [p.connected_node.name for p in comp.ports if p.connected_node]
            if len(port_nodes) != Y_comp.shape[0]:
                logging.warning(f"Component {comp.id} port count mismatch in Y stamping.")
                continue

            for i, ni in enumerate(port_nodes):
                for j, nj in enumerate(port_nodes):
                    rows.append(node_index[ni])
                    cols.append(node_index[nj])
                    data.append(Y_comp[i, j])

        # Create a sparse matrix from the data.
        Y_global_sparse = sp.coo_matrix((data, (rows, cols)), shape=(n, n))
        Y_global = Y_global_sparse.todense()
        return Y_global, node_index

    def evaluate(self, circuit, freq: float, params: dict):
        """
        The main high-level function. We build Y_global, reduce it,
        then get S from the reduced Y.
        """
        Y_global, node_index = self.assemble_global_ymatrix(circuit, freq, params)

        # If the user defined external ports:
        if hasattr(circuit, 'external_ports') and circuit.external_ports:
            ext_nodes = [n for n in circuit.external_ports if n in node_index]
            missing_ext = [n for n in circuit.external_ports if n not in node_index]
            if missing_ext:
                logging.error("External nodes not found in circuit: " + ", ".join(missing_ext))

            ext_indices = [node_index[n] for n in ext_nodes]
            all_nodes = list(node_index.keys())
            int_nodes = [n for n in all_nodes if n not in ext_nodes]
            int_indices = [node_index[n] for n in int_nodes]

            Y_ee = Y_global[np.ix_(ext_indices, ext_indices)]
            if int_indices:
                Y_ei = Y_global[np.ix_(ext_indices, int_indices)]
                Y_ie = Y_global[np.ix_(int_indices, ext_indices)]
                Y_ii = Y_global[np.ix_(int_indices, int_indices)]
                # reduce
                try:
                    Y_ii_inv = np.linalg.inv(Y_ii)
                except np.linalg.LinAlgError:
                    logging.warning("Y_ii is singular; using pseudoinverse for network reduction.")
                    Y_ii_inv = np.linalg.pinv(Y_ii)
                Y_eff = Y_ee - Y_ei @ Y_ii_inv @ Y_ie
            else:
                # no internal nodes
                Y_eff = Y_ee

            # Convert to S
            from utils.matrix import y_to_s
            S = y_to_s(Y_eff, Z0=self.context.Z0)
            port_order = ext_nodes
            stats = {"n_ports": len(port_order)}
            return EvaluationResult(S, port_order, node_index, stats=stats)

        else:
            # No external_ports → we just treat each component's ports as "ports"
            # same idea: gather their node indices -> produce Y_ports -> convert to S
            port_order = []
            port_indices = []
            for comp in circuit.components:
                for port in comp.ports:
                    port_order.append(f"{comp.id}.{port.name}")
                    if port.connected_node and node_index:
                        port_indices.append(node_index[port.connected_node.name])
                    else:
                        port_indices.append(None)

            n_ports = len(port_order)
            Y_ports = np.zeros((n_ports, n_ports), dtype=complex)
            for i in range(n_ports):
                for j in range(n_ports):
                    if port_indices[i] is None or port_indices[j] is None:
                        # treat that like an open?
                        Y_ports[i, j] += 0.0
                    else:
                        Y_ports[i, j] += Y_global[port_indices[i], port_indices[j]]

            S = y_to_s(Y_ports, Z0=self.context.Z0)
            stats = {"n_ports": n_ports}
            return EvaluationResult(S, port_order, node_index, stats=stats)
