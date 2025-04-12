# symbolic/dependency_resolver.py
import re
from collections import deque
from typing import Dict, List, Set
from symbolic.units import is_number

def build_dependency_graph(param_dict: Dict[str, str]) -> Dict[str, Set[str]]:
    """
    Build a dependency graph mapping each parameter to the set of parameters
    it depends on.

    :param param_dict: Dictionary mapping parameter names to their expressions.
    :return: A dictionary representing the dependency graph.
    """
    token_pattern = re.compile(r'\b([a-zA-Z_]\w*)\b')
    # Use a dictionary comprehension to build the graph.
    return {
        key: (
            {token for token in token_pattern.findall(expr)
             if token in param_dict and not is_number(token)}
            if isinstance(expr, str) else set()
        )
        for key, expr in param_dict.items()
    }

def topological_sort(graph: Dict[str, Set[str]]) -> List[str]:
    """
    Perform a topological sort on the dependency graph.
    
    :param graph: The dependency graph mapping parameter names to dependencies.
    :return: A list of parameter names in a dependency-resolved order.
    :raises Exception: If a circular dependency is detected.
    """
    # Initialize in-degree for each node and build a reverse dependency mapping.
    in_degree = {node: 0 for node in graph}
    reverse_map: Dict[str, Set[str]] = {node: set() for node in graph}
    
    for node, deps in graph.items():
        for dep in deps:
            in_degree[dep] += 1
            reverse_map.setdefault(dep, set()).add(node)
    
    # Start with nodes having in-degree of zero.
    queue = deque([node for node, degree in in_degree.items() if degree == 0])
    sorted_nodes = []

    while queue:
        node = queue.popleft()
        sorted_nodes.append(node)
        # For each node that depends on the current node,
        # reduce its in-degree and add it to the queue if zero.
        for dependent in reverse_map.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    if len(sorted_nodes) != len(graph):
        raise Exception("Circular dependency detected in parameters!")
    
    return sorted_nodes
