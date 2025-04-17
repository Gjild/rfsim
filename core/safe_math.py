# core/safe_math.py  – NEW
import math, numpy as np, sympy as sp
from typing import Mapping, Callable

_ALLOWED_FUNCS = {
    # scalars
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "asin": sp.asin,
    "acos": sp.acos, "atan": sp.atan, "exp": sp.exp, "log": sp.log,
    "sqrt": sp.sqrt, "abs": sp.Abs,
    # constants
    "pi":  sp.pi,  "e": sp.E,   "I": sp.I,
}

def parse_expr(src: str) -> sp.Expr:
    """Parse *pure* maths, nothing else."""
    try:
        return sp.sympify(src, locals=_ALLOWED_FUNCS, convert_xor=True)
    except (sp.SympifyError, SyntaxError) as exc:
        raise ValueError(f"Bad expression '{src}': {exc}") from exc


def make_numeric_fn(expr: sp.Expr, symbols: Mapping[str, sp.Symbol]) -> Callable[..., float|complex]:
    """Return fast NumPy lambda over given symbols (freq, params…)."""
    # Use lambdify with a single private module dict ➔ no globals, no `eval`
    lamb = sp.lambdify(tuple(symbols.values()), expr, modules=[{"sqrt": np.sqrt,
                                                                "abs":  np.abs,
                                                                **{n: getattr(np, n) for n in (
                                                                    "sin","cos","tan","arcsin","arccos",
                                                                    "arctan","log","exp")}}, "math"])
    return lamb
