"""
Logarithm tool implementation for the Math MCP server.
"""

import math

async def log(x: float, base: float = math.e) -> float:
    """
    Calculate the logarithm of a number with an optional base.
    
    Args:
        x: The number to calculate the logarithm of
        base: The base of the logarithm (defaults to e for natural log)
        
    Returns:
        The logarithm of the input
        
    Raises:
        ValueError: If x is non-positive or base is invalid
    """
    x = float(x)
    base = float(base)
    
    if x <= 0:
        raise ValueError("Cannot calculate logarithm of a non-positive number.")
    if base <= 0 or base == 1:
        raise ValueError("Logarithm base must be positive and not equal to 1.")
    
    if base == math.e:
        return math.log(x)  # Natural logarithm
    else:
        return math.log(x, base)  # Logarithm with custom base