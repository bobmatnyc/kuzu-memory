#!/usr/bin/env python
"""Simple test to verify MCP server can initialize."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_mcp_init():
    """Test basic MCP server initialization."""
    try:
        from kuzu_memory.mcp.server import KuzuMemoryMCPServer

        # Create server instance
        server = KuzuMemoryMCPServer(project_root=Path.cwd())
        print("✓ MCP server initialized successfully")
        print(f"✓ Project root: {server.project_root}")

        # Test a simple CLI command wrapper
        result = await server._run_command(["--version"])
        print(f"✓ CLI wrapper working: {result[:50]}...")

        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  Run: pip install mcp")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_mcp_init())
    sys.exit(0 if success else 1)
