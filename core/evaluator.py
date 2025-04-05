# core/evaluator.py
import numpy as np
import networkx as nx
import logging
from utils.matrix import z_to_s, s_to_z

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

    def assemble_global_zmatrix(self, circuit, freq, params):
        """
        Assemble the global impedance matrix for a circuit.
        """
        node_names = list(circuit.topology_manager.nodes.keys())
        n = len(node_names)
        node_index = {node: i for i, node in enumerate(node_names)}
        Z_global = np.zeros((n, n), dtype=complex)
        if self.context.backend == "Z":
            for comp in circuit.components:
                try:
                    Z_comp = comp.get_zmatrix(freq, params)
                except AttributeError:
                    try:
                        S = comp.get_smatrix(freq, params, Z0=self.context.Z0)
                        Z_comp = s_to_z(S, Z0=self.context.Z0)
                    except Exception as e:
                        logging.error(f"Component {comp.id} conversion failure: {e}")
                        continue
                port_nodes = [port.connected_node.name for port in comp.ports if port.connected_node]
                if len(port_nodes) != Z_comp.shape[0]:
                    logging.warning(f"Component {comp.id} port count mismatch in Z stamping.")
                    continue
                for i, ni in enumerate(port_nodes):
                    for j, nj in enumerate(port_nodes):
                        Z_global[node_index[ni], node_index[nj]] += Z_comp[i, j]
            for i in range(n):
                Z_global[i, i] += self.context.Z0
            return Z_global, node_index
        else:
            S_blocks = []
            for comp in circuit.components:
                S = comp.get_smatrix(freq, params, Z0=self.context.Z0)
                S_blocks.append(S)
            S_global = np.block([
                [S_blocks[i] if i == j else np.zeros((S_blocks[i].shape[0], S_blocks[j].shape[1]), dtype=complex)
                 for j in range(len(S_blocks))]
                for i in range(len(S_blocks))
            ])
            return s_to_z(S_global, Z0=self.context.Z0), {}

    def evaluate(self, circuit, freq: float, params: dict):
        """
        Evaluate the circuit at the given frequency and parameter values.
        """
        Z_global, node_index = self.assemble_global_zmatrix(circuit, freq, params)
        if hasattr(circuit, 'external_ports') and circuit.external_ports:
            ext_nodes = [node for node in circuit.external_ports if node in node_index]
            missing_ext = [node for node in circuit.external_ports if node not in node_index]
            if missing_ext:
                logging.error("External nodes not found in circuit: " + ", ".join(missing_ext))
            ext_indices = [node_index[node] for node in ext_nodes]
            all_nodes = list(node_index.keys())
            int_nodes = [node for node in all_nodes if node not in ext_nodes]
            int_indices = [node_index[node] for node in int_nodes]
            Z_ee = Z_global[np.ix_(ext_indices, ext_indices)]
            if int_indices:
                Z_ei = Z_global[np.ix_(ext_indices, int_indices)]
                Z_ie = Z_global[np.ix_(int_indices, ext_indices)]
                Z_ii = Z_global[np.ix_(int_indices, int_indices)]
                try:
                    Z_ii_inv = np.linalg.inv(Z_ii)
                except np.linalg.LinAlgError:
                    logging.warning("Z_ii is singular; using pseudoinverse for network reduction.")
                    Z_ii_inv = np.linalg.pinv(Z_ii)
                effective_Z = Z_ee - Z_ei @ Z_ii_inv @ Z_ie
            else:
                effective_Z = Z_ee
            S = z_to_s(effective_Z, Z0=self.context.Z0)
            port_order = ext_nodes
            stats = {"n_ports": len(port_order)}
            return EvaluationResult(S, port_order, node_index, stats=stats)
        else:
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
            Z_ports = np.zeros((n_ports, n_ports), dtype=complex)
            for i in range(n_ports):
                for j in range(n_ports):
                    if port_indices[i] is None or port_indices[j] is None:
                        Z_ports[i, j] = 1e12
                    else:
                        Z_ports[i, j] = Z_global[port_indices[i], port_indices[j]]
            S = z_to_s(Z_ports, Z0=self.context.Z0)
            stats = {"n_ports": n_ports}
            return EvaluationResult(S, port_order, node_index, stats=stats)
