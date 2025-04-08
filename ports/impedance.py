# rfsim/ports/impedance.py
from abc import ABC, abstractmethod
from typing import Optional, Dict

class PortImpedance(ABC):
    @abstractmethod
    def get_impedance(self, freq: float, params: Optional[Dict] = None) -> complex:
        """
        Return the simulation impedance (which may be frequency dependent).
        """
        pass

    @abstractmethod
    def get_display_value(self) -> str:
        """
        Return a frequency-independent string for display purposes.
        """
        pass

    def clear_cache(self) -> None:
        """
        Optional hook to clear any internal caches.
        Override this if caching is implemented.
        """
        pass

class FixedPortImpedance(PortImpedance):
    def __init__(self, value: complex):
        self.value = value

    def get_impedance(self, freq: float, params: Optional[Dict] = None) -> complex:
        return self.value

    def get_display_value(self) -> str:
        return str(self.value)
