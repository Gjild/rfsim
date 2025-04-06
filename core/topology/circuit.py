# core/topology/circuit.py
import logging
import networkx as nx
from core.exceptions import RFSimError
from core.topology_manager import TopologyManager
from core.evaluator import EvaluationContext, Evaluator

class Circuit:
    def __init__(self, context=None):
        self.components = []         # List of component instances
        self.parameters = {}         # Global parameters
        self.topology_manager = TopologyManager()  # Delegate topology management
        self.context = context if context is not None else EvaluationContext()
        self.evaluator = Evaluator(self.context)     # Evaluator for simulation
        self.external_ports = None   # Optional list of external ports

    def add_component(self, comp, type_name=None, params=None) -> None:
        from components.factory import get_component_class
        if hasattr(comp, 'get_smatrix'):
            component = comp
        else:
            if type_name is None or params is None:
                raise RFSimError("When adding by ID, both type_name and params must be provided.")
            ComponentClass = get_component_class(type_name)
            component = ComponentClass(comp, params)
        self.components.append(component)
        # Update topology manager for ports that are already connected.
        for port in component.ports:
            if port.connected_node is not None:
                self.topology_manager.update_topology_for_port(component.id, port)

    def assemble_global_ymatrix(self, freq, params):
        return self.evaluator.assemble_global_ymatrix(self, freq, params)

    def remove_component(self, comp_id: str) -> None:
        """
        Remove a component from the circuit and rebuild topology.
        """
        comp = next((c for c in self.components if c.id == comp_id), None)
        if not comp:
            raise RFSimError(f"Component '{comp_id}' not found.")
        self.components.remove(comp)
        self._rebuild_topology()

    def _rebuild_topology(self):
        """
        Rebuild the topology graph based on current component connections.
        """
        self.topology_manager = TopologyManager()
        for comp in self.components:
            for port in comp.ports:
                if port.connected_node:
                    self.topology_manager.update_topology_for_port(comp.id, port)

    def update_component_params(self, comp_id: str, new_params: dict) -> None:
        """
        Update the parameters of a specific component.
        """
        from symbolic.utils import merge_params
        comp = next((c for c in self.components if c.id == comp_id), None)
        if not comp:
            raise RFSimError(f"Component '{comp_id}' not found.")
        comp.params = merge_params(comp.params, new_params)

    def replace_component_type(self, comp_id: str, new_type: str, params: dict) -> None:
        """
        Replace an existing component with a new type.
        """
        self.remove_component(comp_id)
        self.add_component(comp_id, new_type, params)

    def connect_port(self, comp_id: str, port_name: str, node_name: str, force: bool = False) -> None:
        """
        Delegate connecting a component port to the TopologyManager.
        """
        comp = next((c for c in self.components if c.id == comp_id), None)
        if not comp:
            raise RFSimError(f"Component '{comp_id}' not found.")
        matching_ports = [p for p in comp.ports if p.name == port_name]
        if not matching_ports:
            raise RFSimError(f"Component '{comp_id}' has no port named '{port_name}'.")
        if len(matching_ports) > 1:
            raise RFSimError(f"Component '{comp_id}' has duplicate ports named '{port_name}'.")
        port = matching_ports[0]
        self.topology_manager.connect_port(comp_id, port, node_name)

    def disconnect_port(self, comp_id: str, port_name: str) -> None:
        """
        Delegate disconnecting a port to the TopologyManager.
        """
        comp = next((c for c in self.components if c.id == comp_id), None)
        if not comp:
            raise RFSimError(f"Component '{comp_id}' not found.")
        matching_ports = [p for p in comp.ports if p.name == port_name]
        if not matching_ports:
            raise RFSimError(f"Component '{comp_id}' has no port named '{port_name}'.")
        port = matching_ports[0]
        self.topology_manager.disconnect_port(comp_id, port)

    def clone(self):
        """
        Create a shallow clone of the circuit, including components and parameters.
        """
        new_circuit = Circuit(context=self.context)
        new_circuit.parameters = self.parameters.copy()
        new_circuit.components = [comp.clone() for comp in self.components]
        new_circuit._rebuild_topology()
        new_circuit.external_ports = self.external_ports.copy() if self.external_ports else None
        return new_circuit

    def prepare_for_parallel(self):
        """
        Prepare a sanitized clone for parallel evaluation.
        """
        sanitized = self.clone()
        if hasattr(sanitized, 'lock'):
            sanitized.lock = None
        return sanitized

    def evaluate(self, freq: float, params: dict):
        """
        Delegate circuit evaluation to the Evaluator.
        """
        return self.evaluator.evaluate(self, freq, params)

    def validate(self, verbose: bool = True) -> None:
        """
        Perform basic validation of component connections and graph consistency.
        """
        errors = []
        for comp in self.components:
            for port in comp.ports:
                if port.connected_node is None:
                    errors.append(f"Floating port: Component '{comp.id}' port '{port.name}' is unconnected.")
                elif port.connected_node.name not in self.topology_manager.nodes:
                    errors.append(f"Invalid connection: Component '{comp.id}' port '{port.name}' connects to unknown node '{port.connected_node.name}'.")
        for node_name in self.topology_manager.nodes:
            if not self.topology_manager.graph.has_node(node_name):
                errors.append(f"Graph inconsistency: Registered node '{node_name}' missing from circuit graph.")
        for u, v, data in self.topology_manager.graph.edges(data=True):
            if u == v:
                errors.append(f"Self-connection detected at node '{u}'.")
        if self.topology_manager.graph.number_of_nodes() > 0 and not nx.is_connected(self.topology_manager.graph):
            errors.append("The circuit graph is not fully connected. Please verify all connections.")
        if errors:
            raise RFSimError("Circuit validation failed: " + "; ".join(errors))
        if verbose:
            logging.info("Circuit validation passed with no errors.")
