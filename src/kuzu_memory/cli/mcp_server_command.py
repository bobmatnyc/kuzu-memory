"""
MCP Server command - starts the MCP stdio server.

This module provides the CLI command to start the KuzuMemory MCP server
via stdio for integration with Claude Desktop and other MCP-compatible tools.
"""

import asyncio
import logging
import sys

import click


@click.command(name="mcp")
def mcp_server() -> None:
    """
    Start the MCP server (stdio mode).

    Launches the KuzuMemory MCP server for integration with Claude Desktop,
    Claude Code, Cursor, and other MCP-compatible AI tools.

    The server communicates via stdio (standard input/output) using the
    Model Context Protocol (MCP) specification.

    \b
    🚀 USAGE:
      This command is typically configured in MCP client configurations:

      Claude Desktop (claude_desktop_config.json):
      {
        "mcpServers": {
          "kuzu-memory": {
            "command": "kuzu-memory",
            "args": ["mcp"]
          }
        }
      }

      Cursor (.cursor/mcp.json):
      {
        "mcpServers": {
          "kuzu-memory": {
            "command": "kuzu-memory",
            "args": ["mcp"]
          }
        }
      }

    \b
    🔌 MCP TOOLS PROVIDED:
      • kuzu_enhance  - Enhance prompts with project context
      • kuzu_learn    - Store learnings asynchronously
      • kuzu_recall   - Query specific memories
      • kuzu_remember - Store important information
      • kuzu_stats    - Get memory system statistics

    \b
    🛑 STOPPING THE SERVER:
      Press Ctrl+C to gracefully stop the server.

    \b
    📚 MORE INFO:
      For installation instructions, see:
        kuzu-memory install --help
    """
    # Set up logging to stderr (stdout is used for MCP protocol)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    try:
        # Import the MCP server main function
        from ..mcp.server import main as mcp_server_main

        # Run the async server
        asyncio.run(mcp_server_main())
    except ImportError as e:
        click.echo(
            "❌ Error: MCP SDK is not installed.\n"
            "   Install with: pip install mcp\n"
            f"   Details: {e}",
            err=True,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n✅ MCP server stopped by user", err=True)
        sys.exit(0)
    except Exception as e:
        click.echo(f"❌ MCP server error: {e}", err=True)
        sys.exit(1)
