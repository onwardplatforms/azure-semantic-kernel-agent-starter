"""
Power/exponentiation tool implementation for the Math MCP server.
"""

async def power(base: float, exponent: float) -> float:
    """
    Raise a number to the power of another.
    
    Args:
        base: The base number
        exponent: The exponent to raise the base to
        
    Returns:
        The result of the exponentiation
    """
    return float(base) ** float(exponent)