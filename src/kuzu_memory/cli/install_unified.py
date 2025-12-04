"""
Unified install/uninstall commands for KuzuMemory.

ONE way to do ANYTHING - single installation path for all integrations.
"""

import sys
from pathlib import Path

import click

from ..installers.base import InstalledSystem
from ..installers.json_utils import (
    fix_broken_mcp_args,
    load_json_config,
    save_json_config,
)
from ..installers.registry import get_installer
from ..utils.project_setup import find_project_root
from .cli_utils import rich_panel, rich_print

# Available integrations (simplified names)
# NOTE: claude-desktop removed - focus on coding tools only (Claude Code, VS Code, Cursor, etc.)
AVAILABLE_INTEGRATIONS = [
    "claude-code",
    "codex",
    "cursor",
    "vscode",
    "windsurf",
    "auggie",
    "auggie-mcp",
]


def _repair_all_mcp_configs() -> tuple[int, list[str]]:
    """
    Scan and repair broken MCP configurations across all projects.

    Checks ~/.claude.json and fixes any broken ["mcp", "serve"] args.

    Returns:
        Tuple of (num_fixes, list_of_fix_messages)
    """
    global_config_path = Path.home() / ".claude.json"

    if not global_config_path.exists():
        return 0, []

    try:
        # Load global config
        config = load_json_config(global_config_path)

        # Fix broken args
        fixed_config, fixes = fix_broken_mcp_args(config)

        # Save if fixes were applied
        if fixes:
            save_json_config(global_config_path, fixed_config)
            return len(fixes), fixes

        return 0, []

    except Exception as e:
        return 0, [f"Failed to repair MCP configs: {e}"]


def _detect_installed_systems(project_root: Path) -> list[InstalledSystem]:
    """
    Detect which AI systems are installed in the project.

    Checks for installation markers for each supported integration.

    Args:
        project_root: Project root directory

    Returns:
        List of detected installed systems
    """
    installed_systems = []

    # Check each integration
    for integration_name in AVAILABLE_INTEGRATIONS:
        try:
            installer = get_installer(integration_name, project_root)
            if installer:
                detected = installer.detect_installation()
                if detected.is_installed:
                    installed_systems.append(detected)
        except Exception:
            # Skip integrations that fail detection
            continue

    return installed_systems


def _show_detection_menu(installed_systems: list[InstalledSystem]) -> str | None:
    """
    Auto-select detected system for repair/reinstall.

    Args:
        installed_systems: List of detected systems

    Returns:
        Selected integration name or None if no systems detected
    """
    if not installed_systems:
        rich_print("No installed systems detected in this project.", style="yellow")
        rich_print("\n💡 Available integrations:", style="cyan")
        for name in AVAILABLE_INTEGRATIONS:
            rich_print(f"  • {name}")
        rich_print("\nRun: kuzu-memory install <integration>", style="dim")
        return None

    # Show detected systems
    rich_panel(
        f"Detected {len(installed_systems)} installed system(s)",
        title="🔍 Detection Results",
        style="cyan",
    )

    for i, system in enumerate(installed_systems, 1):
        # Status icon
        if system.health_status == "healthy":
            status_icon = "✅"
            status_color = "green"
        elif system.health_status == "needs_repair":
            status_icon = "⚠️"
            status_color = "yellow"
        else:
            status_icon = "❌"
            status_color = "red"

        # MCP status
        mcp_status = "MCP configured" if system.has_mcp else "MCP not configured"

        rich_print(
            f"\n{i}. {status_icon} {system.name} ({system.health_status})",
            style=status_color,
        )
        rich_print(f"   Files: {len(system.files_present)}/{system.details['total_files']}")
        rich_print(f"   {mcp_status}")

    # Auto-select first detected system for repair/reinstall
    selected_system = installed_systems[0].name

    if len(installed_systems) == 1:
        rich_print(f"\n🔄 Auto-selected: {selected_system} (reinstall/repair)", style="cyan")
    else:
        rich_print(
            f"\n🔄 Auto-selected: {selected_system} (first detected system)",
            style="cyan",
        )
        rich_print(
            "   💡 To install a specific system, use: kuzu-memory install <integration>",
            style="dim",
        )

    return selected_system


@click.command(name="install")
@click.argument("integration", type=click.Choice(AVAILABLE_INTEGRATIONS), required=False)
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.option("--force", is_flag=True, help="Force reinstall")
@click.option("--dry-run", is_flag=True, help="Preview changes without installing")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def install_command(
    integration: str | None,
    project_root: str | None,
    force: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """
    Install kuzu-memory integration for coding tools.

    If no integration is specified, auto-detects installed systems and offers to repair/reinstall.

    Installs the right components for each platform automatically:
      • claude-code: MCP server + hooks (complete integration)
      • cursor: MCP server only
      • vscode: MCP server only
      • windsurf: MCP server only
      • codex: MCP server only
      • auggie: Rules integration
      • auggie-mcp: MCP server integration (global)

    NOTE: claude-desktop is no longer supported. Use claude-code instead for Claude AI coding.

    \b
    Examples:
        kuzu-memory install                    # Auto-detect and repair
        kuzu-memory install claude-code        # Recommended for Claude AI
        kuzu-memory install cursor --dry-run
        kuzu-memory install vscode --verbose
        kuzu-memory install auggie-mcp
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

        # Auto-detect if no integration specified
        if integration is None:
            rich_panel(
                f"Detecting installed systems in {root.name}...",
                title="🔍 Auto-Detection",
                style="cyan",
            )

            detected_systems = _detect_installed_systems(root)
            integration = _show_detection_menu(detected_systems)

            if integration is None:
                rich_print("\nInstallation cancelled.", style="yellow")
                sys.exit(0)

            rich_print(f"\n✓ Selected: {integration}", style="green")

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

            # Post-install: Auto-repair broken MCP configurations across all projects
            if not dry_run:
                num_fixes, fix_messages = _repair_all_mcp_configs()
                if num_fixes > 0:
                    rich_print(
                        f"\n🔧 Auto-repaired {num_fixes} broken MCP configuration(s) in other projects",
                        style="cyan",
                    )
                    if verbose:
                        for msg in fix_messages:
                            rich_print(f"  • {msg}", style="dim")

            # Show next steps based on integration
            rich_print("\n🎯 Next Steps:", style="cyan")
            if integration == "claude-code":
                rich_print("1. Reload Claude Code window or restart")
                rich_print("2. MCP tools + hooks active for enhanced context")
                rich_print("3. Check .claude/settings.local.json for configuration")
            elif integration in ["cursor", "vscode", "windsurf"]:
                rich_print(f"1. Reload or restart {installer.ai_system_name}")
                rich_print("2. KuzuMemory MCP server will be active")
                rich_print("3. Check the configuration file for details")
            elif integration == "auggie":
                rich_print("1. Open or reload your Auggie workspace")
                rich_print("2. Rules will be active for enhanced context")
                rich_print("3. Check AGENTS.md and .augment/rules/ for configuration")
            elif integration == "auggie-mcp":
                rich_print("1. Restart Auggie application")
                rich_print("2. KuzuMemory MCP tools will be available")
                rich_print("3. Configuration: ~/.augment/settings.json")
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
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
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
            rich_panel(result.message, title="✅ Uninstallation Complete", style="green")
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
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
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


@click.command(name="repair")
@click.option("--project-root", type=click.Path(exists=True), help="Project root directory")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def repair_command(
    project_root: str | None,
    verbose: bool,
) -> None:
    """
    Repair broken MCP configurations across all detected frameworks.

    Scans for installed systems and fixes broken ["mcp", "serve"] args to ["mcp"].
    This command is useful when MCP servers fail due to incorrect args configuration.

    \\b
    Examples:
        kuzu-memory repair                  # Auto-detect and repair all
        kuzu-memory repair --verbose        # Show detailed repair info
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

        rich_panel(
            f"Scanning for broken MCP configurations in {root.name}...",
            title="🔧 MCP Configuration Repair",
            style="cyan",
        )

        # Detect installed systems
        detected_systems = _detect_installed_systems(root)

        if not detected_systems:
            rich_print("No installed systems detected in this project.", style="yellow")
            rich_print(
                "\n💡 Run 'kuzu-memory install <integration>' to install first.",
                style="dim",
            )
            sys.exit(0)

        # Show detected systems
        rich_print(f"\n✓ Found {len(detected_systems)} installed system(s):", style="green")
        for system in detected_systems:
            rich_print(f"  • {system.name}", style="cyan")

        # Run global MCP config repair
        rich_print("\n🔍 Checking MCP configurations...", style="cyan")
        num_fixes, fix_messages = _repair_all_mcp_configs()

        if num_fixes > 0:
            rich_panel(
                f"Fixed {num_fixes} broken MCP configuration(s)",
                title="✅ Repair Complete",
                style="green",
            )
            if verbose or num_fixes <= 5:
                rich_print("\n📝 Repairs applied:")
                for msg in fix_messages:
                    rich_print(f"  • {msg}", style="green")
        else:
            rich_panel(
                "No broken MCP configurations found. All configs are healthy!",
                title="✅ All Good",
                style="green",
            )

        # Show next steps
        rich_print("\n🎯 Next Steps:", style="cyan")
        rich_print("1. Reload or restart your AI coding assistant")
        rich_print("2. MCP server should now start correctly with args: ['mcp']")
        rich_print("3. Check MCP server status in your AI assistant's settings")

    except Exception as e:
        rich_print(f"❌ Repair failed: {e}", style="red")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


__all__ = ["install_command", "remove_command", "repair_command", "uninstall_command"]
