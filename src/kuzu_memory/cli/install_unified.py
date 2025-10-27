"""
Unified install/uninstall commands for KuzuMemory.

ONE way to do ANYTHING - single installation path for all integrations.
"""

import sys
from pathlib import Path

import click

from ..installers.registry import get_installer
from ..utils.project_setup import find_project_root
from .cli_utils import rich_panel, rich_print

# Available integrations (simplified names)
AVAILABLE_INTEGRATIONS = [
    "claude-code",
    "claude-desktop",
    "cursor",
    "vscode",
    "windsurf",
    "auggie",
]


@click.command(name="install")
@click.argument("integration", type=click.Choice(AVAILABLE_INTEGRATIONS))
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.option("--force", is_flag=True, help="Force reinstall")
@click.option("--dry-run", is_flag=True, help="Preview changes without installing")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def install_command(
    integration: str,
    project_root: str | None,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """
    Install kuzu-memory integration.

    Installs the right components for each platform automatically:
      • claude-code: MCP server + hooks (complete integration)
      • claude-desktop: MCP server only
      • cursor: MCP server only
      • vscode: MCP server only
      • windsurf: MCP server only
      • auggie: Rules integration

    \b
    Examples:
        kuzu-memory install claude-code
        kuzu-memory install claude-desktop
        kuzu-memory install cursor --dry-run
        kuzu-memory install vscode --verbose
    """
    try:
        # Determine project root
        if project_root:
            root = Path(project_root).resolve()
        else:
            try:
                root = find_project_root()
            except Exception:
                root = Path.cwd()

        # Show installation header
        rich_panel(
            f"Installing KuzuMemory for {integration}\n"
            f"Project: {root}\n"
            f"{'DRY RUN MODE - No changes will be made' if dry_run else 'Installing...'}",
            title="🚀 Installation",
            style="cyan",
        )

        # Get installer from registry
        installer = get_installer(integration, root)
        if not installer:
            rich_print(f"❌ No installer found for: {integration}", style="red")
            rich_print("\n💡 Available integrations:", style="yellow")
            for name in AVAILABLE_INTEGRATIONS:
                rich_print(f"  • {name}")
            sys.exit(1)

        # Show what will be installed
        if verbose:
            rich_print(f"\n📋 Installer: {installer.__class__.__name__}")
            rich_print(f"📝 Description: {installer.description}")

        # Perform installation
        result = installer.install(dry_run=dry_run, verbose=verbose)

        # Show results
        if result.success:
            rich_panel(result.message, title="✅ Installation Complete", style="green")

            # Show created files
            if result.files_created:
                rich_print("\n📄 Files created:")
                for file_path in result.files_created:
                    rich_print(f"  • {file_path}", style="green")

            # Show modified files
            if result.files_modified:
                rich_print("\n📝 Files modified:")
                for file_path in result.files_modified:
                    rich_print(f"  • {file_path}", style="yellow")

            # Show warnings
            if result.warnings:
                rich_print("\n⚠️  Warnings:", style="yellow")
                for warning in result.warnings:
                    rich_print(f"  • {warning}", style="yellow")

            # Show next steps based on integration
            rich_print("\n🎯 Next Steps:", style="cyan")
            if integration == "claude-code":
                rich_print("1. Reload Claude Code window or restart")
                rich_print("2. MCP tools + hooks active for enhanced context")
                rich_print("3. Check .claude/config.local.json for configuration")
            elif integration == "claude-desktop":
                rich_print("1. Restart Claude Desktop application")
                rich_print("2. Open a new conversation")
                rich_print("3. KuzuMemory MCP tools will be available")
            elif integration in ["cursor", "vscode", "windsurf"]:
                rich_print(f"1. Reload or restart {installer.ai_system_name}")
                rich_print("2. KuzuMemory MCP server will be active")
                rich_print("3. Check the configuration file for details")
            elif integration == "auggie":
                rich_print("1. Open or reload your Auggie workspace")
                rich_print("2. Rules will be active for enhanced context")
                rich_print("3. Check AGENTS.md and .augment/rules/ for configuration")
        else:
            rich_print(f"\n❌ {result.message}", style="red")
            if result.warnings:
                for warning in result.warnings:
                    rich_print(f"  • {warning}", style="yellow")
            sys.exit(1)

    except Exception as e:
        rich_print(f"❌ Installation failed: {e}", style="red")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@click.command(name="uninstall")
@click.argument("integration", type=click.Choice(AVAILABLE_INTEGRATIONS))
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.option("--verbose", is_flag=True, help="Show detailed output")
def uninstall_command(
    integration: str,
    project_root: str | None,
    verbose: bool,
) -> None:
    """
    Uninstall kuzu-memory integration.

    Removes integration files and configuration for the specified platform.

    \b
    Examples:
        kuzu-memory uninstall claude-code
        kuzu-memory uninstall claude-desktop
        kuzu-memory uninstall cursor --verbose
    """
    try:
        # Determine project root
        if project_root:
            root = Path(project_root).resolve()
        else:
            try:
                root = find_project_root()
            except Exception:
                root = Path.cwd()

        # Get installer from registry
        installer = get_installer(integration, root)
        if not installer:
            rich_print(f"❌ No installer found for: {integration}", style="red")
            sys.exit(1)

        # Check if installed
        status = installer.get_status()
        if not status.get("installed", False):
            rich_print(f"Note: {integration} is not currently installed.", style="blue")
            sys.exit(0)

        # Show uninstallation header
        rich_panel(
            f"Uninstalling KuzuMemory for {integration}\nProject: {root}",
            title="🗑️  Uninstallation",
            style="yellow",
        )

        # Confirm
        if not click.confirm("Continue with uninstallation?", default=True):
            rich_print("Uninstallation cancelled.", style="yellow")
            sys.exit(0)

        # Perform uninstallation
        result = installer.uninstall(verbose=verbose)

        # Show results
        if result.success:
            rich_panel(
                result.message, title="✅ Uninstallation Complete", style="green"
            )
        else:
            rich_print(f"❌ {result.message}", style="red")
            if result.warnings:
                for warning in result.warnings:
                    rich_print(f"  • {warning}", style="yellow")
            sys.exit(1)

    except Exception as e:
        rich_print(f"❌ Uninstallation failed: {e}", style="red")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@click.command(name="remove", hidden=True)
@click.argument("integration", type=click.Choice(AVAILABLE_INTEGRATIONS))
@click.option(
    "--project-root", type=click.Path(exists=True), help="Project root directory"
)
@click.option("--verbose", is_flag=True, help="Show detailed output")
def remove_command(
    integration: str,
    project_root: str | None,
    verbose: bool,
) -> None:
    """Alias for uninstall command."""
    ctx = click.get_current_context()
    ctx.invoke(
        uninstall_command,
        integration=integration,
        project_root=project_root,
        verbose=verbose,
    )


__all__ = ["install_command", "remove_command", "uninstall_command"]
