# core/topology/port.py
import uuid
from ports.impedance import PortImpedance, FixedPortImpedance
from typing import Union

class Port:
    def __init__(self, name: str, index: int, connected_node=None,
                 impedance: Union[int, float, complex, PortImpedance] = 50):
        self.name = name
        self.index = index
        self.connected_node = connected_node  # Instance of Node.
        # Generate a unique port identifier.
        self.id = f"{name}_{index}_{uuid.uuid4().hex[:4]}"
        # Wrap scalars automatically into a FixedPortImpedance.
        if isinstance(impedance, (int, float, complex)):
            self.impedance = FixedPortImpedance(impedance)
        else:
            self.impedance = impedance

    def __repr__(self):
        cn = self.connected_node.name if self.connected_node else None
        return (f"<Port {self.name} (id={self.id}, index={self.index}, node={cn}, " 
                f"impedance={self.impedance.get_display_value()})>")
