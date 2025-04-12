# rfsim/ports/impedance_factory.py
import re
from typing import Union, Callable, Optional, Dict, Any
from ports.impedance import FixedPortImpedance, PortImpedance

def parse_complex(imp_str: str) -> complex:
    """Parse a string into a complex number after stripping spaces."""
    imp_str = imp_str.replace(" ", "")
    try:
        return complex(imp_str)
    except Exception as exc:
        raise ValueError(f"Cannot parse impedance '{imp_str}': {exc}") from exc

def create_impedance_model(impedance_spec: Union[str, int, float, complex]) -> PortImpedance:
    """
    Create a fixed impedance model. For numeric types and their string representations,
    this returns a FixedPortImpedance instance.
    """
    if isinstance(impedance_spec, (int, float, complex)):
        return FixedPortImpedance(impedance_spec)
    elif isinstance(impedance_spec, str):
        return FixedPortImpedance(parse_complex(impedance_spec))
    
    raise TypeError(f"Unsupported impedance specification type: {type(impedance_spec)}")

class FrequencyDependentPortImpedance(PortImpedance):
    """
    A frequency-dependent impedance model defined by a user-provided callable.
    """
    def __init__(self, func: Callable[[float, Optional[Dict[str, Any]]], complex]) -> None:
        self.func = func

    def get_impedance(self, freq: float, params: Optional[Dict[str, Any]] = None) -> complex:
        return self.func(freq, params or {})

    def get_display_value(self) -> str:
        return "Freq-dependent impedance"

def create_impedance_model_from_config(config: dict) -> PortImpedance:
    """
    Factory to create an impedance model from a configuration dictionary.
    
    Supports two types:
        - "fixed": A fixed impedance value, defaulting to "50" if not provided.
        - "freq_dep": A frequency-dependent impedance where a 'function' key must
          supply a valid expression evaluating to a callable.
    """
    impedance_type = config.get("type", "fixed").lower()
    
    if impedance_type == "fixed":
        value = config.get("value", "50")
        return create_impedance_model(value)
    
    if impedance_type == "freq_dep":
        func_expr = config.get("function")
        if not func_expr:
            raise ValueError("Frequency-dependent impedance requires a 'function' key.")
        
        # Use a restricted namespace for evaluation (replace with a safer mechanism if needed)
        safe_namespace = {"__builtins__": {}}
        try:
            func = eval(func_expr, safe_namespace)
        except Exception as exc:
            raise ValueError(f"Error evaluating function expression '{func_expr}': {exc}") from exc

        if not callable(func):
            raise ValueError(f"Evaluated expression '{func_expr}' is not callable.")

        return FrequencyDependentPortImpedance(func)
    
    raise ValueError(f"Unknown impedance type: {impedance_type}")
