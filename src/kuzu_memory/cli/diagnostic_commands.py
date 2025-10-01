"""
MCP Diagnostic CLI Commands.

Command-line interface for MCP server diagnostics, troubleshooting,
and health checks.
"""

import asyncio
import json
import sys
from pathlib import Path

import click

from ..mcp.testing.diagnostics import MCPDiagnostics
from .cli_utils import rich_panel, rich_print


@click.group()
def diagnose():
    """
    🔍 MCP diagnostic and troubleshooting commands.

    Run comprehensive diagnostics to identify and fix issues with
    MCP server configuration, connectivity, and functionality.
    """
    pass


@diagnose.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output with detailed information",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Save report to file (supports .txt, .json, .html)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json", "html"], case_sensitive=False),
    default="text",
    help="Output format (default: text)",
)
@click.option(
    "--fix",
    is_flag=True,
    help="Attempt to automatically fix detected issues",
)
@click.option(
    "--project-root",
    type=click.Path(exists=True),
    help="Project root directory",
)
@click.pass_context
def run(
    ctx,
    verbose: bool,
    output: str | None,
    format: str,
    fix: bool,
    project_root: str | None,
):
    """
    Run full MCP diagnostics suite.

    Performs comprehensive checks on configuration, connection,
    tool discovery, and performance. Optionally attempts to fix
    issues automatically.

    Examples:
        # Run full diagnostics
        kuzu-memory mcp diagnose run

        # Run with auto-fix
        kuzu-memory mcp diagnose run --fix

        # Save report to file
        kuzu-memory mcp diagnose run --output report.html --format html

        # Verbose output with JSON export
        kuzu-memory mcp diagnose run -v --output report.json --format json
    """
    try:
        rich_print("🔍 Running MCP diagnostics...", style="blue")

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

        # Exit with appropriate code
        if report.has_critical_errors:
            rich_print(
                "\n❌ Critical errors detected. See report for details.",
                style="red",
            )
            sys.exit(1)
        elif report.failed > 0:
            rich_print(
                f"\n⚠️  {report.failed} checks failed. See report for details.",
                style="yellow",
            )
            sys.exit(1)
        else:
            rich_print(
                "\n✅ All diagnostics passed successfully!",
                style="green",
            )
            sys.exit(0)

    except KeyboardInterrupt:
        rich_print("\n🛑 Diagnostics cancelled", style="yellow")
        sys.exit(1)
    except Exception as e:
        rich_print(f"❌ Diagnostic error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


@diagnose.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
@click.option(
    "--fix",
    is_flag=True,
    help="Attempt to automatically fix configuration issues",
)
@click.pass_context
def config(ctx, verbose: bool, output: str | None, fix: bool):
    """
    Check MCP configuration validity.

    Validates Claude Desktop configuration, environment variables,
    and database directory settings.

    Examples:
        # Check configuration
        kuzu-memory mcp diagnose config

        # Check and auto-fix issues
        kuzu-memory mcp diagnose config --fix

        # Verbose output with JSON export
        kuzu-memory mcp diagnose config -v --output config-check.json
    """
    try:
        rich_print("🔍 Checking MCP configuration...", style="blue")

        diagnostics = MCPDiagnostics(verbose=verbose)

        # Run configuration checks
        results = asyncio.run(diagnostics.check_configuration())

        # Auto-fix if requested and there are failures
        if fix and any(not r.success for r in results):
            rich_print("\n🔧 Attempting auto-fix...", style="yellow")
            fix_result = asyncio.run(diagnostics.auto_fix_configuration())
            results.append(fix_result)

            if fix_result.success:
                # Re-run checks
                rich_print("✅ Auto-fix completed. Re-checking...", style="green")
                results = asyncio.run(diagnostics.check_configuration())

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
                rich_print(f"   Duration: {result.duration_ms:.2f}ms", style="dim")

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_data = {
                "check_type": "configuration",
                "passed": passed,
                "total": total,
                "results": [r.to_dict() for r in results],
            }
            output_path.write_text(json.dumps(output_data, indent=2))
            rich_print(f"\n✅ Results saved to: {output_path}", style="green")

        # Summary
        rich_panel(
            f"Configuration Check: {passed}/{total} passed",
            title=(
                "✅ Configuration Valid"
                if passed == total
                else "⚠️  Configuration Issues"
            ),
            style="green" if passed == total else "yellow",
        )

        sys.exit(0 if passed == total else 1)

    except Exception as e:
        rich_print(f"❌ Configuration check error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)


@diagnose.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
@click.option(
    "--project-root",
    type=click.Path(exists=True),
    help="Project root directory",
)
@click.pass_context
def connection(ctx, verbose: bool, output: str | None, project_root: str | None):
    """
    Test MCP server connection and protocol.

    Validates server startup, stdio communication, protocol initialization,
    and JSON-RPC compliance.

    Examples:
        # Test connection
        kuzu-memory mcp diagnose connection

        # Verbose output with specific project
        kuzu-memory mcp diagnose connection -v --project-root /path/to/project

        # Save results to JSON
        kuzu-memory mcp diagnose connection --output connection-test.json
    """
    try:
        rich_print("🔍 Testing MCP server connection...", style="blue")

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


@diagnose.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
@click.option(
    "--project-root",
    type=click.Path(exists=True),
    help="Project root directory",
)
@click.pass_context
def tools(ctx, verbose: bool, output: str | None, project_root: str | None):
    """
    Test MCP tool discovery and execution.

    Discovers all available MCP tools and tests their execution
    with sample parameters.

    Examples:
        # Test tools
        kuzu-memory mcp diagnose tools

        # Verbose output
        kuzu-memory mcp diagnose tools -v

        # Save results to JSON
        kuzu-memory mcp diagnose tools --output tools-test.json
    """
    try:
        rich_print("🔍 Testing MCP tools...", style="blue")

        project_path = Path(project_root) if project_root else Path.cwd()
        diagnostics = MCPDiagnostics(project_root=project_path, verbose=verbose)

        # Run tool checks
        results = asyncio.run(diagnostics.check_tools())

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
                if result.metadata:
                    rich_print(f"   Metadata: {result.metadata}", style="dim")
                rich_print(f"   Duration: {result.duration_ms:.2f}ms", style="dim")

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_data = {
                "check_type": "tools",
                "passed": passed,
                "total": total,
                "results": [r.to_dict() for r in results],
            }
            output_path.write_text(json.dumps(output_data, indent=2))
            rich_print(f"\n✅ Results saved to: {output_path}", style="green")

        # Summary
        rich_panel(
            f"Tools Test: {passed}/{total} passed",
            title=("✅ All Tools Working" if passed == total else "⚠️  Tool Issues"),
            style="green" if passed == total else "yellow",
        )

        sys.exit(0 if passed == total else 1)

    except Exception as e:
        rich_print(f"❌ Tools test error: {e}", style="red")
        if ctx.obj.get("debug") or verbose:
            raise
        sys.exit(1)
