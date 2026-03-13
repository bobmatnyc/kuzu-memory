"""
User-level cross-project memory CLI commands.

Provides the `user` command group with subcommands to manage the shared
~/.kuzu-memory/user.db that aggregates high-quality memories across projects.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from .cli_utils import rich_panel, rich_print, rich_table


@click.group()
def user() -> None:
    """
    User-level cross-project memory management.

    Manages the shared ~/.kuzu-memory/user.db that aggregates high-quality
    memories (rules, patterns, gotchas, architecture decisions) from all
    projects.

    \b
    Commands:
      setup    Initialize user DB and enable user mode
      status   Show user DB statistics
      promote  Manually promote memories from current project
      disable  Revert to project-only mode
    """
    pass


@user.command()
@click.option(
    "--user-db-path",
    default=None,
    help="Override default user DB path (~/.kuzu-memory/user.db)",
)
@click.pass_context
def setup(ctx: click.Context, user_db_path: str | None) -> None:
    """
    Initialize user DB and enable user mode.

    Creates ~/.kuzu-memory/user.db, initialises the schema, and sets
    mode: user in ~/.kuzu-memory/config.yaml so all future sessions
    promote eligible memories automatically.
    """
    from ..core.config import KuzuMemoryConfig
    from ..services.user_memory_service import UserMemoryService

    try:
        config = ctx.obj.get("config", KuzuMemoryConfig()) if ctx.obj else KuzuMemoryConfig()
        if not isinstance(config, KuzuMemoryConfig):
            config = KuzuMemoryConfig()

        if user_db_path:
            config.user.user_db_path = user_db_path

        db_path = config.user.effective_user_db_path()

        rich_print(f"Setting up user DB at: {db_path}")
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Open the user DB — this initialises the schema via KuzuMemory.__enter__
        with UserMemoryService(config) as user_svc:
            stats = user_svc.get_stats()
            total = stats.get("total_memories", 0)

        # Enable user mode in config
        config.user.mode = "user"
        user_config_path = Path.home() / ".kuzu-memory" / "config.yaml"
        user_config_path.parent.mkdir(parents=True, exist_ok=True)
        config.save_to_file(user_config_path)

        rich_panel(
            f"User DB initialised: {db_path}\n"
            f"Existing memories: {total}\n"
            f"Mode: user (saved to {user_config_path})\n\n"
            "From now on, sessions will automatically promote high-quality\n"
            "memories (importance >= 0.8, type in rule/pattern/gotcha/architecture)\n"
            "to this shared database at session end.",
            title="User Mode Enabled",
            style="green",
        )

    except Exception as e:
        rich_print(f"Error: {e}", style="red")
        if ctx.obj and ctx.obj.get("debug"):
            raise
        sys.exit(1)


@user.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """
    Show user DB statistics.

    Displays total memory count, breakdown by knowledge_type, and the
    top projects that have contributed memories to the user DB.
    """
    from ..core.config import KuzuMemoryConfig
    from ..services.user_memory_service import UserMemoryService

    try:
        config = ctx.obj.get("config", KuzuMemoryConfig()) if ctx.obj else KuzuMemoryConfig()
        if not isinstance(config, KuzuMemoryConfig):
            config = KuzuMemoryConfig()

        db_path = config.user.effective_user_db_path()

        if not db_path.exists():
            rich_print(
                "User DB not found. Run 'kuzu-memory user setup' to initialise.",
                style="yellow",
            )
            return

        with UserMemoryService(config) as user_svc:
            stats = user_svc.get_stats()

        total = stats.get("total_memories", 0)
        by_type: dict[str, Any] = stats.get("by_knowledge_type", {})
        by_project: dict[str, Any] = stats.get("by_project", {})

        lines = [
            f"User DB: {db_path}",
            f"Mode: {config.user.mode}",
            f"Total memories: {total}",
        ]
        if by_type:
            type_str = ", ".join(f"{k}={v}" for k, v in sorted(by_type.items()))
            lines.append(f"By type: {type_str}")
        if by_project:
            proj_str = ", ".join(f"{k} ({v})" for k, v in by_project.items())
            lines.append(f"From projects: {proj_str}")

        rich_panel("\n".join(lines), title="User Memory Status", style="blue")

    except Exception as e:
        rich_print(f"Error: {e}", style="red")
        if ctx.obj and ctx.obj.get("debug"):
            raise
        sys.exit(1)


@user.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be promoted without writing to user DB",
)
@click.option(
    "--min-importance",
    default=None,
    type=float,
    help="Override minimum importance threshold (default from config)",
)
@click.option("--db-path", type=click.Path(), default=None, help="Project DB path override")
@click.pass_context
def promote(
    ctx: click.Context,
    dry_run: bool,
    min_importance: float | None,
    db_path: str | None,
) -> None:
    """
    Manually promote memories from the current project to user DB.

    Scans the project DB for memories meeting the promotion criteria
    (knowledge_type in rule/pattern/gotcha/architecture AND importance >= threshold)
    and writes them to the user DB. Deduplicates by content_hash.

    Use --dry-run to preview what would be promoted.
    """
    import datetime

    from ..core.config import KuzuMemoryConfig
    from ..core.models import Memory
    from ..services import MemoryService
    from ..services.user_memory_service import UserMemoryService
    from ..utils.project_setup import get_project_db_path

    try:
        config = ctx.obj.get("config", KuzuMemoryConfig()) if ctx.obj else KuzuMemoryConfig()
        if not isinstance(config, KuzuMemoryConfig):
            config = KuzuMemoryConfig()

        if min_importance is not None:
            config.user.promotion_min_importance = min_importance

        # Resolve project DB path
        if db_path:
            project_db = Path(db_path)
        elif ctx.obj and ctx.obj.get("project_root"):
            project_db = get_project_db_path(ctx.obj["project_root"])
        else:
            from ..utils.project_setup import find_project_root

            root = find_project_root()
            project_db = get_project_db_path(root) if root else Path.cwd() / ".kuzu-memory"

        if not project_db.exists():
            rich_print(
                f"Project DB not found at {project_db}. Run 'kuzu-memory setup' first.",
                style="yellow",
            )
            return

        # Query candidates from project DB using the public db_adapter API
        with MemoryService(db_path=project_db, enable_git_sync=False, config=config) as mem_svc:
            candidate_rows = mem_svc.kuzu_memory.db_adapter.execute_query(
                """MATCH (m:Memory)
                WHERE m.knowledge_type IN $types
                  AND m.importance >= $min_imp
                  AND (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now))
                RETURN m ORDER BY m.importance DESC LIMIT 100""",
                {
                    "types": config.user.promotion_knowledge_types,
                    "min_imp": config.user.promotion_min_importance,
                    "now": datetime.datetime.now().isoformat(),
                },
            )

        if not candidate_rows:
            rich_print("No memories meet the promotion criteria.", style="yellow")
            return

        memories = [Memory.from_dict(row.get("m", row)) for row in candidate_rows]
        project_tag = config.user.effective_project_tag()

        rich_print(
            f"Found {len(memories)} candidate memories "
            f"(project_tag={project_tag!r}, min_importance={config.user.promotion_min_importance})"
        )

        if dry_run:
            table_data = [
                [m.knowledge_type.value, f"{m.importance:.2f}", m.content[:80]] for m in memories
            ]
            rich_table(
                ["Type", "Importance", "Content"],
                table_data,
                title="Promotion Candidates (dry-run)",
            )
            return

        # Actually promote
        with UserMemoryService(config) as user_svc:
            written = user_svc.promote_batch(memories, project_tag)

        rich_print(
            f"Promoted {written}/{len(memories)} memories to user DB "
            f"({len(memories) - written} already present).",
            style="green",
        )

    except Exception as e:
        rich_print(f"Error: {e}", style="red")
        if ctx.obj and ctx.obj.get("debug"):
            raise
        sys.exit(1)


@user.command()
@click.pass_context
def disable(ctx: click.Context) -> None:
    """
    Revert to project-only mode (stop promotion).

    Sets mode: project in ~/.kuzu-memory/config.yaml. The user DB is
    preserved — re-enabling user mode resumes from existing state.
    """
    from ..core.config import KuzuMemoryConfig

    try:
        config = ctx.obj.get("config", KuzuMemoryConfig()) if ctx.obj else KuzuMemoryConfig()
        if not isinstance(config, KuzuMemoryConfig):
            config = KuzuMemoryConfig()

        config.user.mode = "project"
        user_config_path = Path.home() / ".kuzu-memory" / "config.yaml"
        user_config_path.parent.mkdir(parents=True, exist_ok=True)
        config.save_to_file(user_config_path)

        rich_panel(
            f"Mode set to: project\nConfig saved to: {user_config_path}\n\n"
            "Promotion is disabled. The user DB is preserved.\n"
            "Re-enable with 'kuzu-memory user setup'.",
            title="User Mode Disabled",
            style="yellow",
        )

    except Exception as e:
        rich_print(f"Error: {e}", style="red")
        if ctx.obj and ctx.obj.get("debug"):
            raise
        sys.exit(1)
