"""
Project initialization CLI command for KuzuMemory.

Extracted from project_commands.py for clean top-level command structure.
"""

import json
import logging
import sys
from pathlib import Path

import click

from ..core.config import KuzuMemoryConfig
from ..core.memory import KuzuMemory
from ..integrations.auggie import AuggieIntegration
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
@click.option(
    "--config-path", type=click.Path(), help="Path to save example configuration"
)
@click.pass_context
def init(ctx, force: bool, config_path):
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
        project_root = ctx.obj.get("project_root") or find_project_root()
        memories_dir = get_project_memories_dir(project_root)
        db_path = get_project_db_path(project_root)

        rich_print(f"🚀 Initializing KuzuMemory for project: {project_root}")

        # Check if already initialized
        if db_path.exists() and not force:
            rich_print(
                f"⚠️  Project already initialized at {memories_dir}", style="yellow"
            )
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

            # Note: Auto git sync already triggered during KuzuMemory.__init__()
            # via _auto_git_sync("init") call

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
            auggie = AuggieIntegration(project_root)

            if auggie.is_auggie_project():
                rich_print("\n🤖 Auggie project detected!")
                if rich_confirm(
                    "Would you like to set up Auggie integration?", default=True
                ):
                    try:
                        auggie.setup_project_integration()
                        rich_print("✅ Auggie integration configured")
                    except Exception as e:
                        rich_print(
                            f"⚠️  Auggie integration setup failed: {e}", style="yellow"
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

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Initialization failed: {e}", style="red")
        sys.exit(1)


__all__ = ["init"]
