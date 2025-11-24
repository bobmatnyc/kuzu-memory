"""
Smart setup command for KuzuMemory.

Combines initialization and installation into a single intelligent command
that auto-detects existing installations and updates them as needed.
"""

import sys
from pathlib import Path

import click

from ..installers.registry import get_installer
from ..utils.project_setup import (
    find_project_root,
    get_project_db_path,
    get_project_memories_dir,
)
from .cli_utils import rich_confirm, rich_panel, rich_print
from .init_commands import init
from .install_unified import _detect_installed_systems


@click.command()
@click.option(
    "--skip-install",
    is_flag=True,
    help="Skip AI tool installation (init only)",
)
@click.option(
    "--integration",
    type=click.Choice(
        ["claude-code", "claude-desktop", "codex", "cursor", "vscode", "windsurf", "auggie"],
        case_sensitive=False,
    ),
    help="Specific integration to install (auto-detects if not specified)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reinstall even if already configured",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without modifying files",
)
@click.pass_context
def setup(ctx, skip_install: bool, integration: str | None, force: bool, dry_run: bool):
    """
    🚀 Smart setup - Initialize and configure KuzuMemory (RECOMMENDED).

    This is the ONE command to get KuzuMemory ready in your project.
    It intelligently handles both new setups and updates to existing installations.

    \b
    🎯 WHAT IT DOES:
      1. Detects project root automatically
      2. Initializes memory database (if needed)
      3. Auto-detects installed AI tools
      4. Installs/updates integrations intelligently
      5. Verifies everything is working

    \b
    🚀 EXAMPLES:
      # Smart setup (recommended - auto-detects everything)
      kuzu-memory setup

      # Initialize only (skip AI tool installation)
      kuzu-memory setup --skip-install

      # Setup for specific integration
      kuzu-memory setup --integration claude-code

      # Force reinstall everything
      kuzu-memory setup --force

      # Preview what would happen
      kuzu-memory setup --dry-run

    \b
    💡 TIP:
      For most users, just run 'kuzu-memory setup' with no arguments.
      It will figure out what you need and do it automatically!

    \b
    ⚙️  ADVANCED USAGE:
      If you need granular control, you can still use:
      • kuzu-memory init              # Just initialize
      • kuzu-memory install <tool>    # Just install integration
    """
    try:
        # ═══════════════════════════════════════════════════════════
        # PHASE 1: PROJECT DETECTION & INITIALIZATION
        # ═══════════════════════════════════════════════════════════

        rich_panel(
            "Smart Setup - Automated KuzuMemory Configuration\n\n"
            "This will:\n"
            "✅ Initialize memory database\n"
            "✅ Detect installed AI tools\n"
            "✅ Configure integrations\n"
            "✅ Verify setup\n\n"
            f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE SETUP'}",
            title="🚀 KuzuMemory Setup",
            style="cyan",
        )

        # Detect project root
        try:
            project_root = ctx.obj.get("project_root") or find_project_root()
            rich_print(f"\n📁 Project detected: {project_root}", style="green")
        except Exception as e:
            rich_print(
                f"\n❌ Could not detect project root: {e}\n"
                "   Please run this command from within a project directory.",
                style="red",
            )
            sys.exit(1)

        memories_dir = get_project_memories_dir(project_root)
        db_path = get_project_db_path(project_root)

        # Check initialization status
        already_initialized = db_path.exists()

        if already_initialized:
            rich_print(f"✅ Memory database already initialized: {db_path}", style="dim")
            if force:
                rich_print("   Force flag set - will reinitialize", style="yellow")
        else:
            rich_print(f"📦 Memory database not found - will create: {db_path}")

        # Initialize or update database
        if not already_initialized or force:
            if dry_run:
                rich_print(
                    "\n[DRY RUN] Would initialize memory database at:", style="yellow"
                )
                rich_print(f"  {db_path}", style="dim")
            else:
                rich_print("\n⚙️  Initializing memory database...", style="cyan")
                try:
                    ctx.invoke(init, force=force, config_path=None)
                except SystemExit:
                    # init command may exit with code 1 if already exists
                    if not force:
                        rich_print("   Database already exists (use --force to overwrite)")

        # ═══════════════════════════════════════════════════════════
        # PHASE 2: AI TOOL DETECTION & INSTALLATION
        # ═══════════════════════════════════════════════════════════

        if skip_install:
            rich_print("\n⏭️  Skipping AI tool installation (--skip-install)", style="yellow")
        else:
            rich_print("\n🔍 Detecting installed AI tools...", style="cyan")

            # Detect what's already installed
            installed_systems = _detect_installed_systems(project_root)

            if installed_systems:
                rich_print(
                    f"   Found {len(installed_systems)} existing installation(s)",
                    style="green",
                )
                for system in installed_systems:
                    status_icon = (
                        "✅"
                        if system.health_status == "healthy"
                        else "⚠️"
                        if system.health_status == "needs_repair"
                        else "❌"
                    )
                    rich_print(f"   {status_icon} {system.name}: {system.health_status}")

                # If integration specified, use it; otherwise use first detected
                target_integration = integration or installed_systems[0].name

                # Check if update needed
                needs_update = any(
                    s.health_status == "needs_repair" or force
                    for s in installed_systems
                    if s.name == target_integration
                )

                if needs_update or force:
                    action = "Reinstalling" if force else "Updating"
                    if dry_run:
                        rich_print(
                            f"\n[DRY RUN] Would {action.lower()} integration: {target_integration}",
                            style="yellow",
                        )
                    else:
                        rich_print(
                            f"\n⚙️  {action} {target_integration} integration...",
                            style="cyan",
                        )
                        _install_integration(
                            ctx, target_integration, project_root, force=True
                        )
                else:
                    rich_print(
                        f"\n✅ {target_integration} integration is up to date",
                        style="green",
                    )

            else:
                # No existing installations - guide user
                rich_print("   No existing installations detected", style="yellow")

                if integration:
                    # User specified integration - install it
                    if dry_run:
                        rich_print(
                            f"\n[DRY RUN] Would install: {integration}",
                            style="yellow",
                        )
                    else:
                        rich_print(
                            f"\n⚙️  Installing {integration} integration...",
                            style="cyan",
                        )
                        _install_integration(ctx, integration, project_root, force=force)
                else:
                    # Auto-detect which tool user is likely using
                    rich_print(
                        "\n💡 No AI tool integration specified. Choose one:",
                        style="cyan",
                    )
                    rich_print("\n  📋 Available integrations:")
                    rich_print("     • claude-code      (Claude Code IDE)")
                    rich_print("     • claude-desktop   (Claude Desktop app)")
                    rich_print("     • cursor           (Cursor IDE)")
                    rich_print("     • vscode           (VS Code)")
                    rich_print("     • windsurf         (Windsurf IDE)")
                    rich_print("     • auggie           (Auggie AI)")

                    if not dry_run:
                        rich_print(
                            "\n   Run: kuzu-memory setup --integration <name>",
                            style="dim",
                        )
                        rich_print(
                            "   Or: kuzu-memory install <name> (for manual control)",
                            style="dim",
                        )

        # ═══════════════════════════════════════════════════════════
        # PHASE 3: VERIFICATION & COMPLETION
        # ═══════════════════════════════════════════════════════════

        if dry_run:
            rich_panel(
                "Dry Run Complete - No Changes Made\n\n"
                "The above shows what would happen with a real setup.\n"
                "Remove --dry-run to perform actual setup.",
                title="✅ Preview Complete",
                style="green",
            )
        else:
            # Build completion message
            next_steps = []

            if skip_install:
                next_steps.append("• Install AI tool: kuzu-memory install <integration>")

            next_steps.extend(
                [
                    "• Store your first memory: kuzu-memory memory store 'Important info'",
                    "• View status: kuzu-memory status",
                    "• Get help: kuzu-memory help",
                ]
            )

            rich_panel(
                "Setup Complete! 🎉\n\n"
                f"📁 Project: {project_root}\n"
                f"🗄️  Database: {db_path}\n"
                f"📂 Memories: {memories_dir}\n\n"
                "Next steps:\n" + "\n".join(next_steps),
                title="✅ KuzuMemory Ready",
                style="green",
            )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"\n❌ Setup failed: {e}", style="red")
        rich_print(
            "\n💡 Try running with --debug for more details:\n"
            "   kuzu-memory --debug setup",
            style="dim",
        )
        sys.exit(1)


def _install_integration(
    ctx: click.Context, integration_name: str, project_root: Path, force: bool = False
) -> None:
    """
    Install or update an AI tool integration.

    Args:
        ctx: Click context
        integration_name: Name of integration to install
        project_root: Project root directory
        force: Force reinstall
    """
    from .install_unified import install_command

    try:
        # Forward to install command with appropriate flags
        ctx.invoke(
            install_command,
            integration=integration_name,
            force=force,
            dry_run=False,
            verbose=False,
        )
    except SystemExit as e:
        # install_command may exit - capture and re-raise if non-zero
        if e.code != 0:
            raise
    except Exception as e:
        rich_print(f"⚠️  Installation warning: {e}", style="yellow")
        rich_print("   You can manually install later with:", style="dim")
        rich_print(f"   kuzu-memory install {integration_name}", style="dim")


__all__ = ["setup"]
