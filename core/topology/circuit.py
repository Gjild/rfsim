# core/topology/circuit.py
import logging
import networkx as nx
from core.exceptions import RFSimError
from core.topology_manager import TopologyManager
from core.evaluator import EvaluationContext, Evaluator

class Circuit:
    def __init__(self, context=None):
        self.components = []
        self.parameters = {}
        self.topology_manager = TopologyManager()
        self.context = context or EvaluationContext()
        self.evaluator = Evaluator(self.context)
        self.external_ports = None

    def add_component(self, comp, type_name=None, params=None) -> None:
        from components.factory import get_component_class
        if not hasattr(comp, 'get_smatrix'):
            if None in (type_name, params):
                raise RFSimError("When adding by ID, both type_name and params must be provided.")
            comp = get_component_class(type_name)(comp, params)
        self.components.append(comp)
        for port in comp.ports:
            if port.connected_node:
                self.topology_manager.update_topology_for_port(comp.id, port)

    def assemble_global_ymatrix(self, freq, params):
        return self.evaluator.assemble_global_ymatrix(self, freq, params)

    def _find_component(self, comp_id: str):
        comp = next((c for c in self.components if c.id == comp_id), None)
        if comp is None:
            raise RFSimError(f"Component '{comp_id}' not found.")
        return comp

    def _find_port(self, comp, port_name: str):
        ports = [p for p in comp.ports if p.name == port_name]
        if not ports:
            raise RFSimError(f"Component '{comp.id}' has no port named '{port_name}'.")
        if len(ports) > 1:
            raise RFSimError(f"Component '{comp.id}' has duplicate ports named '{port_name}'.")
        return ports[0]

    def remove_component(self, comp_id: str) -> None:
        comp = self._find_component(comp_id)
        self.components.remove(comp)
        self._rebuild_topology()

    def _rebuild_topology(self):
        self.topology_manager = TopologyManager()
        for comp in self.components:
            for port in comp.ports:
                if port.connected_node:
                    self.topology_manager.update_topology_for_port(comp.id, port)

    def update_component_params(self, comp_id: str, new_params: dict) -> None:
        from symbolic.utils import merge_params
        comp = self._find_component(comp_id)
        comp.params = merge_params(comp.params, new_params)

    def replace_component_type(self, comp_id: str, new_type: str, params: dict) -> None:
        self.remove_component(comp_id)
        self.add_component(comp_id, new_type, params)

    def connect_port(self, comp_id: str, port_name: str, node_name: str, force: bool = False) -> None:
        comp = self._find_component(comp_id)
        port = self._find_port(comp, port_name)
        self.topology_manager.connect_port(comp_id, port, node_name)

    def disconnect_port(self, comp_id: str, port_name: str) -> None:
        comp = self._find_component(comp_id)
        port = self._find_port(comp, port_name)
        self.topology_manager.disconnect_port(comp_id, port)

    def clone(self):
        new_circuit = Circuit(context=self.context)
        new_circuit.parameters = self.parameters.copy()
        new_circuit.components = [comp.clone() for comp in self.components]
        new_circuit._rebuild_topology()
        new_circuit.external_ports = self.external_ports.copy() if self.external_ports else None
        return new_circuit

    def prepare_for_parallel(self):
        sanitized = self.clone()
        if hasattr(sanitized, 'lock'):
            sanitized.lock = None
        return sanitized

    def evaluate(self, freq: float, params: dict):
        return self.evaluator.evaluate(self, freq, params)

    def validate(self, verbose: bool = True) -> None:
        errors = []
        for comp in self.components:
            connected = [p.connected_node.name for p in comp.ports if p.connected_node]
            if len(connected) != len(set(connected)):
                errors.append(f"Component '{comp.id}' has multiple ports connected to the same node.")
            for port in comp.ports:
                if not port.connected_node:
                    errors.append(f"Floating port: Component '{comp.id}' port '{port.name}' is unconnected.")
                elif port.connected_node.name not in self.topology_manager.nodes:
                    errors.append(f"Invalid connection: Component '{comp.id}' port '{port.name}' connects to unknown node '{port.connected_node.name}'.")
        for node in self.topology_manager.nodes:
            if not self.topology_manager.graph.has_node(node):
                errors.append(f"Graph inconsistency: Registered node '{node}' missing from circuit graph.")
        for u, v, _ in self.topology_manager.graph.edges(data=True):
            if u == v:
                errors.append(f"Self-connection detected at node '{u}'.")
        if self.topology_manager.graph.number_of_nodes() and not nx.is_connected(self.topology_manager.graph):
            errors.append("The circuit graph is not fully connected. Please verify all connections.")
        if errors:
            raise RFSimError("Circuit validation failed: " + "; ".join(errors))
        if verbose:
            logging.info("Circuit validation passed with no errors.")
