# core/components/base.py
"""
Base Component API for RFSim v2.
Defines the interface for port definitions and admittance stamping.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
import numpy as np
from core.parameters.resolver import resolve as _resolve_params


class Component(ABC):
    """
    Abstract base class for all RF components.
    Subclasses must define port ordering and Y-matrix behavior.
    """
    def __init__(self, comp_id: str, params: Dict[str, Any]):
        self.id = comp_id
        # Raw parameter expressions (strings or sympy Expr)
        self.params = params

    @property
    @abstractmethod
    def ports(self) -> List[str]:
        """
        Ordered list of port names for this component.
        Port order must match indices of the Y-matrix.
        """
        pass

    @property
    def n_ports(self) -> int:
        """Number of ports this component defines."""
        return len(self.ports)

    @abstractmethod
    def get_ymatrix(self, freq: float, params: Dict[str, float]) -> np.ndarray:
        """
        Compute the component's admittance matrix at the given frequency
        and with fully resolved numeric parameters.

        Returns:
            A NumPy array of shape (n_ports, n_ports).
        """
        pass

    def y_stamp(
        self,
        net_indices: List[int],
        freq: float,
        params: Dict[str, float]
    ) -> Tuple[List[int], List[int], List[complex]]:
        """
        Create sparse matrix stamp triplets for MNA assembly.

        Args:
            net_indices: List of integer net indices corresponding to self.ports.
            freq: Frequency for evaluation.
            params: Dictionary of resolved parameters (global + local).

        Returns:
            Tuple of (rows, cols, data) for sparse matrix assembly.
        """
       # Merge global/sweep parameters with the component’s own definitions
        # and resolve them to *numeric* values once per evaluation.
        resolved = _resolve_params({**params, **self.params})
        Y = self.get_ymatrix(freq, resolved)
        n = Y.shape[0]
        rows: List[int] = []
        cols: List[int] = []
        data: List[complex] = []
        for i in range(n):
            for j in range(n):
                rows.append(net_indices[i])
                cols.append(net_indices[j])
                data.append(Y[i, j])
        return rows, cols, data