"""
Addition tool implementation for the Math MCP server.
"""

async def add(a: float, b: float) -> float:
    """
    Add two numbers together.
    
    Args:
        a: The first number to add
        b: The second number to add
        
    Returns:
        The sum of the two numbers
    """
    return float(a) + float(b)