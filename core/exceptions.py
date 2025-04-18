# core/exceptions.py
"""
Core exception definitions for RFSim v2.
"""

class RFSimError(Exception):
    """Base exception for RFSim errors."""
    pass

class ParameterError(RFSimError):
    """Raised when parameter resolution or evaluation fails."""
    pass

class TopologyError(RFSimError):
    """Raised when there is an issue with circuit topology."""
    pass

class ComponentEvaluationError(RFSimError):
    """Raised when a component fails during Y/Z stamping or evaluation."""
    pass

class SubcircuitMappingError(RFSimError):
    """Raised when a subcircuit interface mapping is invalid."""
    pass
