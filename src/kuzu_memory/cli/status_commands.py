"""
Status and information CLI commands for KuzuMemory.

Provides unified status command combining stats and project info.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import click

from ..utils.config_loader import get_config_loader
from ..utils.project_setup import (
    find_project_root,
    get_project_db_path,
    get_project_memories_dir,
)
from .cli_utils import rich_panel, rich_print
from .enums import OutputFormat
from .service_manager import ServiceManager

logger = logging.getLogger(__name__)


@click.command()
@click.option("--validate", is_flag=True, help="Run health validation checks")
@click.option("--project", "show_project", is_flag=True, help="Show detailed project information")
@click.option("--detailed", is_flag=True, help="Show detailed statistics")
@click.option(
    "--format",
    "output_format",
    default=OutputFormat.TEXT.value,
    type=click.Choice([OutputFormat.TEXT.value, OutputFormat.JSON.value]),
    help="Output format",
)
@click.option("--db-path", type=click.Path(), help="Database path (overrides project default)")
@click.pass_context
def status(
    ctx: click.Context,
    validate: bool,
    show_project: bool,
    detailed: bool,
    output_format: str,
    db_path: str | None,
) -> None:
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
        # Resolve project root and database path
        project_root = ctx.obj.get("project_root") or find_project_root()
        db_path_obj: Path | None = None
        if db_path:
            db_path_obj = Path(db_path)
        else:
            db_path_obj = get_project_db_path(project_root)

        # Check if initialized
        if not db_path_obj.exists():
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
        with ServiceManager.memory_service(
            db_path=db_path_obj, enable_git_sync=enable_sync
        ) as memory:
            # Collect statistics
            total_memories = memory.get_memory_count()
            recent_memories = memory.get_recent_memories(limit=24)

            stats_data = {
                "initialized": True,
                "project_root": str(project_root),
                "database_path": str(db_path_obj),
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
                # Note: These methods are not in IMemoryService protocol yet
                # They will be added in a future protocol update
                # For now, we access the underlying KuzuMemory instance
                if hasattr(memory, "kuzu_memory"):
                    km = memory.kuzu_memory
                    stats_data.update(
                        {
                            "avg_memory_length": (
                                km.get_average_memory_length()
                                if hasattr(km, "get_average_memory_length")
                                else None
                            ),
                            "oldest_memory": (
                                km.get_oldest_memory_date()
                                if hasattr(km, "get_oldest_memory_date")
                                else None
                            ),
                            "newest_memory": (
                                km.get_newest_memory_date()
                                if hasattr(km, "get_newest_memory_date")
                                else None
                            ),
                            "daily_activity": (
                                km.get_daily_activity_stats(days=7)
                                if hasattr(km, "get_daily_activity_stats")
                                else {}
                            ),
                        }
                    )

            # Run validation if requested
            if validate:
                health_checks = []
                try:
                    # Test basic operations
                    memory.get_recent_memories(limit=1)
                    health_checks.append({"check": "database_connection", "status": "pass"})

                    # Test write capability (use kuzu_memory for store_memory method)
                    if hasattr(memory, "kuzu_memory"):
                        km = memory.kuzu_memory
                        test_id = km.store_memory("_health_check_test", source="health_check")
                        if test_id:
                            health_checks.append({"check": "write_capability", "status": "pass"})
                            # Clean up test memory
                            km.delete_memory(test_id)
                        else:
                            health_checks.append({"check": "write_capability", "status": "fail"})
                    else:
                        health_checks.append(
                            {
                                "check": "write_capability",
                                "status": "skip",
                                "message": "Service doesn't expose store_memory",
                            }
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
                def serialize_datetime(obj: Any) -> Any:
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
                    rich_print(f"   Memories Dir: {stats_data.get('memories_directory', 'N/A')}")
                    rich_print("\n⚙️  Configuration:")
                    rich_print(f"   Source: {stats_data.get('config_source', 'default')}")
                    if stats_data.get("config_path"):
                        rich_print(f"   Path: {stats_data['config_path']}")

                    if "auggie_integration" in stats_data:
                        auggie_info = stats_data["auggie_integration"]
                        assert isinstance(auggie_info, dict)
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

                    oldest_memory = stats_data.get("oldest_memory")
                    if oldest_memory:
                        assert isinstance(oldest_memory, datetime)
                        rich_print("\n📅 Memory Timeline:")
                        rich_print(f"   Oldest: {oldest_memory.strftime('%Y-%m-%d %H:%M')}")
                        newest_memory = stats_data.get("newest_memory")
                        if newest_memory:
                            assert isinstance(newest_memory, datetime)
                            rich_print(f"   Newest: {newest_memory.strftime('%Y-%m-%d %H:%M')}")

                    daily_activity = stats_data.get("daily_activity")
                    if daily_activity:
                        assert isinstance(daily_activity, dict)
                        rich_print("\n📊 Daily Activity (Last 7 Days):")
                        for date, count in daily_activity.items():
                            rich_print(f"   {date}: {count} memories")

                if validate:
                    health_status = cast(str, stats_data.get("health_status", "unknown"))
                    health_icon = "✅" if health_status == "healthy" else "⚠️"
                    rich_print(f"\n🏥 Health Status: {health_icon} {health_status.title()}")

                    health_checks_obj = stats_data.get("health_checks")
                    if health_checks_obj:
                        health_checks = cast(list[dict[str, Any]], health_checks_obj)
                        rich_print("\n🔍 Health Checks:")
                        for check in health_checks:
                            status_icon = "✅" if check["status"] == "pass" else "❌"
                            rich_print(f"   {status_icon} {check['check']}")
                            if check.get("error"):
                                rich_print(f"      Error: {check['error']}", style="dim")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Status check failed: {e}", style="red")
        sys.exit(1)


__all__ = ["status"]
