"""
Simple CLI commands for installer system.
"""

import sys
from pathlib import Path

import click

from ..installers import get_installer
from ..installers.registry import list_installers as registry_list_installers
from ..utils.project_setup import find_project_root
from .cli_utils import rich_print
from .enums import AISystem


@click.group(invoke_without_command=True)
@click.pass_context
def install(ctx):
    """
    🚀 Manage AI system integrations.

    Install, remove, and manage integrations for various AI systems
    including Claude Desktop, Claude Code, and Auggie.

    \b
    🎮 COMMANDS:
      add        Install integration for an AI system
      remove     Remove an integration
      list       List available installers
      status     Show installation status

    Use 'kuzu-memory install COMMAND --help' for detailed help.
    """
    # If no subcommand provided, show help
    if ctx.invoked_subcommand is None:
        rich_print(ctx.get_help())


@install.command()
@click.argument(
    "platform",
    type=click.Choice(
        ["claude-code", "claude-desktop", "cursor", "vscode", "windsurf", "auggie"]
    ),
)
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without making changes"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def add(
    platform: str,
    project,
    dry_run: bool,
    verbose: bool,
):
    """
    Install KuzuMemory integration for an AI platform.

    Each platform gets the right components automatically:
      - claude-code: MCP server + hooks (complete integration)
      - claude-desktop: MCP server only
      - cursor: MCP server only
      - vscode: MCP server only
      - windsurf: MCP server only
      - auggie: Rules integration (treated as hooks)

    \b
    🎯 EXAMPLES:
      # Install Claude Code (MCP + hooks)
      kuzu-memory install add claude-code

      # Install Claude Desktop (MCP only)
      kuzu-memory install add claude-desktop

      # Install Cursor (MCP only)
      kuzu-memory install add cursor

      # Install Auggie (rules only)
      kuzu-memory install add auggie

    \b
    📝 NOTE:
      No --force flag needed. Installations always update existing configs safely
      kuzu-memory install add claude-desktop
    """
    try:
        # Get project root
        if project:
            project_root = Path(project)
        else:
            project_root = find_project_root()
            if not project_root:
                print("❌ Could not find project root. Use --project to specify.")
                sys.exit(1)

        # Show what will be installed
        print(f"\n{'=' * 70}")
        print(f"Installing KuzuMemory for {platform}")
        print(f"{'=' * 70}")

        # Map platform to installer(s)
        if platform == "claude-code":
            print("📦 Components: MCP server + hooks (complete integration)")
        elif platform in ["claude-desktop", "cursor", "vscode", "windsurf"]:
            print("📦 Component: MCP server")
        elif platform == "auggie":
            print("📦 Component: Rules integration")

        print(f"📁 Project: {project_root}")
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        print()

        # Get installer - use platform name directly
        installer = get_installer(platform, project_root)
        if not installer:
            print(f"❌ Failed to create installer for {platform}")
            sys.exit(1)

        # Perform installation (installers now auto-update without force flag)
        result = installer.install(dry_run=dry_run, verbose=verbose)

        # Show results
        if result.success:
            print(f"\n✅ {result.message}")

            # Show created files
            if result.files_created:
                print("\n📄 Files created:")
                for file_path in result.files_created:
                    # Add helpful context for specific files
                    if ".claude-mpm/config.json" in str(file_path):
                        print(f"  • {file_path} (Claude MPM integration)")
                    else:
                        print(f"  • {file_path}")

            # Show modified files
            if result.files_modified:
                print("\n📝 Files modified:")
                for file_path in result.files_modified:
                    # Add helpful context for specific files
                    if "config.local.json" in str(file_path):
                        print(f"  • {file_path} (merged with existing config)")
                    elif ".claude-mpm/config.json" in str(file_path):
                        print(f"  • {file_path} (Claude MPM integration)")
                    else:
                        print(f"  • {file_path}")

            # Add explanation for Claude MPM config if it was created/modified
            mpm_files = [
                f
                for f in (result.files_created + result.files_modified)
                if ".claude-mpm/config.json" in str(f)
            ]
            # Show explanation for Claude Code platform
            if mpm_files and platform == "claude-code":
                print("\n💡 Claude MPM Integration:")
                print(
                    "   .claude-mpm/config.json enables project-wide memory settings for Claude MPM."
                )
                print(
                    "   This is optional and only used if you're using Claude MPM for project management."
                )

            # Show warnings
            if result.warnings:
                print("\n⚠️  Warnings:")
                for warning in result.warnings:
                    print(f"  • {warning}")

            # Show next steps based on platform
            print("\n🎯 Next Steps:")
            if platform == "claude-code":
                print("1. Reload Claude Code window or restart")
                print("2. MCP tools + hooks active for enhanced context")
                print("3. Check .claude/settings.local.json for configuration")
            elif platform == "claude-desktop":
                print("1. Restart Claude Desktop application")
                print("2. Open a new conversation")
                print("3. KuzuMemory MCP tools will be available")
            elif platform in ["cursor", "vscode", "windsurf"]:
                print(f"1. Reload or restart {installer.ai_system_name}")
                print("2. KuzuMemory MCP server will be active")
                print("3. Check the configuration file for details")
            elif platform == "auggie":
                print(
                    "1. Test: kuzu-memory memory enhance 'How do I deploy this?' --format plain"
                )
                print(
                    "2. Store info: kuzu-memory memory store 'This project uses FastAPI'"
                )
                print("3. Start using Auggie with enhanced context!")

        else:
            print(f"\n❌ {result.message}")
            if result.warnings:
                for warning in result.warnings:
                    print(f"  • {warning}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Installation failed: {e}")
        sys.exit(1)


@install.command()
@click.argument("ai_system", type=click.Choice([s.value for s in AISystem]))
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def remove(ai_system: str, project, confirm: bool):
    """
    Remove an AI system integration.

    Uninstalls the specified integration and cleans up configuration files.

    \b
    🎮 EXAMPLES:
      # Remove Claude Desktop integration
      kuzu-memory install remove claude-desktop

      # Remove without confirmation
      kuzu-memory install remove claude-code --confirm
    """
    try:
        # Get project root
        if project:
            project_root = Path(project)
        else:
            project_root = find_project_root()
            if not project_root:
                print("❌ Could not find project root. Use --project to specify.")
                sys.exit(1)

        # Get installer
        installer = get_installer(ai_system, project_root)
        if not installer:
            print(f"❌ Unknown AI system: {ai_system}")
            sys.exit(1)

        # Check installation status
        status = installer.get_status()
        if not status["installed"]:
            print(f"[i]  {installer.ai_system_name} integration is not installed.")
            sys.exit(0)

        print(f"🗑️  Uninstalling {installer.ai_system_name} integration...")

        # Confirm uninstallation
        if not confirm:
            if not click.confirm("Continue with uninstallation?"):
                print("Uninstallation cancelled.")
                sys.exit(0)

        # Perform uninstallation
        result = installer.uninstall()

        # Show results
        if result.success:
            print(f"\n✅ {result.message}")
        else:
            print(f"\n❌ {result.message}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Uninstallation failed: {e}")
        sys.exit(1)


@install.command()
@click.option("--project", type=click.Path(exists=True), help="Project directory")
def status(project):
    """
    Show installation status for all AI systems.

    Checks which integrations are installed and their current state.

    \b
    🎮 EXAMPLES:
      # Check installation status
      kuzu-memory install status

      # Check status for specific project
      kuzu-memory install status --project /path/to/project
    """
    try:
        # Get project root
        if project:
            project_root = Path(project)
        else:
            project_root = find_project_root()
            if not project_root:
                print("❌ Could not find project root. Use --project to specify.")
                sys.exit(1)

        print(f"📊 Installation Status for {project_root}")
        print()

        # Check status for each installer
        for installer_info in registry_list_installers():
            installer = get_installer(installer_info["name"], project_root)
            if installer:
                status = installer.get_status()
                status_text = (
                    "✅ Installed" if status["installed"] else "❌ Not Installed"
                )
                print(f"  {installer.ai_system_name}: {status_text}")

    except Exception as e:
        print(f"❌ Status check failed: {e}")
        sys.exit(1)


@install.command(name="list")
def list_cmd():
    """
    List all available installers.

    Shows all AI systems that can be integrated with KuzuMemory.

    \b
    🎮 EXAMPLES:
      # List available installers
      kuzu-memory install list
    """
    print("📋 Available AI System Installers")
    print()

    for installer_info in registry_list_installers():
        print(f"  • {installer_info['name']} - {installer_info['ai_system']}")
        print(f"    {installer_info['description']}")
        print()

    print("💡 Usage: kuzu-memory install add <name>")


__all__ = ["install"]
