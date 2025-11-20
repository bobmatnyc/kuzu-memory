"""
Setup command for KuzuMemory - combines initialization and installation with validation.

Provides a streamlined setup workflow that:
1. Detects project and platform
2. Initializes database
3. Installs MCP configuration
4. Validates the setup
5. Reports status
"""

import logging
import shutil
import sys
from pathlib import Path

import click

from ..installers.detection import AISystemDetector
from ..installers.registry import get_installer
from ..utils.project_setup import (
    find_project_root,
    get_project_db_path,
    get_project_memories_dir,
)
from .cli_utils import rich_panel, rich_print, rich_table
from .init_commands import init
from .install_unified import install_command

logger = logging.getLogger(__name__)


def _validate_database(db_path: Path) -> tuple[bool, str]:
    """
    Validate database exists and is accessible.

    Args:
        db_path: Path to the database

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        if not db_path.exists():
            return False, f"Database not found at {db_path}"

        # Check that parent directory exists (for database writes)
        parent_dir = db_path.parent
        if not parent_dir.exists() or not parent_dir.is_dir():
            return False, f"Database parent directory missing: {parent_dir}"

        # Check basic accessibility by trying to access it
        import os
        if not os.access(db_path, os.R_OK):
            return False, f"Database is not readable: {db_path}"

        return True, "Database exists and is accessible"

    except Exception as e:
        return False, f"Database validation failed: {e}"


def _validate_mcp_config(platform: str, project_root: Path) -> tuple[bool, str, Path | None]:
    """
    Validate MCP configuration exists and has correct args.

    Args:
        platform: Platform name (e.g., 'claude-code', 'cursor')
        project_root: Project root directory

    Returns:
        Tuple of (is_valid, message, config_path)
    """
    try:
        # Get installer to check config
        installer = get_installer(platform, project_root)
        if not installer:
            return False, f"No installer found for platform: {platform}", None

        # Check if required files exist
        config_path = None
        for file_pattern in installer.required_files:
            file_path = project_root / file_pattern
            if ".json" in file_pattern or "config" in file_pattern:
                config_path = file_path
                break

        if not config_path:
            return False, "Could not determine config file path", None

        if not config_path.exists():
            return False, f"MCP config not found at {config_path}", config_path

        # Validate config has correct args
        import json
        try:
            with open(config_path) as f:
                config = json.load(f)

            # Check for kuzu-memory server
            servers = config.get("mcpServers", {})
            if "kuzu-memory" not in servers:
                return False, "kuzu-memory server not found in MCP config", config_path

            kuzu_config = servers["kuzu-memory"]
            args = kuzu_config.get("args", [])

            # Check args are correct
            if args != ["mcp"]:
                return False, f"MCP server has incorrect args: {args} (should be ['mcp'])", config_path

            return True, f"MCP config valid at {config_path}", config_path

        except json.JSONDecodeError as e:
            return False, f"MCP config has invalid JSON: {e}", config_path

    except Exception as e:
        return False, f"MCP config validation failed: {e}", None


def _check_kuzu_memory_in_path() -> bool:
    """Check if kuzu-memory executable is in PATH."""
    return shutil.which("kuzu-memory") is not None


def _detect_available_platforms(project_root: Path) -> list[str]:
    """
    Detect available platforms that can be installed.

    Args:
        project_root: Project root directory

    Returns:
        List of platform names (only those with working installers)
    """
    detector = AISystemDetector(project_root)
    available = detector.detect_available()

    # Only include platforms with working installers
    supported_platforms = {"claude-code", "claude-desktop", "cursor", "vscode", "windsurf"}
    return [
        system.installer_name
        for system in available
        if system.installer_name in supported_platforms
    ]


@click.command()
@click.option(
    "--platform",
    type=click.Choice(["claude-code", "claude-desktop", "cursor", "vscode", "windsurf"]),
    help="Platform to install (auto-detect if not specified)",
)
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--force", is_flag=True, help="Force overwrite existing configuration")
@click.option("--skip-init", is_flag=True, help="Skip database initialization (only install)")
@click.option("--skip-install", is_flag=True, help="Skip MCP installation (only init)")
@click.pass_context
def setup(ctx, platform, dry_run, force, skip_init, skip_install):
    """
    🚀 Complete setup: Initialize + Install + Validate

    Combines database initialization and MCP installation in one command.
    Automatically detects project type and installs appropriate configuration.

    \b
    🎯 SETUP WORKFLOW:
      1. Detection   - Auto-detect project root and available platforms
      2. Initialize  - Create database and memory structure
      3. Install     - Configure MCP server for selected platform
      4. Validate    - Verify database and config are correct
      5. Report      - Show summary and next steps

    \b
    🎮 EXAMPLES:
      # Full setup with auto-detection
      kuzu-memory setup

      # Setup for specific platform
      kuzu-memory setup --platform claude-code

      # Preview what would be done
      kuzu-memory setup --dry-run

      # Force re-setup (overwrite existing)
      kuzu-memory setup --force

      # Only initialize database
      kuzu-memory setup --skip-install

      # Only install MCP (assume db exists)
      kuzu-memory setup --skip-init

    \b
    ⚙️  VALIDATION:
      Setup automatically validates:
      • Database exists and is accessible
      • MCP config exists with correct args: ["mcp"]
      • kuzu-memory is in PATH
      • Project structure is correct
    """
    try:
        # Get project root
        project_root = ctx.obj.get("project_root") or find_project_root()

        rich_panel(
            f"🚀 KuzuMemory Setup\n\n"
            f"Project: {project_root}\n"
            f"Mode: {'DRY RUN' if dry_run else 'LIVE'}\n"
            f"Force: {'Yes' if force else 'No'}",
            title="Setup Configuration",
            style="blue",
        )

        # Phase 1: Detection
        rich_print("\n📍 Phase 1: Detection", style="bold cyan")

        # Detect available platforms
        available_platforms = _detect_available_platforms(project_root)

        if not platform:
            if available_platforms:
                platform = available_platforms[0]
                rich_print(f"✓ Auto-detected platform: {platform}", style="green")
            else:
                rich_print("✗ No compatible platforms detected", style="red")
                rich_print("\nAvailable platforms: claude-code, claude-desktop, cursor, vscode, windsurf")
                rich_print("Specify with: kuzu-memory setup --platform <name>")
                sys.exit(1)
        else:
            rich_print(f"✓ Using specified platform: {platform}", style="green")

        if available_platforms:
            rich_print(f"  Other available platforms: {', '.join(available_platforms)}", style="dim")

        # Phase 2: Initialization
        if not skip_init:
            rich_print("\n📦 Phase 2: Database Initialization", style="bold cyan")

            db_path = get_project_db_path(project_root)
            memories_dir = get_project_memories_dir(project_root)

            if db_path.exists() and not force:
                rich_print(f"✓ Database already exists at {db_path}", style="green")
            else:
                if dry_run:
                    rich_print(f"[DRY RUN] Would initialize database at {db_path}", style="yellow")
                else:
                    rich_print(f"Initializing database at {db_path}...")
                    ctx.invoke(init, force=force, config_path=None)
                    rich_print("✓ Database initialized", style="green")
        else:
            rich_print("\n⏭️  Phase 2: Skipped (--skip-init)", style="dim")

        # Phase 3: Installation
        if not skip_install:
            rich_print("\n🔌 Phase 3: MCP Installation", style="bold cyan")

            if dry_run:
                rich_print(f"[DRY RUN] Would install MCP config for {platform}", style="yellow")
            else:
                rich_print(f"Installing MCP configuration for {platform}...")
                # Use the unified install command
                ctx.invoke(install_command, integration=platform, verbose=False)
                rich_print("✓ MCP configuration installed", style="green")
        else:
            rich_print("\n⏭️  Phase 3: Skipped (--skip-install)", style="dim")

        # Phase 4: Validation
        rich_print("\n✅ Phase 4: Validation", style="bold cyan")

        validation_results = []

        # Check 1: Database
        if not skip_init:
            db_path = get_project_db_path(project_root)
            db_valid, db_msg = _validate_database(db_path)
            validation_results.append(("Database", db_valid, db_msg))

        # Check 2: MCP Config
        if not skip_install:
            mcp_valid, mcp_msg, config_path = _validate_mcp_config(platform, project_root)
            validation_results.append(("MCP Config", mcp_valid, mcp_msg))

        # Check 3: kuzu-memory in PATH
        in_path = _check_kuzu_memory_in_path()
        path_msg = "kuzu-memory found in PATH" if in_path else "kuzu-memory not found in PATH"
        validation_results.append(("Executable", in_path, path_msg))

        # Display validation results
        for check_name, is_valid, message in validation_results:
            icon = "✓" if is_valid else "✗"
            style = "green" if is_valid else "red"
            rich_print(f"{icon} {check_name}: {message}", style=style)

        # Check if all validations passed
        all_valid = all(result[1] for result in validation_results)

        # Phase 5: Report
        rich_print("\n📊 Phase 5: Setup Summary", style="bold cyan")

        if all_valid:
            rich_panel(
                f"Setup Complete! 🎉\n\n"
                f"✓ Database: {get_project_db_path(project_root)}\n"
                f"✓ Platform: {platform}\n"
                f"✓ All validations passed\n\n"
                f"Next steps:\n"
                f"• Store your first memory: kuzu-memory remember 'Your info here'\n"
                f"• Enhance prompts: kuzu-memory enhance 'Your question'\n"
                f"• Check status: kuzu-memory status\n"
                f"• View recent: kuzu-memory recent\n\n"
                f"Platform-specific:\n"
                + _get_platform_next_steps(platform),
                title="✅ Setup Successful",
                style="green",
            )
        else:
            failed_checks = [name for name, valid, _ in validation_results if not valid]
            rich_panel(
                f"Setup completed with issues ⚠️\n\n"
                f"Failed checks: {', '.join(failed_checks)}\n\n"
                f"Run diagnostics for more details:\n"
                f"  kuzu-memory doctor\n\n"
                f"Or try force re-setup:\n"
                f"  kuzu-memory setup --force",
                title="⚠️  Setup Incomplete",
                style="yellow",
            )
            sys.exit(1)

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Setup failed: {e}", style="red")
        rich_print("\nTry with --debug flag for more details:", style="dim")
        rich_print("  kuzu-memory --debug setup", style="dim")
        sys.exit(1)


def _get_platform_next_steps(platform: str) -> str:
    """Get platform-specific next steps."""
    steps = {
        "claude-code": (
            "• Reload Claude Code window (Cmd+R or Ctrl+R)\n"
            "• MCP tools + hooks are now active\n"
            "• Check .claude/config.local.json for config"
        ),
        "claude-desktop": (
            "• Restart Claude Desktop application\n"
            "• Open a new conversation\n"
            "• MCP tools will be available in chat"
        ),
        "cursor": (
            "• Reload or restart Cursor IDE\n"
            "• MCP server will be active\n"
            "• Check .cursor/mcp.json for config"
        ),
        "vscode": (
            "• Reload or restart VS Code\n"
            "• MCP server will be active\n"
            "• Check .vscode/mcp.json for config"
        ),
        "windsurf": (
            "• Reload or restart Windsurf IDE\n"
            "• MCP server will be active\n"
            "• Check ~/.codeium/windsurf/mcp_config.json"
        ),
    }
    return steps.get(platform, "• Restart your IDE/editor\n• MCP server should be active")


__all__ = ["setup"]
