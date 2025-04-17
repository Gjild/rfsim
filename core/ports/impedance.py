# core/ports/impedance.py
"""
Port impedance models for RFSim v2.
"""
from abc import ABC, abstractmethod

class PortImpedance(ABC):
    """Abstract base class representing a port impedance model."""
    @abstractmethod
    def get_impedance(self, freq: float, params: dict = None) -> complex:
        """Return the impedance at the given frequency."""
        pass

    @abstractmethod
    def get_display_value(self) -> str:
        """Return a human-readable representation of the impedance."""
        pass

class FixedPortImpedance(PortImpedance):
    """Frequency-independent, fixed impedance."""
    def __init__(self, value: complex):
        self.value = value

    def get_impedance(self, freq: float, params: dict = None) -> complex:
        return self.value

    def get_display_value(self) -> str:
        return str(self.value)
