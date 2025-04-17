# core/ports/impedance_factory.py
"""
Factory to create PortImpedance instances from config dictionaries.
Supports fixed and frequency-dependent models.
"""
from typing import Union, Callable, Dict, Any
import sympy as sp
import numpy as np

from core.safe_math import parse_expr, make_numeric_fn
from core.ports.impedance import FixedPortImpedance, PortImpedance


def parse_complex(imp_str: str) -> complex:
    """
    Parse a simple complex string like '50+10j' or '75j'.
    """
    imp_str = imp_str.replace(" ", "")
    try:
        return complex(imp_str)
    except Exception as exc:
        raise ValueError(f"Cannot parse impedance '{imp_str}': {exc}") from exc


def create_impedance_model(impedance_spec: Union[str, int, float, complex]) -> PortImpedance:
    """
    Create a FixedPortImpedance from a numeric or string spec.
    """
    if isinstance(impedance_spec, (int, float, complex)):
        return FixedPortImpedance(impedance_spec)
    elif isinstance(impedance_spec, str):
        return FixedPortImpedance(parse_complex(impedance_spec))
    else:
        raise TypeError(f"Unsupported impedance spec type: {type(impedance_spec)}")


class FrequencyDependentPortImpedance(PortImpedance):
    """Impedance defined by a user-provided function of frequency."""
    def __init__(self, func: Callable[[float, Dict[str, Any]], complex]) -> None:
        self.func = func

    def get_impedance(self, freq: float, params: dict = None) -> complex:
        return self.func(freq, params or {})

    def get_display_value(self) -> str:
        return "Frequency-dependent impedance"


def create_impedance_model_from_config(config: Dict[str, Any]) -> PortImpedance:
    """
    Factory to create an impedance model from a config dict with keys:
      - type: 'fixed' or 'freq_dep'
      - value: for fixed
      - function: string to eval for freq_dep
    """
    imp_type = config.get("type", "fixed").lower()
    if imp_type == "fixed":
        value = config.get("value", "50")
        return create_impedance_model(value)

    if imp_type == "freq_dep":
        func_src = config.get("function")
        if not func_src:
            raise ValueError("Frequency-dependent impedance requires a 'function' key.")

        # 1) Parse safely
        try:
            expr = parse_expr(func_src)
        except Exception as exc:
            raise ValueError(f"Bad impedance function syntax '{func_src}': {exc}") from exc

        # 2) Build symbol map: freq plus any extra parameters
        symbols: Dict[str, sp.Symbol] = {"freq": sp.symbols("freq")}
        for sym in expr.free_symbols:
            name = str(sym)
            if name != "freq":
                symbols[name] = sp.symbols(name)

        # 3) Compile NumPy lambda (thread-safe, pickle-safe)
        num_fn = make_numeric_fn(expr, symbols)
        names_no_freq = [n for n in symbols if n != "freq"]

        def _func(freq: float, params: Dict[str, Any]) -> complex:
            try:
                args = [freq] + [params[k] for k in names_no_freq]
            except KeyError as missing:
                raise ValueError(
                    f"Parameter '{missing.args[0]}' needed by impedance function is undefined"
                )
            return complex(num_fn(*args))

        return FrequencyDependentPortImpedance(_func)

    raise ValueError(f"Unsupported impedance model type: '{imp_type}'")
