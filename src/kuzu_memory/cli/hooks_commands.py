"""
Hooks installation CLI commands for KuzuMemory.

Provides unified hooks installation commands for Claude Code and Auggie.
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ..installers.registry import get_installer, has_installer
from ..utils.project_setup import find_project_root
from .enums import HookSystem

console = Console()


@click.group(name="hooks")
def hooks_group():
    """
    🪝 Manage hook system integrations.

    ⚠️  DEPRECATED: Use 'kuzu-memory install' instead.

    This command group is deprecated. Use the unified install command:
      • kuzu-memory install claude-code
      • kuzu-memory install auggie
      • kuzu-memory uninstall claude-code

    Install and manage hook-based integrations for AI coding assistants
    that support hooks (Claude Code) or rules (Auggie).

    \b
    🎮 COMMANDS:
      status     Show hooks installation status
      install    Install hooks for a system
      list       List available hook systems

    \b
    🎯 HOOK SYSTEMS:
      claude-code  Claude Code with UserPromptSubmit and Stop hooks
      auggie       Auggie with Augment rules

    Use 'kuzu-memory hooks COMMAND --help' for detailed help.
    """
    console.print("\n⚠️  [yellow]WARNING: 'kuzu-memory hooks' is deprecated.[/yellow]")
    console.print(
        "[yellow]⚠️  Use 'kuzu-memory install <integration>' instead.[/yellow]"
    )
    console.print()
    console.print("[dim]Examples:[/dim]")
    console.print("[dim]  kuzu-memory install claude-code[/dim]")
    console.print("[dim]  kuzu-memory uninstall claude-code[/dim]\n")


@hooks_group.command(name="status")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--verbose", is_flag=True, help="Show detailed information")
def hooks_status(project, verbose: bool):
    """
    Show hooks installation status for all systems.

    Checks the installation status of all hook-based systems.

    \b
    🎯 EXAMPLES:
      # Show status for all hook systems
      kuzu-memory hooks status

      # Show detailed status
      kuzu-memory hooks status --verbose
    """
    try:
        # Determine project root
        if project:
            project_root = Path(project)
        else:
            try:
                project_root = find_project_root()
            except Exception:
                project_root = Path.cwd()

        console.print("\n🪝 [bold cyan]Hook Systems Installation Status[/bold cyan]")
        console.print(f"Project: {project_root}\n")

        # Create table for status
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("System", style="cyan", width=15)
        table.add_column("Status", width=15)
        table.add_column("Details", width=40)

        # Check each hook system
        for hook_system in HookSystem:
            system_name = hook_system.value
            if not has_installer(system_name):
                continue

            installer = get_installer(system_name, project_root)
            if not installer:
                continue

            status_info = installer.get_status()
            is_installed = status_info.get("installed", False)

            # Status icon and text
            if is_installed:
                status_str = "[green]✅ Installed[/green]"
                details = "All files present"
            else:
                status_str = "[yellow]❌ Not Installed[/yellow]"
                details = "Run install to set up"

            # Add detailed info if verbose
            if verbose and is_installed:
                files = status_info.get("files", {})
                present_files = [k for k, v in files.items() if v]
                details = f"{len(present_files)} files present"

            table.add_row(hook_system.display_name, status_str, details)

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]❌ Status check failed: {e}[/red]")
        sys.exit(1)


@hooks_group.command(name="install")
@click.argument("system", type=click.Choice([s.value for s in HookSystem]))
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--verbose", is_flag=True, help="Show detailed output")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
def install_hooks(system: str, dry_run: bool, verbose: bool, project):
    """
    Install hooks for specified system.

    ℹ️  RECOMMENDED: Use 'kuzu-memory install <platform>' instead.
        The unified install command automatically handles MCP + hooks per platform.

    Hooks are automatically updated if already installed (no --force flag needed).

    \b
    🎯 HOOK SYSTEMS:
      claude-code  Install Claude Code hooks (UserPromptSubmit, Stop)
      auggie       Install Auggie rules (treated as hooks)

    \b
    🎯 RECOMMENDED COMMAND:
      kuzu-memory install <platform>
        • Installs MCP + hooks for claude-code
        • Installs rules for auggie
        • No need to think about MCP vs hooks - it does the right thing

    \b
    🎯 EXAMPLES (still supported):
      # Install Claude Code hooks
      kuzu-memory hooks install claude-code

      # Install Auggie rules
      kuzu-memory hooks install auggie
    """
    # Show informational note about unified command
    console.print(
        "\nℹ️  Note: 'kuzu-memory install <platform>' is now the recommended command."
    )
    console.print(
        "   It automatically installs the right components for each platform.\n"
    )

    try:
        # Determine project root
        if project:
            project_root = Path(project)
        else:
            try:
                project_root = find_project_root()
            except Exception:
                console.print(
                    "[red]❌ Could not find project root. Use --project to specify.[/red]"
                )
                sys.exit(1)

        # Check if installer exists
        if not has_installer(system):
            console.print(f"[red]❌ Unknown hook system: {system}[/red]")
            console.print("\n💡 Available hook systems:")
            for hook_system in HookSystem:
                console.print(f"  • {hook_system.value} - {hook_system.display_name}")
            sys.exit(1)

        # Get installer
        installer = get_installer(system, project_root)
        if not installer:
            console.print(f"[red]❌ Failed to create installer for {system}[/red]")
            sys.exit(1)

        # Show installation info
        console.print(
            f"\n🪝 [bold cyan]Installing {installer.ai_system_name}[/bold cyan]"
        )
        console.print(f"📁 Project: {project_root}")
        console.print(f"📋 Description: {installer.description}")

        if dry_run:
            console.print(
                "\n[yellow]🔍 DRY RUN MODE - No changes will be made[/yellow]"
            )

        console.print()

        # Perform installation (always update existing - no force parameter)
        result = installer.install(dry_run=dry_run, verbose=verbose)

        # Show results
        if result.success:
            console.print(f"\n[green]✅ {result.message}[/green]")

            # Show created files
            if result.files_created:
                console.print("\n[cyan]📄 Files created:[/cyan]")
                for file_path in result.files_created:
                    console.print(f"  • {file_path}")

            # Show modified files
            if result.files_modified:
                console.print("\n[yellow]📝 Files modified:[/yellow]")
                for file_path in result.files_modified:
                    console.print(f"  • {file_path}")

            # Show backups
            if result.backup_files and verbose:
                console.print("\n[blue]💾 Backup files:[/blue]")
                for file_path in result.backup_files:
                    console.print(f"  • {file_path}")

            # Show warnings
            if result.warnings:
                console.print("\n[yellow]⚠️  Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  • {warning}")

            # Show next steps
            console.print("\n[green]🎯 Next Steps:[/green]")
            if system == "claude-code":
                console.print("1. Reload Claude Code window or restart")
                console.print(
                    "2. Hooks will auto-enhance prompts and learn from responses"
                )
                console.print("3. Check .claude/config.local.json for configuration")
            elif system == "auggie":
                console.print("1. Open or reload your Auggie workspace")
                console.print("2. Rules will be active for enhanced context")
                console.print(
                    "3. Check AGENTS.md and .augment/rules/ for configuration"
                )

        else:
            console.print(f"\n[red]❌ {result.message}[/red]")
            if result.warnings:
                for warning in result.warnings:
                    console.print(f"[yellow]  • {warning}[/yellow]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]❌ Installation failed: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@hooks_group.command(name="list")
def list_hooks():
    """
    List available hook systems.

    Shows all hook-based systems that can be installed with kuzu-memory.

    \b
    🎯 EXAMPLES:
      # List available hook systems
      kuzu-memory hooks list
    """
    console.print("\n🪝 [bold cyan]Available Hook Systems[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("System", style="cyan", width=15)
    table.add_column("Name", width=15)
    table.add_column("Type", width=15)

    for hook_system in HookSystem:
        system_name = hook_system.value
        display_name = hook_system.display_name

        # Determine type
        if system_name == "claude-code":
            hook_type = "Hooks (Events)"
        elif system_name == "auggie":
            hook_type = "Rules (Markdown)"
        else:
            hook_type = "Unknown"

        table.add_row(system_name, display_name, hook_type)

    console.print(table)

    console.print(
        "\n💡 [dim]Use 'kuzu-memory hooks install <system>' to install[/dim]\n"
    )


__all__ = ["hooks_group"]
