# components/factory.py
from typing import Type, Dict
from core.behavior.component import Component
from components.resistor import ResistorComponent
from components.capacitor import CapacitorComponent
from components.inductor import InductorComponent
from components.transmission_line import TransmissionLineComponent
from core.exceptions import RFSimError

# Registry mapping component type names to their classes.
_component_registry: Dict[str, Type[Component]] = {
    "resistor": ResistorComponent,
    "capacitor": CapacitorComponent,
    "inductor": InductorComponent,
    "transmission_line": TransmissionLineComponent
}

def get_component_class(type_name: str) -> Type[Component]:
    """
    Retrieve the component class corresponding to the given type name.
    
    Args:
        type_name: The type name of the component.
    
    Returns:
        The component class.
    
    Raises:
        RFSimError: If type_name is not a string or the component is not registered.
    """
    if not isinstance(type_name, str):
        raise RFSimError("Component type name must be a string.")
    comp_class = _component_registry.get(type_name.lower())
    if comp_class is None:
        raise RFSimError(f"Unknown component type: {type_name}")
    return comp_class

def register_component(type_name: str, comp_class: Type[Component]) -> None:
    """
    Register a new component class under the specified type name.
    
    Args:
        type_name: The type name for registration.
        comp_class: The component class (subclass of Component).
    
    Raises:
        RFSimError: If the inputs are invalid.
    """
    if not isinstance(type_name, str):
        raise RFSimError("Component type name must be a string.")
    if not issubclass(comp_class, Component):
        raise RFSimError("Registered component must be a subclass of Component.")
    _component_registry[type_name.lower()] = comp_class