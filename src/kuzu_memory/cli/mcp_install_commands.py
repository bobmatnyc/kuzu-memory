"""
MCP installation CLI commands for KuzuMemory.

Provides unified MCP installation commands with auto-detection.
"""

import sys
from pathlib import Path

import click

from ..installers.detection import AISystemDetector, DetectedSystem
from ..installers.registry import get_installer, has_installer
from ..utils.project_setup import find_project_root


@click.group(name="mcp")
def mcp_install_group():
    """
    🔌 Manage MCP server integrations.

    Auto-detect and install MCP server configurations for various AI coding assistants.

    \b
    🎮 COMMANDS:
      detect     Detect installed AI systems
      install    Install MCP configurations
      list       List available MCP installers

    Use 'kuzu-memory mcp COMMAND --help' for detailed help.
    """
    pass


@mcp_install_group.command(name="detect")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--verbose", is_flag=True, help="Show detailed information")
@click.option("--available", is_flag=True, help="Show only available systems")
@click.option("--installed", is_flag=True, help="Show only installed systems")
def detect_systems(project, verbose: bool, available: bool, installed: bool):
    """
    Detect AI systems in current project.

    Scans for both project-specific and global AI system configurations.

    \b
    🎯 EXAMPLES:
      # Detect all systems
      kuzu-memory mcp detect

      # Show only available systems (can be installed)
      kuzu-memory mcp detect --available

      # Show only installed systems (have existing configs)
      kuzu-memory mcp detect --installed

      # Show detailed information
      kuzu-memory mcp detect --verbose
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

        # Detect systems
        detector = AISystemDetector(project_root)

        # Filter based on options
        if available:
            systems = detector.detect_available()
            title = "Available AI Systems (Can Install)"
        elif installed:
            systems = detector.detect_installed()
            title = "Installed AI Systems (Existing Configs)"
        else:
            systems = detector.detect_all()
            title = "Detected AI Systems"

        # Display results
        if not systems:
            print(f"\n{title}: None found")
            return

        print(f"\n{title}:")
        print("=" * 70)

        for system in systems:
            _display_system(system, verbose)

        # Show summary
        print("\n" + "=" * 70)
        print(f"Total: {len(systems)} system(s)")

        if not available and not installed:
            available_count = len([s for s in systems if s.can_install])
            installed_count = len([s for s in systems if s.exists])
            print(f"Available: {available_count} | Installed: {installed_count}")

    except Exception as e:
        print(f"❌ Detection failed: {e}")
        sys.exit(1)


@mcp_install_group.command(name="install")
@click.option("--system", help="Install specific system only (e.g., cursor, vscode)")
@click.option(
    "--all", "install_all", is_flag=True, help="Install all available systems"
)
@click.option("--force", is_flag=True, help="Force installation (overwrite existing)")
@click.option("--dry-run", is_flag=True, help="Preview changes without installing")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def install_mcp(
    system: str | None,
    install_all: bool,
    force: bool,
    dry_run: bool,
    project,
    verbose: bool,
):
    """
    Install MCP configurations for AI systems.

    Auto-detects available AI systems and installs MCP server configurations.
    Preserves existing MCP servers in configurations.

    \b
    🎯 EXAMPLES:
      # Auto-install all detected systems
      kuzu-memory mcp install --all

      # Install specific system
      kuzu-memory mcp install --system cursor

      # Preview changes
      kuzu-memory mcp install --all --dry-run

      # Force reinstall
      kuzu-memory mcp install --system vscode --force

      # Install with verbose output
      kuzu-memory mcp install --all --verbose
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

        # Detect available systems
        detector = AISystemDetector(project_root)

        # Determine which systems to install
        if system:
            # Install specific system
            systems_to_install = [detector.get_system(system)]
            if not systems_to_install[0]:
                print(f"❌ Unknown system: {system}")
                print("\nAvailable systems:")
                for s in detector.detect_available():
                    print(f"  • {s.installer_name} - {s.name}")
                sys.exit(1)
        elif install_all:
            # Install all available systems
            systems_to_install = detector.detect_available()
        else:
            # Interactive mode - show recommendations
            recommended = detector.get_recommended_systems()
            if not recommended:
                print("✅ All available AI systems already have MCP configurations!")
                print(
                    "\nUse --force to reinstall, or --system to install specific system."
                )
                return

            print("💡 Recommended systems to install:")
            for s in recommended:
                print(f"  • {s.installer_name} - {s.name}")

            if not click.confirm("\nInstall MCP configs for these systems?"):
                print("Installation cancelled.")
                return

            systems_to_install = recommended

        if not systems_to_install:
            print("❌ No systems available for installation")
            sys.exit(1)

        # Install each system
        success_count = 0
        failure_count = 0

        for detected_system in systems_to_install:
            if not detected_system.can_install:
                print(f"⚠️  Skipping {detected_system.name}: {detected_system.notes}")
                continue

            print(f"\n{'=' * 70}")
            print(f"Installing MCP configuration for {detected_system.name}...")
            print(f"{'=' * 70}")

            # Get installer
            installer = get_installer(detected_system.installer_name, project_root)
            if not installer:
                print(f"⚠️  No installer available for {detected_system.installer_name}")
                failure_count += 1
                continue

            # Install
            result = installer.install(force=force, dry_run=dry_run, verbose=verbose)

            # Display result
            if result.success:
                print(f"✅ {result.message}")
                success_count += 1
            else:
                print(f"❌ {result.message}")
                failure_count += 1

            # Show warnings
            if result.warnings:
                print("\nWarnings:")
                for warning in result.warnings:
                    print(f"  ⚠️  {warning}")

            # Show files
            if verbose and (result.files_created or result.files_modified):
                print("\nFiles:")
                for f in result.files_created:
                    print(f"  ✨ Created: {f}")
                for f in result.files_modified:
                    print(f"  📝 Modified: {f}")
                for f in result.backup_files:
                    print(f"  💾 Backup: {f}")

        # Final summary
        print(f"\n{'=' * 70}")
        print("Installation Summary:")
        print(f"  ✅ Success: {success_count}")
        print(f"  ❌ Failed: {failure_count}")

        if dry_run:
            print("\n💡 This was a dry run. Use --force to actually install.")

    except Exception as e:
        print(f"❌ Installation failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@mcp_install_group.command(name="list")
@click.option("--verbose", is_flag=True, help="Show detailed information")
def list_mcp_installers(verbose: bool):
    """
    List available MCP installers.

    Shows all MCP installers that can be used with 'kuzu-memory mcp install'.

    \b
    🎯 PRIORITY 1 INSTALLERS (Implemented):
      • cursor    - Cursor IDE (.cursor/mcp.json)
      • vscode    - VS Code with Claude (.vscode/mcp.json)
      • windsurf  - Windsurf IDE (~/.codeium/windsurf/mcp_config.json)

    \b
    🚧 COMING SOON:
      • roo-code  - Roo Code (.roo/mcp.json)
      • zed       - Zed Editor (.zed/settings.json)
      • continue  - Continue (.continue/config.yaml)
      • junie     - JetBrains Junie (.junie/mcp/mcp.json)
    """
    implemented = ["cursor", "vscode", "windsurf"]

    print("\n🔌 Available MCP Installers:")
    print("=" * 70)

    print("\n✅ PRIORITY 1 (Implemented):")
    for name in implemented:
        if has_installer(name):
            installer = get_installer(name, Path.cwd())
            if installer:
                print(f"  • {name:<12} - {installer.description}")

    print("\n🚧 COMING SOON:")
    coming_soon = {
        "roo-code": "Roo Code project-specific MCP",
        "zed": "Zed Editor settings integration",
        "continue": "Continue YAML configuration",
        "junie": "JetBrains Junie MCP integration",
    }
    for name, desc in coming_soon.items():
        print(f"  • {name:<12} - {desc}")

    print("\n" + "=" * 70)
    print(f"Total implemented: {len(implemented)}")


def _display_system(system: DetectedSystem, verbose: bool = False):
    """Display information about a detected system."""
    # Status icon
    if system.exists:
        icon = "✅"
    elif system.can_install:
        icon = "📦"
    else:
        icon = "⚠️"

    # Basic info
    print(f"\n{icon} {system.name}")
    print(f"   Installer: {system.installer_name}")
    print(f"   Type: {system.config_type}")

    if verbose:
        print(f"   Config: {system.config_path}")
        print(f"   Exists: {'Yes' if system.exists else 'No'}")
        print(f"   Can Install: {'Yes' if system.can_install else 'No'}")

    if system.notes:
        print(f"   Notes: {system.notes}")
