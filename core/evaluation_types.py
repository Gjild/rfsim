# core/evaluation_types.py
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import numpy as np

@dataclass
class EvaluationPoint:
    """
    Represents a single evaluation point in a sweep.
    
    Attributes:
        frequency: Frequency at which the evaluation is performed.
        parameters: A dictionary of parameter values used during evaluation.
        s_matrix: The resulting scattering matrix (or None if evaluation failed).
        error: Optional error message if the evaluation encountered an error.
    """
    frequency: float
    parameters: Dict[str, Any]
    s_matrix: Optional[np.ndarray] = None
    error: Optional[str] = None
