"""
MCP (Model Context Protocol) commands for Claude Code integration.
"""

import asyncio
import sys
from pathlib import Path

import click

from ..mcp import create_mcp_server
from .cli_utils import rich_panel, rich_print


@click.group()
def mcp():
    """
    🤖 MCP server commands for Claude Code integration.

    Run the Model Context Protocol server to provide memory operations
    as tools for Claude Code and other MCP-compatible AI systems.
    """
    pass


@mcp.command()
@click.option("--port", type=int, help="Port to run server on (for network mode)")
@click.option(
    "--stdio", is_flag=True, default=True, help="Use stdio for communication (default)"
)
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.pass_context
def serve(ctx, port: int | None, stdio: bool, project_root: str | None):
    """
    Run the MCP server for Claude Code integration.

    This provides all KuzuMemory operations as MCP tools that can be
    used directly by Claude Code without requiring subprocess calls.

    Examples:
        # Run MCP server (stdio mode for Claude Code)
        kuzu-memory mcp serve

        # Run with specific project root
        kuzu-memory mcp serve --project-root /path/to/project
    """
    try:
        if project_root:
            project_path = Path(project_root)
        else:
            project_path = Path.cwd()

        rich_print(f"Starting MCP server for project: {project_path}", style="blue")

        # Import the run_server module
        from ..mcp.run_server import main

        # Run the async main function
        asyncio.run(main())

    except KeyboardInterrupt:
        rich_print("\n🛑 MCP server stopped", style="yellow")
        sys.exit(0)
    except Exception as e:
        rich_print(f"❌ MCP server error: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@mcp.command()
@click.pass_context
def test(ctx):
    """
    Test MCP server functionality.

    Runs a quick test to verify the MCP server is working correctly.
    """
    try:
        rich_print("🧪 Testing MCP server...", style="blue")

        # Create server instance
        server = create_mcp_server()

        # Test basic operations
        tests = [
            ("enhance", {"prompt": "test prompt", "format": "plain"}),
            ("recall", {"query": "test query"}),
            ("stats", {"detailed": False}),
            ("project", {"verbose": False}),
        ]

        results = []
        for tool_name, params in tests:
            try:
                method = getattr(server, tool_name)
                result = method(**params)
                success = result.get("success", False)
                results.append((tool_name, success))

                if success:
                    rich_print(f"  ✅ {tool_name}: OK", style="green")
                else:
                    rich_print(
                        f"  ⚠️  {tool_name}: {result.get('error', 'Failed')}",
                        style="yellow",
                    )
            except Exception as e:
                results.append((tool_name, False))
                rich_print(f"  ❌ {tool_name}: {e}", style="red")

        # Summary
        passed = sum(1 for _, success in results if success)
        total = len(results)

        if passed == total:
            rich_panel(
                f"All {total} tests passed! ✨\n\n"
                "MCP server is ready for Claude Code integration.",
                title="🎉 Test Success",
                style="green",
            )
        else:
            rich_panel(
                f"{passed}/{total} tests passed.\n\n"
                "Some tests failed. Check configuration and try again.",
                title="⚠️ Test Partial Success",
                style="yellow",
            )

    except Exception as e:
        rich_print(f"❌ MCP test failed: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@mcp.command()
@click.pass_context
def info(ctx):
    """
    Show MCP server information and configuration.
    """
    try:
        server = create_mcp_server()
        tools = server.get_tools()

        rich_panel(
            f"MCP Server Information\n\n"
            f"Version: 1.0.0\n"
            f"Project Root: {server.project_root}\n"
            f"CLI Path: {server.cli_path}\n"
            f"Available Tools: {len(tools)}",
            title="🤖 MCP Server Info",
            style="blue",
        )

        rich_print("\n📋 Available Tools:", style="blue")
        for tool in tools:
            params = tool.get("parameters", {})
            required = [p for p, info in params.items() if info.get("required")]
            optional = [p for p, info in params.items() if not info.get("required")]

            rich_print(f"\n  • {tool['name']}: {tool['description']}")
            if required:
                rich_print(f"    Required: {', '.join(required)}", style="yellow")
            if optional:
                rich_print(f"    Optional: {', '.join(optional)}", style="dim")

    except Exception as e:
        rich_print(f"❌ Failed to get MCP info: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@mcp.command()
@click.option("--output", type=click.Path(), help="Save configuration to file")
@click.pass_context
def config(ctx, output: str | None):
    """
    Generate MCP configuration for Claude Code.

    Creates the configuration JSON needed to add KuzuMemory
    as an MCP server in Claude Code settings.
    """
    try:
        import json
        from pathlib import Path

        config = {
            "mcpServers": {
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": ["mcp", "serve"],
                    "env": {"KUZU_MEMORY_PROJECT": "${PROJECT_ROOT}"},
                }
            }
        }

        config_json = json.dumps(config, indent=2)

        if output:
            output_path = Path(output)
            output_path.write_text(config_json)
            rich_print(f"✅ Configuration saved to: {output_path}", style="green")
        else:
            rich_panel(
                config_json, title="📋 Claude Code MCP Configuration", style="blue"
            )

            rich_print("\n📌 To use this configuration:", style="blue")
            rich_print("1. Copy the JSON above")
            rich_print("2. Open Claude Code settings")
            rich_print("3. Add to 'mcpServers' section")
            rich_print("4. Restart Claude Code")

    except Exception as e:
        rich_print(f"❌ Failed to generate config: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)
