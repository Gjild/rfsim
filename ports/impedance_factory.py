# rfsim/ports/impedance_factory.py
import re
from ports.impedance import FixedPortImpedance, PortImpedance
from typing import Union

def parse_complex(imp_str: str) -> complex:
    imp_str = imp_str.replace(" ", "")
    try:
        return complex(imp_str)
    except Exception as e:
        raise ValueError(f"Cannot parse impedance '{imp_str}': {e}")

def create_impedance_model(impedance_spec: Union[str, float, int, complex]) -> PortImpedance:
    # For fixed impedance, assume the spec is a simple number.
    if isinstance(impedance_spec, (int, float, complex)):
        return FixedPortImpedance(impedance_spec)
    elif isinstance(impedance_spec, str):
        value = parse_complex(impedance_spec)
        return FixedPortImpedance(value)
    else:
        raise TypeError(f"Unsupported impedance specification type: {type(impedance_spec)}")

def create_impedance_model_from_config(config: dict) -> PortImpedance:
    impedance_type = config.get("type", "fixed").lower()
    if impedance_type == "fixed":
        value = config.get("value", "50")
        return create_impedance_model(value)
    elif impedance_type == "freq_dep":
        func_expr = config.get("function")
        if func_expr is None:
            raise ValueError("Frequency-dependent impedance requires a 'function' key.")
        # Use a safe parser or restricted namespace for evaluating expressions.
        safe_namespace = {"__builtins__": {}}
        try:
            func = eval(func_expr, safe_namespace)  # Replace with a safe evaluator in production.
        except Exception as e:
            raise ValueError(f"Error evaluating function expression '{func_expr}': {e}")
        from ports.impedance import PortImpedance
        class FrequencyDependentPortImpedance(PortImpedance):
            def __init__(self, func):
                self.func = func
            def get_impedance(self, freq: float, params: dict = None) -> complex:
                return self.func(freq, params or {})
            def get_display_value(self) -> str:
                return "Freq-dependent impedance"
        return FrequencyDependentPortImpedance(func)
    else:
        raise ValueError(f"Unknown impedance type: {impedance_type}")
