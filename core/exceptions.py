# core/exceptions.py
class RFSimError(Exception):
    """Base exception for all RFSim errors."""
    pass

class ParameterError(RFSimError):
    """Exception raised for errors during parameter resolution."""
    pass

class TopologyError(RFSimError):
    """Exception raised for circuit topology validation errors."""
    pass

class SubcircuitMappingError(RFSimError):
    """Exception raised for subcircuit port mapping errors."""
    pass
