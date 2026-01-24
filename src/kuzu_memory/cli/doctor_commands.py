"""
Diagnostic and troubleshooting CLI commands for KuzuMemory.

Provides unified doctor command for system diagnostics and health checks.

Design Decision: Service-Oriented Doctor Commands
--------------------------------------------------
Rationale: Use DiagnosticService through ServiceManager for lifecycle management
and dependency injection. Async methods bridged via run_async() utility.

Trade-offs:
- Simplicity: ServiceManager handles initialization/cleanup automatically
- Testability: Easy to mock DiagnosticService in tests
- Maintainability: Single source of truth for diagnostic logic

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Phase: 5.3 (High-Risk Async Command Migrations)
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from ..mcp.testing.diagnostics import MCPDiagnostics
from ..mcp.testing.health_checker import HealthStatus, MCPHealthChecker
from .async_utils import run_async
from .cli_utils import rich_print
from .enums import OutputFormat
from .service_manager import ServiceManager


@click.group(invoke_without_command=True)
@click.option("--fix", is_flag=True, help="Attempt to automatically fix detected issues")
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
@click.option("--hooks/--no-hooks", default=True, help="Run hooks diagnostics (default: enabled)")
@click.option(
    "--server-lifecycle/--no-server-lifecycle",
    default=True,
    help="Run server lifecycle diagnostics (default: enabled)",
)
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def doctor(
    ctx: click.Context,
    fix: bool,
    verbose: bool,
    output: str | None,
    format: str,
    hooks: bool,
    server_lifecycle: bool,
    project_root: str | None,
) -> None:
    """
    🩺 Diagnose and fix PROJECT issues.

    Run comprehensive diagnostics to identify and fix issues with
    PROJECT-LEVEL configurations only:
    - Project memory database (kuzu-memories/)
    - Claude Code MCP configuration (.claude/config.local.json)
    - Claude Code hooks (if configured)
    - MCP server lifecycle (startup, health, shutdown)

    Does NOT check user-level configurations:
    - Claude Desktop (use install commands instead)
    - Global home directory configurations

    \b
    🎮 EXAMPLES:
      # Run full diagnostics (interactive)
      kuzu-memory doctor

      # Auto-fix issues (non-interactive)
      kuzu-memory doctor --fix

      # Skip hooks and lifecycle checks
      kuzu-memory doctor --no-hooks --no-server-lifecycle

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
            hooks=hooks,
            server_lifecycle=server_lifecycle,
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
@click.option("--fix", is_flag=True, help="Attempt to automatically fix detected issues")
@click.option("--hooks/--no-hooks", default=True, help="Run hooks diagnostics (default: enabled)")
@click.option(
    "--server-lifecycle/--no-server-lifecycle",
    default=True,
    help="Run server lifecycle diagnostics (default: enabled)",
)
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def diagnose(
    ctx: click.Context,
    verbose: bool,
    output: str | None,
    format: str,
    fix: bool,
    hooks: bool,
    server_lifecycle: bool,
    project_root: str | None,
) -> None:
    """
    Run full PROJECT diagnostic suite.

    Performs comprehensive checks on project-level configuration,
    connection, tool discovery, performance, hooks, and server lifecycle.

    Does NOT check user-level (Claude Desktop) configurations.

    Note: Uses DiagnosticService with async-to-sync bridge for I/O operations.
    """
    try:
        rich_print("🔍 Running full diagnostics...", style="blue")

        # Initialize diagnostics using legacy MCPDiagnostics directly
        # TODO: Migrate fully to DiagnosticService once all features are ported
        project_path = Path(project_root) if project_root else Path.cwd()
        diagnostics = MCPDiagnostics(project_root=project_path, verbose=verbose)

        # Initialize config service for hooks check
        from ..services import ConfigService

        project_path = Path(project_root) if project_root else Path.cwd()
        config_service = ConfigService(project_path)
        config_service.initialize()

        # Run diagnostics
        report = asyncio.run(
            diagnostics.run_full_diagnostics(
                auto_fix=fix,
                check_hooks=hooks,
                check_server_lifecycle=server_lifecycle,
            )
        )

        # Add hooks status to report if requested
        hooks_status = None
        if hooks:
            try:
                with ServiceManager.diagnostic_service(config_service) as diagnostic:
                    hooks_status = run_async(diagnostic.check_hooks_status(project_path))
            except Exception:
                # Hooks check failed - continue without hooks status
                pass

        config_service.cleanup()

        # Generate output based on format
        if format == "json":
            report_dict = report.to_dict()
            if hooks_status:
                report_dict["hooks_status"] = hooks_status
            output_content = json.dumps(report_dict, indent=2)
        elif format == "html":
            output_content = diagnostics.generate_html_report(report)
        else:  # text
            output_content = diagnostics.generate_text_report(report)

            # Append hooks status to text report if available
            if hooks_status:
                output_content += "\n\n" + "=" * 70
                output_content += "\nHOOKS STATUS"
                output_content += "\n" + "-" * 70

                # Git hooks
                git_hooks = hooks_status["git_hooks"]
                git_installed = "✅ Installed" if git_hooks["installed"] else "❌ Not installed"
                output_content += f"\nGit Hooks: {git_installed}"
                if git_hooks.get("path"):
                    output_content += f"\n  Path: {git_hooks['path']}"
                if git_hooks.get("installed") and not git_hooks.get("executable", True):
                    output_content += "\n  ⚠️  Not executable"

                # Claude Code hooks
                cc_hooks = hooks_status["claude_code_hooks"]
                cc_installed = "✅ Configured" if cc_hooks["installed"] else "❌ Not configured"
                output_content += f"\nClaude Code Hooks: {cc_installed}"
                if cc_hooks.get("events"):
                    events_str = ", ".join(cc_hooks["events"])
                    output_content += f"\n  Events: {events_str}"
                if cc_hooks.get("installed") and not cc_hooks.get("valid", True):
                    output_content += "\n  ⚠️  Invalid configuration"

                # Overall status
                overall = hooks_status["overall_status"]
                if overall == "fully_configured":
                    output_content += "\n\n✅ All hooks configured"
                elif overall == "partially_configured":
                    output_content += "\n\n⚠️  Partially configured"
                else:
                    output_content += "\n\n❌ No hooks configured"

                # Recommendations
                if hooks_status.get("recommendations"):
                    output_content += "\n\nRecommendations:"
                    for rec in hooks_status["recommendations"]:
                        output_content += f"\n  • {rec}"

                output_content += "\n" + "=" * 70

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

            if click.confirm("Would you like to attempt automatic fixes?", default=True):
                rich_print("\n🔧 Attempting automatic fixes...", style="blue")

                # Re-run diagnostics with auto-fix enabled
                fix_report = asyncio.run(diagnostics.run_full_diagnostics(auto_fix=True))

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
            rich_print("\n❌ Critical errors detected. See report for details.", style="red")
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
@click.option("--full", "-f", is_flag=True, help="Run full protocol compliance tests")
@click.option("--fix", is_flag=True, help="Auto-fix detected issues")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def mcp(
    ctx: click.Context,
    full: bool,
    fix: bool,
    verbose: bool,
    output: str | None,
    project_root: str | None,
) -> None:
    """
    Diagnose MCP server installation.

    Runs comprehensive diagnostics on MCP server configuration:
    - Platform detection
    - Command accessibility
    - Environment variables
    - Configuration validation

    With --full, also tests JSON-RPC protocol compliance.
    With --fix, attempts to auto-fix detected issues.

    Note: Uses MCPInstallerAdapter for enhanced diagnostics.
    """
    from ..installers.mcp_installer_adapter import HAS_MCP_INSTALLER
    from ..services import ConfigService

    try:
        rich_print("🔍 Running MCP installation diagnostics...", style="blue")

        # Initialize config service
        project_path = Path(project_root) if project_root else Path.cwd()
        config_service = ConfigService(project_path)
        config_service.initialize()

        try:
            # Use DiagnosticService for MCP installation check
            with ServiceManager.diagnostic_service(config_service) as diagnostic:
                # Run async MCP installation check using run_async bridge
                mcp_install = run_async(diagnostic.check_mcp_installation(full=full))

                # Display results
                available = mcp_install.get("available", False)
                status = mcp_install.get("status", "unknown")
                platform = mcp_install.get("platform", "N/A")
                checks_passed = mcp_install.get("checks_passed", 0)
                checks_total = mcp_install.get("checks_total", 0)
                issues = mcp_install.get("issues", [])
                recommendations = mcp_install.get("recommendations", [])

                if not available:
                    rich_print("⚠️  MCPInstallerAdapter not available", style="yellow")
                    rich_print(
                        "   Install py-mcp-installer-service submodule for enhanced diagnostics",
                        style="dim",
                    )
                    if HAS_MCP_INSTALLER:
                        rich_print("   Status: Available", style="green")
                    else:
                        rich_print("   Status: Not Available", style="red")
                        rich_print(
                            "   Run: git submodule update --init --recursive",
                            style="dim",
                        )
                else:
                    # Show status
                    if status == "healthy":
                        rich_print("✅ MCP installation is healthy", style="green")
                    elif status == "degraded":
                        rich_print("⚠️  MCP installation has issues", style="yellow")
                    elif status == "critical":
                        rich_print("❌ MCP installation has critical issues", style="red")
                    else:
                        rich_print(f"Info: MCP installation status: {status}", style="blue")

                    rich_print(f"   Platform: {platform}", style="dim")
                    rich_print(f"   Checks: {checks_passed}/{checks_total} passed", style="dim")

                if issues:
                    rich_print("\n⚠️  Issues detected:", style="yellow")
                    for issue in issues:
                        severity = issue.get("severity", "unknown").upper()
                        message = issue.get("message", "Unknown issue")
                        rich_print(f"   • [{severity}] {message}", style="yellow")

                if recommendations:
                    rich_print("\n💡 Recommendations:", style="blue")
                    for rec in recommendations:
                        rich_print(f"   • {rec}", style="blue")

                # Auto-fix if requested
                if fix and available and issues:
                    rich_print("\n🔧 Attempting automatic fixes...", style="blue")
                    from ..installers.mcp_installer_adapter import MCPInstallerAdapter

                    try:
                        adapter = MCPInstallerAdapter(project_root=project_path)
                        fixes = adapter.fix_issues(auto_fix=True)
                        if fixes:
                            rich_print(f"\n✅ Applied {len(fixes)} fix(es):", style="green")
                            for fix_desc in fixes:
                                rich_print(f"   • {fix_desc}", style="green")
                        else:
                            rich_print("\n⚠️  No auto-fixes available", style="yellow")
                    except Exception as fix_error:
                        rich_print(f"\n❌ Auto-fix failed: {fix_error}", style="red")

                # Save to file if requested
                if output:
                    output_path = Path(output)
                    output_path.write_text(json.dumps(mcp_install, indent=2))
                    rich_print(f"\n✅ Results saved to: {output_path}", style="green")

                # Exit with appropriate code
                if status == "healthy":
                    sys.exit(0)
                elif status in ["degraded", "warning"]:
                    sys.exit(1)
                else:
                    sys.exit(2)

        finally:
            config_service.cleanup()

    except Exception as e:
        rich_print(f"❌ MCP diagnostic error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


@doctor.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def connection(
    ctx: click.Context, verbose: bool, output: str | None, project_root: str | None
) -> None:
    """
    Test PROJECT database and MCP server connection.

    Validates project-level database connectivity and MCP protocol initialization.
    Uses project memory database (kuzu-memories/), not user-level configurations.

    Note: Uses DiagnosticService with async-to-sync bridge for I/O operations.
    """
    from ..services import ConfigService

    try:
        rich_print("🔍 Testing connections...", style="blue")

        # Initialize config service
        project_path = Path(project_root) if project_root else Path.cwd()
        config_service = ConfigService(project_path)
        config_service.initialize()

        try:
            # Get database path for memory service
            db_path = config_service.get_db_path()

            # Create memory service for database health check
            with (
                ServiceManager.memory_service(db_path) as memory,
                ServiceManager.diagnostic_service(config_service, memory) as diagnostic,
            ):
                # Run async database health check using run_async bridge
                db_health = run_async(diagnostic.check_database_health())

                # Display results
                connected = db_health.get("connected", False)
                memory_count = db_health.get("memory_count", 0)
                db_size_bytes = db_health.get("db_size_bytes", 0)
                issues = db_health.get("issues", [])

                if connected:
                    rich_print("✅ Database connection is healthy", style="green")
                    rich_print(f"   Memories: {memory_count}", style="dim")
                    rich_print(f"   Size: {db_size_bytes / (1024 * 1024):.2f} MB", style="dim")
                else:
                    rich_print("❌ Database connection issues", style="red")

                if issues:
                    rich_print("\n⚠️  Issues detected:", style="yellow")
                    for issue in issues:
                        rich_print(f"   • {issue}", style="yellow")

                # Save to file if requested
                if output:
                    output_path = Path(output)
                    output_path.write_text(json.dumps(db_health, indent=2))
                    rich_print(f"\n✅ Results saved to: {output_path}", style="green")

                # Exit with appropriate code
                all_healthy = connected and len(issues) == 0
                sys.exit(0 if all_healthy else 1)

        finally:
            config_service.cleanup()

    except Exception as e:
        rich_print(f"❌ Connection test error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


@doctor.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed configuration")
@click.option("--fix", is_flag=True, help="Attempt to install missing hooks")
@click.option("--project-root", type=click.Path(exists=True, path_type=Path), help="Project root")
@click.pass_context
def hooks(ctx: click.Context, verbose: bool, fix: bool, project_root: Path | None) -> None:
    """
    Check hooks installation status.

    Verifies installation and configuration of:
    - Git post-commit hooks (.git/hooks/post-commit)
    - Claude Code hooks (.claude/settings.local.json)

    Use --verbose to show detailed hook configuration.
    Use --fix to attempt automatic installation of missing hooks.
    """
    from ..services import ConfigService

    try:
        console = Console()

        # Initialize config service
        project_path = project_root or Path.cwd()
        config_service = ConfigService(project_path)
        config_service.initialize()

        try:
            # Use DiagnosticService for hooks status check
            with ServiceManager.diagnostic_service(config_service) as diagnostic:
                # Run async hooks status check using run_async bridge
                result = run_async(diagnostic.check_hooks_status(project_path))

                # Display results with rich formatting
                console.print("\n[bold]🪝 Hooks Status[/bold]\n")

                # Git hooks
                git_hooks = result["git_hooks"]
                if git_hooks["installed"]:
                    git_status = "[green]✅ Installed[/green]"
                    if verbose and git_hooks.get("path"):
                        git_status += f"\n    Path: {git_hooks['path']}"
                    if not git_hooks.get("executable", True):
                        git_status += "\n    [yellow]⚠️  Not executable[/yellow]"
                else:
                    git_status = "[red]❌ Not installed[/red]"

                console.print(f"  Git Hooks: {git_status}")

                # Claude Code hooks
                cc_hooks = result["claude_code_hooks"]
                if cc_hooks["installed"]:
                    cc_status = "[green]✅ Configured[/green]"
                    if verbose and cc_hooks.get("events"):
                        events_str = ", ".join(cc_hooks["events"])
                        cc_status += f"\n    Events: {events_str}"
                    if not cc_hooks.get("valid", True):
                        cc_status += "\n    [yellow]⚠️  Invalid configuration[/yellow]"
                else:
                    cc_status = "[red]❌ Not configured[/red]"

                console.print(f"  Claude Code Hooks: {cc_status}")

                # Overall status
                overall = result["overall_status"]
                if overall == "fully_configured":
                    console.print("\n[green]✅ All hooks configured[/green]")
                elif overall == "partially_configured":
                    console.print("\n[yellow]⚠️  Partially configured[/yellow]")
                else:
                    console.print("\n[red]❌ No hooks configured[/red]")

                # Recommendations
                if result.get("recommendations"):
                    console.print("\n[yellow]💡 Recommendations:[/yellow]")
                    for rec in result["recommendations"]:
                        console.print(f"  → {rec}")

                # Fix option
                if fix and overall != "fully_configured":
                    console.print("\n[bold]🔧 Attempting to install missing hooks...[/bold]")

                    # Install git hooks if missing
                    if not git_hooks["installed"]:
                        try:
                            from .git_commands import install_hooks as git_install_hooks_cmd

                            console.print("  Installing git hooks...")
                            ctx.invoke(git_install_hooks_cmd, force=False)
                        except Exception as e:
                            console.print(f"  [yellow]⚠️  Git hooks install failed: {e}[/yellow]")

                    # Install Claude Code hooks if missing
                    if not cc_hooks["installed"]:
                        try:
                            from .install_unified import install_command

                            console.print("  Installing Claude Code hooks...")
                            ctx.invoke(
                                install_command,
                                integration="claude-code",
                                force=False,
                                dry_run=False,
                                verbose=False,
                            )
                        except Exception as e:
                            console.print(
                                f"  [yellow]⚠️  Claude Code hooks install failed: {e}[/yellow]"
                            )

                    console.print("\n[green]✅ Hook installation complete[/green]")
                    console.print("Run 'kuzu-memory doctor hooks' again to verify")

                # Exit with appropriate code
                if overall == "fully_configured":
                    sys.exit(0)
                elif overall == "partially_configured":
                    sys.exit(1)
                else:
                    sys.exit(2)

        finally:
            config_service.cleanup()

    except Exception as e:
        console.print(f"[red]❌ Hooks check failed: {e}[/red]")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


@doctor.command()
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
        async def perform_check() -> Any:
            result = await health_checker.check_health(detailed=detailed, retry=True)
            return result

        # Define display function
        def display_health(result: Any) -> None:
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

                    # Wait for next check (continuous is always True in this branch)
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


@doctor.command()
@click.option("--dry-run", is_flag=True, help="Show what would be done without doing it")
@click.option(
    "--no-prune",
    is_flag=True,
    help="Skip automatic pruning even if thresholds exceeded",
)
@click.option("--no-timeout-adjust", is_flag=True, help="Skip automatic timeout adjustment")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def autotune(
    ctx: click.Context,
    dry_run: bool,
    no_prune: bool,
    no_timeout_adjust: bool,
    verbose: bool,
    project_root: str | None,
) -> None:
    """
    🎛️ Auto-tune database performance and maintenance.

    Automatically adjusts performance parameters and triggers maintenance
    operations based on database size and usage patterns.

    Actions taken:
    - Adjusts query timeouts based on database size
    - Triggers automatic pruning if memory count exceeds thresholds
    - Reports warnings for large databases

    Thresholds:
    - 50k memories: Warning
    - 100k memories: Auto-prune (intelligent strategy)
    - 250k memories: Auto-prune (aggressive strategy)
    - 500k memories: Emergency prune

    \b
    🎯 EXAMPLES:
      # Run auto-tuning
      kuzu-memory doctor autotune

      # Preview what would be done
      kuzu-memory doctor autotune --dry-run

      # Only adjust timeouts, no pruning
      kuzu-memory doctor autotune --no-prune
    """
    from ..core.memory import KuzuMemory
    from ..services.autotune_service import AutoTuneService
    from ..utils.project_setup import find_project_root, get_project_db_path

    try:
        # Determine project root
        if project_root:
            project_path = Path(project_root)
        else:
            found_root = find_project_root()
            project_path = found_root if found_root else Path.cwd()

        db_path = get_project_db_path(project_path)

        if not db_path.exists():
            rich_print("❌ Project not initialized. Run 'kuzu-memory init' first.", style="red")
            sys.exit(1)

        rich_print("🎛️ [bold cyan]Running Auto-Tune...[/bold cyan]\n")
        rich_print(f"Project: {project_path}", style="dim")
        rich_print(f"Database: {db_path}\n", style="dim")

        # Initialize memory and run auto-tune
        memory = KuzuMemory(db_path=db_path)

        try:
            service = AutoTuneService(memory)
            result = service.run(
                auto_prune=not no_prune,
                auto_adjust_timeout=not no_timeout_adjust,
                dry_run=dry_run,
            )

            # Display results
            if result.success:
                rich_print("📊 Database Stats:", style="cyan")
                rich_print(f"   Memories: {result.memory_count:,}", style="white")
                rich_print(f"   Size: {result.db_size_mb:.1f} MB", style="white")
                rich_print(
                    f"   Execution time: {result.execution_time_ms:.1f}ms\n",
                    style="dim",
                )

                if result.warnings:
                    rich_print("⚠️  Warnings:", style="yellow")
                    for warning in result.warnings:
                        rich_print(f"   • {warning}", style="yellow")
                    rich_print("")

                if result.actions_taken:
                    action_label = "Actions (dry-run):" if dry_run else "Actions Taken:"
                    rich_print(f"🔧 {action_label}", style="green" if not dry_run else "blue")
                    for action in result.actions_taken:
                        rich_print(f"   • {action}", style="green" if not dry_run else "blue")
                    rich_print("")

                if result.new_timeout_ms:
                    rich_print(
                        f"⏱️  New query timeout: {result.new_timeout_ms}ms",
                        style="cyan",
                    )

                if result.pruned_count > 0:
                    rich_print(
                        f"🗑️  Pruned: {result.pruned_count:,} memories",
                        style="green",
                    )

                if not result.warnings and not result.actions_taken:
                    rich_print("✅ Database is healthy, no tuning needed.", style="green")
                else:
                    rich_print("\n✅ Auto-tune complete.", style="green")

            else:
                rich_print("❌ Auto-tune failed", style="red")
                for action in result.actions_taken:
                    if "Error" in action:
                        rich_print(f"   {action}", style="red")
                sys.exit(1)

        finally:
            memory.close()

    except Exception as e:
        rich_print(f"❌ Auto-tune error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


__all__ = ["doctor"]
