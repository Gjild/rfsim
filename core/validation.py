# core/validation.py
"""
Structural validation utilities for RFSim v2.
Ensures that all component ports are connected to a net and that the
resulting net graph is fully connected (ignoring the ground node).
"""
from typing import List, Dict
import networkx as nx

from core.exceptions import RFSimError
from core.topology.netlist_graph import NetlistGraph


def validate_circuit_structure(circuit) -> None:
    """
    Perform pre‑sweep sanity checks on a CircuitModel.

    Raises:
        RFSimError with a descriptive message if validation fails.
    """
    # 1) All declared ports must appear in the connections list
    missing: List[str] = []
    connection_map: Dict[str, List[str]] = {}
    for conn in circuit.connections:
        key = f"{conn.component_id}.{conn.port_name}"
        connection_map.setdefault(conn.component_id, []).append(conn.port_name)

    for comp in circuit.components:
        declared = set(comp.ports)
        wired = set(connection_map.get(comp.id, []))
        dangling = declared - wired
        if dangling:
            for p in dangling:
                missing.append(f"Component '{comp.id}' port '{p}' unconnected")

    if missing:
        raise RFSimError("Floating port errors: " + "; ".join(missing))

    # 2) Graph connectivity (ignore 'gnd')
    graph = nx.Graph()
    # Add nodes for nets
    nets = {conn.net_name for conn in circuit.connections}
    for net in nets:
        if net.lower() == 'gnd':
            continue
        graph.add_node(net)

    # Add an edge for every component joining two nets (series element)
    conn_dict: Dict[str, List[str]] = {}
    for conn in circuit.connections:
        conn_dict.setdefault(conn.component_id, []).append(conn.net_name)
    for nets in conn_dict.values():
        if len(nets) == 2:
            a, b = nets
            if a.lower() != 'gnd' and b.lower() != 'gnd':
                graph.add_edge(a, b)
        # For multi‑port devices, connect each net to every other (conservative)
        if len(nets) > 2:
            for i in range(len(nets)):
                for j in range(i + 1, len(nets)):
                    a, b = nets[i], nets[j]
                    if a.lower() != 'gnd' and b.lower() != 'gnd':
                        graph.add_edge(a, b)

    if graph.number_of_nodes() and not nx.is_connected(graph):
        raise RFSimError("Circuit graph is not fully connected; some nets are isolated.")
