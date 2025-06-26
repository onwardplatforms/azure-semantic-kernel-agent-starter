"""
Multiplication tool implementation for the Math MCP server.
"""

async def multiply(a: float, b: float) -> float:
    """
    Multiply two numbers together.
    
    Args:
        a: The first number to multiply
        b: The second number to multiply
        
    Returns:
        The product of the two numbers
    """
    return float(a) * float(b)