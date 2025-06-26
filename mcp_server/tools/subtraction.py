"""
Subtraction tool implementation for the Math MCP server.
"""

async def subtract(a: float, b: float) -> float:
    """
    Subtract the second number from the first.
    
    Args:
        a: The first number
        b: The number to subtract
        
    Returns:
        The difference between the two numbers
    """
    return float(a) - float(b)