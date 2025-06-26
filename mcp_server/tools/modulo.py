"""
Modulo and modular arithmetic tools for the Math MCP server.
"""

async def modulo(a: int, b: int) -> int:
    """
    Find the remainder of division of one number by another.
    
    Args:
        a: The number to be divided
        b: The divisor
        
    Returns:
        The remainder of the division
        
    Raises:
        ValueError: If dividing by zero
    """
    if int(b) == 0:
        raise ValueError("Cannot modulo by zero.")
    
    return int(a) % int(b)

async def modular_inverse(a: int, m: int) -> int:
    """
    Find the modular inverse of a number modulo another number.
    
    Args:
        a: The number to find the modular inverse of
        m: The modulus
        
    Returns:
        The modular inverse of a modulo m
        
    Raises:
        ValueError: If no modular inverse exists
    """
    a = int(a)
    m = int(m)
    
    # Ensure a is within modulo range
    a = a % m
    
    # Brute force search for modular inverse
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    
    raise ValueError(f"No modular inverse exists for {a} mod {m}.")