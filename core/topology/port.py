# core/topology/port.py
import uuid
from typing import Union
from ports.impedance import PortImpedance, FixedPortImpedance

class Port:
    def __init__(self, name: str, index: int, connected_node=None,
                 impedance: Union[int, float, complex, PortImpedance] = 50):
        self.name = name
        self.index = index
        self.connected_node = connected_node
        self.id = f"{name}_{index}_{uuid.uuid4().hex[:4]}"
        self.impedance = FixedPortImpedance(impedance) if isinstance(impedance, (int, float, complex)) else impedance

    def __repr__(self):
        node_name = self.connected_node.name if self.connected_node else None
        return (f"<Port {self.name} (id={self.id}, index={self.index}, "
                f"node={node_name}, impedance={self.impedance.get_display_value()})>")
