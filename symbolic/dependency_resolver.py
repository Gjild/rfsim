# symbolic/dependency_resolver.py
import re
from collections import deque
from typing import Dict, List, Set
from symbolic.units import is_number

def build_dependency_graph(param_dict: Dict[str, str]) -> Dict[str, Set[str]]:
    """
    Build a dependency graph where each parameter maps to the set of parameters it depends on.
    
    :param param_dict: A dictionary mapping parameter names to their expressions.
    :return: A dictionary representing the dependency graph.
    """
    token_pattern = re.compile(r'\b([a-zA-Z_]\w*)\b')
    graph = {key: set() for key in param_dict}
    for key, expr in param_dict.items():
        if isinstance(expr, str):
            tokens = token_pattern.findall(expr)
            for token in tokens:
                if token in param_dict and not is_number(token):
                    graph[key].add(token)
    return graph

def topological_sort(graph: Dict[str, Set[str]]) -> List[str]:
    """
    Perform a topological sort on the dependency graph.
    
    :param graph: The dependency graph.
    :return: A list of parameter names sorted in dependency order.
    :raises Exception: If a circular dependency is detected.
    """
    sorted_keys = []
    # Compute in-degrees.
    in_degree = {key: 0 for key in graph}
    for deps in graph.values():
        for dep in deps:
            in_degree[dep] += 1

    queue = deque([k for k, deg in in_degree.items() if deg == 0])
    while queue:
        node = queue.popleft()
        sorted_keys.append(node)
        for key, deps in graph.items():
            if node in deps:
                deps.remove(node)
                in_degree[key] -= 1
                if in_degree[key] == 0:
                    queue.append(key)
    if len(sorted_keys) != len(graph):
        raise Exception("Circular dependency detected in parameters!")
    return sorted_keys
