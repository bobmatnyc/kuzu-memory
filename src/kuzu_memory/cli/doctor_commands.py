"""
Diagnostic and troubleshooting CLI commands for KuzuMemory.

Provides unified doctor command for system diagnostics and health checks.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ..mcp.testing.diagnostics import MCPDiagnostics
from ..mcp.testing.health_checker import HealthStatus, MCPHealthChecker
from .cli_utils import rich_panel, rich_print
from .enums import OutputFormat


@click.group(invoke_without_command=True)
@click.option(
    "--fix", is_flag=True, help="Attempt to automatically fix detected issues"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save report to file")
@click.option(
    "--format",
    "-f",
    type=click.Choice(
        [OutputFormat.TEXT.value, OutputFormat.JSON.value, OutputFormat.HTML.value],
        case_sensitive=False,
    ),
    default=OutputFormat.TEXT.value,
    help="Output format (default: text)",
)
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.pass_context
def doctor(ctx, fix: bool, verbose: bool, output, format: str, project_root):
    """
    🩺 Diagnose and fix PROJECT issues.

    Run comprehensive diagnostics to identify and fix issues with
    PROJECT-LEVEL configurations only:
    - Project memory database (kuzu-memories/)
    - Claude Code MCP configuration (.claude/config.local.json)
    - Claude Code hooks (if configured)

    Does NOT check user-level configurations:
    - Claude Desktop (use install commands instead)
    - Global home directory configurations

    \b
    🎮 EXAMPLES:
      # Run full diagnostics (interactive)
      kuzu-memory doctor

      # Auto-fix issues (non-interactive)
      kuzu-memory doctor --fix

      # MCP-specific diagnostics
      kuzu-memory doctor mcp

      # Quick health check
      kuzu-memory doctor health

      # Test database connection
      kuzu-memory doctor connection

      # Save diagnostic report
      kuzu-memory doctor --output report.html --format html
    """
    # If no subcommand provided, run full diagnostics
    if ctx.invoked_subcommand is None:
        ctx.invoke(
            diagnose,
            verbose=verbose,
            output=output,
            format=format,
            fix=fix,
            project_root=project_root,
        )


@doctor.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save report to file")
@click.option(
    "--format",
    "-f",
    type=click.Choice(
        [OutputFormat.TEXT.value, OutputFormat.JSON.value, OutputFormat.HTML.value],
        case_sensitive=False,
    ),
    default=OutputFormat.TEXT.value,
    help="Output format (default: text)",
)
@click.option(
    "--fix", is_flag=True, help="Attempt to automatically fix detected issues"
)
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.pass_context
def diagnose(ctx, verbose: bool, output, format: str, fix: bool, project_root):
    """
    Run full PROJECT diagnostic suite.

    Performs comprehensive checks on project-level configuration,
    connection, tool discovery, and performance.

    Does NOT check user-level (Claude Desktop) configurations.
    """
    try:
        rich_print("🔍 Running full diagnostics...", style="blue")

        # Initialize diagnostics
        project_path = Path(project_root) if project_root else Path.cwd()
        diagnostics = MCPDiagnostics(project_root=project_path, verbose=verbose)

        # Run diagnostics
        report = asyncio.run(diagnostics.run_full_diagnostics(auto_fix=fix))

        # Generate output based on format
        if format == "json":
            output_content = json.dumps(report.to_dict(), indent=2)
        elif format == "html":
            output_content = diagnostics.generate_html_report(report)
        else:  # text
            output_content = diagnostics.generate_text_report(report)

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.write_text(output_content)
            rich_print(f"✅ Report saved to: {output_path}", style="green")
        else:
            # Print to console
            print(output_content)

        # Check if there are fixable issues and prompt for auto-fix
        has_failures = report.has_critical_errors or report.actionable_failures > 0
        has_fixable = any(r.fix_suggestion for r in report.results if not r.success)

        if has_failures and has_fixable and not fix:
            rich_print(
                f"\n💡 Found {report.actionable_failures} issue(s) with suggested fixes available.",
                style="yellow",
            )

            if click.confirm(
                "Would you like to attempt automatic fixes?", default=True
            ):
                rich_print("\n🔧 Attempting automatic fixes...", style="blue")

                # Re-run diagnostics with auto-fix enabled
                fix_report = asyncio.run(
                    diagnostics.run_full_diagnostics(auto_fix=True)
                )

                # Show fix results
                rich_print("\n📊 Fix Results:", style="blue")

                # Generate fix report
                if format == "json":
                    fix_output = json.dumps(fix_report.to_dict(), indent=2)
                elif format == "html":
                    fix_output = diagnostics.generate_html_report(fix_report)
                else:
                    fix_output = diagnostics.generate_text_report(fix_report)

                print(fix_output)

                # Update report for exit code determination
                report = fix_report

                if fix_report.actionable_failures == 0:
                    rich_print("\n✅ All issues fixed successfully!", style="green")
                else:
                    rich_print(
                        f"\n⚠️  {fix_report.actionable_failures} issue(s) still remain after auto-fix.",
                        style="yellow",
                    )

        # Exit with appropriate code
        if report.has_critical_errors:
            rich_print(
                "\n❌ Critical errors detected. See report for details.", style="red"
            )
            sys.exit(1)
        elif report.actionable_failures > 0:
            rich_print(
                f"\n⚠️  {report.actionable_failures} checks failed. See report for details.",
                style="yellow",
            )
            sys.exit(1)
        else:
            rich_print("\n✅ All diagnostics passed successfully!", style="green")
            sys.exit(0)

    except KeyboardInterrupt:
        rich_print("\n🛑 Diagnostics cancelled", style="yellow")
        sys.exit(1)
    except Exception as e:
        rich_print(f"❌ Diagnostic error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


@doctor.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.pass_context
def mcp(ctx, verbose, output, project_root):
    """
    PROJECT MCP-specific diagnostics.

    Validates PROJECT-LEVEL MCP server configuration:
    - Claude Code MCP config (.claude/config.local.json)
    - Protocol compliance
    - Tool functionality

    Does NOT check Claude Desktop (user-level) MCP configuration.
    """
    try:
        rich_print("🔍 Running MCP diagnostics...", style="blue")

        project_path = Path(project_root) if project_root else Path.cwd()
        diagnostics = MCPDiagnostics(project_root=project_path, verbose=verbose)

        # Run MCP-specific checks
        config_results = asyncio.run(diagnostics.check_configuration())
        tool_results = asyncio.run(diagnostics.check_tools())

        # Combine results
        all_results = config_results + tool_results

        # Display results
        passed = sum(1 for r in all_results if r.success)
        total = len(all_results)

        for result in all_results:
            status = "✅" if result.success else "❌"
            style = "green" if result.success else "red"
            rich_print(f"{status} {result.check_name}: {result.message}", style=style)

            if verbose:
                if result.error:
                    rich_print(f"   Error: {result.error}", style="red")
                if result.fix_suggestion:
                    rich_print(f"   Fix: {result.fix_suggestion}", style="yellow")
                rich_print(f"   Duration: {result.duration_ms:.2f}ms", style="dim")

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_data = {
                "check_type": "mcp",
                "passed": passed,
                "total": total,
                "results": [r.to_dict() for r in all_results],
            }
            output_path.write_text(json.dumps(output_data, indent=2))
            rich_print(f"\n✅ Results saved to: {output_path}", style="green")

        # Summary
        rich_panel(
            f"MCP Diagnostics: {passed}/{total} passed",
            title="✅ MCP Healthy" if passed == total else "⚠️  MCP Issues",
            style="green" if passed == total else "yellow",
        )

        sys.exit(0 if passed == total else 1)

    except Exception as e:
        rich_print(f"❌ MCP diagnostic error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


@doctor.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.pass_context
def connection(ctx, verbose, output, project_root):
    """
    Test PROJECT database and MCP server connection.

    Validates project-level database connectivity and MCP protocol initialization.
    Uses project memory database (kuzu-memories/), not user-level configurations.
    """
    try:
        rich_print("🔍 Testing connections...", style="blue")

        project_path = Path(project_root) if project_root else Path.cwd()
        diagnostics = MCPDiagnostics(project_root=project_path, verbose=verbose)

        # Run connection checks
        results = asyncio.run(diagnostics.check_connection())

        # Display results
        passed = sum(1 for r in results if r.success)
        total = len(results)

        for result in results:
            status = "✅" if result.success else "❌"
            style = "green" if result.success else "red"
            rich_print(f"{status} {result.check_name}: {result.message}", style=style)

            if verbose:
                if result.error:
                    rich_print(f"   Error: {result.error}", style="red")
                if result.fix_suggestion:
                    rich_print(f"   Fix: {result.fix_suggestion}", style="yellow")
                if result.metadata:
                    rich_print(f"   Metadata: {result.metadata}", style="dim")
                rich_print(f"   Duration: {result.duration_ms:.2f}ms", style="dim")

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_data = {
                "check_type": "connection",
                "passed": passed,
                "total": total,
                "results": [r.to_dict() for r in results],
            }
            output_path.write_text(json.dumps(output_data, indent=2))
            rich_print(f"\n✅ Results saved to: {output_path}", style="green")

        # Summary
        rich_panel(
            f"Connection Test: {passed}/{total} passed",
            title=(
                "✅ Connection Healthy" if passed == total else "⚠️  Connection Issues"
            ),
            style="green" if passed == total else "yellow",
        )

        sys.exit(0 if passed == total else 1)

    except Exception as e:
        rich_print(f"❌ Connection test error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


@doctor.command()
@click.option("--detailed", is_flag=True, help="Show detailed component status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option(
    "--continuous", is_flag=True, help="Continuous monitoring mode (use Ctrl+C to stop)"
)
@click.option(
    "--interval",
    type=int,
    default=5,
    help="Check interval in seconds for continuous mode",
)
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.pass_context
def health(ctx, detailed, json_output, continuous, interval, project_root):
    """
    Quick PROJECT health check.

    Performs rapid health checks on PROJECT-LEVEL components:
    - Project memory database (kuzu-memories/)
    - MCP server (if configured)
    - Tool availability

    Does NOT check user-level (Claude Desktop) health.
    """
    try:
        # Determine project root
        if project_root:
            project_path = Path(project_root)
        else:
            project_path = Path.cwd()

        # Create health checker
        health_checker = MCPHealthChecker(project_root=project_path)

        # Define health check function
        async def perform_check():
            result = await health_checker.check_health(detailed=detailed, retry=True)
            return result

        # Define display function
        def display_health(result):
            if json_output:
                # JSON output
                print(json.dumps(result.to_dict(), indent=2))
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
                    console.print(
                        f"  Throughput: {perf.throughput_ops_per_sec:.2f} ops/s"
                    )
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
                console.print(
                    f"  [green]Healthy:[/green] {summary['healthy']}/{summary['total']}"
                )
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

                    # Wait for next check
                    if continuous:
                        time.sleep(interval)
                    else:
                        break

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


__all__ = ["doctor"]
