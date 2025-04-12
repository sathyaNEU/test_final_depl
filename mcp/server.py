from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Demo Server")

# Define a tool for addition
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    print(f"Adding {a} and {b}")
    return a + b


# Run the server with a custom port
if __name__ == "__main__":
    mcp.run(transport='sse')  # Specify your desired port here
