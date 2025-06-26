"""
Square root tool implementation for the Math MCP server.
"""

import math

async def square_root(x: float) -> float:
    """
    Calculate the square root of a number.
    
    Args:
        x: The number to find the square root of
        
    Returns:
        The square root of the number
        
    Raises:
        ValueError: If the number is negative
    """
    x = float(x)
    if x < 0:
        raise ValueError("Cannot calculate square root of a negative number.")
    
    return math.sqrt(x)