"""
Git synchronization CLI commands for KuzuMemory.

Provides commands to sync git commit history to memory system.
"""

import logging
from pathlib import Path

import click

from ..core.memory import KuzuMemory
from ..integrations.git_sync import GitSyncError, GitSyncManager
from ..utils.config_loader import get_config_loader
from ..utils.project_setup import get_project_db_path
from .cli_utils import rich_panel, rich_print

logger = logging.getLogger(__name__)


@click.group()
def git() -> None:
    """Git commit history synchronization commands."""
    pass


@git.command()
@click.option(
    "--initial",
    is_flag=True,
    help="Force full resync (ignore last sync timestamp)",
)
@click.option(
    "--incremental",
    is_flag=True,
    help="Only sync new commits since last sync",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be synced without storing",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Minimal output (for git hooks)",
)
@click.option(
    "--project-root",
    type=click.Path(),
    help="Project root path (optional)",
)
@click.pass_context
def sync(
    ctx: click.Context,
    initial: bool,
    incremental: bool,
    dry_run: bool,
    quiet: bool,
    project_root: str | None,
) -> None:
    """
    Synchronize git commit history to memory.

    Smart sync by default: initial sync if never synced, incremental otherwise.
    Use --initial to force full resync, --incremental for updates only.
    """
    from kuzu_memory.cli.service_manager import ServiceManager
    from kuzu_memory.services import ConfigService

    try:
        # Convert project_root to Path if provided
        project_root_path = (
            Path(project_root) if project_root else ctx.obj.get("project_root", Path.cwd())
        )
        db_path = get_project_db_path(project_root_path)
        config_loader = get_config_loader()
        config = config_loader.load_config()

        # Determine sync mode
        if initial and incremental:
            rich_print(
                "[red]Error:[/red] Cannot use --initial and --incremental together",
            )
            ctx.exit(1)

        mode = "auto"
        if initial:
            mode = "initial"
        elif incremental:
            mode = "incremental"

        # Create config service for GitSyncService
        config_service = ConfigService(project_root_path)
        config_service.initialize()

        try:
            # Use ServiceManager for GitSyncService lifecycle
            with ServiceManager.git_sync_service(config_service) as git_sync:
                if not git_sync.is_available():
                    if not quiet:
                        rich_print(
                            "[yellow]Git sync not available:[/yellow] Not a git repository or git sync disabled",
                        )
                    ctx.exit(0)

                # We need the GitSyncManager for the sync() method
                # GitSyncService exposes it via git_sync property (not in protocol but in implementation)
                sync_manager = git_sync.git_sync  # type: ignore[attr-defined]  # Runtime attribute from implementation

                # Need to inject memory store - create temporary memory instance
                with KuzuMemory(db_path=db_path, config=config) as memory:
                    sync_manager.memory_store = memory.memory_store

                    # Perform sync
                    if not quiet:
                        if dry_run:
                            rich_print("[cyan]Dry run:[/cyan] Previewing commits to sync...")
                        else:
                            rich_print(f"[cyan]Syncing git commits ({mode} mode)...[/cyan]")

                    result = sync_manager.sync(mode=mode, dry_run=dry_run)

                if not result["success"]:
                    rich_print(
                        f"[red]Sync failed:[/red] {result.get('error', 'Unknown error')}",
                    )
                    ctx.exit(1)

                # Display results
                if quiet:
                    # Minimal output for git hooks
                    if not dry_run:
                        print(f"Synced {result['commits_synced']} commits")
                else:
                    # Detailed output
                    if dry_run:
                        rich_panel(
                            f"[green]Dry Run Results[/green]\n\n"
                            f"Commits found: {result['commits_found']}\n\n"
                            f"Preview (first 10):",
                            title="Git Sync Preview",
                        )

                        if result.get("commits"):
                            for commit in result["commits"]:
                                rich_print(
                                    f"  [dim]{commit['sha']}[/dim] {commit['message'][:60]}..."
                                )
                    else:
                        status_msg = (
                            f"[green]Sync Complete[/green]\n\n"
                            f"Mode: {result['mode']}\n"
                            f"Commits found: {result['commits_found']}\n"
                            f"Commits synced: {result['commits_synced']}\n"
                        )

                        # Show skipped count if any duplicates were found
                        if result.get("commits_skipped", 0) > 0:
                            status_msg += (
                                f"Commits skipped (duplicates): {result['commits_skipped']}\n"
                            )

                        if result.get("last_sync_timestamp"):
                            status_msg += f"Last sync: {result['last_sync_timestamp']}\n"
                        if result.get("last_commit_sha"):
                            status_msg += f"Last commit: {result['last_commit_sha']}\n"

                        rich_panel(status_msg, title="Git Sync Status")

                # Save updated config with sync state
                if not dry_run and result["commits_synced"] > 0:
                    config.git_sync = sync_manager.config
                    # Use primary default config path
                    config_path = Path.home() / ".kuzu-memory" / "config.yaml"
                    config_loader.save_config(config, config_path)
                    if not quiet:
                        rich_print("[dim]Config updated with sync state[/dim]")

        finally:
            # Ensure cleanup of config service
            config_service.cleanup()

    except GitSyncError as e:
        rich_print(f"[red]Git sync error:[/red] {e}")
        ctx.exit(1)
    except Exception as e:
        logger.exception("Git sync failed")
        rich_print(f"[red]Unexpected error:[/red] {e}")
        ctx.exit(1)


@git.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show git sync status and configuration."""
    try:
        # Get project root and config
        project_root = ctx.obj.get("project_root", Path.cwd())
        config_loader = get_config_loader()
        config = config_loader.load_config()

        # Initialize git sync manager
        sync_manager = GitSyncManager(
            repo_path=project_root,
            config=config.git_sync,
        )

        status_info = sync_manager.get_sync_status()

        # Build status message
        if not status_info["available"]:
            rich_panel(
                f"[yellow]Git Sync Unavailable[/yellow]\n\n"
                f"Enabled: {status_info['enabled']}\n"
                f"Reason: {status_info.get('reason', 'Unknown')}",
                title="Git Sync Status",
            )
            return

        status_msg = (
            f"[green]Git Sync Available[/green]\n\n"
            f"Enabled: {status_info['enabled']}\n"
            f"Repository: {status_info['repo_path']}\n"
        )

        if status_info.get("last_sync_timestamp"):
            status_msg += f"Last sync: {status_info['last_sync_timestamp']}\n"
        else:
            status_msg += "Last sync: Never\n"

        if status_info.get("last_commit_sha"):
            status_msg += f"Last commit: {status_info['last_commit_sha']}\n"

        status_msg += (
            f"\nBranch patterns:\n"
            f"  Include: {', '.join(status_info['branch_include_patterns'])}\n"
            f"  Exclude: {', '.join(status_info['branch_exclude_patterns'])}\n"
            f"\nAuto-sync on push: {status_info['auto_sync_on_push']}"
        )

        rich_panel(status_msg, title="Git Sync Status")

    except Exception as e:
        logger.exception("Failed to get git sync status")
        rich_print(f"[red]Error:[/red] {e}")
        ctx.exit(1)


@git.command()
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing hooks",
)
@click.pass_context
def install_hooks(ctx: click.Context, force: bool) -> None:
    """Install git post-commit hook for automatic sync."""
    try:
        # Get project root
        project_root = ctx.obj.get("project_root", Path.cwd())

        # Find .git directory
        git_dir = project_root / ".git"
        if not git_dir.exists():
            # Try searching parent directories
            current = project_root
            for _ in range(5):  # Search up to 5 levels
                if (current / ".git").exists():
                    git_dir = current / ".git"
                    break
                current = current.parent

        if not git_dir.exists():
            rich_print(
                "[red]Error:[/red] Not a git repository (no .git directory found)",
            )
            ctx.exit(1)

        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        hook_file = hooks_dir / "post-commit"

        # Check if hook already exists
        if hook_file.exists() and not force:
            rich_print(
                f"[yellow]Hook already exists:[/yellow] {hook_file}\nUse --force to overwrite",
            )
            ctx.exit(1)

        # Create hook script
        hook_content = """#!/bin/sh
# KuzuMemory git post-commit hook
# Auto-sync commits to memory system

kuzu-memory git sync --incremental --quiet 2>/dev/null || true
"""

        hook_file.write_text(hook_content)
        hook_file.chmod(0o755)  # Make executable

        rich_panel(
            f"[green]Git Hook Installed[/green]\n\n"
            f"Location: {hook_file}\n"
            f"Type: post-commit\n\n"
            f"The hook will automatically sync commits after each commit.",
            title="Hook Installation Complete",
        )

    except Exception as e:
        logger.exception("Failed to install git hook")
        rich_print(f"[red]Error:[/red] {e}")
        ctx.exit(1)


@git.command()
@click.pass_context
def uninstall_hooks(ctx: click.Context) -> None:
    """Remove git post-commit hook."""
    try:
        # Get project root
        project_root = ctx.obj.get("project_root", Path.cwd())

        # Find .git directory
        git_dir = project_root / ".git"
        if not git_dir.exists():
            # Try searching parent directories
            current = project_root
            for _ in range(5):
                if (current / ".git").exists():
                    git_dir = current / ".git"
                    break
                current = current.parent

        if not git_dir.exists():
            rich_print(
                "[red]Error:[/red] Not a git repository (no .git directory found)",
            )
            ctx.exit(1)

        hook_file = git_dir / "hooks" / "post-commit"

        if not hook_file.exists():
            rich_print("[yellow]No hook found to remove[/yellow]")
            ctx.exit(0)

        # Check if it's our hook
        content = hook_file.read_text()
        if "KuzuMemory" not in content:
            rich_print(
                f"[yellow]Warning:[/yellow] Hook exists but doesn't appear to be KuzuMemory hook\n"
                f"Location: {hook_file}\n"
                f"Please remove manually if needed",
            )
            ctx.exit(1)

        # Remove hook
        hook_file.unlink()

        rich_panel(
            f"[green]Git Hook Removed[/green]\n\n"
            f"Location: {hook_file}\n\n"
            f"Auto-sync on commit is now disabled.",
            title="Hook Uninstallation Complete",
        )

    except Exception as e:
        logger.exception("Failed to uninstall git hook")
        rich_print(f"[red]Error:[/red] {e}")
        ctx.exit(1)
