import numpy as np
import networkx as nx
import logging
from core.behavior.component import Component
from core.topology.node import Node
from core.topology.port import Port
from utils.matrix import z_to_s, s_to_z
import contextlib
from core.exceptions import *
from typing import Any, Optional, Dict, List
from utils.logging_config import setup_logging, get_logger

logger = get_logger(__name__)

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
        self.backend = backend  # "Z" or "S"

    def __repr__(self):
        return f"<EvaluationContext Z0={self.Z0}, backend={self.backend}>"

class Circuit:
    def __init__(self, context=None):
        self.components = []  # list of Component objects
        self.nodes = {}       # dict: node name -> Node
        self.parameters = {}  # global parameters from YAML "parameters"
        self.graph = nx.MultiGraph()
        self.context = context if context is not None else EvaluationContext()
        self._validate_on_change = False

    def add_component(self, comp: Any, type_name: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> None:
        from components.factory import get_component_class
        if isinstance(comp, Component):
            if type_name is not None or params is not None:
                raise RFSimError("When adding a component instance, do not supply type_name or params.")
            component = comp
        else:
            if type_name is None or params is None:
                raise RFSimError("When adding by ID, type_name and params must be provided.")
            ComponentClass = get_component_class(type_name)
            component = ComponentClass(comp, params)
            component._type_name = type_name
        self.components.append(component)
        # Add ports to the graph and ensure nodes are registered.
        for port in component.ports:
            if port.connected_node:
                # Register node if not already present.
                self.nodes.setdefault(port.connected_node.name, port.connected_node)
                self.graph.add_node(port.connected_node.name, node=port.connected_node)
                self.graph.add_edge(component.id, port.connected_node.name, port=port)


    def remove_component(self, comp_id: str) -> None:
        comp = next((c for c in self.components if c.id == comp_id), None)
        if not comp:
            raise RFSimError(f"Component {comp_id} not found.")
        self.components.remove(comp)
        # Remove edges that involve this component.
        edges_to_remove = [(u, v) for u, v, d in self.graph.edges(data=True) if u == comp.id or v == comp.id]
        for edge in edges_to_remove:
            self.graph.remove_edge(*edge)
        if self._validate_on_change:
            self.validate_now()

    def update_component_params(self, comp_id: str, new_params: dict) -> None:
        from symbolic.parameters import merge_params
        comp = next((c for c in self.components if c.id == comp_id), None)
        if not comp:
            raise RFSimError(f"Component {comp_id} not found.")
        comp.params = merge_params(comp.params, new_params)
        if self._validate_on_change:
            self.validate_now()

    def replace_component_type(self, comp_id: str, new_type: str, params: dict) -> None:
        self.remove_component(comp_id)
        self.add_component(comp_id, new_type, params)

    def add_node(self, node_name: str, **attrs) -> None:
        from core.topology.node import Node
        new_node = Node(node_name, **attrs)
        self.nodes[node_name] = new_node
        # Add the new node to the graph.
        self.graph.add_node(node_name, node=new_node)
        if self._validate_on_change:
            self.validate_now()


    def remove_node(self, node_name: str, force: bool = False) -> None:
        # Check if any component's port is connected to this node.
        for comp in self.components:
            for port in comp.ports:
                if port.connected_node and port.connected_node.name == node_name:
                    if not force:
                        raise RFSimError(f"Cannot remove node {node_name}: still connected to component {comp.id}.")
                    else:
                        port.connected_node = None
        if node_name in self.nodes:
            del self.nodes[node_name]
        if self._validate_on_change:
            self.validate_now()

    def connect_port(self, comp_id: str, port_name: str, node_name: str, force: bool = False) -> None:
        comp = next((c for c in self.components if c.id == comp_id), None)
        if not comp:
            raise RFSimError(f"Component {comp_id} not found.")
        matching_ports = [p for p in comp.ports if p.name == port_name]
        if not matching_ports:
            raise RFSimError(f"Component {comp_id} has no port named {port_name}.")
        if len(matching_ports) > 1:
            raise RFSimError(f"Component {comp_id} has duplicate ports named {port_name}.")
        port = matching_ports[0]
        # If the node does not exist in the circuit's nodes, create and register it.
        if node_name not in self.nodes:
            from core.topology.node import Node
            self.nodes[node_name] = Node(node_name)
        # Connect the port.
        port.connected_node = self.nodes[node_name]
        # **Add the node and an edge to the circuit graph.**
        self.graph.add_node(node_name, node=port.connected_node)
        self.graph.add_edge(comp_id, node_name, port=port)
        if self._validate_on_change:
            self.validate_now()


    def disconnect_port(self, comp_id: str, port_name: str) -> None:
        comp = next((c for c in self.components if c.id == comp_id), None)
        if not comp:
            raise RFSimError(f"Component {comp_id} not found.")
        matching_ports = [p for p in comp.ports if p.name == port_name]
        if not matching_ports:
            raise RFSimError(f"Component {comp_id} has no port named {port_name}.")
        port = matching_ports[0]
        port.connected_node = None
        if self._validate_on_change:
            self.validate_now()

    def to_yaml_dict(self) -> dict:
        comp_list = [comp.to_yaml_dict() for comp in self.components]
        connections = []
        for comp in self.components:
            for port in comp.ports:
                if port.connected_node:
                    connections.append({"port": f"{comp.id}.{port.name}", "node": port.connected_node.name})
        return {
            "parameters": self.parameters,
            "components": comp_list,
            "connections": connections
        }

    def to_yaml_file(self, path: str) -> None:
        import yaml
        with open(path, "w") as f:
            yaml.dump(self.to_yaml_dict(), f)

    def validate_on_change(self, enable: bool = True) -> None:
        self._validate_on_change = enable

    def validate_now(self) -> None:
        self.validate()

    @contextlib.contextmanager
    def transaction(self):
        old_state = self._validate_on_change
        self._validate_on_change = False
        try:
            yield
        finally:
            self._validate_on_change = old_state
            self.validate_now()

    def assemble_global_zmatrix(self, freq, params):
        nodes = list(self.nodes.keys())
        n = len(nodes)
        node_index = {node: i for i, node in enumerate(nodes)}
        Z_global = np.zeros((n, n), dtype=complex)
        if self.context.backend == "Z":
            for comp in self.components:
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
            for comp in self.components:
                S = comp.get_smatrix(freq, params, Z0=self.context.Z0)
                S_blocks.append(S)
            S_global = np.block([
                [S_blocks[i] if i == j else np.zeros((S_blocks[i].shape[0], S_blocks[j].shape[1]), dtype=complex)
                 for j in range(len(S_blocks))]
                for i in range(len(S_blocks))
            ])
            return s_to_z(S_global, Z0=self.context.Z0), {}

    def evaluate(self, freq: float, params: dict):
        # Assemble the full impedance matrix and get the node index mapping.
        Z_global, node_index = self.assemble_global_zmatrix(freq, params)

        # If external_ports is defined, perform a network reduction.
        if hasattr(self, 'external_ports') and self.external_ports:
            # Identify external nodes (physical ports) present in the circuit.
            ext_nodes = [node for node in self.external_ports if node in node_index]
            missing_ext = [node for node in self.external_ports if node not in node_index]
            if missing_ext:
                logger.error("External nodes not found in circuit: " + ", ".join(missing_ext))
            ext_indices = [node_index[node] for node in ext_nodes]

            # Internal nodes: all nodes that are not designated as external.
            all_nodes = list(node_index.keys())
            int_nodes = [node for node in all_nodes if node not in ext_nodes]
            int_indices = [node_index[node] for node in int_nodes]

            # Partition the global Z matrix.
            Z_ee = Z_global[np.ix_(ext_indices, ext_indices)]
            if int_indices:
                Z_ei = Z_global[np.ix_(ext_indices, int_indices)]
                Z_ie = Z_global[np.ix_(int_indices, ext_indices)]
                Z_ii = Z_global[np.ix_(int_indices, int_indices)]
                try:
                    Z_ii_inv = np.linalg.inv(Z_ii)
                except np.linalg.LinAlgError:
                    logger.warning("Z_ii is singular; using pseudoinverse for network reduction.")
                    Z_ii_inv = np.linalg.pinv(Z_ii)
                # Compute the effective impedance matrix via the Schur complement.
                effective_Z = Z_ee - Z_ei @ Z_ii_inv @ Z_ie
            else:
                # No internal nodes: effective impedance is just the extracted block.
                effective_Z = Z_ee

            # Convert the effective impedance matrix to an S-matrix.
            S = z_to_s(effective_Z, Z0=self.context.Z0)
            port_order = ext_nodes  # Preserve the order of external ports as defined in the netlist.
            stats = {"n_ports": len(port_order)}
            return EvaluationResult(S, port_order, node_index, stats=stats)
        else:
            # Fallback: use all component ports (old behavior)
            port_order = []
            port_indices = []
            for comp in self.components:
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




    def validate(self, verbose: bool = True) -> None:
        """
        Validate the circuit's topology and graph consistency.
        
        This method checks:
        - That every port is connected to a registered node.
        - That there are no duplicate or misnamed nodes.
        - That the internal graph is connected.
        - That there are no self-connections.
        
        Raises:
            TopologyError: If any validation check fails.
        """
        errors = []

        # Check for each component's ports.
        for comp in self.components:
            for port in comp.ports:
                if port.connected_node is None:
                    errors.append(f"Floating port: Component '{comp.id}' port '{port.name}' is unconnected.")
                elif port.connected_node.name not in self.nodes:
                    errors.append(f"Invalid connection: Component '{comp.id}' port '{port.name}' connects to unknown node '{port.connected_node.name}'.")

        # Check for duplicate node names.
        node_names = list(self.nodes.keys())
        if len(node_names) != len(set(node_names)):
            errors.append("Duplicate node names detected in the circuit.")

        # Check the consistency of the graph nodes with the circuit's nodes.
        for node_name in self.nodes:
            if not self.graph.has_node(node_name):
                errors.append(f"Graph inconsistency: Registered node '{node_name}' missing from circuit graph.")

        # Check for self-connections in the graph.
        for u, v, data in self.graph.edges(data=True):
            if u == v:
                errors.append(f"Self-connection detected at node '{u}'.")

        # Check connectivity of the entire circuit.
        if self.graph.number_of_nodes() > 0 and not nx.is_connected(self.graph):
            errors.append("The circuit graph is not fully connected. Please verify all connections.")

        # Report errors if any.
        if errors:
            error_msg = "; ".join(errors)
            logging.error("Circuit validation failed: " + error_msg)
            from core.exceptions import TopologyError
            raise TopologyError(error_msg)

        if verbose:
            logging.info("Circuit validation passed with no errors.")
