"""
MCP (Model Context Protocol) commands for Claude Code integration.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import click

from kuzu_memory.cli.cli_utils import rich_panel, rich_print
from kuzu_memory.cli.mcp_install_commands import (
    install_mcp,
    list_mcp_installers,
)
from kuzu_memory.cli.mcp_install_commands import (
    mcp_status as detect_systems,  # Renamed but kept alias for compatibility
)
from kuzu_memory.mcp import create_mcp_server


@click.group()
def mcp() -> None:
    """
    🤖 MCP server commands and integrations.

    \b
    🎮 COMMANDS:
      serve      Run MCP server for Claude Code integration
      install    Install MCP configurations for AI systems
      detect     Detect installed AI systems
      list       List available MCP installers
      health     Check MCP server health
      info       Show MCP server information
      config     Generate MCP configuration
      test       Test MCP server functionality

    Use 'kuzu-memory mcp COMMAND --help' for detailed help.
    """
    pass


@mcp.command()
@click.option("--port", type=int, help="Port to run server on (for network mode)")
@click.option("--stdio", is_flag=True, default=True, help="Use stdio for communication (default)")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def serve(ctx: click.Context, port: int | None, stdio: bool, project_root: str | None) -> None:
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

        # When running MCP server, all logging must go to stderr to avoid
        # contaminating stdout which must contain only JSON-RPC messages
        print(f"Starting MCP server for project: {project_path}", file=sys.stderr)

        # Import the run_server module
        from kuzu_memory.mcp.run_server import main

        # Run the async main function
        asyncio.run(main())  # type: ignore[no-untyped-call]  # MCP server main lacks type annotations

    except KeyboardInterrupt:
        print("\n🛑 MCP server stopped", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ MCP server error: {e}", file=sys.stderr)
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@mcp.command()
@click.option("--port", type=int, help="Port to run server on (for network mode)")
@click.option("--stdio", is_flag=True, default=True, help="Use stdio for communication (default)")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def start(ctx: click.Context, port: int | None, stdio: bool, project_root: str | None) -> None:
    """
    Start the MCP server (alias for 'serve').

    This provides all KuzuMemory operations as MCP tools that can be
    used directly by Claude Code without requiring subprocess calls.

    Examples:
        # Start MCP server (stdio mode for Claude Code)
        kuzu-memory mcp start

        # Start with specific project root
        kuzu-memory mcp start --project-root /path/to/project
    """
    # Delegate to serve command
    ctx.invoke(serve, port=port, stdio=stdio, project_root=project_root)


@mcp.command()
@click.pass_context
def test(ctx: click.Context) -> None:
    """
    Test MCP server functionality.

    Runs a quick test to verify the MCP server is working correctly.
    """
    try:
        rich_print("🧪 Testing MCP server...", style="blue")

        # Create server instance
        server = create_mcp_server()  # type: ignore[no-untyped-call,func-returns-value]

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
                f"All {total} tests passed! ✨\n\nMCP server is ready for Claude Code integration.",
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
def info(ctx: click.Context) -> None:
    """
    Show MCP server information and configuration.
    """
    try:
        server = create_mcp_server()  # type: ignore[no-untyped-call,func-returns-value]
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
def config(ctx: click.Context, output: str | None) -> None:
    """
    Generate MCP configuration for Claude Code.

    Creates the configuration JSON needed to add KuzuMemory
    as an MCP server in Claude Code settings.
    """
    try:
        import json
        from pathlib import Path

        config: dict[str, Any] = {
            "mcpServers": {
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": ["mcp"],
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
            rich_panel(config_json, title="📋 Claude Code MCP Configuration", style="blue")

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


@mcp.command()
@click.option("--detailed", is_flag=True, help="Show detailed component status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--continuous", is_flag=True, help="Continuous monitoring mode (use Ctrl+C to stop)")
@click.option(
    "--interval",
    type=int,
    default=5,
    help="Check interval in seconds for continuous mode",
)
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def health(
    ctx: click.Context,
    detailed: bool,
    json_output: bool,
    continuous: bool,
    interval: int,
    project_root: str | None,
) -> None:
    """
    Check MCP server health and component status.

    Performs comprehensive health checks on all MCP server components including
    CLI, database, protocol, and tools. Supports continuous monitoring mode.

    Examples:
        # Quick health check
        kuzu-memory mcp health

        # Detailed component status
        kuzu-memory mcp health --detailed

        # JSON output for scripting
        kuzu-memory mcp health --json

        # Continuous monitoring
        kuzu-memory mcp health --continuous --interval 10
    """
    import json as json_module
    import time

    from rich.console import Console
    from rich.table import Table

    from kuzu_memory.mcp.testing.health_checker import HealthStatus, MCPHealthChecker

    try:
        # Determine project root
        if project_root:
            project_path = Path(project_root)
        else:
            project_path = Path.cwd()

        # Create health checker
        health_checker = MCPHealthChecker(project_root=project_path)

        # Define health check function
        async def perform_check() -> Any:
            result = await health_checker.check_health(detailed=detailed, retry=True)
            return result

        # Define display function
        def display_health(result: Any) -> None:
            if json_output:
                # JSON output
                print(json_module.dumps(result.to_dict(), indent=2))
            else:
                # Rich console output
                console = Console()

                # Status colors
                status_colors = {
                    HealthStatus.HEALTHY: "green",
                    HealthStatus.DEGRADED: "yellow",
                    HealthStatus.UNHEALTHY: "red",
                }

                # Status symbols
                status_symbols = {
                    HealthStatus.HEALTHY: "✅",
                    HealthStatus.DEGRADED: "⚠️",
                    HealthStatus.UNHEALTHY: "❌",
                }

                # Overall status
                overall_status = result.health.status
                color = status_colors[overall_status]
                symbol = status_symbols[overall_status]

                console.print(
                    f"\n{symbol} [bold {color}]System Health: {overall_status.value.upper()}[/bold {color}]"
                )
                console.print(f"Check Duration: {result.duration_ms:.2f}ms")
                console.print(f"Timestamp: {result.timestamp}\n")

                # Components table
                table = Table(title="Component Health")
                table.add_column("Component", style="cyan")
                table.add_column("Status", style="bold")
                table.add_column("Latency", justify="right")
                table.add_column("Message")

                for component in result.health.components:
                    comp_color = status_colors[component.status]
                    comp_symbol = status_symbols[component.status]

                    table.add_row(
                        component.name,
                        f"{comp_symbol} [{comp_color}]{component.status.value}[/{comp_color}]",
                        f"{component.latency_ms:.2f}ms",
                        component.message,
                    )

                console.print(table)

                # Performance metrics (if detailed)
                if detailed and result.health.performance.total_requests > 0:
                    console.print("\n[bold]Performance Metrics[/bold]")
                    perf = result.health.performance
                    console.print(f"  Average Latency: {perf.average_latency_ms:.2f}ms")
                    console.print(f"  P50 Latency: {perf.latency_p50_ms:.2f}ms")
                    console.print(f"  P95 Latency: {perf.latency_p95_ms:.2f}ms")
                    console.print(f"  P99 Latency: {perf.latency_p99_ms:.2f}ms")
                    console.print(f"  Throughput: {perf.throughput_ops_per_sec:.2f} ops/s")
                    console.print(f"  Error Rate: {perf.error_rate * 100:.2f}%")

                # Resource metrics (if detailed)
                if detailed:
                    console.print("\n[bold]Resource Usage[/bold]")
                    res = result.health.resources
                    console.print(f"  Memory: {res.memory_mb:.2f} MB")
                    console.print(f"  CPU: {res.cpu_percent:.2f}%")
                    console.print(f"  Open Connections: {res.open_connections}")
                    console.print(f"  Active Threads: {res.active_threads}")

                # Summary
                summary = result.health.to_dict()["summary"]
                console.print("\n[bold]Component Summary[/bold]")
                console.print(f"  [green]Healthy:[/green] {summary['healthy']}/{summary['total']}")
                if summary["degraded"] > 0:
                    console.print(f"  [yellow]Degraded:[/yellow] {summary['degraded']}")
                if summary["unhealthy"] > 0:
                    console.print(f"  [red]Unhealthy:[/red] {summary['unhealthy']}")

                console.print()

        # Run health check(s)
        if continuous:
            # Continuous monitoring mode
            rich_print(
                f"🔄 Starting continuous health monitoring (interval: {interval}s)",
                style="blue",
            )
            rich_print("Press Ctrl+C to stop\n", style="dim")

            try:
                while True:
                    result = asyncio.run(perform_check())
                    display_health(result)

                    # Wait for next check (continuous is always True here)
                    time.sleep(interval)

            except KeyboardInterrupt:
                rich_print("\n\n✋ Monitoring stopped", style="yellow")

        else:
            # Single health check
            result = asyncio.run(perform_check())
            display_health(result)

            # Exit with appropriate code
            if result.health.status == HealthStatus.UNHEALTHY:
                sys.exit(1)
            elif result.health.status == HealthStatus.DEGRADED:
                sys.exit(2)

    except Exception as e:
        rich_print(f"❌ Health check failed: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


# Register the new commands with the mcp group
mcp.add_command(detect_systems, name="detect")
mcp.add_command(install_mcp, name="install")
mcp.add_command(list_mcp_installers, name="list")
