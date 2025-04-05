# symbolic/units.py
import pint

ureg = pint.UnitRegistry()

def parse_quantity(expr: str) -> float:
    """
    Parse a string expression as a physical quantity and return its magnitude in base units.
    
    :param expr: The expression string (e.g., "1e-9", "1n", "1000 * ohm").
    :return: The magnitude of the quantity as a float.
    :raises ValueError: If the expression cannot be parsed as a quantity.
    """
    try:
        quantity = ureg.Quantity(expr)
        return quantity.to_base_units().magnitude
    except Exception as e:
        raise ValueError(f"Could not parse '{expr}' as a quantity: {e}")

def is_number(s: str) -> bool:
    """
    Check whether a string represents a numeric value.
    
    :param s: The string to test.
    :return: True if s can be converted to float, otherwise False.
    """
    try:
        float(s)
        return True
    except ValueError:
        return False
