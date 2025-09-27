"""
Main CLI entry point for KuzuMemory.

Provides the main CLI group and imports all subcommands from modular files.
This is the refactored version that keeps the file under 300 lines.
"""

import logging
import sys
from pathlib import Path

import click

from ..__version__ import __version__
from ..core.config import KuzuMemoryConfig
from ..utils.config_loader import get_config_loader
from ..utils.project_setup import find_project_root, get_project_db_path
from .auggie_commands import auggie
from .claude_commands import claude_group
from .cli_utils import rich_panel, rich_print

# Import install commands
from .install_commands_simple import install_group, list_installers, status, uninstall
from .mcp_commands import mcp

# Import command modules
from .memory_commands import enhance, learn, recall, recent, remember
from .project_commands import cleanup, create_config, init, project, stats
from .utility_commands import examples, optimize, setup, temporal_analysis, tips

# Set up logging for CLI
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="kuzu-memory")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to configuration file"
)
@click.option(
    "--db-path",
    type=click.Path(),
    help="Path to database file (overrides project default)",
)
@click.option(
    "--project-root",
    type=click.Path(exists=True),
    help="Project root directory (auto-detected if not specified)",
)
@click.pass_context
def cli(ctx, debug, config, db_path, project_root):
    """
    🧠 KuzuMemory - Intelligent AI Memory System

    A lightweight, high-performance memory system designed for AI applications.
    Stores and recalls project-specific information with sub-100ms response times.

    \b
    🚀 QUICK START:
      kuzu-memory init              # Initialize project memory
      kuzu-memory remember "info"   # Store information
      kuzu-memory enhance "prompt"  # Enhance AI prompts
      kuzu-memory learn "content"   # Learn asynchronously

    \b
    🎯 KEY FEATURES:
      • Sub-100ms context retrieval for AI responses
      • Async learning operations (non-blocking)
      • Project-specific memory (git-committed)
      • Intelligent context enhancement
      • Temporal decay for memory relevance

    Use 'kuzu-memory COMMAND --help' for detailed help on any command.
    """
    # Initialize context object
    ctx.ensure_object(dict)

    # Configure debug logging
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        ctx.obj["debug"] = True

    # Determine project root
    try:
        if project_root:
            project_root = Path(project_root).resolve()
        else:
            project_root = find_project_root()
        ctx.obj["project_root"] = project_root
    except Exception:
        if debug:
            raise
        # For some commands (like quickstart), project root isn't required
        ctx.obj["project_root"] = None

    # Load configuration
    try:
        config_loader = get_config_loader()
        if config:
            loaded_config = config_loader.load_from_file(config)
        else:
            loaded_config = config_loader.load_config(ctx.obj["project_root"])
        ctx.obj["config"] = loaded_config
    except Exception as e:
        if debug:
            logger.debug(f"Config loading failed: {e}")
        # Use default config if loading fails
        ctx.obj["config"] = KuzuMemoryConfig()

    # Override database path if specified
    if db_path:
        ctx.obj["db_path"] = Path(db_path)

    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        # Check if project is initialized
        try:
            if ctx.obj["project_root"]:
                db_path_check = get_project_db_path(ctx.obj["project_root"])
                if not db_path_check.exists():
                    rich_panel(
                        "Welcome to KuzuMemory! 🚀\n\n"
                        "It looks like this project isn't initialized yet.\n"
                        "Get started with: kuzu-memory init\n\n"
                        "Or try the interactive quickstart: kuzu-memory quickstart",
                        title="🧠 KuzuMemory",
                        style="blue",
                    )
                else:
                    rich_panel(
                        "KuzuMemory is ready! 🎉\n\n"
                        "Try these commands:\n"
                        "• kuzu-memory recent        # Show recent memories\n"
                        "• kuzu-memory stats         # System statistics\n"
                        "• kuzu-memory remember      # Store new memory\n"
                        "• kuzu-memory enhance       # Enhance prompts\n"
                        "\nFor all commands: kuzu-memory --help",
                        title="🧠 KuzuMemory",
                        style="green",
                    )
        except Exception:
            pass  # If anything fails, just show help

        rich_print(ctx.get_help())


@click.command()
@click.option("--skip-demo", is_flag=True, help="Skip the interactive demo")
@click.pass_context
def quickstart(ctx, skip_demo):
    """
    🎯 Interactive quickstart guide for KuzuMemory.

    Walks you through setting up KuzuMemory with hands-on examples
    and demonstrates key features through an interactive experience.

    \b
    🎮 WHAT YOU'LL LEARN:
      • How to initialize KuzuMemory
      • Storing and retrieving memories
      • Enhancing AI prompts with context
      • Best practices and tips

    Perfect for first-time users!
    """
    try:
        rich_panel(
            "Welcome to KuzuMemory! 🧠✨\n\n"
            "This quickstart will walk you through:\n"
            "• Setting up your first project\n"
            "• Storing and retrieving memories\n"
            "• Enhancing AI prompts\n"
            "• Learning best practices\n\n"
            "Let's get started!",
            title="🎯 KuzuMemory Quickstart",
            style="blue",
        )

        # Step 1: Project Setup
        rich_print("\n📁 Step 1: Project Setup")
        project_root = ctx.obj.get("project_root")
        if not project_root:
            project_root = Path.cwd()
            rich_print(f"Using current directory: {project_root}")

        db_path = get_project_db_path(project_root)
        if not db_path.exists():
            rich_print("Initializing KuzuMemory for this project...")
            ctx.invoke(init)
        else:
            rich_print("✅ Project already initialized!")

        if skip_demo:
            rich_print("\n🎉 Setup complete! Try these commands:")
            rich_print("• kuzu-memory remember 'Your project info'")
            rich_print("• kuzu-memory enhance 'Your question'")
            rich_print("• kuzu-memory stats")
            return

        # Interactive demo continues...
        rich_print("\n🧠 Step 2: Storing Memories")
        from .cli_utils import rich_confirm, rich_prompt

        if rich_confirm("Would you like to store your first memory?", default=True):
            sample_memory = rich_prompt(
                "Enter something about your project",
                default="This is a Python project using KuzuMemory for AI memory",
            )
            ctx.invoke(remember, content=sample_memory, source="quickstart")

        # Step 3: Demo enhancement
        rich_print("\n🚀 Step 3: Prompt Enhancement")
        if rich_confirm("Try enhancing a prompt?", default=True):
            sample_prompt = rich_prompt(
                "Enter a question about your project",
                default="How should I structure my code?",
            )
            ctx.invoke(
                enhance, prompt=sample_prompt, max_memories=3, output_format="context"
            )

        # Step 4: Show stats
        rich_print("\n📊 Step 4: Project Status")
        ctx.invoke(stats, detailed=False, output_format="text")

        # Completion
        rich_panel(
            "Quickstart Complete! 🎉\n\n"
            "You now know how to:\n"
            "• Store memories with 'remember'\n"
            "• Enhance prompts with 'enhance'\n"
            "• Learn async with 'learn'\n"
            "• Check stats and project info\n\n"
            "Next steps:\n"
            "• Explore: kuzu-memory examples\n"
            "• Get tips: kuzu-memory tips\n"
            "• Read docs: See project documentation",
            title="🎯 Ready to Go!",
            style="green",
        )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Quickstart failed: {e}", style="red")
        sys.exit(1)


@click.command()
@click.pass_context
def demo(ctx):
    """
    🎮 Interactive demo of KuzuMemory features.

    Provides a hands-on demonstration of core functionality
    including memory storage, recall, and enhancement features.
    """
    try:
        rich_panel(
            "KuzuMemory Interactive Demo! 🎮\n\n"
            "This demo will show you how KuzuMemory works with real examples.\n"
            "Follow along to learn the key features.",
            title="🎮 Demo Mode",
            style="magenta",
        )

        # Demo implementation would go here
        # For brevity, redirecting to quickstart
        rich_print("For now, try the quickstart guide:")
        rich_print("kuzu-memory quickstart")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Demo failed: {e}", style="red")
        sys.exit(1)


# Add all commands to the main CLI group
cli.add_command(quickstart)
cli.add_command(demo)

# Memory commands
cli.add_command(enhance)
cli.add_command(learn)
cli.add_command(remember)
cli.add_command(recall)
cli.add_command(recent)

# Project commands
cli.add_command(init)
cli.add_command(project)
cli.add_command(stats)
cli.add_command(cleanup)
cli.add_command(create_config, name="create-config")

# Utility commands
cli.add_command(optimize)
cli.add_command(setup)
cli.add_command(tips)
cli.add_command(examples)
cli.add_command(temporal_analysis, name="temporal-analysis")

# Auggie integration
cli.add_command(auggie)

# Claude integration
cli.add_command(claude_group, name="claude")

# MCP server commands
cli.add_command(mcp)

# Install commands
cli.add_command(install_group)
cli.add_command(uninstall)
cli.add_command(status, name="install-status")
cli.add_command(list_installers, name="list-installers")


if __name__ == "__main__":
    cli()
