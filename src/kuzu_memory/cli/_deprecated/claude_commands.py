"""
CLI commands for Claude Code integration.

Provides commands to install, configure, and manage Claude Code hooks
for seamless KuzuMemory integration.
"""

import json
import sys
from pathlib import Path

import click

from ..installers.claude_hooks import ClaudeHooksInstaller
from ..utils.project_setup import find_project_root
from .cli_utils import RICH_AVAILABLE, console, rich_confirm, rich_panel, rich_print


@click.group(name="claude")
@click.pass_context
def claude_group(ctx: click.Context) -> None:
    """
    🤖 Claude Code integration commands.

    Manage Claude Desktop and Claude Code integration with KuzuMemory.
    """
    pass


@claude_group.command(name="install")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.option("--force", is_flag=True, help="Force installation even if already installed")
@click.option("--no-test", is_flag=True, help="Skip installation testing")
@click.pass_context
def install_claude_hooks(
    ctx: click.Context, project_root: str | None, force: bool, no_test: bool
) -> None:
    """
    [DEPRECATED] Install Claude Code hooks for KuzuMemory integration.

    ⚠️  DEPRECATION WARNING: This command is deprecated.
    Please use: kuzu-memory install claude-code

    This command sets up:
    • MCP server configuration for Claude Desktop
    • Project-specific CLAUDE.md file
    • Shell script wrappers for compatibility
    • Automatic memory enhancement hooks

    \b
    Example:
      kuzu-memory install claude-code
      kuzu-memory install claude-code --project-root /path/to/project
    """
    try:
        # Show deprecation warning
        rich_panel(
            "⚠️  DEPRECATION WARNING\n\n"
            "The 'kuzu-memory claude install' command is deprecated.\n"
            "Please use: kuzu-memory install claude-code\n\n"
            "Continuing with installation for now...",
            title="Deprecated Command",
            style="yellow",
        )
        # Determine project root
        if project_root:
            project_root = Path(project_root).resolve()
        else:
            project_root = find_project_root()

        rich_print(f"📁 Project: {project_root}")

        # Initialize installer
        installer = ClaudeHooksInstaller(project_root)

        # Check current status
        status = installer.status()
        if status["installed"] and not force:
            rich_panel(
                "Claude hooks are already installed! ✅\n\n"
                "Use --force to reinstall or 'kuzu-memory claude status' to check status.",
                title="Already Installed",
                style="yellow",
            )
            return

        # Check prerequisites
        rich_print("\n🔍 Checking prerequisites...")
        errors = installer.check_prerequisites()
        if errors:
            rich_panel(
                "Prerequisites not met:\n" + "\n".join(f"• {e}" for e in errors),
                title="❌ Prerequisites Failed",
                style="red",
            )
            sys.exit(1)

        rich_print("✅ Prerequisites checked")

        # Confirm installation
        if not force:
            rich_panel(
                "This will install Claude Code hooks for KuzuMemory.\n\n"
                "Files to be created/modified:\n"
                "• CLAUDE.md - Project context file\n"
                "• .claude-mpm/config.json - MPM configuration\n"
                "• .claude/kuzu-memory-mcp.json - MCP server config\n"
                + (
                    "• Claude Desktop config (if detected)"
                    if status["claude_desktop_detected"]
                    else ""
                ),
                title="Installation Preview",
                style="blue",
            )

            if not rich_confirm("Proceed with installation?", default=True):
                rich_print("Installation cancelled.")
                return

        # Perform installation
        rich_print("\n🚀 Installing Claude hooks...")
        # Use context manager only when Rich is available
        if RICH_AVAILABLE and console:
            with console.status("[bold green]Installing..."):
                result = installer.install()
        else:
            result = installer.install()

        # Display results
        if result.success:
            rich_panel(
                f"Claude Code hooks installed successfully! 🎉\n\n"
                f"Files created: {len(result.files_created)}\n"
                f"Files modified: {len(result.files_modified)}\n"
                + (
                    "\nWarnings:\n" + "\n".join(f"• {w}" for w in result.warnings)
                    if result.warnings
                    else ""
                ),
                title="✅ Installation Complete",
                style="green",
            )

            # Show next steps
            rich_panel(
                "Next steps:\n\n"
                "1. Restart Claude Desktop (if running)\n"
                "2. Open this project in Claude\n"
                "3. KuzuMemory will automatically enhance your interactions!\n\n"
                "Test with: kuzu-memory claude test",
                title="🎯 Getting Started",
                style="blue",
            )
        else:
            rich_panel(
                f"Installation failed: {result.message}",
                title="❌ Installation Failed",
                style="red",
            )
            sys.exit(1)

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Error: {e}", style="red")
        sys.exit(1)


@claude_group.command(name="uninstall")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.option("--force", is_flag=True, help="Force uninstall without confirmation")
@click.pass_context
def uninstall_claude_hooks(ctx: click.Context, project_root: str | None, force: bool) -> None:
    """
    [DEPRECATED] Uninstall Claude Code hooks.

    ⚠️  DEPRECATION WARNING: This command is deprecated.
    Please use: kuzu-memory uninstall claude-code

    Removes all Claude integration files and configurations.
    """
    try:
        # Show deprecation warning
        rich_panel(
            "⚠️  DEPRECATION WARNING\n\n"
            "The 'kuzu-memory claude uninstall' command is deprecated.\n"
            "Please use: kuzu-memory uninstall claude-code\n\n"
            "Continuing with uninstallation for now...",
            title="Deprecated Command",
            style="yellow",
        )
        # Determine project root
        if project_root:
            project_root = Path(project_root).resolve()
        else:
            project_root = find_project_root()

        rich_print(f"📁 Project: {project_root}")

        # Initialize installer
        installer = ClaudeHooksInstaller(project_root)

        # Check current status
        status = installer.status()
        if not status["installed"]:
            rich_print("Claude hooks are not installed.")
            return

        # Confirm uninstallation
        if not force:
            if not rich_confirm("Are you sure you want to uninstall Claude hooks?", default=False):
                rich_print("Uninstallation cancelled.")
                return

        # Perform uninstallation
        rich_print("\n🔧 Uninstalling Claude hooks...")
        result = installer.uninstall()

        if result.success:
            rich_panel(
                "Claude Code hooks uninstalled successfully.",
                title="✅ Uninstalled",
                style="green",
            )
        else:
            rich_panel(
                f"Uninstallation failed: {result.message}",
                title="❌ Failed",
                style="red",
            )
            sys.exit(1)

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Error: {e}", style="red")
        sys.exit(1)


@claude_group.command(name="status")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def claude_status(ctx: click.Context, project_root: str | None, output_json: bool) -> None:
    """
    [DEPRECATED] Check Claude Code hooks installation status.

    ⚠️  DEPRECATION WARNING: This command is deprecated.
    Please use: kuzu-memory status

    Shows the current state of Claude integration.
    """
    try:
        # Show deprecation warning (unless json output)
        if not output_json:
            rich_panel(
                "⚠️  DEPRECATION WARNING\n\n"
                "The 'kuzu-memory claude status' command is deprecated.\n"
                "Please use: kuzu-memory status\n\n"
                "Showing status for now...",
                title="Deprecated Command",
                style="yellow",
            )
        # Determine project root
        if project_root:
            project_root_path: Path = Path(project_root).resolve()
        else:
            found_root = find_project_root()
            if not found_root:
                rich_print("❌ Could not find project root", style="red")
                sys.exit(1)
            project_root_path = found_root

        # Initialize installer
        installer = ClaudeHooksInstaller(project_root_path)
        status = installer.status()

        if output_json:
            print(json.dumps(status, indent=2, default=str))
        else:
            # Format status for display
            status_text = []

            if status["installed"]:
                status_text.append("✅ Claude hooks installed")
            else:
                status_text.append("❌ Claude hooks not installed")

            if status["claude_desktop_detected"]:
                status_text.append("✅ Claude Desktop detected")
            else:
                status_text.append("⚠️  Claude Desktop not detected")

            if status["mcp_configured"]:
                status_text.append("✅ MCP server configured")

            if status["kuzu_initialized"]:
                status_text.append("✅ KuzuMemory initialized")
            else:
                status_text.append("❌ KuzuMemory not initialized")

            # File status
            status_text.append("\nFiles:")
            for file, exists in status["files"].items():
                icon = "✅" if exists else "❌"
                status_text.append(f"  {icon} {file}")

            rich_panel(
                "\n".join(status_text),
                title=f"Claude Integration Status - {project_root_path.name}",
                style="blue",
            )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Error: {e}", style="red")
        sys.exit(1)


@claude_group.command(name="test")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def test_claude_integration(ctx: click.Context, project_root: str | None) -> None:
    """
    Test Claude Code integration.

    Verifies that the integration is working correctly.
    """
    try:
        import subprocess

        # Determine project root
        if project_root:
            project_root = Path(project_root).resolve()
        else:
            project_root = find_project_root()

        rich_print(f"🧪 Testing Claude integration for: {project_root}")

        # Initialize installer for status check
        installer = ClaudeHooksInstaller(project_root)
        status = installer.status()

        tests = []

        # Test 1: Installation status
        if status["installed"]:
            tests.append(("Installation", True, "Claude hooks are installed"))
        else:
            tests.append(("Installation", False, "Claude hooks not installed"))

        # Test 2: KuzuMemory CLI
        try:
            result = subprocess.run(
                ["kuzu-memory", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                tests.append(("KuzuMemory CLI", True, f"Version: {result.stdout.strip()}"))
            else:
                tests.append(("KuzuMemory CLI", False, "CLI command failed"))
        except Exception as e:
            tests.append(("KuzuMemory CLI", False, str(e)))

        # Test 3: Database initialization
        if status["kuzu_initialized"]:
            tests.append(("Database", True, "KuzuMemory database initialized"))
        else:
            tests.append(("Database", False, "Database not initialized"))

        # Test 4: MCP server module
        try:
            from ..integrations import mcp_server  # noqa: F401

            tests.append(("MCP Server Module", True, "Module available"))
        except ImportError:
            tests.append(("MCP Server Module", False, "Module not found"))

        # Test 5: Test enhance command
        if status["kuzu_initialized"]:
            try:
                result = subprocess.run(
                    ["kuzu-memory", "enhance", "test prompt", "--format", "plain"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    tests.append(("Enhance Command", True, "Working"))
                else:
                    tests.append(("Enhance Command", False, result.stderr.strip()))
            except Exception as e:
                tests.append(("Enhance Command", False, str(e)))

        # Display results
        all_passed = all(passed for _, passed, _ in tests)

        test_results = []
        for name, passed, message in tests:
            icon = "✅" if passed else "❌"
            test_results.append(f"{icon} {name}: {message}")

        if all_passed:
            rich_panel(
                "\n".join(test_results) + "\n\n🎉 All tests passed!",
                title="Test Results",
                style="green",
            )
        else:
            rich_panel(
                "\n".join(test_results) + "\n\n⚠️  Some tests failed",
                title="Test Results",
                style="yellow",
            )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Error: {e}", style="red")
        sys.exit(1)


@claude_group.command(name="mcp-server")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.pass_context
def run_mcp_server(ctx: click.Context, project_root: str | None) -> None:
    """
    [DEPRECATED] Run the MCP server for Claude Desktop integration.

    ⚠️  DEPRECATION WARNING: This command is deprecated.
    Please use: kuzu-memory mcp serve

    This is typically called by Claude Desktop, not manually.
    """
    try:
        # Note: No visible warning here since this is typically called by Claude Desktop
        # and we don't want to pollute its logs
        import asyncio

        from ..integrations.mcp_server import MCP_AVAILABLE, main

        if not MCP_AVAILABLE:
            rich_print("❌ MCP SDK not installed. Install with: pip install mcp", style="red")
            sys.exit(1)

        # Set project root in environment if specified
        if project_root:
            import os

            os.environ["KUZU_MEMORY_PROJECT"] = str(Path(project_root).resolve())

        # Run the MCP server
        asyncio.run(main())

    except KeyboardInterrupt:
        rich_print("\nServer stopped.")
    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Error: {e}", style="red")
        sys.exit(1)


# Add wizard command for interactive setup
@claude_group.command(name="wizard")
@click.pass_context
def claude_wizard(ctx: click.Context) -> None:
    """
    🧙 Interactive setup wizard for Claude integration.

    Walks you through the complete setup process.
    """
    try:
        from .cli_utils import rich_prompt

        rich_panel(
            "Welcome to the Claude Integration Wizard! 🧙✨\n\n"
            "This wizard will help you set up KuzuMemory with Claude Desktop.\n"
            "Let's get started!",
            title="Claude Integration Wizard",
            style="magenta",
        )

        # Step 1: Find project
        rich_print("\n📁 Step 1: Project Selection")
        project_root = find_project_root()
        rich_print(f"Found project: {project_root}")

        if not rich_confirm("Is this the correct project?", default=True):
            custom_path = rich_prompt("Enter project path")
            project_root = Path(custom_path).resolve()

        # Step 2: Check prerequisites
        rich_print("\n🔍 Step 2: Checking Prerequisites")
        installer = ClaudeHooksInstaller(project_root)
        errors = installer.check_prerequisites()

        if errors:
            rich_print("⚠️  Some prerequisites are missing:", style="yellow")
            for error in errors:
                rich_print(f"  • {error}")

            if not rich_confirm("Continue anyway?", default=False):
                rich_print("Wizard cancelled.")
                return
        else:
            rich_print("✅ All prerequisites met!")

        # Step 3: Check Claude Desktop
        rich_print("\n🖥️  Step 3: Claude Desktop Detection")
        status = installer.status()

        if status["claude_desktop_detected"]:
            rich_print("✅ Claude Desktop detected!")
            rich_print("   Global MCP configuration will be updated")
        else:
            rich_print("⚠️  Claude Desktop not detected")
            rich_print("   Local configuration will be created for future use")

        # Step 4: Initialize KuzuMemory if needed
        if not status["kuzu_initialized"]:
            rich_print("\n🧠 Step 4: Initialize KuzuMemory")
            if rich_confirm("KuzuMemory not initialized. Initialize now?", default=True):
                import subprocess

                subprocess.run(["kuzu-memory", "init"], cwd=project_root)
                rich_print("✅ KuzuMemory initialized!")
        else:
            rich_print("\n✅ KuzuMemory already initialized")

        # Step 5: Install hooks
        rich_print("\n🚀 Step 5: Installing Claude Hooks")
        if rich_confirm("Ready to install Claude hooks?", default=True):
            # Use context manager only when Rich is available
            if RICH_AVAILABLE and console:
                with console.status("[bold green]Installing..."):
                    result = installer.install()
            else:
                result = installer.install()

            if result.success:
                rich_panel(
                    "Installation complete! 🎉\n\n"
                    "Claude Code integration is now active.\n"
                    "Restart Claude Desktop to activate the changes.",
                    title="✅ Success",
                    style="green",
                )

                # Step 6: Test
                if rich_confirm("\n🧪 Would you like to test the integration?", default=True):
                    ctx.invoke(test_claude_integration)
            else:
                rich_print(f"❌ Installation failed: {result.message}", style="red")
        else:
            rich_print("Wizard cancelled.")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Error: {e}", style="red")
        sys.exit(1)
