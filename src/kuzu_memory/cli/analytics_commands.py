"""
Analytics CLI commands for KuzuMemory.

Provides commands for viewing access statistics, identifying stale memories,
and managing memory analytics.
"""

import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click

from ..core.config import KuzuMemoryConfig
from ..monitoring.access_tracker import get_access_tracker
from ..storage.kuzu_adapter import KuzuAdapter
from .cli_utils import rich_print, rich_table
from .service_manager import ServiceManager

logger = logging.getLogger(__name__)


@click.group()
def analytics() -> None:
    """
    📊 Memory access analytics and insights.

    View memory usage patterns, identify stale memories,
    and get insights for optimization.

    \b
    🎮 COMMANDS:
      show           Show access tracking statistics
      top-accessed   Show most frequently accessed memories
      stale          Show stale memories (candidates for pruning)

    Use 'kuzu-memory analytics COMMAND --help' for detailed help.
    """
    pass


@analytics.command()
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def show(ctx: click.Context, db_path: str | None) -> None:
    """
    📊 Show access tracking statistics.

    Display current statistics for memory access tracking including
    total tracked accesses, batch writes, and queue status.

    \b
    🎮 EXAMPLES:
      # Show tracking stats for current project
      kuzu-memory analytics show

      # Show stats for specific database
      kuzu-memory analytics show --db-path /path/to/db
    """
    try:
        # Get database path
        db_path_obj = Path(db_path) if db_path else ServiceManager._get_db_path(ctx)

        # Get tracker statistics
        tracker = get_access_tracker(db_path_obj)
        stats = tracker.get_stats()

        # Create statistics table
        table = rich_table(title="📊 Access Tracking Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Tracked", str(stats["total_tracked"]))
        table.add_row("Total Batches", str(stats["total_batches"]))
        table.add_row("Total Writes", str(stats["total_writes"]))
        table.add_row("Queue Size", str(stats["queue_size"]))
        table.add_row("Batch Interval", f"{stats['batch_interval']}s")
        table.add_row("Batch Size", str(stats["batch_size"]))

        last_batch = stats["last_batch_time"]
        if last_batch:
            table.add_row("Last Batch", last_batch)
        else:
            table.add_row("Last Batch", "Never")

        rich_print(table)

        # Show efficiency metrics
        if stats["total_batches"] > 0:
            avg_batch_size = stats["total_writes"] / stats["total_batches"]
            rich_print(
                f"\n✅ Average batch size: {avg_batch_size:.1f} writes/batch",
                style="green",
            )

    except Exception as e:
        if ctx.obj and ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Failed to get statistics: {e}", style="red")
        sys.exit(1)


@analytics.command()
@click.option("--limit", default=20, help="Number of results to show (default: 20)")
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def top_accessed(ctx: click.Context, limit: int, db_path: str | None) -> None:
    """
    🔝 Show most frequently accessed memories.

    Display memories ordered by access count to identify
    the most valuable memories in your system.

    \b
    🎮 EXAMPLES:
      # Show top 20 accessed memories
      kuzu-memory analytics top-accessed

      # Show top 50 accessed memories
      kuzu-memory analytics top-accessed --limit 50

      # Custom database path
      kuzu-memory analytics top-accessed --db-path /path/to/db
    """
    try:
        # Get database path
        db_path_obj = Path(db_path) if db_path else ServiceManager._get_db_path(ctx)

        # Query top accessed memories
        config = KuzuMemoryConfig.default()
        adapter = KuzuAdapter(db_path_obj, config)

        query = """
            MATCH (m:Memory)
            WHERE m.access_count IS NOT NULL AND m.access_count > 0
            RETURN m.id AS id,
                   m.content AS content,
                   m.access_count AS access_count,
                   m.accessed_at AS accessed_at,
                   m.created_at AS created_at
            ORDER BY m.access_count DESC
            LIMIT $limit
        """

        with adapter.get_connection() as conn:
            result = conn.execute(query, {"limit": limit})
            rows = result.get_as_pl()

        if len(rows) == 0:
            rich_print("ℹ️  No accessed memories found", style="yellow")
            rich_print(
                "   Memories will appear here after recall operations track access",
                style="dim",
            )
            return

        # Create results table
        table = rich_table(title=f"🔝 Top {limit} Accessed Memories")
        table.add_column("Access Count", style="cyan", justify="right")
        table.add_column("Content", style="white", no_wrap=False, max_width=60)
        table.add_column("Last Accessed", style="dim")

        for row in rows:
            content = str(row["content"])
            # Truncate long content
            if len(content) > 100:
                content = content[:97] + "..."

            # Format last accessed time
            accessed_at = row["accessed_at"]
            if accessed_at:
                try:
                    accessed_time = datetime.fromisoformat(accessed_at.replace("Z", "+00:00"))
                    now = datetime.now(UTC)
                    delta = now - accessed_time

                    if delta.days > 0:
                        time_str = f"{delta.days}d ago"
                    elif delta.seconds >= 3600:
                        time_str = f"{delta.seconds // 3600}h ago"
                    elif delta.seconds >= 60:
                        time_str = f"{delta.seconds // 60}m ago"
                    else:
                        time_str = "just now"
                except Exception:
                    time_str = "unknown"
            else:
                time_str = "never"

            table.add_row(str(row["access_count"]), content, time_str)

        rich_print(table)

        # Summary statistics
        total_accesses = sum(row["access_count"] for row in rows)
        rich_print(
            f"\n✅ Total accesses across top {len(rows)} memories: {total_accesses}",
            style="green",
        )

    except Exception as e:
        if ctx.obj and ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Failed to retrieve top accessed memories: {e}", style="red")
        sys.exit(1)


@analytics.command()
@click.option(
    "--days",
    default=90,
    help="Days since last access to consider stale (default: 90)",
)
@click.option("--limit", default=50, help="Number of results to show (default: 50)")
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def stale(ctx: click.Context, days: int, limit: int, db_path: str | None) -> None:
    """
    🗑️  Show stale memories (candidates for pruning).

    Display memories that haven't been accessed in a specified
    number of days. These are candidates for removal or archival.

    \b
    🎮 EXAMPLES:
      # Show memories not accessed in 90 days
      kuzu-memory analytics stale

      # Show memories not accessed in 180 days
      kuzu-memory analytics stale --days 180

      # Show top 100 stale memories
      kuzu-memory analytics stale --limit 100

      # Custom database path
      kuzu-memory analytics stale --db-path /path/to/db
    """
    try:
        # Get database path
        db_path_obj = Path(db_path) if db_path else ServiceManager._get_db_path(ctx)

        # Calculate cutoff date
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        # Query stale memories
        config = KuzuMemoryConfig.default()
        adapter = KuzuAdapter(db_path_obj, config)

        query = """
            MATCH (m:Memory)
            WHERE (m.accessed_at IS NULL OR m.accessed_at < $cutoff_date)
              AND m.created_at < $cutoff_date
            RETURN m.id AS id,
                   m.content AS content,
                   m.accessed_at AS accessed_at,
                   m.created_at AS created_at,
                   COALESCE(m.access_count, 0) AS access_count
            ORDER BY m.created_at ASC
            LIMIT $limit
        """

        with adapter.get_connection() as conn:
            result = conn.execute(query, {"cutoff_date": cutoff_iso, "limit": limit})
            rows = result.get_as_pl()

        if len(rows) == 0:
            rich_print(
                f"✅ No stale memories found (older than {days} days without access)",
                style="green",
            )
            return

        # Create results table
        table = rich_table(title=f"🗑️  Stale Memories (>{days} days)")
        table.add_column("Created", style="dim")
        table.add_column("Content", style="white", no_wrap=False, max_width=60)
        table.add_column("Accesses", style="cyan", justify="right")
        table.add_column("Last Accessed", style="dim")

        for row in rows:
            content = str(row["content"])
            # Truncate long content
            if len(content) > 100:
                content = content[:97] + "..."

            # Format created time
            created_at = row["created_at"]
            try:
                created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                now = datetime.now(UTC)
                delta = now - created_time

                if delta.days > 365:
                    created_str = f"{delta.days // 365}y ago"
                elif delta.days > 30:
                    created_str = f"{delta.days // 30}mo ago"
                else:
                    created_str = f"{delta.days}d ago"
            except Exception:
                created_str = "unknown"

            # Format last accessed time
            accessed_at = row["accessed_at"]
            if accessed_at:
                try:
                    accessed_time = datetime.fromisoformat(accessed_at.replace("Z", "+00:00"))
                    now = datetime.now(UTC)
                    delta = now - accessed_time

                    if delta.days > 365:
                        accessed_str = f"{delta.days // 365}y ago"
                    elif delta.days > 30:
                        accessed_str = f"{delta.days // 30}mo ago"
                    else:
                        accessed_str = f"{delta.days}d ago"
                except Exception:
                    accessed_str = "unknown"
            else:
                accessed_str = "never"

            table.add_row(created_str, content, str(row["access_count"]), accessed_str)

        rich_print(table)

        # Summary statistics
        rich_print(
            f"\n⚠️  Found {len(rows)} stale memories (showing up to {limit})",
            style="yellow",
        )
        rich_print(
            "   Consider pruning with: kuzu-memory memory prune --strategy safe",
            style="dim",
        )

    except Exception as e:
        if ctx.obj and ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Failed to retrieve stale memories: {e}", style="red")
        sys.exit(1)
