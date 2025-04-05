# symbolic/expressions.py
import sympy
import logging
from typing import Union, Tuple, Any
from core.exceptions import ParameterError

def compile_expr(expr: Union[str, sympy.Expr]) -> Tuple[sympy.Expr, Any]:
    """
    Compile a symbolic expression into a sympy expression and a numerical function.
    
    :param expr: The expression as a string or sympy.Expr.
    :return: A tuple containing the sympy expression and a lambdified function.
    :raises ParameterError: If the expression cannot be compiled.
    """
    try:
        sym_expr = sympy.sympify(expr)
        symbols = tuple(sorted(sym_expr.free_symbols, key=lambda s: str(s)))
        func = sympy.lambdify(symbols, sym_expr, "numpy")
        return sym_expr, func
    except Exception as e:
        logging.error(f"Could not compile expression '{expr}': {e}")
        raise ParameterError(f"Could not compile expression '{expr}': {e}")
