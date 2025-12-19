"""
Smart setup command for KuzuMemory.

Combines initialization and installation into a single intelligent command
that auto-detects existing installations and updates them as needed.
"""

import sys
from pathlib import Path

import click

from ..installers.claude_hooks import ClaudeHooksInstaller
from ..utils.project_setup import (
    find_project_root,
    get_project_db_path,
    get_project_memories_dir,
)
from .cli_utils import rich_panel, rich_print
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
        [
            "claude-code",
            "claude-desktop",
            "codex",
            "cursor",
            "vscode",
            "windsurf",
            "auggie",
        ],
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
@click.option(
    "--skip-git-hooks",
    is_flag=True,
    help="Skip git post-commit hooks installation (auto-installs when git repo detected)",
)
@click.pass_context
def setup(
    ctx: click.Context,
    skip_install: bool,
    integration: str | None,
    force: bool,
    dry_run: bool,
    skip_git_hooks: bool,
) -> None:
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
      5. Auto-installs Claude Code hooks and MCP
      6. Auto-installs git hooks (when git repo detected)
      7. Verifies everything is working

    \b
    🚀 EXAMPLES:
      # Smart setup (recommended - auto-detects everything)
      kuzu-memory setup

      # Setup without git hooks
      kuzu-memory setup --skip-git-hooks

      # Setup for specific integration without git hooks
      kuzu-memory setup --integration claude-code --skip-git-hooks

      # Initialize only (skip AI tool installation)
      kuzu-memory setup --skip-install

      # Force reinstall everything
      kuzu-memory setup --force

      # Preview what would happen
      kuzu-memory setup --dry-run

    \b
    💡 TIP:
      For most users, just run 'kuzu-memory setup' with no arguments.
      Git hooks and Claude Code hooks are installed automatically.

    \b
    ⚙️  ADVANCED USAGE:
      If you need granular control, you can still use:
      • kuzu-memory init                # Just initialize
      • kuzu-memory install <tool>      # Just install integration
      • kuzu-memory git install-hooks   # Just install git hooks
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
            "✅ Install Claude Code hooks and MCP\n"
            "✅ Install git hooks (if git repo detected)\n"
            "✅ Verify setup\n\n"
            f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE SETUP'}",
            title="🚀 KuzuMemory Setup",
            style="cyan",
        )

        # Detect project root
        try:
            project_root_raw = ctx.obj.get("project_root")
            if project_root_raw is None:
                project_root_raw = find_project_root()

            # Ensure project_root is a Path object for type safety
            if isinstance(project_root_raw, str):
                project_root = Path(project_root_raw)
            elif isinstance(project_root_raw, Path):
                project_root = project_root_raw
            else:
                # Should not happen, but handle gracefully
                raise ValueError(f"Unexpected project_root type: {type(project_root_raw)}")

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
                rich_print("\n[DRY RUN] Would initialize memory database at:", style="yellow")
                rich_print(f"  {db_path}", style="dim")
            else:
                rich_print("\n⚙️  Initializing memory database...", style="cyan")
                try:
                    # Explicitly pass None for Path-typed options to avoid Sentinel error
                    ctx.invoke(init, force=force, config_path=None, project_root=None)
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
                        _install_integration(ctx, target_integration, project_root, force=True)
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
        # PHASE 2.25: CLAUDE CODE HOOKS & MCP INSTALLATION
        # ═══════════════════════════════════════════════════════════

        claude_hooks_installed = False
        if not skip_install:
            if dry_run:
                rich_print(
                    "\n[DRY RUN] Would install Claude Code hooks and MCP",
                    style="yellow",
                )
            else:
                rich_print("\n🪝 Installing Claude Code hooks and MCP...", style="cyan")
                try:
                    hooks_installer = ClaudeHooksInstaller(project_root)
                    # Always update hooks on setup - no force flag needed
                    hooks_result = hooks_installer.install(force=True, dry_run=dry_run)
                    if hooks_result.success:
                        rich_print("  ✅ Claude Code hooks and MCP configured", style="green")
                        claude_hooks_installed = True
                    else:
                        rich_print(
                            f"  ⚠️ Claude Code hooks: {hooks_result.message}",
                            style="yellow",
                        )
                except Exception as e:
                    rich_print(
                        f"  ⚠️ Claude Code hooks installation failed: {e}",
                        style="yellow",
                    )
                    rich_print(
                        "    You can install manually: kuzu-memory install claude-code",
                        style="dim",
                    )

        # ═══════════════════════════════════════════════════════════
        # PHASE 2.5: GIT HOOKS INSTALLATION
        # ═══════════════════════════════════════════════════════════

        git_hooks_installed = False
        git_repo_detected = _detect_git_repository(project_root)

        if git_repo_detected and not skip_git_hooks:
            if dry_run:
                rich_print(
                    "\n[DRY RUN] Would install git hooks for auto-sync",
                    style="yellow",
                )
            else:
                rich_print("\n🪝 Installing git hooks...", style="cyan")
                # Always update git hooks on setup - no force flag needed
                git_hooks_installed = _install_git_hooks(ctx, project_root, force=True)
        elif not git_repo_detected and not skip_git_hooks:
            rich_print(
                "\n⚠️  Git repository not detected - skipping git hooks installation",
                style="yellow",
            )

        # ═══════════════════════════════════════════════════════════
        # PHASE 2.75: VERIFY HOOKS INSTALLATION
        # ═══════════════════════════════════════════════════════════

        if not skip_install and not dry_run:
            # Verify hooks were installed correctly
            rich_print("\n🔍 Verifying hooks installation...", style="cyan")

            try:
                from ..services import ConfigService
                from .async_utils import run_async
                from .service_manager import ServiceManager

                config_service = ConfigService(project_root)
                config_service.initialize()

                with ServiceManager.diagnostic_service(config_service) as diagnostic:
                    hooks_status = run_async(diagnostic.check_hooks_status(project_root))

                    overall = hooks_status["overall_status"]
                    if overall == "fully_configured":
                        rich_print("  ✅ All hooks verified successfully", style="green")
                    elif overall == "partially_configured":
                        rich_print("  ⚠️  Hooks partially configured", style="yellow")

                        # Show what's missing
                        if not hooks_status["git_hooks"]["installed"] and git_repo_detected:
                            rich_print(
                                "    - Git hooks: Not installed (use --with-git-hooks)",
                                style="dim",
                            )
                        if not hooks_status["claude_code_hooks"]["installed"]:
                            rich_print("    - Claude Code hooks: Not configured", style="dim")
                    else:
                        rich_print("  ⚠️  Hooks verification failed", style="yellow")

                config_service.cleanup()

            except Exception as e:
                rich_print(f"  ⚠️  Hooks verification skipped: {e}", style="dim")

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

            # Add hooks status to next steps
            if git_hooks_installed:
                next_steps.append("✅ Git hooks installed - commits will auto-sync to memory")
            elif not skip_git_hooks and git_repo_detected:
                next_steps.append("💡 Note: Git hooks installation attempted - check status above")
            elif skip_git_hooks and git_repo_detected:
                next_steps.append("💡 Enable auto-sync: kuzu-memory git install-hooks")

            if claude_hooks_installed:
                next_steps.append("✅ Claude Code hooks configured - ready to use")

            next_steps.extend(
                [
                    "• Store your first memory: kuzu-memory memory store 'Important info'",
                    "• View status: kuzu-memory status",
                    "• Get help: kuzu-memory help",
                ]
            )

            # Determine hooks status messages
            if git_hooks_installed:
                git_hooks_status = "✅ Installed"
            elif skip_git_hooks:
                git_hooks_status = "⏭️  Skipped (--skip-git-hooks)"
            elif not git_repo_detected:
                git_hooks_status = "⚠️  Not installed (no git repo)"
            else:
                git_hooks_status = "❌ Not installed"

            if claude_hooks_installed:
                claude_hooks_status = "✅ Installed"
            elif skip_install:
                claude_hooks_status = "⏭️  Skipped (--skip-install)"
            else:
                claude_hooks_status = "❌ Not installed"

            rich_panel(
                "Setup Complete! 🎉\n\n"
                f"📁 Project: {project_root}\n"
                f"🗄️  Database: {db_path}\n"
                f"📂 Memories: {memories_dir}\n"
                f"🪝 Git Hooks: {git_hooks_status}\n"
                f"🤖 Claude Code Hooks: {claude_hooks_status}\n\n"
                "Next steps:\n" + "\n".join(next_steps),
                title="✅ KuzuMemory Ready",
                style="green",
            )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"\n❌ Setup failed: {e}", style="red")
        rich_print(
            "\n💡 Try running with --debug for more details:\n   kuzu-memory --debug setup",
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
            project_root=None,
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


def _detect_git_repository(project_root: Path) -> bool:
    """
    Check if project_root is in a git repository.

    Searches up to 5 parent directories for .git directory.

    Args:
        project_root: Project root directory to start search

    Returns:
        True if git repository detected, False otherwise
    """
    current = project_root
    for _ in range(5):
        if (current / ".git").exists():
            return True
        if current == current.parent:
            break
        current = current.parent
    return False


def _find_git_directory(project_root: Path) -> Path | None:
    """
    Find .git directory by searching up directory tree.

    Searches up to 5 parent directories for .git directory.

    Args:
        project_root: Project root directory to start search

    Returns:
        Path to .git directory if found, None otherwise
    """
    current = project_root
    for _ in range(5):
        git_dir = current / ".git"
        if git_dir.exists():
            return git_dir
        if current == current.parent:
            break
        current = current.parent
    return None


def _install_git_hooks(ctx: click.Context, project_root: Path, force: bool = False) -> bool:
    """
    Install git post-commit hooks for automatic sync.

    Delegates to the existing git install-hooks command.

    Args:
        ctx: Click context
        project_root: Project root directory
        force: Force overwrite existing hooks

    Returns:
        True if hooks installed successfully, False otherwise
    """
    try:
        # Delegate to git install-hooks command
        from .git_commands import install_hooks as git_install_hooks_cmd

        ctx.invoke(git_install_hooks_cmd, force=force)
        rich_print("✅ Git hooks installed successfully", style="green")
        return True

    except SystemExit as e:
        if e.code != 0:
            rich_print("⚠️  Git hooks installation failed", style="yellow")
            rich_print(
                "   You can install manually: kuzu-memory git install-hooks",
                style="dim",
            )
        return False

    except Exception as e:
        rich_print(f"⚠️  Git hooks warning: {e}", style="yellow")
        rich_print(
            "   You can install manually: kuzu-memory git install-hooks",
            style="dim",
        )
        return False


__all__ = ["setup"]
