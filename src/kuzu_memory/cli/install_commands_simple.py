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
def install_group(ai_system, force, project):
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

      # Force reinstall
      kuzu-memory install auggie --force
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

        # Check if installer exists
        if not has_installer(ai_system):
            print(f"❌ Unknown AI system: {ai_system}")
            print("\n💡 Available installers:")
            for installer_info in registry_list_installers():
                print(f"  • {installer_info['name']} - {installer_info['description']}")
            sys.exit(1)

        # Get installer
        installer = get_installer(ai_system, project_root)
        if not installer:
            print(f"❌ Failed to create installer for {ai_system}")
            sys.exit(1)

        # Show installation info
        print(f"🚀 Installing {installer.ai_system_name} integration...")
        print(f"📁 Project: {project_root}")
        print(f"📋 Description: {installer.description}")

        # Perform installation
        result = installer.install(force=force)

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

            # Show next steps
            if ai_system.lower() in ["auggie", "claude"]:
                print("\n🎯 Next Steps:")
                print(
                    "1. Test: kuzu-memory enhance 'How do I deploy this?' --format plain"
                )
                print("2. Store info: kuzu-memory remember 'This project uses FastAPI'")
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
