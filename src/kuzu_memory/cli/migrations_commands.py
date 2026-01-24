"""CLI commands for managing migrations."""

from __future__ import annotations

import click

from ..__version__ import __version__
from ..migrations import get_migration_manager
from ..migrations.base import MigrationType
from .cli_utils import rich_print


@click.group(name="migrations")
def migrations_group() -> None:
    """Manage database and configuration migrations."""
    pass


@migrations_group.command("status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed history")
def migrations_status(verbose: bool) -> None:
    """Show migration status and history."""
    from ..migrations import get_migration_manager

    manager = get_migration_manager()

    rich_print("[bold]Migration Status[/bold]")
    rich_print(f"Current version: [cyan]{__version__}[/cyan]")
    rich_print(f"Last migrated: [cyan]{manager.state.last_version}[/cyan]")
    rich_print("")

    pending = manager.get_pending_migrations(__version__)
    if pending:
        rich_print("[yellow]Pending migrations:[/yellow]")
        for m in pending:
            type_badge = f"[{m.migration_type.value}]"
            rich_print(f"  • {m.name} {type_badge}: {m.description()}")
    else:
        rich_print("[green]✓ No pending migrations[/green]")

    if verbose:
        rich_print("")
        history = manager.get_history(10)
        if history:
            rich_print("[bold]Recent history:[/bold]")
            for h in history:
                status = "[green]✓[/green]" if h.success else "[red]✗[/red]"
                timestamp = h.timestamp[:10]  # Just the date
                rich_print(f"  {status} {h.name} [{h.migration_type}] ({timestamp})")
                if h.changes:
                    for change in h.changes[:3]:  # Show first 3 changes
                        rich_print(f"      - {change}")


@migrations_group.command("run")
@click.option("--dry-run", is_flag=True, help="Show what would run without executing")
@click.option(
    "--type",
    "migration_type",
    type=click.Choice([t.value for t in MigrationType]),
    help="Only run specific type",
)
def migrations_run(dry_run: bool, migration_type: str | None) -> None:
    """Run pending migrations."""
    manager = get_migration_manager()

    types = None
    if migration_type:
        types = [MigrationType(migration_type)]

    rich_print(f"[bold]Running migrations to v{__version__}[/bold]")
    if dry_run:
        rich_print("[yellow](dry run - no changes will be made)[/yellow]")
    rich_print("")

    results = manager.run_migrations(__version__, dry_run=dry_run, migration_types=types)

    if not results:
        rich_print("[green]✓ No migrations needed[/green]")
        return

    for result in results:
        status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
        rich_print(f"{status} {result.message}")

        if result.changes:
            for change in result.changes:
                rich_print(f"    - {change}")

        if result.warnings:
            for warning in result.warnings:
                rich_print(f"    [yellow]⚠ {warning}[/yellow]")


@migrations_group.command("reset")
@click.confirmation_option(prompt="This will reset migration history. Continue?")
def migrations_reset() -> None:
    """Reset migration state (for development)."""
    manager = get_migration_manager()
    manager.reset_state()
    rich_print("[green]✓ Migration state reset[/green]")


@migrations_group.command("history")
@click.option("--limit", default=10, help="Number of history entries to show")
@click.option("--type", "migration_type", help="Filter by migration type")
def migrations_history(limit: int, migration_type: str | None) -> None:
    """Show migration history."""
    manager = get_migration_manager()

    history = manager.get_history(limit)

    # Filter by type if specified
    if migration_type:
        history = [h for h in history if h.migration_type == migration_type]

    if not history:
        rich_print("[yellow]No migration history found[/yellow]")
        return

    rich_print(f"[bold]Migration History (last {len(history)} entries)[/bold]")
    rich_print("")

    for h in history:
        status = "[green]✓[/green]" if h.success else "[red]✗[/red]"
        timestamp = h.timestamp.split("T")[0]  # Just the date
        rich_print(f"{status} [cyan]{h.name}[/cyan] [{h.migration_type}] - {timestamp}")
        rich_print(f"    {h.message}")

        if h.changes:
            rich_print("    [bold]Changes:[/bold]")
            for change in h.changes:
                rich_print(f"      - {change}")


# Alias for convenience
migrations = migrations_group
