import numpy as np
import networkx as nx
import logging
import scipy.sparse as sp
from utils.matrix import y_to_s, s_to_y  # Now supports vectorized and arbitrary impedances

class EvaluationResult:
    def __init__(self, s_matrix, port_order, node_mapping, errors=None, stats=None):
        self.s_matrix = s_matrix
        self.port_order = port_order
        self.node_mapping = node_mapping
        self.errors = errors or []
        self.stats = stats or {}

    def __repr__(self):
        s_shape = self.s_matrix.shape if self.s_matrix is not None else None
        return (f"<EvaluationResult: s_matrix shape={s_shape}, ports={self.port_order}, "
                f"errors={self.errors}, stats={self.stats}>")

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
    def __init__(self, context):
        self.context = context

    def _get_component_ymatrix(self, comp, freq, params):
        """
        Attempt to retrieve the Y matrix from the component.
        If unavailable, convert its S matrix to a Y matrix.
        """
        try:
            return comp.get_ymatrix(freq, params)
        except AttributeError:
            try:
                S = comp.get_smatrix(freq, params, Z0=self.context.Z0)
                return s_to_y(S, Z0=self.context.Z0)
            except Exception as e:
                logging.error(f"Component {comp.id} conversion failure: {e}")
                return None

    def assemble_global_ymatrix(self, circuit, freq, params):
        """
        Assemble the global nodal Y matrix for the circuit.
        Returns:
            Y_global: dense admittance matrix
            node_index: dict mapping node name -> row/col index
        """
        node_names = list(circuit.topology_manager.nodes.keys())
        n = len(node_names)
        node_index = {node: i for i, node in enumerate(node_names)}

        rows, cols, data = [], [], []
        for comp in circuit.components:
            Y_comp = self._get_component_ymatrix(comp, freq, params)
            if Y_comp is None:
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
        Y_sparse = sp.coo_matrix((data, (rows, cols)), shape=(n, n))
        return Y_sparse.todense(), node_index

    def evaluate(self, circuit, freq: float, params: dict):
        """
        Evaluate the circuit: build the global Y matrix, reduce it to the external ports,
        and then convert it to the scattering matrix (S-parameters).
        """
        Y_global, node_index = self.assemble_global_ymatrix(circuit, freq, params)

        if circuit.external_ports:
            return self._evaluate_external(circuit, freq, params, Y_global, node_index)
        else:
            return self._evaluate_fallback(circuit, freq, params, Y_global, node_index)

    def _evaluate_external(self, circuit, freq, params, Y_global, node_index):
        ext_nodes, ext_impedance = [], []
        for node_name, port_obj in circuit.external_ports.items():
            if node_name not in node_index:
                raise ValueError(f"External node '{node_name}' not found in circuit.")
            ext_nodes.append(node_name)
            try:
                imp = port_obj.impedance.get_impedance(freq, params)
            except Exception as e:
                logging.error(f"Failed to evaluate impedance for port '{node_name}': {e}")
                raise
            ext_impedance.append(imp)

        ext_indices = [node_index[n] for n in ext_nodes]
        all_nodes = list(node_index.keys())
        int_nodes = [n for n in all_nodes if n not in ext_nodes and n.lower() != "gnd"]
        int_indices = [node_index[n] for n in int_nodes]

        Y_ee = Y_global[np.ix_(ext_indices, ext_indices)]
        if int_indices:
            Y_ei = Y_global[np.ix_(ext_indices, int_indices)]
            Y_ie = Y_global[np.ix_(int_indices, ext_indices)]
            Y_ii = Y_global[np.ix_(int_indices, int_indices)]
            try:
                Y_ii_inv = np.linalg.inv(Y_ii)
            except np.linalg.LinAlgError:
                logging.warning("Y_ii is singular; using pseudoinverse for network reduction.")
                Y_ii_inv = np.linalg.pinv(Y_ii)
            Y_eff = Y_ee - Y_ei @ Y_ii_inv @ Y_ie
        else:
            Y_eff = Y_ee

        S = y_to_s(Y_eff, Z0=ext_impedance)
        stats = {"n_ports": len(ext_nodes), "ref_impedance_vector": ext_impedance}
        return EvaluationResult(S, ext_nodes, node_index, stats=stats)

    def _evaluate_fallback(self, circuit, freq, params, Y_global, node_index):
        port_order, ref_impedance, port_indices = [], [], []
        for comp in circuit.components:
            for port in comp.ports:
                port_order.append(f"{comp.id}.{port.name}")
                if port.connected_node and port.connected_node.name in node_index:
                    port_indices.append(node_index[port.connected_node.name])
                    try:
                        impedance = port.impedance.get_impedance(freq, params)
                    except Exception as e:
                        logging.error(f"Error retrieving impedance for port {comp.id}.{port.name}: {e}")
                        impedance = self.context.Z0
                else:
                    port_indices.append(None)
                    impedance = self.context.Z0
                ref_impedance.append(impedance)

        n_ports = len(port_order)
        Y_ports = np.zeros((n_ports, n_ports), dtype=complex)
        for i in range(n_ports):
            for j in range(n_ports):
                if port_indices[i] is not None and port_indices[j] is not None:
                    Y_ports[i, j] = Y_global[port_indices[i], port_indices[j]]
        S = y_to_s(Y_ports, Z0=ref_impedance)
        stats = {"n_ports": n_ports, "ref_impedance_vector": ref_impedance}
        return EvaluationResult(S, port_order, node_index, stats=stats)
