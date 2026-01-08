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
def mcp_install_group() -> None:
    """
    🔌 Manage MCP server integrations.

    ⚠️  DEPRECATED: Use 'kuzu-memory install' instead.

    This command group is deprecated. Use the unified install command:
      • kuzu-memory install claude-code
      • kuzu-memory install claude-desktop
      • kuzu-memory install cursor
      • kuzu-memory uninstall cursor

    Auto-detect and install MCP server configurations for various AI coding assistants.

    \b
    🎮 COMMANDS:
      detect     Detect installed AI systems
      install    Install MCP configurations
      list       List available MCP installers

    Use 'kuzu-memory mcp COMMAND --help' for detailed help.
    """
    print("\n⚠️  WARNING: 'kuzu-memory mcp' is deprecated.")
    print("⚠️  Use 'kuzu-memory install <integration>' instead.")
    print()
    print("Examples:")
    print("  kuzu-memory install claude-code")
    print("  kuzu-memory install cursor")
    print("  kuzu-memory uninstall claude-desktop\n")


@mcp_install_group.command(name="status")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--verbose", is_flag=True, help="Show detailed information")
@click.option("--available", is_flag=True, help="Show only available systems")
@click.option("--installed", is_flag=True, help="Show only installed systems")
def mcp_status(project: str | None, verbose: bool, available: bool, installed: bool) -> None:
    """
    Show MCP installation status for all systems.

    Scans for both project-specific and global AI system configurations.

    \b
    🎯 EXAMPLES:
      # Show status for all systems
      kuzu-memory mcp status

      # Show only available systems (can be installed)
      kuzu-memory mcp status --available

      # Show only installed systems (have existing configs)
      kuzu-memory mcp status --installed

      # Show detailed information
      kuzu-memory mcp status --verbose
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
@click.argument(
    "system",
    type=click.Choice(["claude-desktop", "claude-code", "cursor", "vscode", "windsurf"]),
)
@click.option("--dry-run", is_flag=True, help="Preview changes without installing")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def install_mcp(
    system: str,
    dry_run: bool,
    project: str | None,
    verbose: bool,
) -> None:
    """
    Install MCP server for specified system.

    NOTE: RECOMMENDED: Use 'kuzu-memory install <platform>' instead.
          The unified install command automatically handles MCP + hooks per platform.

    Automatically updates existing installations (no --force flag needed).
    Preserves existing MCP servers in configurations.

    \b
    🎯 MCP SYSTEMS:
      claude-desktop  Claude Desktop MCP server
      claude-code     Claude Code MCP server (also installs hooks)
      cursor          Cursor IDE MCP configuration
      vscode          VS Code with Claude extension
      windsurf        Windsurf IDE MCP configuration

    \b
    🎯 RECOMMENDED COMMAND:
      kuzu-memory install <platform>
        • Installs MCP + hooks for claude-code
        • Installs MCP only for claude-desktop, cursor, vscode, windsurf
        • No need to think about MCP vs hooks - it does the right thing

    \b
    🎯 EXAMPLES (still supported):
      # Install for Claude Code (MCP + hooks)
      kuzu-memory mcp install claude-code

      # Install for Cursor
      kuzu-memory mcp install cursor

      # Install for VS Code
      kuzu-memory mcp install vscode
    """
    # Show informational note about unified command
    print("\nNote: 'kuzu-memory install <platform>' is now the recommended command.")
    print("     It automatically installs the right components for each platform.\n")

    try:
        # Determine project root
        if project:
            project_root = Path(project)
        else:
            try:
                project_root = find_project_root()
            except Exception:
                project_root = Path.cwd()

        # Get installer for the specified system
        installer = get_installer(system, project_root)
        if not installer:
            print(f"❌ No installer available for {system}")
            print("\nAvailable MCP systems:")
            print("  • claude-desktop - Claude Desktop")
            print("  • claude-code    - Claude Code (MCP + hooks)")
            print("  • cursor         - Cursor IDE")
            print("  • vscode         - VS Code with Claude")
            print("  • windsurf       - Windsurf IDE")
            sys.exit(1)

        # Show installation info
        print(f"\n{'=' * 70}")
        print(f"Installing MCP server for {installer.ai_system_name}...")
        print(f"{'=' * 70}")
        print(f"📁 Project: {project_root}")
        print(f"📋 Description: {installer.description}")

        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made")

        print()

        # Install (always update existing - no force parameter)
        result = installer.install(dry_run=dry_run, verbose=verbose)

        # Display result
        if result.success:
            print(f"\n✅ {result.message}")

            # Show created files
            if result.files_created:
                print("\n📄 Files created:")
                for f in result.files_created:
                    print(f"  ✨ {f}")

            # Show modified files
            if result.files_modified:
                print("\n📝 Files modified:")
                for f in result.files_modified:
                    print(f"  📝 {f}")

            # Show backups
            if result.backup_files and verbose:
                print("\n💾 Backup files:")
                for f in result.backup_files:
                    print(f"  💾 {f}")

            # Show warnings
            if result.warnings:
                print("\n⚠️  Warnings:")
                for warning in result.warnings:
                    print(f"  • {warning}")

            # Show next steps
            print("\n🎯 Next Steps:")
            if system == "claude-desktop":
                print("1. Restart Claude Desktop application")
                print("2. Open a new conversation")
                print("3. KuzuMemory MCP tools will be available")
            elif system == "claude-code":
                print("1. Reload Claude Code window or restart")
                print("2. MCP tools + hooks active for enhanced context")
                print("3. Check .claude/settings.local.json for configuration")
            elif system in ["cursor", "vscode", "windsurf"]:
                print(f"1. Reload or restart {installer.ai_system_name}")
                print("2. KuzuMemory MCP server will be active")
                print("3. Check the configuration file for details")

        else:
            print(f"\n❌ {result.message}")
            if result.warnings:
                for warning in result.warnings:
                    print(f"  ⚠️  {warning}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Installation failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


# Backward compatibility: keep 'detect' as hidden alias for 'status'
@mcp_install_group.command(name="detect", hidden=True)
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--verbose", is_flag=True, help="Show detailed information")
@click.option("--available", is_flag=True, help="Show only available systems")
@click.option("--installed", is_flag=True, help="Show only installed systems")
def detect_alias(project: str | None, verbose: bool, available: bool, installed: bool) -> None:
    """[DEPRECATED] Use 'mcp status' instead."""
    print("⚠️  Warning: 'mcp detect' is deprecated. Please use 'mcp status' instead.\n")
    import click

    ctx = click.get_current_context()
    ctx.invoke(
        mcp_status,
        project=project,
        verbose=verbose,
        available=available,
        installed=installed,
    )


@mcp_install_group.command(name="list")
@click.option("--verbose", is_flag=True, help="Show detailed information")
def list_mcp_installers(verbose: bool) -> None:
    """
    List available MCP installers.

    Shows all MCP installers that can be used with 'kuzu-memory mcp install'.

    \b
    🎯 PRIORITY 1 INSTALLERS (Implemented):
      • claude-code - Claude Code (.claude/config.local.json) with MCP + hooks
      • cursor      - Cursor IDE (.cursor/mcp.json)
      • vscode      - VS Code with Claude (.vscode/mcp.json)
      • windsurf    - Windsurf IDE (~/.codeium/windsurf/mcp_config.json)

    \b
    🚧 COMING SOON:
      • roo-code    - Roo Code (.roo/mcp.json)
      • continue    - Continue (.continue/config.yaml)
      • junie       - JetBrains Junie (.junie/mcp/mcp.json)
    """
    implemented = ["claude-code", "cursor", "vscode", "windsurf"]

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
        "continue": "Continue YAML configuration",
        "junie": "JetBrains Junie MCP integration",
    }
    for name, desc in coming_soon.items():
        print(f"  • {name:<12} - {desc}")

    print("\n" + "=" * 70)
    print(f"Total implemented: {len(implemented)}")


def _display_system(system: DetectedSystem, verbose: bool = False) -> None:
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
