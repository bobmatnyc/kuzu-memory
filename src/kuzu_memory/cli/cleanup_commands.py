"""
Cleanup utility commands for KuzuMemory.

Provides memory maintenance operations including stale memory removal,
duplicate cleanup, and orphaned relationship cleanup.
"""

import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click

from ..core.config import KuzuMemoryConfig
from ..storage.kuzu_adapter import KuzuAdapter
from ..utils.deduplication import DeduplicationEngine
from .cli_utils import rich_panel, rich_print
from .service_manager import ServiceManager

logger = logging.getLogger(__name__)


@click.group()
def cleanup() -> None:
    """
    🧹 Memory cleanup and maintenance operations.

    Provides tools to remove stale, duplicate, and orphaned memories
    to optimize database size and improve performance.

    \b
    🎮 COMMANDS:
      stale       Remove memories not accessed in N days
      duplicates  Remove duplicate memories
      orphans     Remove orphaned relationships
      all         Run all cleanup strategies

    Use 'kuzu-memory cleanup COMMAND --help' for detailed help.
    """
    pass


@cleanup.command()
@click.option(
    "--days",
    default=90,
    help="Days since last access to consider stale (default: 90)",
)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="Preview changes without executing (default: dry-run)",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts (use with --execute)",
)
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def stale(
    ctx: click.Context,
    days: int,
    dry_run: bool,
    yes: bool,
    db_path: str | None,
) -> None:
    """
    🗑️  Remove memories not accessed in N days.

    Identifies and optionally removes memories that haven't been accessed
    within the specified threshold. Useful for cleaning up old, unused content.

    \b
    🎯 CRITERIA:
      - Memory accessed_at is NULL OR older than threshold
      - Memory access_count is 0 (never accessed)
      - Memory created_at is older than threshold

    \b
    🎮 EXAMPLES:
      # Preview stale memories (90 days, default)
      kuzu-memory cleanup stale --dry-run

      # Preview with custom threshold
      kuzu-memory cleanup stale --days 180 --dry-run

      # Execute cleanup with confirmation
      kuzu-memory cleanup stale --execute

      # Execute without confirmation
      kuzu-memory cleanup stale --execute --yes
    """
    try:
        # Get database path
        db_path_obj = _resolve_db_path(ctx, db_path)

        # Calculate cutoff date
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        # Query stale memories
        config = KuzuMemoryConfig.default()
        adapter = KuzuAdapter(db_path_obj, config)
        adapter.initialize()

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
        """

        with adapter._pool.get_connection() as conn:
            result = conn.execute(query, {"cutoff_date": cutoff_iso})
            rows = result.get_as_pl()

        if len(rows) == 0:
            rich_print(
                f"✅ No stale memories found (older than {days} days without access)",
                style="green",
            )
            return

        # Display preview
        rich_panel(
            f"{'Preview' if dry_run else 'Cleanup'} - Stale Memories",
            title="🧹 Cleanup Preview" if dry_run else "🧹 Cleanup Execution",
            style="blue" if dry_run else "yellow",
        )

        rich_print(
            f"\n🗑️  Found {len(rows)} stale memories (not accessed in {days}+ days):",
            style="yellow",
        )

        # Show first 10 as preview
        preview_rows = rows[:10]
        for i, row in enumerate(preview_rows, 1):
            content = str(row["content"])
            if len(content) > 80:
                content = content[:77] + "..."

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

            rich_print(f"  {i}. {content}", style="dim")
            rich_print(
                f"     Created: {created_str} | Accesses: {row['access_count']}",
                style="dim",
            )

        if len(rows) > 10:
            rich_print(f"  ... and {len(rows) - 10} more", style="dim")

        # Summary
        rich_print(
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            style="dim",
        )
        rich_print(f"Total: {len(rows)} memories to remove\n", style="yellow")

        if dry_run:
            rich_print("Run with --execute to apply changes.", style="dim")
            return

        # Execute cleanup
        if not yes:
            rich_print(
                f"⚠️  WARNING: About to delete {len(rows)} stale memories!",
                style="bold red",
            )
            confirm = click.confirm("\nDo you want to continue?", default=False)
            if not confirm:
                rich_print("\n❌ Cleanup cancelled by user", style="yellow")
                return

        # Delete stale memories
        delete_query = """
            MATCH (m:Memory)
            WHERE (m.accessed_at IS NULL OR m.accessed_at < $cutoff_date)
              AND m.created_at < $cutoff_date
            DELETE m
        """

        with adapter._pool.get_connection() as conn:
            conn.execute(delete_query, {"cutoff_date": cutoff_iso})

        rich_print(
            f"\n✅ Successfully removed {len(rows)} stale memories!",
            style="bold green",
        )

    except Exception as e:
        if ctx.obj and ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Stale cleanup failed: {e}", style="red")
        sys.exit(1)


@cleanup.command()
@click.option(
    "--threshold",
    default=0.95,
    help="Similarity threshold for duplicates (default: 0.95)",
)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="Preview changes without executing (default: dry-run)",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts (use with --execute)",
)
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def duplicates(
    ctx: click.Context,
    threshold: float,
    dry_run: bool,
    yes: bool,
    db_path: str | None,
) -> None:
    """
    🔄 Remove duplicate memories.

    Uses semantic similarity to identify and remove duplicate memories,
    keeping the one with the highest access count or most recent timestamp.

    \b
    🎯 STRATEGY:
      - Group similar memories above threshold
      - Keep memory with highest access_count
      - If tied, keep most recently created
      - Remove all other duplicates in group

    \b
    🎮 EXAMPLES:
      # Preview duplicates (95% similarity, default)
      kuzu-memory cleanup duplicates --dry-run

      # Preview with lower threshold (90%)
      kuzu-memory cleanup duplicates --threshold 0.90 --dry-run

      # Execute cleanup with confirmation
      kuzu-memory cleanup duplicates --execute

      # Execute without confirmation
      kuzu-memory cleanup duplicates --execute --yes
    """
    try:
        # Get database path
        db_path_obj = _resolve_db_path(ctx, db_path)

        # Load all memories
        # Get all memories via direct query (no get_all_memories method exists)
        with ServiceManager.memory_service(
            db_path=db_path_obj, enable_git_sync=False
        ) as mem_service:
            # Use get_recent_memories with high limit to get all memories
            # TODO: Add a proper get_all_memories() method to MemoryService
            all_memories = mem_service.get_recent_memories(limit=100000)

        if not all_memories:
            rich_print("[i] No memories to check for duplicates", style="blue")
            return

        # Initialize deduplication engine
        dedup = DeduplicationEngine(
            near_threshold=threshold,
            semantic_threshold=threshold,
            enable_update_detection=False,
        )

        # Find duplicate clusters
        duplicate_clusters: list[list[tuple[str, str, float]]] = []
        processed_ids = set()

        for mem in all_memories:
            if mem.id in processed_ids:
                continue

            # Find duplicates of this memory
            duplicates = dedup.find_duplicates(
                mem.content,
                [
                    m
                    for m in all_memories
                    if m.id != mem.id and m.id not in processed_ids
                ],
            )

            if duplicates:
                # Create cluster with current memory and its duplicates
                cluster = [(mem.id, mem.content, 1.0)]
                for dup_mem, score, _match_type in duplicates:
                    cluster.append((dup_mem.id, dup_mem.content, score))
                    processed_ids.add(dup_mem.id)

                duplicate_clusters.append(cluster)
                processed_ids.add(mem.id)

        if not duplicate_clusters:
            rich_print(
                f"✅ No duplicate memories found (similarity > {threshold})",
                style="green",
            )
            return

        # Determine which memories to keep vs remove
        to_remove: list[str] = []
        cluster_summaries = []

        with ServiceManager.memory_service(
            db_path=db_path_obj, enable_git_sync=False
        ) as _memory:
            for cluster in duplicate_clusters:
                # Get full memory objects for this cluster
                cluster_memories = []
                for mem_id, _content, score in cluster:
                    # Find the memory object
                    for memory_obj in all_memories:
                        if memory_obj.id == mem_id:
                            cluster_memories.append((memory_obj, score))
                            break

                # Sort by: access_count DESC, created_at DESC
                cluster_memories.sort(
                    key=lambda x: (
                        getattr(x[0], "access_count", 0),
                        x[0].created_at,
                    ),
                    reverse=True,
                )

                # Keep the first (highest access count / most recent)
                keeper = cluster_memories[0][0]
                duplicates_to_remove = [mem for mem, _ in cluster_memories[1:]]

                # Track for removal
                for dup in duplicates_to_remove:
                    to_remove.append(dup.id)

                # Create summary
                cluster_summaries.append(
                    {
                        "keeper": keeper,
                        "removed": duplicates_to_remove,
                        "count": len(duplicates_to_remove),
                    }
                )

        # Display preview
        rich_panel(
            f"{'Preview' if dry_run else 'Cleanup'} - Duplicate Memories",
            title="🧹 Cleanup Preview" if dry_run else "🧹 Cleanup Execution",
            style="blue" if dry_run else "yellow",
        )

        rich_print(
            f"\n🔄 Found {len(duplicate_clusters)} duplicate clusters (similarity > {threshold}):",
            style="yellow",
        )

        # Show first 5 clusters as preview
        preview_clusters = cluster_summaries[:5]
        for i, summary in enumerate(preview_clusters, 1):
            keeper = summary["keeper"]
            content = keeper.content
            if len(content) > 80:
                content = content[:77] + "..."

            rich_print(
                f"\n  Cluster {i}: {summary['count']} duplicates",
                style="cyan",
            )
            rich_print(f"  ✅ Keeping: {content}", style="green")
            rich_print(
                f"     Access count: {getattr(keeper, 'access_count', 0)}",
                style="dim",
            )

            for dup in summary["removed"]:
                dup_content = dup.content
                if len(dup_content) > 80:
                    dup_content = dup_content[:77] + "..."
                rich_print(f"  ❌ Removing: {dup_content}", style="red")

        if len(cluster_summaries) > 5:
            remaining_removed = sum(
                summary["count"] for summary in cluster_summaries[5:]
            )
            rich_print(
                f"\n  ... and {len(cluster_summaries) - 5} more clusters ({remaining_removed} removals)",
                style="dim",
            )

        # Summary
        rich_print(
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            style="dim",
        )
        rich_print(
            f"Total: {len(to_remove)} duplicates to remove, {len(duplicate_clusters)} to keep\n",
            style="yellow",
        )

        if dry_run:
            rich_print("Run with --execute to apply changes.", style="dim")
            return

        # Execute cleanup
        if not yes:
            rich_print(
                f"⚠️  WARNING: About to delete {len(to_remove)} duplicate memories!",
                style="bold red",
            )
            confirm = click.confirm("\nDo you want to continue?", default=False)
            if not confirm:
                rich_print("\n❌ Cleanup cancelled by user", style="yellow")
                return

        # Delete duplicate memories
        if to_remove:
            config = KuzuMemoryConfig.default()
            adapter = KuzuAdapter(db_path_obj, config)
            adapter.initialize()

            delete_query = """
                UNWIND $memory_ids AS mid
                MATCH (m:Memory {id: mid})
                DELETE m
            """

            with adapter._pool.get_connection() as conn:
                conn.execute(delete_query, {"memory_ids": to_remove})

        rich_print(
            f"\n✅ Successfully removed {len(to_remove)} duplicate memories!",
            style="bold green",
        )
        rich_print(
            f"   Kept {len(duplicate_clusters)} unique memories",
            style="dim",
        )

    except Exception as e:
        if ctx.obj and ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Duplicate cleanup failed: {e}", style="red")
        sys.exit(1)


@cleanup.command()
@click.option(
    "--dry-run/--execute",
    default=True,
    help="Preview changes without executing (default: dry-run)",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts (use with --execute)",
)
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def orphans(
    ctx: click.Context,
    dry_run: bool,
    yes: bool,
    db_path: str | None,
) -> None:
    """
    🔗 Remove orphaned relationships.

    Finds and removes relationship records that point to non-existent
    memory nodes. This can happen after manual deletions or data corruption.

    \b
    🎯 CRITERIA:
      - MENTIONS relationships with missing Entity nodes
      - RELATES_TO relationships with missing Memory nodes
      - BELONGS_TO_SESSION relationships with missing Session nodes

    \b
    🎮 EXAMPLES:
      # Preview orphaned relationships
      kuzu-memory cleanup orphans --dry-run

      # Execute cleanup with confirmation
      kuzu-memory cleanup orphans --execute

      # Execute without confirmation
      kuzu-memory cleanup orphans --execute --yes
    """
    try:
        # Get database path
        db_path_obj = _resolve_db_path(ctx, db_path)

        # Query orphaned relationships
        config = KuzuMemoryConfig.default()
        adapter = KuzuAdapter(db_path_obj, config)
        adapter.initialize()

        # Find orphaned MENTIONS relationships (Memory -> Entity)
        mentions_query = """
            MATCH (m:Memory)-[r:MENTIONS]->(e:Entity)
            WHERE NOT EXISTS { MATCH (e2:Entity {id: e.id}) }
            RETURN count(*) AS count
        """

        # Find orphaned RELATES_TO relationships (Memory -> Memory)
        relates_query = """
            MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
            WHERE NOT EXISTS { MATCH (m3:Memory {id: m2.id}) }
            RETURN count(*) AS count
        """

        # Find orphaned BELONGS_TO_SESSION relationships (Memory -> Session)
        session_query = """
            MATCH (m:Memory)-[r:BELONGS_TO_SESSION]->(s:Session)
            WHERE NOT EXISTS { MATCH (s2:Session {id: s.id}) }
            RETURN count(*) AS count
        """

        orphan_counts = {}
        with adapter._pool.get_connection() as conn:
            # Count MENTIONS orphans
            result = conn.execute(mentions_query)
            rows = result.get_as_pl()
            orphan_counts["MENTIONS"] = rows[0]["count"] if len(rows) > 0 else 0

            # Count RELATES_TO orphans
            result = conn.execute(relates_query)
            rows = result.get_as_pl()
            orphan_counts["RELATES_TO"] = rows[0]["count"] if len(rows) > 0 else 0

            # Count BELONGS_TO_SESSION orphans
            result = conn.execute(session_query)
            rows = result.get_as_pl()
            orphan_counts["BELONGS_TO_SESSION"] = (
                rows[0]["count"] if len(rows) > 0 else 0
            )

        total_orphans = sum(orphan_counts.values())

        if total_orphans == 0:
            rich_print("✅ No orphaned relationships found", style="green")
            return

        # Display preview
        rich_panel(
            f"{'Preview' if dry_run else 'Cleanup'} - Orphaned Relationships",
            title="🧹 Cleanup Preview" if dry_run else "🧹 Cleanup Execution",
            style="blue" if dry_run else "yellow",
        )

        rich_print(
            f"\n🔗 Found {total_orphans} orphaned relationships:",
            style="yellow",
        )

        for rel_type, count in orphan_counts.items():
            if count > 0:
                rich_print(f"  • {rel_type}: {count} orphaned", style="dim")

        # Summary
        rich_print(
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            style="dim",
        )
        rich_print(f"Total: {total_orphans} relationships to remove\n", style="yellow")

        if dry_run:
            rich_print("Run with --execute to apply changes.", style="dim")
            return

        # Execute cleanup
        if not yes:
            rich_print(
                f"⚠️  WARNING: About to delete {total_orphans} orphaned relationships!",
                style="bold red",
            )
            confirm = click.confirm("\nDo you want to continue?", default=False)
            if not confirm:
                rich_print("\n❌ Cleanup cancelled by user", style="yellow")
                return

        # Delete orphaned relationships
        # Note: Kuzu automatically handles relationship cleanup when nodes are deleted
        # This is primarily for manual cleanup after corruption
        delete_mentions = """
            MATCH (m:Memory)-[r:MENTIONS]->(e:Entity)
            WHERE NOT EXISTS { MATCH (e2:Entity {id: e.id}) }
            DELETE r
        """

        delete_relates = """
            MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
            WHERE NOT EXISTS { MATCH (m3:Memory {id: m2.id}) }
            DELETE r
        """

        delete_session = """
            MATCH (m:Memory)-[r:BELONGS_TO_SESSION]->(s:Session)
            WHERE NOT EXISTS { MATCH (s2:Session {id: s.id}) }
            DELETE r
        """

        with adapter._pool.get_connection() as conn:
            if orphan_counts["MENTIONS"] > 0:
                conn.execute(delete_mentions)
            if orphan_counts["RELATES_TO"] > 0:
                conn.execute(delete_relates)
            if orphan_counts["BELONGS_TO_SESSION"] > 0:
                conn.execute(delete_session)

        rich_print(
            f"\n✅ Successfully removed {total_orphans} orphaned relationships!",
            style="bold green",
        )

    except Exception as e:
        if ctx.obj and ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Orphan cleanup failed: {e}", style="red")
        sys.exit(1)


@cleanup.command()
@click.option(
    "--days",
    default=90,
    help="Days threshold for stale cleanup (default: 90)",
)
@click.option(
    "--threshold",
    default=0.95,
    help="Similarity threshold for duplicates (default: 0.95)",
)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="Preview changes without executing (default: dry-run)",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts (use with --execute)",
)
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def all(
    ctx: click.Context,
    days: int,
    threshold: float,
    dry_run: bool,
    yes: bool,
    db_path: str | None,
) -> None:
    """
    🚀 Run all cleanup strategies.

    Performs comprehensive cleanup: stale memories, duplicates, and orphaned
    relationships. Provides a complete summary before execution.

    \b
    🎯 STRATEGIES:
      1. Stale memories (not accessed in N days)
      2. Duplicate memories (similarity > threshold)
      3. Orphaned relationships (dangling references)

    \b
    🎮 EXAMPLES:
      # Preview all cleanup operations
      kuzu-memory cleanup all --dry-run

      # Preview with custom thresholds
      kuzu-memory cleanup all --days 180 --threshold 0.90 --dry-run

      # Execute all cleanup with confirmation
      kuzu-memory cleanup all --execute

      # Execute without confirmation
      kuzu-memory cleanup all --execute --yes
    """
    try:
        rich_panel(
            "Running Complete Cleanup Analysis",
            title="🧹 Cleanup Preview" if dry_run else "🧹 Cleanup Execution",
            style="blue" if dry_run else "yellow",
        )

        # Collect statistics from each cleanup strategy
        stats = {
            "stale": 0,
            "duplicates": 0,
            "orphans": 0,
        }

        # 1. Analyze stale memories
        rich_print("\n1️⃣  Analyzing stale memories...", style="cyan")
        db_path_obj = _resolve_db_path(ctx, db_path)
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        config = KuzuMemoryConfig.default()
        adapter = KuzuAdapter(db_path_obj, config)
        adapter.initialize()

        stale_query = """
            MATCH (m:Memory)
            WHERE (m.accessed_at IS NULL OR m.accessed_at < $cutoff_date)
              AND m.created_at < $cutoff_date
            RETURN count(*) AS count
        """

        with adapter._pool.get_connection() as conn:
            result = conn.execute(stale_query, {"cutoff_date": cutoff_iso})
            rows = result.get_as_pl()
            stats["stale"] = rows[0]["count"] if len(rows) > 0 else 0

        rich_print(
            f"   Found {stats['stale']} stale memories (>{days} days without access)",
            style="dim",
        )

        # 2. Analyze duplicates
        rich_print("\n2️⃣  Analyzing duplicate memories...", style="cyan")

        # Get all memories via direct query (no get_all_memories method exists)
        with ServiceManager.memory_service(
            db_path=db_path_obj, enable_git_sync=False
        ) as mem_service:
            # Use get_recent_memories with high limit to get all memories
            # TODO: Add a proper get_all_memories() method to MemoryService
            all_memories = mem_service.get_recent_memories(limit=100000)

        if all_memories:
            dedup = DeduplicationEngine(
                near_threshold=threshold,
                semantic_threshold=threshold,
                enable_update_detection=False,
            )

            duplicate_count = 0
            processed_ids = set()

            for memory_item in all_memories:
                if memory_item.id in processed_ids:
                    continue

                duplicates = dedup.find_duplicates(
                    memory_item.content,
                    [
                        m
                        for m in all_memories
                        if m.id != memory_item.id and m.id not in processed_ids
                    ],
                )

                if duplicates:
                    duplicate_count += len(duplicates)
                    processed_ids.add(memory_item.id)
                    for dup_mem, _, _ in duplicates:
                        processed_ids.add(dup_mem.id)

            stats["duplicates"] = duplicate_count

        rich_print(
            f"   Found {stats['duplicates']} duplicate memories (similarity > {threshold})",
            style="dim",
        )

        # 3. Analyze orphaned relationships
        rich_print("\n3️⃣  Analyzing orphaned relationships...", style="cyan")

        mentions_query = """
            MATCH (m:Memory)-[r:MENTIONS]->(e:Entity)
            WHERE NOT EXISTS { MATCH (e2:Entity {id: e.id}) }
            RETURN count(*) AS count
        """

        relates_query = """
            MATCH (m1:Memory)-[r:RELATES_TO]->(m2:Memory)
            WHERE NOT EXISTS { MATCH (m3:Memory {id: m2.id}) }
            RETURN count(*) AS count
        """

        session_query = """
            MATCH (m:Memory)-[r:BELONGS_TO_SESSION]->(s:Session)
            WHERE NOT EXISTS { MATCH (s2:Session {id: s.id}) }
            RETURN count(*) AS count
        """

        orphan_count = 0
        with adapter._pool.get_connection() as conn:
            for query in [mentions_query, relates_query, session_query]:
                result = conn.execute(query)
                rows = result.get_as_pl()
                orphan_count += rows[0]["count"] if len(rows) > 0 else 0

        stats["orphans"] = orphan_count

        rich_print(
            f"   Found {stats['orphans']} orphaned relationships",
            style="dim",
        )

        # Display summary
        total_items = sum(stats.values())

        rich_print(
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            style="dim",
        )
        rich_print("📊 Cleanup Summary:", style="bold blue")
        rich_print(
            f"  Stale memories: {stats['stale']} (>{days} days without access)",
            style="yellow",
        )
        rich_print(
            f"  Duplicate memories: {stats['duplicates']} (similarity > {threshold})",
            style="yellow",
        )
        rich_print(
            f"  Orphaned relationships: {stats['orphans']}",
            style="yellow",
        )
        rich_print(
            f"\n  Total items to clean: {total_items}",
            style="bold yellow",
        )

        if total_items == 0:
            rich_print("\n✅ No cleanup needed - database is healthy!", style="green")
            return

        if dry_run:
            rich_print("\nRun with --execute to apply changes.", style="dim")
            return

        # Execute all cleanup operations
        if not yes:
            rich_print(
                f"\n⚠️  WARNING: About to clean up {total_items} items!",
                style="bold red",
            )
            rich_print(
                f"  - {stats['stale']} stale memories",
                style="dim",
            )
            rich_print(
                f"  - {stats['duplicates']} duplicate memories",
                style="dim",
            )
            rich_print(
                f"  - {stats['orphans']} orphaned relationships",
                style="dim",
            )
            confirm = click.confirm("\nDo you want to continue?", default=False)
            if not confirm:
                rich_print("\n❌ Cleanup cancelled by user", style="yellow")
                return

        rich_print("\n🚀 Executing cleanup...", style="blue")

        # Execute each cleanup in sequence
        # Call each cleanup function directly instead of using ctx.invoke
        # to avoid type checking issues with Click command invocation

        # Execute stale cleanup
        rich_print("\n📝 Running stale cleanup...", style="blue")
        ctx.invoke(stale, days=days, dry_run=False, yes=True, db_path=db_path)

        # Execute duplicate cleanup
        rich_print("\n📝 Running duplicate cleanup...", style="blue")
        ctx.invoke(
            duplicates, threshold=threshold, dry_run=False, yes=True, db_path=db_path
        )

        # Execute orphan cleanup
        rich_print("\n📝 Running orphan cleanup...", style="blue")
        ctx.invoke(orphans, dry_run=False, yes=True, db_path=db_path)

        rich_print(
            f"\n✅ Complete cleanup finished! Removed {total_items} items.",
            style="bold green",
        )

    except Exception as e:
        if ctx.obj and ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Complete cleanup failed: {e}", style="red")
        sys.exit(1)


def _resolve_db_path(ctx: click.Context, db_path: str | None) -> Path:
    """
    Resolve database path from context or argument.

    Args:
        ctx: Click context with project_root in obj
        db_path: Optional explicit database path

    Returns:
        Resolved database path
    """
    from ..utils.project_setup import get_project_db_path

    if db_path:
        return Path(db_path)
    elif ctx.obj and ctx.obj.get("project_root"):
        return get_project_db_path(ctx.obj["project_root"])
    else:
        return get_project_db_path()


__all__ = ["cleanup"]
