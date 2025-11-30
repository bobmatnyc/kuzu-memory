"""
Project management CLI commands for KuzuMemory.

Contains commands for init, project, stats, cleanup operations.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import click

from ..core.memory import KuzuMemory
from ..integrations.auggie import AuggieIntegration
from ..utils.config_loader import get_config_loader
from ..utils.project_setup import (
    create_project_memories_structure,
    find_project_root,
    get_project_context_summary,
    get_project_db_path,
    get_project_memories_dir,
)
from .cli_utils import rich_confirm, rich_panel, rich_print

logger = logging.getLogger(__name__)


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing project memories")
@click.option("--config-path", type=click.Path(), help="Path to save example configuration")
@click.pass_context
def init(ctx: click.Context, force: bool, config_path: Path | str | None) -> None:
    """
    🚀 Initialize KuzuMemory for this project.

    Sets up the project memory database and creates example configurations.
    This command should be run once per project to enable memory functionality.

    \b
    🎮 EXAMPLES:
      # Basic initialization
      kuzu-memory init

      # Force re-initialization
      kuzu-memory init --force

      # Initialize with custom config
      kuzu-memory init --config-path ./my-kuzu-config.json
    """
    try:
        from ..core.config import KuzuMemoryConfig
        from ..core.memory import KuzuMemory

        project_root = ctx.obj.get("project_root") or find_project_root()
        memories_dir = get_project_memories_dir(project_root)
        db_path = get_project_db_path(project_root)

        rich_print(f"🚀 Initializing KuzuMemory for project: {project_root}")

        # Check if already initialized
        if db_path.exists() and not force:
            rich_print(f"⚠️  Project already initialized at {memories_dir}", style="yellow")
            rich_print("   Use --force to overwrite existing memories", style="dim")
            sys.exit(1)

        # Create project structure
        create_project_memories_structure(project_root)
        rich_print(f"✅ Created memories directory: {memories_dir}")

        # Initialize database with default config
        config = KuzuMemoryConfig()
        with KuzuMemory(db_path=db_path, config=config) as memory:
            # Store initial project context
            project_context = get_project_context_summary(project_root)
            if project_context:
                # Convert dict to string for memory content
                context_str = f"Project {project_context['project_name']} initialized at {project_context['project_root']}"
                memory.remember(
                    context_str,
                    source="project-initialization",
                    metadata={
                        "type": "project-context",
                        "auto-generated": True,
                        **project_context,
                    },
                )

        rich_print(f"✅ Initialized database: {db_path}")

        # Create example config if requested
        if config_path:
            config_path = Path(config_path)
            example_config = {
                "storage": {"db_path": str(db_path), "backup_enabled": True},
                "memory": {"max_memories_per_query": 10, "similarity_threshold": 0.7},
                "temporal_decay": {"enabled": True, "recent_boost_hours": 24},
            }

            config_path.write_text(json.dumps(example_config, indent=2))
            rich_print(f"✅ Created example config: {config_path}")

        # Check for Auggie integration
        try:
            from ..integrations.auggie import AuggieIntegration

            auggie = AuggieIntegration(project_root)

            if auggie.is_auggie_project():
                rich_print("\n🤖 Auggie project detected!")
                if rich_confirm("Would you like to set up Auggie integration?", default=True):
                    try:
                        auggie.setup_project_integration()
                        rich_print("✅ Auggie integration configured")
                    except Exception as e:
                        rich_print(f"⚠️  Auggie integration setup failed: {e}", style="yellow")
        except ImportError:
            pass

        rich_panel(
            f"KuzuMemory is now ready! 🎉\n\n"
            f"📁 Memories directory: {memories_dir}\n"
            f"🗄️  Database: {db_path}\n\n"
            f"Next steps:\n"
            f"• Store your first memory: kuzu-memory remember 'Project uses FastAPI'\n"
            f"• Enhance prompts: kuzu-memory enhance 'How do I deploy?'\n"
            f"• Learn from conversations: kuzu-memory learn 'User prefers TypeScript'\n",
            title="🎯 Initialization Complete",
            style="green",
        )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Initialization failed: {e}", style="red")
        sys.exit(1)


@click.command()
@click.option("--verbose", is_flag=True, help="Show detailed project information")
@click.pass_context
def project(ctx: click.Context, verbose: bool) -> None:
    """
    📊 Show project memory information and health status.

    Displays comprehensive information about the current project's
    memory system, including database status, memory counts, and configuration.

    \b
    🎮 EXAMPLES:
      # Basic project info
      kuzu-memory project

      # Detailed information
      kuzu-memory project --verbose
    """
    try:
        project_root = ctx.obj.get("project_root") or find_project_root()
        memories_dir = get_project_memories_dir(project_root)
        db_path = get_project_db_path(project_root)

        rich_print("📊 Project Memory Status")
        rich_print(f"Project Root: {project_root}")
        rich_print(f"Memories Directory: {memories_dir}")
        rich_print(f"Database Path: {db_path}")

        if not db_path.exists():
            rich_panel(
                "Project not initialized.\nRun 'kuzu-memory init' to get started.",
                title="⚠️  Not Initialized",
                style="yellow",
            )
            return

        # Disable git_sync for read-only project info operation (performance optimization)
        with KuzuMemory(db_path=db_path, enable_git_sync=False) as memory:
            # Get basic stats
            total_memories = memory.get_memory_count()
            recent_memories = memory.get_recent_memories(limit=5)

            # Memory type breakdown
            type_stats = memory.get_memory_type_stats()
            source_stats = memory.get_source_stats()

            rich_print("\n🧠 Memory Statistics:")
            rich_print(f"   Total Memories: {total_memories}")
            rich_print(f"   Recent Activity: {len(recent_memories)} in last 5")

            if verbose:
                # Detailed type breakdown
                if type_stats:
                    rich_print("\n📋 Memory Types:")
                    for memory_type, count in type_stats.items():
                        rich_print(f"   {memory_type}: {count}")

                # Source breakdown
                if source_stats:
                    rich_print("\n📤 Sources:")
                    for source, count in source_stats.items():
                        rich_print(f"   {source}: {count}")

                # Recent memories
                if recent_memories:
                    rich_print("\n🕒 Recent Memories:")
                    for mem in recent_memories:
                        content_preview = mem.content[:80] + (
                            "..." if len(mem.content) > 80 else ""
                        )
                        rich_print(f"   • {content_preview}")
                        # Note: Memory.source attribute might not exist in all versions
                        source_str = getattr(mem, "source", "unknown")
                        rich_print(
                            f"     {source_str} | {mem.created_at.strftime('%Y-%m-%d %H:%M')}",
                            style="dim",
                        )

        # Configuration status
        config_loader = get_config_loader()
        config_info = config_loader.get_config_info(project_root)

        rich_print("\n⚙️  Configuration:")
        rich_print(f"   Config Source: {config_info.get('source', 'default')}")
        if config_info.get("path"):
            rich_print(f"   Config Path: {config_info['path']}")

        # Check for Auggie integration
        try:
            auggie = AuggieIntegration(project_root)
            if auggie.is_auggie_project():
                rich_print("\n🤖 Auggie Integration:")
                rich_print(
                    f"   Status: {'✅ Active' if auggie.is_integration_active() else '⚠️  Available but inactive'}"
                )

                if verbose:
                    rules_info = auggie.get_rules_summary()
                    rich_print(f"   Rules Files: {len(rules_info.get('files', []))}")
                    rich_print(f"   Memory Rules: {len(rules_info.get('memory_rules', []))}")
        except ImportError:
            pass

        # Health check
        health_status = "✅ Healthy"
        try:
            # Basic health checks (read-only, no git_sync needed)
            with KuzuMemory(db_path=db_path, enable_git_sync=False) as memory:
                memory.get_recent_memories(limit=1)
                # Add more health checks as needed
        except Exception as e:
            health_status = f"⚠️  Issues detected: {e}"

        rich_print(f"\n🏥 Health Status: {health_status}")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Project status check failed: {e}", style="red")
        sys.exit(1)


@click.command()
@click.option("--detailed", is_flag=True, help="Show detailed statistics")
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
@click.pass_context
def stats(ctx: click.Context, detailed: bool, output_format: str) -> None:
    """
    📈 Display comprehensive memory system statistics.

    Shows detailed statistics about the project's memory system,
    including memory counts, types, sources, and performance metrics.

    \b
    🎮 EXAMPLES:
      # Basic statistics
      kuzu-memory stats

      # Detailed statistics
      kuzu-memory stats --detailed

      # JSON output for scripts
      kuzu-memory stats --format json
    """
    try:
        db_path = get_project_db_path(ctx.obj.get("project_root"))

        # Disable git_sync for read-only stats operation (performance optimization)
        with KuzuMemory(db_path=db_path, enable_git_sync=False) as memory:
            # Collect all statistics - simplified to avoid query errors
            recent_memories = memory.get_recent_memories(limit=24)
            stats_data: dict[str, Any] = {
                "total_memories": memory.get_memory_count(),
                "memory_types": {},  # Temporarily disabled due to query issues
                "sources": {},  # Temporarily disabled due to query issues
                "recent_activity": len(recent_memories),  # Last 24 entries
            }

            if detailed:
                # Add detailed statistics
                stats_data.update(
                    {
                        "daily_activity": memory.get_daily_activity_stats(days=7),
                        "avg_memory_length": memory.get_average_memory_length(),
                        "oldest_memory": memory.get_oldest_memory_date(),
                        "newest_memory": memory.get_newest_memory_date(),
                    }
                )

            if output_format == "json":
                # Convert datetime objects to ISO format for JSON
                def serialize_datetime(obj: Any) -> Any:
                    if hasattr(obj, "isoformat"):
                        return obj.isoformat()
                    return obj

                rich_print(json.dumps(stats_data, indent=2, default=serialize_datetime))
            else:
                # Text format
                rich_panel(
                    f"Total Memories: {stats_data['total_memories']}",
                    title="📈 Memory Statistics",
                    style="blue",
                )

                # Memory types
                if stats_data["memory_types"]:
                    rich_print("\n📋 Memory Types:")
                    for memory_type, count in sorted(
                        stats_data["memory_types"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    ):
                        percentage = (
                            (count / stats_data["total_memories"]) * 100
                            if stats_data["total_memories"] > 0
                            else 0
                        )
                        rich_print(f"   {memory_type}: {count} ({percentage:.1f}%)")

                # Sources
                if stats_data["sources"]:
                    rich_print("\n📤 Sources:")
                    for source, count in sorted(
                        stats_data["sources"].items(), key=lambda x: x[1], reverse=True
                    ):
                        percentage = (
                            (count / stats_data["total_memories"]) * 100
                            if stats_data["total_memories"] > 0
                            else 0
                        )
                        rich_print(f"   {source}: {count} ({percentage:.1f}%)")

                rich_print(f"\n🕒 Recent Activity: {stats_data['recent_activity']} memories")

                if detailed:
                    # Additional detailed information
                    if stats_data.get("avg_memory_length"):
                        rich_print(
                            f"\n📏 Average Memory Length: {stats_data['avg_memory_length']:.0f} characters"
                        )

                    if stats_data.get("oldest_memory"):
                        rich_print("\n📅 Memory Timeline:")
                        rich_print(
                            f"   Oldest: {stats_data['oldest_memory'].strftime('%Y-%m-%d %H:%M')}"
                        )
                        if stats_data.get("newest_memory"):
                            rich_print(
                                f"   Newest: {stats_data['newest_memory'].strftime('%Y-%m-%d %H:%M')}"
                            )

                    # Daily activity (last 7 days)
                    if stats_data.get("daily_activity"):
                        rich_print("\n📊 Daily Activity (Last 7 Days):")
                        for date, count in stats_data["daily_activity"].items():
                            rich_print(f"   {date}: {count} memories")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Statistics generation failed: {e}", style="red")
        sys.exit(1)


@click.command()
@click.option("--force", is_flag=True, help="Force cleanup without confirmation")
@click.pass_context
def cleanup(ctx: click.Context, force: bool) -> None:
    """
    🧹 Clean up expired and redundant memories.

    Removes expired memories based on retention policies and
    cleans up duplicate or redundant entries to optimize performance.

    \b
    🎮 EXAMPLES:
      # Interactive cleanup
      kuzu-memory cleanup

      # Force cleanup without confirmation
      kuzu-memory cleanup --force
    """
    try:
        db_path = get_project_db_path(ctx.obj.get("project_root"))

        with KuzuMemory(db_path=db_path) as memory:
            # Note: These cleanup methods are not yet implemented in KuzuMemory
            # This is placeholder code for future functionality
            rich_print("⚠️  Cleanup functionality not yet fully implemented", style="yellow")
            rich_print("Future features will include:")
            rich_print("  - Expired memory cleanup based on retention policies")
            rich_print("  - Duplicate detection and removal")
            rich_print("  - Memory optimization and consolidation")

            # For now, just show current memory count
            total = memory.get_memory_count()
            rich_print(f"\n📊 Current total memories: {total}")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Cleanup failed: {e}", style="red")
        sys.exit(1)


@click.command()
@click.argument("config_path", type=click.Path())
@click.pass_context
def create_config(ctx: click.Context, config_path: Path | str) -> None:
    """
    ⚙️  Create a configuration file with current settings.

    Generates a configuration file based on the current project settings
    and allows customization of memory behavior and database options.

    \b
    🎮 EXAMPLES:
      # Create basic config
      kuzu-memory create-config ./kuzu-config.json

      # Create config in project directory
      kuzu-memory create-config ./.kuzu-memory/config.json
    """
    try:
        from ..core.config import KuzuMemoryConfig

        config = KuzuMemoryConfig()
        config_dict = config.to_dict()

        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with config_path.open("w") as f:
            json.dump(config_dict, f, indent=2)

        rich_print(f"✅ Configuration created: {config_path}", style="green")
        rich_print("Edit the file to customize memory behavior", style="dim")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Config creation failed: {e}", style="red")
        sys.exit(1)
