# components/factory.py
from typing import Type, Dict
from core.behavior.component import Component
from components.resistor import ResistorComponent
from components.capacitor import CapacitorComponent
from components.inductor import InductorComponent
from components.transmission_line import TransmissionLineComponent
from components.touchstone import TouchstoneComponent
from core.exceptions import RFSimError
from components.phase_shifter import PhaseShifterComponent
from components.circulator import CirculatorComponent
from components.attenuator import AttenuatorComponent
from components.hybrid_coupler import HybridCouplerComponent
from components.directional_coupler import DirectionalCouplerComponent
from components.wilkinson import WilkinsonDividerComponent
from components.transformer import TransformerComponent

# Use the type_name attributes from each class.
_component_registry: Dict[str, Type[Component]] = {
    ResistorComponent.type_name: ResistorComponent,
    CapacitorComponent.type_name: CapacitorComponent,
    InductorComponent.type_name: InductorComponent,
    TransmissionLineComponent.type_name: TransmissionLineComponent,
    TouchstoneComponent.type_name: TouchstoneComponent,
    PhaseShifterComponent.type_name: PhaseShifterComponent,
    CirculatorComponent.type_name: CirculatorComponent,
    AttenuatorComponent.type_name: AttenuatorComponent,
    HybridCouplerComponent.type_name: HybridCouplerComponent,
    DirectionalCouplerComponent.type_name: DirectionalCouplerComponent,
    WilkinsonDividerComponent.type_name: WilkinsonDividerComponent,
    TransformerComponent.type_name: TransformerComponent,

    }

def get_component_class(type_name: str) -> Type[Component]:
    if not isinstance(type_name, str):
        raise RFSimError("Component type name must be a string.")
    comp_class = _component_registry.get(type_name.lower())
    if comp_class is None:
        raise RFSimError(f"Unknown component type: {type_name}")
    return comp_class

def register_component(type_name: str, comp_class: Type[Component]) -> None:
    if not isinstance(type_name, str):
        raise RFSimError("Component type name must be a string.")
    if not issubclass(comp_class, Component):
        raise RFSimError("Registered component must be a subclass of Component.")
    _component_registry[type_name.lower()] = comp_class
