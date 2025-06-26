#!/usr/bin/env python
"""
A simple MCP server implementation for math functions.
This script creates a simple MCP server that exposes math calculation functions.

To use this as an MCP server, run it with:
    python server.py
"""

from mcp.server.fastmcp import FastMCP

# Import math tools
from tools.addition import add
from tools.subtraction import subtract
from tools.multiplication import multiply
from tools.division import divide
from tools.square_root import square_root
from tools.power import power
from tools.logarithm import log
from tools.modulo import modulo, modular_inverse

# Initialize the FastMCP server
mcp = FastMCP("math_server")

# Register math tools
mcp.tool()(add)
mcp.tool()(subtract)
mcp.tool()(multiply)
mcp.tool()(divide)
mcp.tool()(square_root)
mcp.tool()(power)
mcp.tool()(log)
mcp.tool()(modulo)
mcp.tool()(modular_inverse)

if __name__ == "__main__":
    # For development, you can run with stdio or sse transport
    import sys
    
    transport = 'stdio'
    if len(sys.argv) > 1 and sys.argv[1] == '--sse':
        transport = 'sse'
        host = 'localhost'
        port = 5005
        mcp.run(transport=transport, host=host, port=port)
    else:
        mcp.run(transport=transport)