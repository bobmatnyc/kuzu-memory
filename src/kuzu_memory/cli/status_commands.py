"""
Status and information CLI commands for KuzuMemory.

Provides unified status command combining stats and project info.
"""

import json
import logging
import sys

import click

from ..core.memory import KuzuMemory
from ..utils.config_loader import get_config_loader
from ..utils.project_setup import (
    find_project_root,
    get_project_db_path,
    get_project_memories_dir,
)
from .cli_utils import rich_panel, rich_print
from .enums import OutputFormat

logger = logging.getLogger(__name__)


@click.command()
@click.option("--validate", is_flag=True, help="Run health validation checks")
@click.option(
    "--project", "show_project", is_flag=True, help="Show detailed project information"
)
@click.option("--detailed", is_flag=True, help="Show detailed statistics")
@click.option(
    "--format",
    "output_format",
    default=OutputFormat.TEXT.value,
    type=click.Choice([OutputFormat.TEXT.value, OutputFormat.JSON.value]),
    help="Output format",
)
@click.pass_context
def status(ctx, validate: bool, show_project: bool, detailed: bool, output_format: str):
    """
    📊 Display system status and statistics.

    Shows memory system status, statistics, and project information.
    Use flags to control the level of detail and output format.

    \b
    🎮 EXAMPLES:
      # Basic status
      kuzu-memory status

      # Detailed statistics
      kuzu-memory status --detailed

      # Project information
      kuzu-memory status --project

      # Health validation
      kuzu-memory status --validate

      # JSON output for scripts
      kuzu-memory status --format json
    """
    try:
        project_root = ctx.obj.get("project_root") or find_project_root()
        db_path = get_project_db_path(project_root)

        # Check if initialized
        if not db_path.exists():
            if output_format == "json":
                result = {
                    "initialized": False,
                    "project_root": str(project_root),
                    "error": "Project not initialized",
                }
                rich_print(json.dumps(result, indent=2))
            else:
                rich_panel(
                    "Project not initialized.\nRun 'kuzu-memory init' to get started.",
                    title="⚠️  Not Initialized",
                    style="yellow",
                )
            return

        # Disable git_sync for read-only status operation (performance optimization)
        # Exception: enable it during validation since we test write capability
        enable_sync = validate
        with KuzuMemory(db_path=db_path, enable_git_sync=enable_sync) as memory:
            # Collect statistics
            total_memories = memory.get_memory_count()
            recent_memories = memory.get_recent_memories(limit=24)

            stats_data = {
                "initialized": True,
                "project_root": str(project_root),
                "database_path": str(db_path),
                "total_memories": total_memories,
                "recent_activity": len(recent_memories),
            }

            # Add project information if requested
            if show_project:
                memories_dir = get_project_memories_dir(project_root)
                config_loader = get_config_loader()
                config_info = config_loader.get_config_info(project_root)

                stats_data.update(
                    {
                        "memories_directory": str(memories_dir),
                        "config_source": config_info.get("source", "default"),
                        "config_path": str(config_info.get("path", "")),
                    }
                )

                # Check for Auggie integration
                try:
                    from ..integrations.auggie import AuggieIntegration

                    auggie = AuggieIntegration(project_root)
                    if auggie.is_auggie_project():
                        rules_info = auggie.get_rules_summary()
                        stats_data["auggie_integration"] = {
                            "active": auggie.is_integration_active(),
                            "rules_files": len(rules_info.get("files", [])),
                            "memory_rules": len(rules_info.get("memory_rules", [])),
                        }
                except ImportError:
                    pass

            # Add detailed statistics if requested
            if detailed:
                stats_data.update(
                    {
                        "avg_memory_length": memory.get_average_memory_length(),
                        "oldest_memory": memory.get_oldest_memory_date(),
                        "newest_memory": memory.get_newest_memory_date(),
                        "daily_activity": memory.get_daily_activity_stats(days=7),
                    }
                )

            # Run validation if requested
            if validate:
                health_checks = []
                try:
                    # Test basic operations
                    memory.get_recent_memories(limit=1)
                    health_checks.append(
                        {"check": "database_connection", "status": "pass"}
                    )

                    # Test write capability
                    test_id = memory.store_memory(
                        "_health_check_test", source="health_check"
                    )
                    if test_id:
                        health_checks.append(
                            {"check": "write_capability", "status": "pass"}
                        )
                        # Clean up test memory
                        memory.delete_memory(test_id)
                    else:
                        health_checks.append(
                            {"check": "write_capability", "status": "fail"}
                        )

                except Exception as e:
                    health_checks.append(
                        {"check": "validation_error", "status": "fail", "error": str(e)}
                    )

                stats_data["health_checks"] = health_checks
                stats_data["health_status"] = (
                    "healthy"
                    if all(c.get("status") == "pass" for c in health_checks)
                    else "unhealthy"
                )

            # Output results
            if output_format == "json":
                # Convert datetime objects to ISO format for JSON
                def serialize_datetime(obj):
                    if hasattr(obj, "isoformat"):
                        return obj.isoformat()
                    return obj

                rich_print(json.dumps(stats_data, indent=2, default=serialize_datetime))
            else:
                # Text format
                rich_panel(
                    f"Total Memories: {stats_data['total_memories']}\n"
                    f"Recent Activity: {stats_data['recent_activity']} memories",
                    title="📊 System Status",
                    style="blue",
                )

                if show_project:
                    rich_print("\n📁 Project Information:")
                    rich_print(f"   Root: {stats_data['project_root']}")
                    rich_print(f"   Database: {stats_data['database_path']}")
                    rich_print(
                        f"   Memories Dir: {stats_data.get('memories_directory', 'N/A')}"
                    )
                    rich_print("\n⚙️  Configuration:")
                    rich_print(
                        f"   Source: {stats_data.get('config_source', 'default')}"
                    )
                    if stats_data.get("config_path"):
                        rich_print(f"   Path: {stats_data['config_path']}")

                    if "auggie_integration" in stats_data:
                        auggie_info = stats_data["auggie_integration"]
                        rich_print("\n🤖 Auggie Integration:")
                        rich_print(
                            f"   Status: {'✅ Active' if auggie_info['active'] else '⚠️  Available but inactive'}"
                        )
                        rich_print(f"   Rules Files: {auggie_info['rules_files']}")
                        rich_print(f"   Memory Rules: {auggie_info['memory_rules']}")

                if detailed:
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

                    if stats_data.get("daily_activity"):
                        rich_print("\n📊 Daily Activity (Last 7 Days):")
                        for date, count in stats_data["daily_activity"].items():
                            rich_print(f"   {date}: {count} memories")

                if validate:
                    health_status = stats_data.get("health_status", "unknown")
                    health_icon = "✅" if health_status == "healthy" else "⚠️"
                    rich_print(
                        f"\n🏥 Health Status: {health_icon} {health_status.title()}"
                    )

                    if stats_data.get("health_checks"):
                        rich_print("\n🔍 Health Checks:")
                        for check in stats_data["health_checks"]:
                            status_icon = "✅" if check["status"] == "pass" else "❌"
                            rich_print(f"   {status_icon} {check['check']}")
                            if check.get("error"):
                                rich_print(
                                    f"      Error: {check['error']}", style="dim"
                                )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Status check failed: {e}", style="red")
        sys.exit(1)


__all__ = ["status"]
