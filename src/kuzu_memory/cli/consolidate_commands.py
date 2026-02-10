"""
CLI commands for memory consolidation.

Provides commands to cluster and merge similar old memories, reducing database
size while preserving important information through intelligent summarization.
"""

import logging
import sys

import click

from ..nlp.consolidation import ConsolidationEngine
from ..storage.kuzu_adapter import KuzuAdapter
from ..utils.config_loader import get_config_loader
from ..utils.deduplication import DeduplicationEngine
from ..utils.project_setup import get_project_db_path
from .cli_utils import rich_panel, rich_print, rich_table

logger = logging.getLogger(__name__)


@click.group()
def consolidate() -> None:
    """
    🔄 Memory consolidation operations.

    Cluster and merge similar old memories to reduce database size while
    preserving information through intelligent summarization.

    \b
    WORKFLOW:
      1. kuzu-memory consolidate show-clusters  # Preview clusters
      2. kuzu-memory consolidate --dry-run      # Analyze impact
      3. kuzu-memory consolidate --execute      # Apply consolidation

    \b
    CRITERIA:
      • Age > 90 days (configurable with --min-age)
      • Access count <= 3 (low-value memories)
      • Similarity >= 0.70 (configurable with --threshold)
      • Types: EPISODIC, SENSORY, WORKING only

    \b
    PROTECTED:
      • SEMANTIC (facts, never consolidated)
      • PREFERENCE (user preferences)
      • PROCEDURAL (instructions)
      • High-access memories
      • Recent memories
    """


@consolidate.command(name="show-clusters")
@click.option(
    "--threshold",
    type=float,
    default=0.70,
    help="Similarity threshold for clustering (0-1, default: 0.70)",
)
@click.option(
    "--min-age",
    type=int,
    default=90,
    help="Minimum age in days for consolidation (default: 90)",
)
@click.option(
    "--max-access",
    type=int,
    default=3,
    help="Maximum access count for consolidation (default: 3)",
)
@click.pass_context
def show_clusters(
    ctx: click.Context,
    threshold: float,
    min_age: int,
    max_access: int,
) -> None:
    """
    🔍 Visualize consolidation clusters without making changes.

    Shows which memories would be clustered together based on similarity,
    helping you understand the impact before running consolidation.

    \b
    EXAMPLE:
      kuzu-memory consolidate show-clusters --threshold 0.8
    """
    try:
        # Get project root and database path
        project_root = ctx.obj.get("project_root")
        if not project_root:
            rich_print("❌ Could not detect project root. Run from a git repository.", style="red")
            sys.exit(1)

        db_path = get_project_db_path(project_root)
        if not db_path.exists():
            rich_print("❌ Database not initialized. Run: kuzu-memory init", style="red")
            sys.exit(1)

        # Load config and create adapter
        config_loader = get_config_loader()
        config = config_loader.load_config(project_root)
        db_adapter = KuzuAdapter(db_path, config)
        db_adapter.initialize()

        # Create consolidation engine
        dedup_engine = DeduplicationEngine(
            near_threshold=threshold,
            semantic_threshold=threshold * 0.7,
        )
        engine = ConsolidationEngine(
            db_adapter=db_adapter,
            dedup_engine=dedup_engine,
            similarity_threshold=threshold,
            min_age_days=min_age,
            max_access_count=max_access,
        )

        # Find candidates and cluster
        rich_print("\n🔍 Finding consolidation candidates...", style="cyan")
        candidates = engine.find_candidates()

        if not candidates:
            rich_panel(
                "No consolidation candidates found.\n\n"
                "This might mean:\n"
                "• All memories are recent (< 90 days old)\n"
                "• Memories have high access counts (> 3)\n"
                "• No eligible memory types (EPISODIC, SENSORY, WORKING)\n\n"
                "Try adjusting criteria:\n"
                "  --min-age 60     # Lower age threshold\n"
                "  --max-access 5   # Higher access threshold",
                title="✨ No Candidates",
                style="yellow",
            )
            sys.exit(0)

        rich_print(f"✅ Found {len(candidates)} consolidation candidates", style="green")
        rich_print("\n🔗 Clustering similar memories...", style="cyan")

        clusters = engine.cluster_memories(candidates)

        if not clusters:
            rich_panel(
                f"No clusters found with similarity >= {threshold:.2f}\n\n"
                "Try lowering the threshold:\n"
                f"  --threshold {threshold - 0.1:.2f}",
                title="No Clusters",
                style="yellow",
            )
            sys.exit(0)

        # Display cluster summary
        rich_print(f"\n✅ Found {len(clusters)} clusters\n", style="green")

        # Show cluster details
        for i, cluster in enumerate(clusters, 1):
            # Calculate potential savings
            original_size = sum(len(m.content) for m in cluster.memories)
            summary_size = len(engine.create_summary(cluster))
            savings_bytes = original_size - summary_size
            savings_pct = (savings_bytes / original_size * 100) if original_size > 0 else 0

            rich_panel(
                f"Cluster ID: {cluster.cluster_id}\n"
                f"Memories: {len(cluster.memories)}\n"
                f"Avg Similarity: {cluster.avg_similarity:.3f}\n"
                f"Centroid: {cluster.centroid_memory.content[:80]}...\n"
                f"Potential Savings: {savings_bytes} bytes ({savings_pct:.1f}%)",
                title=f"Cluster {i}/{len(clusters)}",
                style="blue",
            )

            # Show cluster members
            cluster_data = []
            for memory in cluster.memories:
                similarity = cluster.similarity_scores.get(memory.id, 0.0)
                is_centroid = "✓" if memory.id == cluster.centroid_memory.id else ""
                cluster_data.append(
                    [
                        is_centroid,
                        memory.id[:12],
                        f"{similarity:.3f}",
                        memory.memory_type.value,
                        str(memory.access_count),
                        memory.content[:60] + "..." if len(memory.content) > 60 else memory.content,
                    ]
                )

            table = rich_table(
                ["Centroid", "ID", "Similarity", "Type", "Access", "Content"],
                cluster_data,
                title=f"Cluster {i} Members",
                print_table=False,
            )
            if table:
                from rich.console import Console

                console = Console()
                console.print(table)

            rich_print("")  # Spacing

        # Summary statistics
        total_memories = sum(len(c.memories) for c in clusters)
        total_savings = sum(
            sum(len(m.content) for m in c.memories) - len(engine.create_summary(c))
            for c in clusters
        )

        rich_panel(
            f"Clusters Found: {len(clusters)}\n"
            f"Total Memories: {total_memories}\n"
            f"Would Create: {len(clusters)} consolidated memories\n"
            f"Would Archive: {total_memories} original memories\n"
            f"Estimated Savings: {total_savings} bytes\n\n"
            f"Next Steps:\n"
            f"• kuzu-memory consolidate --dry-run    # Test run\n"
            f"• kuzu-memory consolidate --execute    # Apply changes",
            title="📊 Consolidation Preview",
            style="green",
        )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Failed to show clusters: {e}", style="red")
        sys.exit(1)
    finally:
        if "db_adapter" in locals():
            db_adapter.close()


@consolidate.command(name="run")
@click.option(
    "--dry-run",
    is_flag=True,
    default=True,
    help="Preview changes without applying (default: true)",
)
@click.option(
    "--execute",
    is_flag=True,
    help="Execute consolidation (overrides --dry-run)",
)
@click.option(
    "--threshold",
    type=float,
    default=0.70,
    help="Similarity threshold for clustering (0-1, default: 0.70)",
)
@click.option(
    "--min-age",
    type=int,
    default=90,
    help="Minimum age in days for consolidation (default: 90)",
)
@click.option(
    "--max-access",
    type=int,
    default=3,
    help="Maximum access count for consolidation (default: 3)",
)
@click.pass_context
def run_consolidation(
    ctx: click.Context,
    dry_run: bool,
    execute: bool,
    threshold: float,
    min_age: int,
    max_access: int,
) -> None:
    """
    🔄 Run memory consolidation.

    Clusters similar memories and creates summaries, reducing database size
    while preserving important information.

    \b
    SAFETY:
      • Dry-run by default (--execute to apply)
      • Archives originals (30-day recovery)
      • Creates CONSOLIDATED_INTO relationships
      • Only processes old, low-access memories

    \b
    EXAMPLES:
      # Preview consolidation
      kuzu-memory consolidate run

      # Execute with default settings
      kuzu-memory consolidate run --execute

      # Custom thresholds
      kuzu-memory consolidate run --execute --threshold 0.8 --min-age 60
    """
    try:
        # Determine if we're really executing
        is_dry_run = not execute

        # Get project root and database path
        project_root = ctx.obj.get("project_root")
        if not project_root:
            rich_print("❌ Could not detect project root. Run from a git repository.", style="red")
            sys.exit(1)

        db_path = get_project_db_path(project_root)
        if not db_path.exists():
            rich_print("❌ Database not initialized. Run: kuzu-memory init", style="red")
            sys.exit(1)

        # Load config and create adapter
        config_loader = get_config_loader()
        config = config_loader.load_config(project_root)
        db_adapter = KuzuAdapter(db_path, config)
        db_adapter.initialize()

        # Create consolidation engine
        dedup_engine = DeduplicationEngine(
            near_threshold=threshold,
            semantic_threshold=threshold * 0.7,
        )
        engine = ConsolidationEngine(
            db_adapter=db_adapter,
            dedup_engine=dedup_engine,
            similarity_threshold=threshold,
            min_age_days=min_age,
            max_access_count=max_access,
        )

        # Show mode
        mode_text = "DRY RUN (no changes)" if is_dry_run else "EXECUTE (will apply changes)"
        mode_style = "yellow" if is_dry_run else "red"

        rich_panel(
            f"Mode: {mode_text}\n"
            f"Similarity Threshold: {threshold:.2f}\n"
            f"Minimum Age: {min_age} days\n"
            f"Max Access Count: {max_access}",
            title="🔄 Memory Consolidation",
            style=mode_style,
        )

        # Execute consolidation
        rich_print("\n⏳ Running consolidation...", style="cyan")
        result = engine.execute(dry_run=is_dry_run, create_backup=True)

        if not result.success:
            rich_print(f"\n❌ Consolidation failed: {result.error}", style="red")
            sys.exit(1)

        # Display results
        if is_dry_run:
            rich_panel(
                f"Analysis Complete\n\n"
                f"Clusters Found: {result.clusters_found}\n"
                f"Memories Analyzed: {result.memories_analyzed}\n"
                f"Would Consolidate: {sum(len(c.memories) for c in result.clusters)} memories\n"
                f"Would Create: {result.clusters_found} summaries\n"
                f"Execution Time: {result.execution_time_ms:.1f}ms\n\n"
                f"To apply changes, run:\n"
                f"  kuzu-memory consolidate run --execute",
                title="📊 Dry Run Results",
                style="green",
            )

            # Show detailed cluster info
            if result.clusters:
                rich_print("\n🔍 Cluster Details:\n")
                for i, cluster in enumerate(result.clusters, 1):
                    rich_print(
                        f"  Cluster {i}: {len(cluster.memories)} memories "
                        f"(avg similarity: {cluster.avg_similarity:.3f})"
                    )

        else:
            rich_panel(
                f"Consolidation Complete! 🎉\n\n"
                f"Clusters Found: {result.clusters_found}\n"
                f"Memories Analyzed: {result.memories_analyzed}\n"
                f"Memories Consolidated: {result.memories_consolidated}\n"
                f"Memories Archived: {result.memories_archived}\n"
                f"New Summaries Created: {result.new_memories_created}\n"
                f"Execution Time: {result.execution_time_ms:.1f}ms\n\n"
                f"✅ Archived memories can be recovered for 30 days\n"
                f"   Use: kuzu-memory cleanup show-archives",
                title="✨ Consolidation Complete",
                style="green",
            )

            # Show savings
            if result.memories_consolidated > 0:
                reduction_count = result.memories_consolidated - result.new_memories_created
                reduction_pct = (reduction_count / result.memories_consolidated) * 100
                rich_print(
                    f"\n💾 Memory Reduction: {reduction_count} memories "
                    f"({reduction_pct:.1f}% reduction)",
                    style="green",
                )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Consolidation failed: {e}", style="red")
        sys.exit(1)
    finally:
        if "db_adapter" in locals():
            db_adapter.close()


# Make 'consolidate' the default command
consolidate.add_command(run_consolidation, name="run")

if __name__ == "__main__":
    consolidate()
