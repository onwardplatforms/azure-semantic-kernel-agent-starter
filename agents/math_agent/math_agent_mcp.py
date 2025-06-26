#!/usr/bin/env python3

import asyncio
import json
import time
import uuid
import os
import logging
import subprocess
from flask import Flask, request, jsonify, Response, stream_with_context
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

AGENT_ID = "math-agent"

# MCP client session
mcp_session = None

async def init_mcp_client():
    """Initialize the MCP client connection to the math server."""
    global mcp_session
    
    # Start the MCP math server as a subprocess
    server_params = StdioServerParameters(
        command="python",
        args=["../../mcp_server/server.py"],
        env=os.environ.copy()
    )
    
    try:
        mcp_session = await stdio_client(server_params)
        await mcp_session.__aenter__()
        
        # Initialize the session
        await mcp_session.initialize()
        
        print("MCP Math Server connected successfully")
        return True
    except Exception as e:
        print(f"Failed to connect to MCP Math Server: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "agent_id": AGENT_ID,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mcp_connected": mcp_session is not None
    }), 200

@app.route('/api/message', methods=['POST'])
def receive_message():
    """Endpoint to receive messages from the runtime or external calls."""
    
    message = request.json
    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Check if streaming is requested
    stream = message.get("stream", False)

    if stream:
        return Response(
            stream_with_context(process_message_stream(message)),
            content_type='text/event-stream'
        )
    else:
        # Process synchronously
        try:
            response_content = process_message(message)
            response = {
                "messageId": str(uuid.uuid4()),
                "conversationId": message.get("conversationId", ""),
                "senderId": AGENT_ID,
                "recipientId": message.get("senderId", ""),
                "content": response_content,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": "Text"
            }
            return jsonify(response), 200
        except Exception as e:
            print(f"Error processing message: {e}")
            return jsonify({"error": str(e)}), 500

def stream_with_context_wrapper(generator):
    """Helper that yields SSE lines and ends with [DONE]."""
    try:
        for chunk in generator:
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        print(f"Error in streaming: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

def process_message_stream(message):
    """Process a message from the client and stream the response."""
    content = message.get("content", "")
    conversation_id = message.get("conversationId", "")
    sender_id = message.get("senderId", "")
    message_id = str(uuid.uuid4())

    # Yield an initial chunk to indicate the calculation has started
    yield {
        "messageId": message_id,
        "conversationId": conversation_id,
        "senderId": AGENT_ID,
        "recipientId": sender_id,
        "content": "",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": "Text",
        "chunk": "ƒ(x) calling math-agent...",
        "complete": False
    }
    
    try:
        # Process the math query using MCP
        response = process_message(message)
        
        # Stream the response word by word for better UX
        words = response.split()
        accumulated_response = ""
        
        for word in words:
            accumulated_response += word + " "
            
            yield {
                "messageId": message_id,
                "conversationId": conversation_id,
                "senderId": AGENT_ID,
                "recipientId": sender_id,
                "content": "",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": "Text",
                "chunk": word + " ",
                "complete": False
            }
            
            # Small delay for streaming effect
            time.sleep(0.05)
            
        # Final chunk with the complete response
        yield {
            "messageId": message_id,
            "conversationId": conversation_id,
            "senderId": AGENT_ID,
            "recipientId": sender_id,
            "content": accumulated_response.strip(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "type": "Text",
            "chunk": None,
            "complete": True,
            "response": accumulated_response.strip()
        }
    except Exception as e:
        print(f"Error in streaming process: {e}")
        import traceback
        traceback.print_exc()
        
        # Yield an error response
        yield {
            "messageId": message_id,
            "conversationId": conversation_id,
            "senderId": AGENT_ID,
            "recipientId": sender_id,
            "content": f"Error: {str(e)}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "type": "Text",
            "chunk": f"Error: {str(e)}",
            "complete": True
        }

def process_message(message):
    """Process a math query using the MCP server."""
    content = message.get("content", "").lower()
    
    if not mcp_session:
        return "Math Agent Error: MCP server not connected. Please check the math server status."
    
    try:
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Parse the math query and determine which operations to perform
        result = loop.run_until_complete(solve_math_problem(content))
        
        return result
    except Exception as e:
        print(f"Error processing math query: {e}")
        import traceback
        traceback.print_exc()
        return f"Math Agent Error: {str(e)}"

async def solve_math_problem(query):
    """Solve a math problem by breaking it down and using MCP tools."""
    query = query.lower().strip()
    
    # Simple parsing for basic operations
    if "add" in query or "plus" in query or " + " in query:
        return await handle_addition(query)
    elif "subtract" in query or "minus" in query or " - " in query:
        return await handle_subtraction(query)
    elif "multiply" in query or "times" in query or " * " in query or " × " in query:
        return await handle_multiplication(query)
    elif "divide" in query or "divided by" in query or " / " in query or " ÷ " in query:
        return await handle_division(query)
    elif "square root" in query or "sqrt" in query:
        return await handle_square_root(query)
    elif "power" in query or "raised to" in query or " ^ " in query or "**" in query:
        return await handle_power(query)
    elif "log" in query or "logarithm" in query:
        return await handle_logarithm(query)
    elif "modulo" in query or "mod " in query or " % " in query:
        return await handle_modulo(query)
    else:
        # Try to evaluate as a complex expression
        return await handle_complex_expression(query)

async def handle_addition(query):
    """Handle addition operations."""
    # Extract numbers from the query
    numbers = extract_numbers(query)
    if len(numbers) >= 2:
        result = await mcp_session.call_tool("add", {"a": numbers[0], "b": numbers[1]})
        return f"The result of {numbers[0]} + {numbers[1]} = **{result.content[0].text}**"
    return "Please provide two numbers to add."

async def handle_subtraction(query):
    """Handle subtraction operations."""
    numbers = extract_numbers(query)
    if len(numbers) >= 2:
        result = await mcp_session.call_tool("subtract", {"a": numbers[0], "b": numbers[1]})
        return f"The result of {numbers[0]} - {numbers[1]} = **{result.content[0].text}**"
    return "Please provide two numbers to subtract."

async def handle_multiplication(query):
    """Handle multiplication operations."""
    numbers = extract_numbers(query)
    if len(numbers) >= 2:
        result = await mcp_session.call_tool("multiply", {"a": numbers[0], "b": numbers[1]})
        return f"The result of {numbers[0]} × {numbers[1]} = **{result.content[0].text}**"
    return "Please provide two numbers to multiply."

async def handle_division(query):
    """Handle division operations."""
    numbers = extract_numbers(query)
    if len(numbers) >= 2:
        try:
            result = await mcp_session.call_tool("divide", {"a": numbers[0], "b": numbers[1]})
            return f"The result of {numbers[0]} ÷ {numbers[1]} = **{result.content[0].text}**"
        except Exception as e:
            if "divide by zero" in str(e).lower():
                return "Error: Cannot divide by zero!"
            return f"Division error: {str(e)}"
    return "Please provide two numbers to divide."

async def handle_square_root(query):
    """Handle square root operations."""
    numbers = extract_numbers(query)
    if len(numbers) >= 1:
        try:
            result = await mcp_session.call_tool("square_root", {"x": numbers[0]})
            return f"The square root of {numbers[0]} = **{result.content[0].text}**"
        except Exception as e:
            if "negative" in str(e).lower():
                return "Error: Cannot calculate square root of a negative number!"
            return f"Square root error: {str(e)}"
    return "Please provide a number to find the square root of."

async def handle_power(query):
    """Handle power/exponentiation operations."""
    numbers = extract_numbers(query)
    if len(numbers) >= 2:
        result = await mcp_session.call_tool("power", {"base": numbers[0], "exponent": numbers[1]})
        return f"The result of {numbers[0]} raised to the power of {numbers[1]} = **{result.content[0].text}**"
    return "Please provide a base and exponent for the power operation."

async def handle_logarithm(query):
    """Handle logarithm operations."""
    numbers = extract_numbers(query)
    if len(numbers) >= 1:
        try:
            if len(numbers) >= 2:
                result = await mcp_session.call_tool("log", {"x": numbers[0], "base": numbers[1]})
                return f"The logarithm of {numbers[0]} with base {numbers[1]} = **{result.content[0].text}**"
            else:
                result = await mcp_session.call_tool("log", {"x": numbers[0]})
                return f"The natural logarithm of {numbers[0]} = **{result.content[0].text}**"
        except Exception as e:
            return f"Logarithm error: {str(e)}"
    return "Please provide a number for the logarithm operation."

async def handle_modulo(query):
    """Handle modulo operations."""
    numbers = extract_numbers(query)
    if len(numbers) >= 2:
        try:
            result = await mcp_session.call_tool("modulo", {"a": int(numbers[0]), "b": int(numbers[1])})
            return f"The result of {int(numbers[0])} mod {int(numbers[1])} = **{result.content[0].text}**"
        except Exception as e:
            if "modulo by zero" in str(e).lower():
                return "Error: Cannot modulo by zero!"
            return f"Modulo error: {str(e)}"
    return "Please provide two integers for the modulo operation."

async def handle_complex_expression(query):
    """Handle more complex mathematical expressions."""
    # For now, provide guidance on supported operations
    return """I can help you with the following math operations:
    
**Basic Operations:**
- Addition: "add 5 and 3" or "5 + 3"
- Subtraction: "subtract 3 from 5" or "5 - 3"  
- Multiplication: "multiply 5 by 3" or "5 × 3"
- Division: "divide 15 by 3" or "15 ÷ 3"

**Advanced Operations:**
- Square root: "square root of 25" or "sqrt(25)"
- Power: "2 raised to the power of 3" or "2^3"
- Logarithm: "log of 100" or "log 100 base 10"
- Modulo: "15 mod 4" or "15 % 4"

Please rephrase your question using one of these formats!"""

def extract_numbers(text):
    """Extract numbers from text."""
    import re
    # Find all numbers (including decimals) in the text
    numbers = re.findall(r'-?\d+\.?\d*', text)
    return [float(num) for num in numbers if num]

async def startup():
    """Initialize the MCP connection on startup."""
    success = await init_mcp_client()
    if not success:
        print("Warning: Math Agent starting without MCP connection")

if __name__ == "__main__":
    print("Starting Math Agent (MCP-powered) with ID:", AGENT_ID)
    
    # Initialize MCP connection
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(startup())
    
    # Disable Flask access logs
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app.run(host="0.0.0.0", port=5004)