"""
Main CLI entry point for KuzuMemory.

Provides the main CLI group and imports all subcommands from modular files.
This is the refactored version that keeps the file under 300 lines.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from ..__version__ import __version__
from ..core.config import KuzuMemoryConfig
from ..utils.config_loader import get_config_loader
from ..utils.project_setup import find_project_root, get_project_db_path

# Import top-level command groups (10 total now with setup)
from .cli_utils import rich_panel, rich_print, rich_table
from .doctor_commands import doctor
from .enums import OutputFormat
from .git_commands import git
from .help_commands import help_group
from .hooks_commands import hooks_group
from .init_commands import init
from .install_unified import (
    install_command,
    remove_command,
    repair_command,
    uninstall_command,
)
from .mcp_server_command import mcp_server
from .memory_commands import enhance, memory, recall, recent, store
from .setup_commands import setup
from .status_commands import status
from .update_commands import update

# Set up logging for CLI
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _silent_repair_mcp_configs() -> None:
    """
    Silently repair broken MCP configurations before running commands.

    This runs automatically on every CLI invocation to ensure configs
    are always in the correct state. No user interaction required.

    Auto-detects and fixes the broken ["mcp", "serve"] args pattern
    to the correct ["mcp"] pattern across all projects in ~/.claude.json.
    """
    try:
        # Import here to avoid circular imports
        from ..installers.json_utils import (
            fix_broken_mcp_args,
            load_json_config,
            save_json_config,
        )

        claude_json = Path.home() / ".claude.json"
        if not claude_json.exists():
            return  # No config to repair

        # Read current config
        config = load_json_config(claude_json)

        # Apply auto-fix
        fixed_config, fixes = fix_broken_mcp_args(config)

        if fixes:
            # Write repaired config
            save_json_config(claude_json, fixed_config, indent=2)

            # Log repairs (info level, not visible to user unless --debug)
            logger.info(f"Auto-repaired {len(fixes)} broken MCP configuration(s)")
            for fix in fixes:
                logger.debug(fix)

    except Exception as e:
        # Silent failure - don't block other commands
        logger.debug(f"Auto-repair skipped: {e}")


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="kuzu-memory")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--config", type=click.Path(exists=True), help="Path to configuration file")
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
def cli(
    ctx: click.Context,
    debug: bool,
    config: str | None,
    db_path: str | None,
    project_root: str | None,
) -> None:
    """
    🧠 KuzuMemory - Intelligent AI Memory System

    A lightweight, high-performance memory system designed for AI applications.
    Stores and recalls project-specific information with sub-100ms response times.

    \b
    🚀 QUICK START (RECOMMENDED):
      kuzu-memory setup                   # Smart setup (auto-detects everything)
      kuzu-memory remember "info"         # Store information
      kuzu-memory enhance "prompt"        # Enhance AI prompts
      kuzu-memory learn "content"         # Learn asynchronously

    \b
    🛠️  ADVANCED (MANUAL CONTROL):
      kuzu-memory init                    # Just initialize database
      kuzu-memory install claude-code     # Just install integration

    \b
    🔧 INSTALLATION (ONE WAY):
      kuzu-memory install <integration>   # Install for an IDE/tool
      kuzu-memory uninstall <integration> # Uninstall integration
      kuzu-memory remove <integration>    # Alias for uninstall
      kuzu-memory repair                  # Repair broken MCP configs

    \b
    📦 AVAILABLE INTEGRATIONS:
      claude-code      Claude Code (MCP + hooks)
      claude-desktop   Claude Desktop (MCP only)
      cursor           Cursor IDE (MCP only)
      vscode           VS Code (MCP only)
      windsurf         Windsurf IDE (MCP only)
      auggie           Auggie (rules)

    \b
    🎯 KEY FEATURES:
      • Sub-100ms context retrieval for AI responses
      • Async learning operations (non-blocking)
      • Project-specific memory (git-committed)
      • Intelligent context enhancement
      • Temporal decay for memory relevance

    Use 'kuzu-memory COMMAND --help' for detailed help on any command.
    """
    # Auto-repair MCP configs before running any command
    # Skip for help/version commands to avoid unnecessary overhead
    skip_repair_commands = {None, "help", "--help", "--version"}
    if ctx.invoked_subcommand not in skip_repair_commands:
        _silent_repair_mcp_configs()

    # Initialize context object
    ctx.ensure_object(dict)

    # Configure debug logging
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        ctx.obj["debug"] = True

    # Determine project root
    try:
        resolved_root: Path | None
        if project_root:
            resolved_root = Path(project_root).resolve()
        else:
            resolved_root = find_project_root()
        ctx.obj["project_root"] = resolved_root
    except Exception:
        if debug:
            raise
        # For some commands (like quickstart), project root isn't required
        ctx.obj["project_root"] = None

    # Load configuration
    try:
        config_loader = get_config_loader()
        if config:
            loaded_config = config_loader.load_from_file(config)  # type: ignore[attr-defined]  # Runtime method exists
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
                        "Get started with the smart setup (recommended):\n\n"
                        "  kuzu-memory setup\n\n"
                        "Or try the interactive quickstart:\n\n"
                        "  kuzu-memory quickstart\n\n"
                        "💡 The 'setup' command auto-detects and configures everything!",
                        title="🧠 KuzuMemory",
                        style="blue",
                    )
                else:
                    rich_panel(
                        "KuzuMemory is ready! 🎉\n\n"
                        "Try these commands:\n"
                        "• kuzu-memory recent        # Show recent memories\n"
                        "• kuzu-memory status        # System statistics\n"
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
def quickstart(ctx: click.Context, skip_demo: bool) -> None:
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
    import time

    from .cli_utils import rich_confirm, rich_prompt

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
            ctx.invoke(init, force=False)
        else:
            rich_print("✅ Project already initialized!")

        if skip_demo:
            rich_print("\n🎉 Setup complete! Try these commands:")
            rich_print("• kuzu-memory remember 'Your project info'")
            rich_print("• kuzu-memory enhance 'Your question'")
            rich_print("• kuzu-memory status")
            return

        # Interactive demo continues...
        rich_print("\n🧠 Step 2: Storing Memories")

        if rich_confirm("Would you like to store your first memory?", default=True):
            sample_memory = rich_prompt(
                "Enter something about your project",
                default="This is a Python project using KuzuMemory for AI memory",
            )
            ctx.invoke(
                store,
                content=sample_memory,
                source="quickstart",
                session_id=None,
                agent_id="quickstart",
                metadata=None,
            )

        # Step 3: Demo enhancement
        rich_print("\n🚀 Step 3: Prompt Enhancement")
        if rich_confirm("Try enhancing a prompt?", default=True):
            sample_prompt = rich_prompt(
                "Enter a question about your project",
                default="How should I structure my code?",
            )
            ctx.invoke(enhance, prompt=sample_prompt, max_memories=3, output_format="context")

        # Step 4: Show stats
        rich_print("\n📊 Step 4: Project Status")
        ctx.invoke(
            status,
            validate=False,
            show_project=False,
            detailed=False,
            output_format="text",
        )

        # Step 5: Recent Memories
        rich_print("\n" + "─" * 50)
        rich_print("📚 [bold magenta]Step 5: View Recent Memories[/bold magenta]")

        if rich_confirm("Would you like to view your recent memories?", default=True):
            ctx.invoke(recent, limit=5, output_format="list")
            time.sleep(1)

        # Step 6: Memory Recall
        rich_print("\n" + "─" * 50)
        rich_print("🔍 [bold magenta]Step 6: Try Memory Recall[/bold magenta]")
        rich_print("Recall uses semantic search to find relevant memories based on your query.\n")
        if rich_confirm("Would you like to try querying your memories?", default=True):
            query = rich_prompt("Enter a search query", default="Python project structure")
            ctx.invoke(
                recall,
                prompt=query,
                max_memories=5,
                strategy="auto",
                session_id=None,
                agent_id="cli",
                output_format="simple",
                explain_ranking=False,
            )
            time.sleep(1)

        # Step 7: Memory Types
        rich_print("\n" + "─" * 50)
        rich_print("🧠 [bold magenta]Step 7: Understanding Memory Types[/bold magenta]")
        if rich_confirm("Want to learn about different memory types?", default=True):
            memory_types_data = [
                [
                    "SEMANTIC",
                    "Facts & Specifications",
                    "Never expires",
                    "Alice works at TechCorp",
                ],
                [
                    "PROCEDURAL",
                    "How-to & Instructions",
                    "Never expires",
                    "Always use type hints",
                ],
                [
                    "PREFERENCE",
                    "User/Team Preferences",
                    "Never expires",
                    "Team prefers pytest",
                ],
                [
                    "EPISODIC",
                    "Decisions & Events",
                    "30 days",
                    "Decided to use Kuzu DB",
                ],
                [
                    "WORKING",
                    "Current Tasks",
                    "1 day",
                    "Currently debugging async",
                ],
                [
                    "SENSORY",
                    "Observations & Feedback",
                    "6 hours",
                    "CLI feels slow during testing",
                ],
            ]
            table = rich_table(
                ["Type", "Description", "Retention", "Example"],
                memory_types_data,
                title="🧠 Cognitive Memory Types",
                print_table=False,
            )
            if table:
                from rich.console import Console

                console = Console()
                console.print(table)
            rich_print(
                "\n💡 [italic]KuzuMemory automatically classifies memories based on content![/italic]",
                style="blue",
            )
            time.sleep(1)

        # Completion
        rich_panel(
            "Quickstart Complete! 🎉\n\n"
            "You now know how to:\n"
            "• Store memories with 'kuzu-memory memory store'\n"
            "• Enhance prompts with 'kuzu-memory memory enhance'\n"
            "• Query memories with 'kuzu-memory memory recall'\n"
            "• View recent memories\n"
            "• Understand memory types\n\n"
            "Next steps:\n"
            "• Try the demo: kuzu-memory demo\n"
            "• Get examples: kuzu-memory help examples\n"
            "• Get tips: kuzu-memory help tips\n"
            "• Read docs: docs/GETTING_STARTED.md\n"
            "• Claude integration: docs/CLAUDE_SETUP.md",
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
def demo(ctx: click.Context) -> None:
    """
    🎮 Automated demo of KuzuMemory features.

    Provides a complete walkthrough of all major features with
    automated demonstrations including memory storage, recall,
    enhancement, and statistics.
    """
    import time

    try:
        # Step 1: Welcome & Introduction
        rich_panel(
            "Welcome to KuzuMemory! 🧠✨\n\n"
            "This automated demo will showcase:\n"
            "• Database initialization\n"
            "• Storing diverse memory types\n"
            "• Memory recall capabilities\n"
            "• Prompt enhancement with context\n"
            "• System statistics and insights\n"
            "• Recent memory browsing\n\n"
            "Sit back and watch the magic! ✨",
            title="🎮 KuzuMemory Interactive Demo",
            style="magenta",
        )
        time.sleep(1.5)

        # Step 2: Initialize Database
        rich_print("\n📁 Step 1: Initializing Memory Database", style="bold cyan")
        rich_print("Creating project memory structure...")
        time.sleep(0.5)

        try:
            ctx.invoke(init, force=False)
        except SystemExit:
            # Already initialized, that's fine
            rich_print("✅ Database already initialized!", style="green")

        time.sleep(1)

        # Step 3: Store Sample Memories
        rich_print("\n💾 Step 2: Storing Sample Memories (All Types)", style="bold cyan")
        rich_print("Demonstrating all cognitive memory types...\n")
        time.sleep(0.5)

        # Sample memories covering all types
        sample_memories = [
            (
                "KuzuMemory is a graph-based memory system for AI applications built with Kuzu database",
                "demo-semantic",
            ),
            (
                "To store a memory, use: kuzu-memory memory store <text>. To recall memories, use: kuzu-memory memory recall <query>",
                "demo-procedural",
            ),
            (
                "I prefer to use Python 3.11+ for development and follow PEP 8 style guidelines",
                "demo-preference",
            ),
            (
                "We decided to use Kuzu database for this project on 2025-01-15 because of its performance and graph capabilities",
                "demo-episodic",
            ),
            (
                "Currently working on implementing the interactive demo feature for the CLI interface",
                "demo-working",
            ),
            (
                "The CLI interface feels responsive and fast with sub-100ms response times",
                "demo-sensory",
            ),
        ]

        for i, (content, source) in enumerate(sample_memories, 1):
            rich_print(f"{i}. Storing: {content[:80]}...", style="dim")
            ctx.invoke(
                store,
                content=content,
                source=source,
                session_id=None,
                agent_id="demo",
                metadata=None,
            )
            time.sleep(0.3)

        rich_print(f"\n✅ Stored {len(sample_memories)} diverse memories!", style="green")
        time.sleep(1)

        # Step 4: Demonstrate Memory Recall
        rich_print("\n🔍 Step 3: Testing Memory Recall", style="bold cyan")
        query = "How do I store a memory?"
        rich_print(f"Querying: '{query}'\n")
        time.sleep(0.5)

        ctx.invoke(
            recall,
            prompt=query,
            max_memories=3,
            strategy="auto",
            session_id=None,
            agent_id="cli",
            output_format="simple",
            explain_ranking=False,
        )
        time.sleep(1.5)

        # Step 5: Prompt Enhancement
        rich_print("\n✨ Step 4: Prompt Enhancement Demo", style="bold cyan")
        original_prompt = "Write a Python function for memory management"
        rich_print(f"Original prompt: '{original_prompt}'\n")
        time.sleep(0.5)

        rich_panel(
            f"Original: {original_prompt}",
            title="📝 Before Enhancement",
            style="yellow",
        )
        time.sleep(0.5)

        ctx.invoke(enhance, prompt=original_prompt, max_memories=3, output_format="context")
        time.sleep(1.5)

        # Step 6: View Statistics
        rich_print("\n📊 Step 5: System Statistics", style="bold cyan")
        rich_print("Viewing memory system statistics...\n")
        time.sleep(0.5)

        ctx.invoke(
            status,
            validate=False,
            show_project=False,
            detailed=False,
            output_format="text",
        )
        time.sleep(1.5)

        # Step 7: Recent Memories
        rich_print("\n📚 Step 6: Recent Memories", style="bold cyan")
        rich_print("Showing last 5 memories stored...\n")
        time.sleep(0.5)

        ctx.invoke(recent, limit=5, output_format="table")
        time.sleep(1.5)

        # Step 8: Next Steps & Resources
        rich_panel(
            "Demo Complete! 🎉\n\n"
            "You've seen all major KuzuMemory features in action!\n\n"
            "📚 Next Steps:\n"
            "• Full reference: kuzu-memory help\n"
            "• Practical examples: kuzu-memory help examples\n"
            "• Best practices: kuzu-memory help tips\n"
            "• Interactive setup: kuzu-memory quickstart\n\n"
            "📖 Documentation:\n"
            "• Quick Start: docs/GETTING_STARTED.md\n"
            "• Memory Types: docs/MEMORY_SYSTEM.md\n"
            "• AI Integration: docs/AI_INTEGRATION.md\n\n"
            "🚀 Ready to use KuzuMemory in your project!\n"
            "   Start with: kuzu-memory memory store 'Your first real memory'",
            title="🎯 Demo Complete",
            style="green",
        )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_panel(
            f"Demo encountered an error:\n{e}\n\n"
            "This might happen if:\n"
            "• Database is not initialized (run: kuzu-memory init)\n"
            "• Project root cannot be detected\n"
            "• Permissions issue with database files\n\n"
            "Try running with --debug flag for more details:\n"
            "kuzu-memory --debug demo",
            title="❌ Demo Error",
            style="red",
        )
        sys.exit(1)


# Register top-level commands (clean architecture)
# PRIMARY COMMAND (recommended for users)
cli.add_command(setup)  # 0. Smart setup (RECOMMENDED - combines init + install)

# INDIVIDUAL COMMANDS (for advanced users who need granular control)
cli.add_command(init)  # 1. Initialize project (manual)
cli.add_command(install_command)  # 2. Install integrations (manual - ONE WAY)
cli.add_command(uninstall_command)  # 3. Uninstall integrations
cli.add_command(remove_command)  # 4. Remove (alias for uninstall)
cli.add_command(repair_command)  # 5. Repair broken MCP configs

# CORE FUNCTIONALITY
cli.add_command(memory)  # 6. Memory operations (store, learn, recall, enhance, recent)
cli.add_command(status)  # 7. System status and info
cli.add_command(doctor)  # 8. Diagnostics and health checks
cli.add_command(help_group, name="help")  # 9. Help and examples
cli.add_command(git)  # 10. Git commit history synchronization
cli.add_command(hooks_group, name="hooks")  # 11. Hook system integrations (DEPRECATED)
cli.add_command(mcp_server)  # 12. MCP server (stdio mode) - replaces deprecated mcp install group
cli.add_command(update)  # 13. Check for and install updates from PyPI

# Note: The 'mcp' command now starts the MCP server via stdio
# The old 'mcp install' subcommands are deprecated - use 'kuzu-memory install <integration>' instead

# Keep quickstart/demo for onboarding
cli.add_command(quickstart)
cli.add_command(demo)


# Backward compatibility: 'stats' command as alias to 'status'
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
@click.pass_context
def stats(
    ctx: click.Context,
    validate: bool,
    show_project: bool,
    detailed: bool,
    output_format: str,
) -> None:
    """
    📊 Display system statistics (deprecated - use 'status' instead).

    ⚠️  DEPRECATED: This command is deprecated. Please use 'kuzu-memory status' instead.

    Shows memory system status and statistics. This is an alias to the 'status' command
    maintained for backward compatibility.
    """
    # Show deprecation warning (unless JSON output)
    if output_format != OutputFormat.JSON.value:
        rich_print(
            "⚠️  Warning: 'stats' is deprecated. Please use 'kuzu-memory status' instead.",
            style="yellow",
        )

    # Forward to status command
    ctx.invoke(
        status,
        validate=validate,
        show_project=show_project,
        detailed=detailed,
        output_format=output_format,
    )


# Alias: 'health' as alias for 'status'
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
@click.pass_context
def health(
    ctx: click.Context,
    validate: bool,
    show_project: bool,
    detailed: bool,
    output_format: str,
) -> None:
    """
    🏥 System health check (alias for 'status').

    Shows memory system status and statistics. This is a convenient alias
    for the 'status' command.
    """
    # Forward to status command
    ctx.invoke(
        status,
        validate=validate,
        show_project=show_project,
        detailed=detailed,
        output_format=output_format,
    )


# Register deprecated 'stats' alias and 'health' alias
cli.add_command(stats)
cli.add_command(health)


if __name__ == "__main__":
    cli()
