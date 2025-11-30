"""
Project initialization CLI command for KuzuMemory.

Extracted from project_commands.py for clean top-level command structure.
"""

import json
import logging
import sys
from pathlib import Path

import click

from ..integrations.auggie import AuggieIntegration
from ..utils.project_setup import (
    find_project_root,
    get_project_context_summary,
    get_project_db_path,
    get_project_memories_dir,
)
from .cli_utils import rich_confirm, rich_panel, rich_print
from .service_manager import ServiceManager

logger = logging.getLogger(__name__)


@click.command()
@click.option("--force", is_flag=True, help="Overwrite existing project memories")
@click.option("--config-path", type=click.Path(), help="Path to save example configuration")
@click.option("--project-root", type=click.Path(), help="Project root path (optional)")
@click.pass_context
def init(
    ctx: click.Context,
    force: bool,
    config_path: Path | str | None,
    project_root: str | None,
) -> None:
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

      # Initialize specific project
      kuzu-memory init --project-root /path/to/project
    """
    from kuzu_memory.services import ConfigService, SetupService

    try:
        # Convert project_root to Path if provided
        project_root_path = Path(project_root) if project_root else None
        if project_root_path is None:
            project_root_path = ctx.obj.get("project_root") or find_project_root()

        rich_print(f"🚀 Initializing KuzuMemory for project: {project_root_path}")

        # Multi-service orchestration: ConfigService + SetupService
        config_service = ConfigService(project_root_path)
        config_service.initialize()

        setup_service = SetupService(config_service)
        setup_service.initialize()

        try:
            # Get paths before initialization check
            memories_dir = get_project_memories_dir(project_root_path)
            db_path = get_project_db_path(project_root_path)

            # Check if already initialized
            if db_path.exists() and not force:
                rich_print(f"⚠️  Project already initialized at {memories_dir}", style="yellow")
                rich_print("   Use --force to overwrite existing memories", style="dim")
                sys.exit(1)

            # Initialize project structure
            result = setup_service.initialize_project(force=force)

            if not result["success"]:
                rich_print(
                    f"❌ Project initialization failed: {result['summary']}",
                    style="red",
                )
                if result.get("warnings"):
                    for warning in result["warnings"]:
                        rich_print(f"   ⚠️  {warning}", style="yellow")
                sys.exit(1)

            rich_print(f"✅ Created memories directory: {memories_dir}")

            # Initialize database with project context using ServiceManager
            with ServiceManager.memory_service(db_path) as memory:
                # Store initial project context
                project_context = get_project_context_summary(project_root_path)
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
                config_path_obj = Path(config_path)
                example_config = {
                    "storage": {"db_path": str(db_path), "backup_enabled": True},
                    "memory": {
                        "max_memories_per_query": 10,
                        "similarity_threshold": 0.7,
                    },
                    "temporal_decay": {"enabled": True, "recent_boost_hours": 24},
                }

                config_path_obj.write_text(json.dumps(example_config, indent=2))
                rich_print(f"✅ Created example config: {config_path_obj}")

            # Check for Auggie integration
            try:
                auggie = AuggieIntegration(project_root_path)

                if auggie.is_auggie_project():
                    rich_print("\n🤖 Auggie project detected!")
                    if rich_confirm("Would you like to set up Auggie integration?", default=True):
                        try:
                            auggie.setup_project_integration()
                            rich_print("✅ Auggie integration configured")
                        except Exception as e:
                            rich_print(
                                f"⚠️  Auggie integration setup failed: {e}",
                                style="yellow",
                            )
            except ImportError:
                pass

            rich_panel(
                f"KuzuMemory is now ready! 🎉\n\n"
                f"📁 Memories directory: {memories_dir}\n"
                f"🗄️  Database: {db_path}\n\n"
                f"Next steps:\n"
                f"• Store your first memory: kuzu-memory memory store 'Project uses FastAPI'\n"
                f"• Enhance prompts: kuzu-memory memory enhance 'How do I deploy?'\n"
                f"• Learn from conversations: kuzu-memory memory learn 'User prefers TypeScript'\n",
                title="🎯 Initialization Complete",
                style="green",
            )

        finally:
            # Ensure cleanup of services
            setup_service.cleanup()
            config_service.cleanup()

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Initialization failed: {e}", style="red")
        sys.exit(1)


__all__ = ["init"]
