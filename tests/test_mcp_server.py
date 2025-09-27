#!/usr/bin/env python3
"""
Test script for KuzuMemory MCP Server.
"""

import json
import sys
from pathlib import Path

# Add src to path for development testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kuzu_memory.mcp import create_mcp_server


def test_mcp_server():
    """Test MCP server functionality."""
    print("🧪 Testing KuzuMemory MCP Server\n")

    # Create server instance
    server = create_mcp_server()
    print(f"✅ Created MCP server for project: {server.project_root}\n")

    # Test available tools
    tools = server.get_tools()
    print(f"📋 Available tools: {len(tools)}")
    for tool in tools:
        print(f"  • {tool['name']}: {tool['description']}")
    print()

    # Test some operations
    print("🔬 Testing operations:\n")

    # Test enhance
    result = server.enhance("How do I build an API?", format="plain", limit=3)
    print(f"1. Enhance test: {'✅ Success' if result.get('success') else '❌ Failed'}")
    if not result.get("success"):
        print(f"   Error: {result.get('error', 'Unknown')}")

    # Test learn (async, should always succeed)
    result = server.learn("Test learning content", source="test")
    print(f"2. Learn test: {'✅ Success' if result.get('success') else '❌ Failed'}")

    # Test recall
    result = server.recall("test", limit=5)
    print(f"3. Recall test: {'✅ Success' if result.get('success') else '❌ Failed'}")

    # Test stats
    result = server.stats()
    print(f"4. Stats test: {'✅ Success' if result.get('success') else '❌ Failed'}")

    # Test project info
    result = server.project()
    print(f"5. Project test: {'✅ Success' if result.get('success') else '❌ Failed'}")

    print("\n✨ MCP server test complete!")


if __name__ == "__main__":
    try:
        test_mcp_server()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
