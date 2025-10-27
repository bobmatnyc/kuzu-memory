#!/usr/bin/env python
"""Test MCP server functionality."""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_mcp_tools():
    """Test MCP tool definitions."""
    from kuzu_memory.mcp.server import KuzuMemoryMCPServer

    try:
        # Create server instance
        server = KuzuMemoryMCPServer(project_root=Path.cwd())
        print("✓ MCP server initialized")

        # Get tool list through the handler
        tools = await server.server.list_tools()
        print(f"✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:60]}...")

        # Test a simple tool call
        result = await server._stats(detailed=False)
        print(f"✓ Stats call successful: {result[:100]}...")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_mcp_tools())
    sys.exit(0 if success else 1)
