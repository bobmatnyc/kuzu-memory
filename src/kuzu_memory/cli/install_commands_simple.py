"""
Simple CLI commands for installer system.
"""

import sys
from pathlib import Path

import click

from ..installers import get_installer, has_installer
from ..installers.registry import list_installers as registry_list_installers
from ..utils.project_setup import find_project_root


@click.command(name="install")
@click.argument("ai_system")
@click.option("--force", is_flag=True, help="Force installation even if files exist")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without making changes"
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.option(
    "--mode",
    type=click.Choice(["auto", "pipx", "home", "wrapper", "standalone"]),
    default="auto",
    help="Installation mode (auto=detect, pipx=use pipx, home=home dir)",
)
@click.option("--backup-dir", type=click.Path(), help="Custom backup directory")
@click.option("--memory-db", type=click.Path(), help="Custom memory database path")
def install_group(
    ai_system, force, project, dry_run, verbose, mode, backup_dir, memory_db
):
    """
    🚀 Install integration for an AI system.

    \b
    🎯 SUPPORTED AI SYSTEMS (ONE PATH):
      auggie                  Augment rules for Auggie integration
      claude-code             Claude Code with hooks/MCP
      claude-desktop          Claude Desktop (auto-detects pipx/home)
      universal               Generic integration for any AI system

    \b
    🎮 EXAMPLES:
      # Install Auggie integration
      kuzu-memory install auggie

      # Install Claude Code integration
      kuzu-memory install claude-code

      # Install Claude Desktop (auto-detects best method)
      kuzu-memory install claude-desktop

      # Install Claude Desktop with specific mode
      kuzu-memory install claude-desktop --mode pipx
      kuzu-memory install claude-desktop --mode home

      # Force reinstall with custom settings
      kuzu-memory install claude-desktop --force --memory-db ~/my-memories

      # Dry run to see what would happen
      kuzu-memory install claude-desktop --dry-run --verbose
    """
    try:
        # Deprecation warnings for old installer names
        deprecated_mappings = {
            "claude": ("claude-code", "kuzu-memory install claude-code"),
            "claude-mcp": ("claude-code", "kuzu-memory install claude-code"),
            "claude-desktop-pipx": (
                "claude-desktop",
                "kuzu-memory install claude-desktop",
            ),
            "claude-desktop-home": (
                "claude-desktop --mode=home",
                "kuzu-memory install claude-desktop --mode home",
            ),
            "generic": ("universal", "kuzu-memory install universal"),
        }

        if ai_system in deprecated_mappings:
            new_name, new_command = deprecated_mappings[ai_system]
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
                    print(f"  • {file_path}")

            # Show modified files
            if result.files_modified:
                print("\n📝 Files modified:")
                for file_path in result.files_modified:
                    print(f"  • {file_path}")

            # Show warnings
            if result.warnings:
                print("\n⚠️  Warnings:")
                for warning in result.warnings:
                    print(f"  • {warning}")

            # Show next steps based on installer type
            if ai_system.lower() in ["auggie", "claude"]:
                print("\n🎯 Next Steps:")
                print(
                    "1. Test: kuzu-memory enhance 'How do I deploy this?' --format plain"
                )
                print("2. Store info: kuzu-memory remember 'This project uses FastAPI'")
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


@click.command()
@click.argument("ai_system")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def uninstall(ai_system, project, confirm):
    """
    🗑️  Uninstall AI system integration.
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


@click.command()
@click.option("--project", type=click.Path(exists=True), help="Project directory")
def status(project):
    """
    📊 Show installation status for all AI systems.
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


@click.command()
def list_installers():
    """
    📋 List all available installers.
    """
    print("📋 Available AI System Installers")
    print()

    for installer_info in registry_list_installers():
        print(f"  • {installer_info['name']} - {installer_info['ai_system']}")
        print(f"    {installer_info['description']}")
        print()

    print("💡 Usage: kuzu-memory install <name>")
