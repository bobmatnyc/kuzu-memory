"""
CLI commands for installer system.

Provides install, uninstall, and status commands for AI system integrations.
"""

import sys
from pathlib import Path

import click
from rich import print as rich_print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..installers import get_installer, has_installer, list_installers
from ..utils.project_setup import find_project_root

console = Console()


@click.group(name="install")
def install_group() -> None:
    """🔧 Install AI system integrations."""
    pass


@install_group.command()
@click.argument("ai_system")
@click.option("--force", is_flag=True, help="Force installation even if files exist")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--language", help="Primary language for examples (python, javascript, shell)")
@click.option("--ai-name", help="Custom AI system name for universal installer")
@click.pass_context
def install(
    ctx: click.Context,
    ai_system: str,
    force: bool,
    project: str | None,
    language: str | None,
    ai_name: str | None,
) -> None:
    """
    🚀 Install integration for an AI system.

    \b
    🎯 SUPPORTED AI SYSTEMS:
      auggie/claude    Augment rules for Auggie/Claude integration
      universal        Generic integration for any AI system

    \b
    🎮 EXAMPLES:
      # Install Auggie integration
      kuzu-memory install auggie

      # Install universal integration
      kuzu-memory install universal --language python

      # Force reinstall
      kuzu-memory install auggie --force

      # Install for specific project
      kuzu-memory install universal --project /path/to/project
    """
    try:
        # Get project root
        if project:
            project_root = Path(project)
        else:
            project_root = find_project_root()
            if not project_root:
                rich_print("[red]❌ Could not find project root. Use --project to specify.[/red]")
                sys.exit(1)

        # Check if installer exists
        if not has_installer(ai_system):
            rich_print(f"[red]❌ Unknown AI system: {ai_system}[/red]")
            rich_print("[blue]\n💡 Available installers:[/blue]")
            for installer_info in list_installers():
                rich_print(f"  • {installer_info['name']} - {installer_info['description']}")
            sys.exit(1)

        # Get installer
        installer = get_installer(ai_system, project_root)
        if not installer:
            rich_print(f"[red]❌ Failed to create installer for {ai_system}[/red]")
            sys.exit(1)

        # Prepare installation options
        install_options = {}
        if language:
            install_options["language"] = language
        if ai_name:
            install_options["ai_system"] = ai_name

        # Show installation info
        rich_print(f"[blue]🚀 Installing {installer.ai_system_name} integration...[/blue]")
        rich_print(f"[dim]📁 Project: {project_root}[/dim]")
        rich_print(f"[dim]📋 Description: {installer.description}[/dim]")

        if not force:
            # Check for existing files
            existing_files = []
            for file_pattern in installer.required_files:
                file_path = project_root / file_pattern
                if file_path.exists():
                    existing_files.append(str(file_path))

            if existing_files:
                rich_print("[yellow]\n⚠️  Existing files found:[/yellow]")
                for file_path in existing_files:
                    rich_print(f"[yellow]  • {file_path}[/yellow]")

                if not click.confirm("Continue with installation? (will create backups)"):
                    rich_print("[yellow]Installation cancelled.[/yellow]")
                    sys.exit(0)

        # Perform installation
        result = installer.install(force=force, **install_options)

        # Show results
        if result.success:
            rich_print(f"[green]\n✅ {result.message}[/green]")

            # Show created files
            if result.files_created:
                rich_print("[green]\n📄 Files created:[/green]")
                for file_path in result.files_created:
                    rich_print(f"[green]  • {file_path}[/green]")

            # Show modified files
            if result.files_modified:
                rich_print("[yellow]\n📝 Files modified:[/yellow]")
                for file_path in result.files_modified:
                    rich_print(f"[yellow]  • {file_path}[/yellow]")

            # Show backup files
            if result.backup_files:
                rich_print("[blue]\n💾 Backup files created:[/blue]")
                for file_path in result.backup_files:
                    rich_print(f"[blue]  • {file_path}[/blue]")

            # Show warnings
            if result.warnings:
                rich_print("[yellow]\n⚠️  Warnings:[/yellow]")
                for warning in result.warnings:
                    rich_print(f"[yellow]  • {warning}[/yellow]")

            # Show next steps
            _show_next_steps(ai_system, project_root)

        else:
            rich_print(f"[red]\n❌ {result.message}[/red]")
            if result.warnings:
                for warning in result.warnings:
                    rich_print(f"[red]  • {warning}[/red]")
            sys.exit(1)

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"[red]❌ Installation failed: {e}[/red]")
        sys.exit(1)


@install_group.command()
@click.argument("ai_system")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def uninstall(ctx: click.Context, ai_system: str, project: str | None, confirm: bool) -> None:
    """
    🗑️  Uninstall AI system integration.

    \b
    🎮 EXAMPLES:
      # Uninstall Auggie integration
      kuzu-memory install uninstall auggie

      # Skip confirmation
      kuzu-memory install uninstall auggie --confirm
    """
    try:
        # Get project root
        if project:
            project_root = Path(project)
        else:
            project_root = find_project_root()
            if not project_root:
                rich_print("[red]❌ Could not find project root. Use --project to specify.[/red]")
                sys.exit(1)

        # Check if installer exists
        if not has_installer(ai_system):
            rich_print(f"[red]❌ Unknown AI system: {ai_system}[/red]")
            sys.exit(1)

        # Get installer
        installer = get_installer(ai_system, project_root)
        if not installer:
            rich_print(f"[red]❌ Failed to create installer for {ai_system}[/red]")
            sys.exit(1)

        # Check installation status
        status = installer.get_status()
        if not status["installed"]:
            rich_print(f"[blue][i] {installer.ai_system_name} integration is not installed.[/blue]")
            sys.exit(0)

        # Show uninstallation info
        rich_print(f"[blue]🗑️  Uninstalling {installer.ai_system_name} integration...[/blue]")
        rich_print(f"[dim]📁 Project: {project_root}[/dim]")

        # Show files that will be removed
        if status["files_present"]:
            rich_print("[yellow]\n📄 Files to be removed:[/yellow]")
            for file_path in status["files_present"]:
                rich_print(f"[yellow]  • {file_path}[/yellow]")

        # Confirm uninstallation
        if not confirm:
            if not click.confirm("Continue with uninstallation?"):
                rich_print("[yellow]Uninstallation cancelled.[/yellow]")
                sys.exit(0)

        # Perform uninstallation
        result = installer.uninstall()

        # Show results
        if result.success:
            rich_print(f"[green]\n✅ {result.message}[/green]")

            # Show restored files
            if result.files_modified:
                rich_print("[green]\n🔄 Files restored from backup:[/green]")
                for file_path in result.files_modified:
                    rich_print(f"[green]  • {file_path}[/green]")
        else:
            rich_print(f"[red]\n❌ {result.message}[/red]")
            if result.warnings:
                for warning in result.warnings:
                    rich_print(f"[red]  • {warning}[/red]")
            sys.exit(1)

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"[red]❌ Uninstallation failed: {e}[/red]")
        sys.exit(1)


@install_group.command()
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.pass_context
def status(ctx: click.Context, project: str | None) -> None:
    """
    📊 Show installation status for all AI systems.

    \b
    🎮 EXAMPLES:
      # Show status for current project
      kuzu-memory install status

      # Show status for specific project
      kuzu-memory install status --project /path/to/project
    """
    try:
        # Get project root
        if project:
            project_root = Path(project)
        else:
            project_root = find_project_root()
            if not project_root:
                rich_print("[red]❌ Could not find project root. Use --project to specify.[/red]")
                sys.exit(1)

        rich_print(f"[blue]📊 Installation Status for {project_root}[/blue]")

        # Create status table
        table = Table(title="AI System Integration Status")
        table.add_column("AI System", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Files Present", style="blue")
        table.add_column("Files Missing", style="red")
        table.add_column("Backups", style="yellow")

        # Check status for each installer
        for installer_info in list_installers():
            installer = get_installer(installer_info["name"], project_root)
            if installer:
                status = installer.get_status()

                # Format status
                status_text = "✅ Installed" if status["installed"] else "❌ Not Installed"
                files_present = str(len(status["files_present"]))
                files_missing = str(len(status["files_missing"]))
                backups = "✅ Yes" if status.get("has_backups", False) else "❌ No"

                table.add_row(
                    installer.ai_system_name,
                    status_text,
                    files_present,
                    files_missing,
                    backups,
                )

        console.print(table)

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"[red]❌ Status check failed: {e}[/red]")
        sys.exit(1)


@install_group.command()
def list() -> None:
    """
    📋 List all available installers.

    \b
    🎮 EXAMPLE:
      kuzu-memory install list
    """
    print("📋 Available AI System Installers")
    print()

    for installer_info in list_installers():
        print(f"  • {installer_info['name']} - {installer_info['ai_system']}")
        print(f"    {installer_info['description']}")
        print()

    print("💡 Usage: kuzu-memory install <name>")


def _show_next_steps(ai_system: str, project_root: Path) -> None:
    """Show next steps after installation."""
    if ai_system.lower() in ["auggie", "claude"]:
        next_steps = """
🎯 Next Steps for Auggie Integration:

1. **Test the integration:**
   kuzu-memory enhance "How do I structure an API?" --format plain

2. **Store some project information:**
   kuzu-memory remember "This project uses FastAPI with PostgreSQL"

3. **Check that Auggie can see the rules:**
   - AGENTS.md should be in your project root
   - .augment/rules/ should contain integration rules

4. **Start a conversation with Auggie:**
   - Ask technical questions about your project
   - Provide project information and preferences
   - Notice how responses become more project-specific

5. **Monitor the memory system:**
   kuzu-memory stats
   kuzu-memory recent
"""
    else:
        next_steps = """
🎯 Next Steps for Universal Integration:

1. **Review the integration guide:**
   cat kuzu-memory-integration.md

2. **Check the examples:**
   ls examples/

3. **Test basic functionality:**
   kuzu-memory enhance "How do I deploy this?" --format plain
   kuzu-memory learn "Test integration" --quiet

4. **Customize for your AI system:**
   - Adapt examples in examples/ directory
   - Modify integration patterns for your needs
   - Add your AI system-specific logic

5. **Monitor the system:**
   kuzu-memory stats
   kuzu-memory project
"""

    panel = Panel(next_steps.strip(), title="🚀 Installation Complete!", border_style="green")
    console.print(panel)
