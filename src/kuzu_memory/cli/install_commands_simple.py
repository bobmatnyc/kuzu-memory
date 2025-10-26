"""
Simple CLI commands for installer system.
"""

import sys
from pathlib import Path

import click

from ..installers import get_installer, has_installer
from ..installers.registry import list_installers as registry_list_installers
from ..utils.project_setup import find_project_root
from .cli_utils import rich_print
from .enums import AISystem, InstallationMode


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
@click.argument("ai_system", type=click.Choice([s.value for s in AISystem]))
@click.option("--force", is_flag=True, help="Force installation even if files exist")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without making changes"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.option(
    "--mode",
    type=click.Choice([m.value for m in InstallationMode]),
    default=InstallationMode.AUTO.value,
    help="Installation mode (auto=detect, pipx=use pipx, home=home dir)",
)
@click.option("--backup-dir", type=click.Path(), help="Custom backup directory")
@click.option("--memory-db", type=click.Path(), help="Custom memory database path")
def add(
    ai_system: str,
    force: bool,
    project,
    dry_run: bool,
    verbose: bool,
    mode: str,
    backup_dir,
    memory_db,
):
    """
    Install integration for an AI system.

    ⚠️  DEPRECATED: This command is deprecated. Please use the new commands:
      - 'kuzu-memory hooks install <system>' for hook integrations
      - 'kuzu-memory mcp install <system>' for MCP integrations

    \b
    🎯 SUPPORTED AI SYSTEMS (ONE PATH):
      auggie                  Augment rules for Auggie integration
      claude-code             Claude Code with hooks/MCP
      claude-desktop          Claude Desktop (auto-detects pipx/home)
      universal               Generic integration for any AI system

    \b
    🎮 NEW RECOMMENDED COMMANDS:
      # Install hook systems (Claude Code, Auggie)
      kuzu-memory hooks install claude-code
      kuzu-memory hooks install auggie

      # Install MCP systems (Claude Desktop, Cursor, VS Code, Windsurf)
      kuzu-memory mcp install claude-desktop
      kuzu-memory mcp install cursor
      kuzu-memory mcp install vscode
      kuzu-memory mcp install windsurf

    \b
    🎮 OLD EXAMPLES (still work but deprecated):
      # Install Auggie integration
      kuzu-memory install add auggie

      # Install Claude Code integration
      kuzu-memory install add claude-code

      # Install Claude Desktop (auto-detects best method)
      kuzu-memory install add claude-desktop
    """
    # Show deprecation warning
    print("\n" + "=" * 70)
    print("⚠️  DEPRECATION WARNING")
    print("=" * 70)
    print("This command is deprecated and will be removed in a future version.")
    print("\nPlease use the new commands instead:")

    # Show migration path based on system
    if ai_system in ["claude-code", "auggie"]:
        print(f"\n  🪝 New command: kuzu-memory hooks install {ai_system}")
        print(f"     (Hook-based integration)")
    elif ai_system in ["claude-desktop", "cursor", "vscode", "windsurf"]:
        mcp_system = ai_system
        print(f"\n  🔌 New command: kuzu-memory mcp install {mcp_system}")
        print(f"     (MCP server integration)")
    elif ai_system == "universal":
        print("\n  ℹ️  Universal installer is still available through 'install add'")

    print("\n" + "=" * 70)

    # Ask for confirmation to continue
    if not dry_run and not click.confirm("\nContinue with deprecated command?", default=True):
        print("Installation cancelled.")
        return

    print()

    try:
        # Deprecation warnings for old installer names
        deprecated_mappings = {
            "claude": ("claude-code", "kuzu-memory install add claude-code"),
            "claude-mcp": ("claude-code", "kuzu-memory install add claude-code"),
            "claude-desktop-pipx": (
                "claude-desktop",
                "kuzu-memory install add claude-desktop",
            ),
            "claude-desktop-home": (
                "claude-desktop --mode=home",
                "kuzu-memory install add claude-desktop --mode home",
            ),
            "generic": ("universal", "kuzu-memory install add universal"),
        }

        if ai_system in deprecated_mappings:
            _new_name, new_command = deprecated_mappings[ai_system]
            print(f"⚠️  DEPRECATION WARNING: '{ai_system}' is deprecated.")
            print(f"   Please use: {new_command}")
            print(f"   Continuing with installation using '{ai_system}' for now...\n")
        # Get project root
        if project:
            project_root = Path(project)
        else:
            project_root = find_project_root()
            if not project_root:
                print("❌ Could not find project root. Use --project to specify.")
                sys.exit(1)

        # Check if installer exists
        if not has_installer(ai_system):
            print(f"❌ Unknown AI system: {ai_system}")
            print("\n💡 Available installers:")
            for installer_info in registry_list_installers():
                print(f"  • {installer_info['name']} - {installer_info['description']}")
            sys.exit(1)

        # Prepare installer options
        installer_options = {}
        if dry_run:
            installer_options["dry_run"] = dry_run
        if verbose:
            installer_options["verbose"] = verbose
        # Mode applies to claude-desktop and claude-desktop-home
        if mode and ai_system in ["claude-desktop", "claude-desktop-home"]:
            installer_options["mode"] = mode
        if backup_dir:
            from pathlib import Path

            installer_options["backup_dir"] = Path(backup_dir)
        if memory_db:
            from pathlib import Path

            installer_options["memory_db"] = Path(memory_db)

        # Get installer with options
        installer = get_installer(ai_system, project_root)
        if not installer:
            print(f"❌ Failed to create installer for {ai_system}")
            sys.exit(1)

        # Update installer with options if they apply
        for key, value in installer_options.items():
            if hasattr(installer, key):
                setattr(installer, key, value)

        # Show installation info
        print(f"🚀 Installing {installer.ai_system_name} integration...")
        if project_root and ai_system not in [
            "claude-desktop",
            "claude-desktop-pipx",
            "claude-desktop-home",
        ]:
            print(f"📁 Project: {project_root}")
        print(f"📋 Description: {installer.description}")
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")

        # Perform installation
        result = installer.install(force=force, **installer_options)

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
            # Show explanation for both "claude-code" and deprecated "claude" names
            if mpm_files and ai_system in ["claude-code", "claude", "claude-mcp"]:
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

            # Show next steps based on installer type
            if ai_system.lower() in ["auggie", "claude"]:
                print("\n🎯 Next Steps:")
                print(
                    "1. Test: kuzu-memory memory enhance 'How do I deploy this?' --format plain"
                )
                print(
                    "2. Store info: kuzu-memory memory store 'This project uses FastAPI'"
                )
                print("3. Start using Auggie with enhanced context!")
            elif "claude-desktop" in ai_system.lower():
                print("\n🎯 Next Steps:")
                print("1. Restart Claude Desktop application")
                print("2. Open a new conversation in Claude Desktop")
                print("3. KuzuMemory MCP tools will be available:")
                print("   • kuzu_enhance - Enhance prompts with context")
                print("   • kuzu_learn - Store learnings")
                print("   • kuzu_recall - Query memories")
                print("   • kuzu_remember - Store information")
                print("   • kuzu_stats - Get statistics")
                print("\n💡 Tip: You can validate the installation with:")
                print("   kuzu-memory install-status")

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
