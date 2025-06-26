"""
Division tool implementation for the Math MCP server.
"""

async def divide(a: float, b: float) -> float:
    """
    Divide the first number by the second.
    
    Args:
        a: The number to be divided
        b: The number to divide by
        
    Returns:
        The quotient of the division
        
    Raises:
        ValueError: If dividing by zero
    """
    if float(b) == 0:
        raise ValueError("Cannot divide by zero.")
    
    return float(a) / float(b)