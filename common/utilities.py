
def convert_to_float(n):
    """
    This function attempts to convert the input to a float.
    Returns: None or float
    """
    try:
        return float(n)
    except (TypeError, ValueError):
        return None

def round_float(value: float, decimals: int = 1):
    """
    This method returns a rounded float, decimals defines the precision
    Returns: None or float
    """
    if value is not None:
        return round(value, decimals)
    else:
        return None
    
def round_to_pt5(num):
    """Round a number to the closest half integer."""

    if num is None:
        return num

    return round(num * 2) / 2
