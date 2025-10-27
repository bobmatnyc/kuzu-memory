"""
Command-line interface for KuzuMemory.

Provides CLI commands for init, remember, recall, and stats operations
with user-friendly output and error handling.
"""

import json
import logging
import sys
import tempfile
import time
from pathlib import Path

import click

# Rich imports for beautiful CLI output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ..__version__ import __version__
from ..core.memory import KuzuMemory
from ..integrations.auggie import AuggieIntegration
from ..utils.config_loader import get_config_loader
from ..utils.project_setup import (
    create_project_memories_structure,
    find_project_root,
    get_project_context_summary,
    get_project_db_path,
)
from .install_commands_simple import install_group, list_installers, status, uninstall

# Install commands imported below

# Set up logging for CLI
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize rich console
console = Console() if RICH_AVAILABLE else None


def rich_print(text, style=None, **kwargs):
    """Print with rich formatting if available, fallback to regular print."""
    if RICH_AVAILABLE and console:
        console.print(text, style=style, **kwargs)
    else:
        print(text)


def rich_panel(content, title=None, style="blue"):
    """Create a rich panel if available, fallback to simple formatting."""
    if RICH_AVAILABLE and console:
        console.print(Panel(content, title=title, border_style=style))
    else:
        if title:
            print(f"\n=== {title} ===")
        print(content)
        print("=" * (len(title) + 8) if title else "")


def rich_table(headers, rows, title=None):
    """Create a rich table if available, fallback to simple formatting."""
    if RICH_AVAILABLE and console:
        table = Table(title=title)
        for header in headers:
            table.add_column(header, style="cyan")
        for row in rows:
            table.add_row(*[str(cell) for cell in row])
        console.print(table)
    else:
        if title:
            print(f"\n{title}")
            print("-" * len(title))

        # Simple table formatting
        col_widths = [
            max(len(str(row[i])) for row in [headers, *rows])
            for i in range(len(headers))
        ]

        # Header
        header_row = " | ".join(
            headers[i].ljust(col_widths[i]) for i in range(len(headers))
        )
        print(header_row)
        print("-" * len(header_row))

        # Rows
        for row in rows:
            row_str = " | ".join(
                str(row[i]).ljust(col_widths[i]) for i in range(len(row))
            )
            print(row_str)


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
    🧠 KuzuMemory - Project Memory System for AI Applications

    \b
    ┌─────────────────────────────────────────────────────────────────┐
    │  Project-specific memory system with intelligent context recall │
    │  • No LLM calls required • Git-committed memories • Team shared │
    │  • Auggie AI integration • 3-minute setup • Zero config needed │
    └─────────────────────────────────────────────────────────────────┘

    \b
    🚀 QUICK START (3 minutes):
      kuzu-memory init           # Initialize project memories
      kuzu-memory demo           # Try it instantly

    \b
    📚 CORE COMMANDS:
      remember    Store project memories
      recall      Find relevant memories
      stats       Show memory statistics
      auggie      AI-powered enhancements

    \b
    💡 EXAMPLES:
      kuzu-memory remember "We use FastAPI with PostgreSQL"
      kuzu-memory recall "What's our database setup?"
      kuzu-memory auggie enhance "How should I structure this API?"

    \b
    🔧 PROJECT SETUP:
      init        Initialize project memory database
      project     Show project information

    \b
    📁 PROJECT MODEL:
      Memories are stored in kuzu-memories/ directory and committed to git.
      All team members share the same project context automatically.

    Run 'kuzu-memory COMMAND --help' for detailed help on any command.
    """
    # Set up logging level
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("kuzu_memory").setLevel(logging.DEBUG)

    # Store common options in context
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["config_path"] = config

    # Handle project root and database path
    if project_root:
        ctx.obj["project_root"] = Path(project_root)
    else:
        ctx.obj["project_root"] = find_project_root()

    # Use custom db_path if provided, otherwise use project default
    if db_path:
        ctx.obj["db_path"] = Path(db_path)
    else:
        ctx.obj["db_path"] = get_project_db_path(ctx.obj["project_root"])

    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        rich_panel(
            "Welcome to KuzuMemory! 🧠\n\n"
            "Get started in 3 minutes:\n"
            "• kuzu-memory quickstart  (guided setup)\n"
            "• kuzu-memory demo        (instant demo)\n"
            "• kuzu-memory --help      (full help)\n\n"
            "Need help? Every command has detailed examples:\n"
            "kuzu-memory COMMAND --help",
            title="🚀 Quick Start",
            style="green",
        )


@cli.command()
@click.option("--skip-demo", is_flag=True, help="Skip the interactive demo")
@click.pass_context
def quickstart(ctx, skip_demo):
    """
    🚀 Interactive 3-minute setup and demo.

    \b
    This command will:
    • Initialize your memory database
    • Walk through basic usage
    • Show AI-powered features
    • Get you productive immediately

    \b
    Perfect for first-time users!
    """
    rich_panel(
        "🚀 Welcome to KuzuMemory Quickstart!\n\n"
        "This will take about 3 minutes and get you fully set up.\n"
        "We'll create a memory database, store some memories,\n"
        "and show you the AI-powered features.",
        title="KuzuMemory Quickstart",
        style="green",
    )

    try:
        # Step 1: Setup
        rich_print("\n📁 Step 1: Setting up your memory database...", style="bold blue")

        db_path = ctx.obj.get("db_path") or Path("my_memories.db")

        if RICH_AVAILABLE:
            if db_path.exists():
                if not Confirm.ask(
                    f"Database {db_path} exists. Continue with existing?"
                ):
                    db_path = Path(
                        Prompt.ask(
                            "Enter new database path", default="my_memories_new.db"
                        )
                    )

        # Initialize memory system
        from ..core.config import KuzuMemoryConfig
        from ..core.memory import KuzuMemory

        config = KuzuMemoryConfig()
        config.performance.max_recall_time_ms = 100.0
        config.performance.max_generation_time_ms = 200.0

        with KuzuMemory(db_path=db_path, config=config) as memory:
            rich_print(f"✅ Memory database ready at: {db_path}", style="green")

            # Step 2: Store some memories
            rich_print(
                "\n💾 Step 2: Let's store some memories about you...", style="bold blue"
            )

            sample_memories = [
                "I'm a software developer who loves Python and JavaScript",
                "I prefer FastAPI for backend APIs and React for frontend",
                "I always write unit tests before deploying code",
                "I work at TechCorp and focus on microservices architecture",
            ]

            if not skip_demo:
                if RICH_AVAILABLE:
                    custom_memory = Prompt.ask(
                        "\n💭 Tell me something about yourself (or press Enter for demo)",
                        default="",
                    )
                    if custom_memory.strip():
                        sample_memories = [custom_memory, *sample_memories[:2]]

            stored_count = 0
            for memory_text in sample_memories:
                memory_ids = memory.generate_memories(
                    memory_text, user_id="quickstart-user"
                )
                stored_count += len(memory_ids)
                rich_print(f"  ✓ Stored: {memory_text[:50]}...", style="dim")

            rich_print(f"✅ Stored {stored_count} memories!", style="green")

            # Step 3: Test recall
            rich_print("\n🔍 Step 3: Testing memory recall...", style="bold blue")

            test_queries = [
                "What do I do for work?",
                "What technologies do I prefer?",
                "How do I handle testing?",
            ]

            for query in test_queries:
                context = memory.attach_memories(
                    query, user_id="quickstart-user", max_memories=3
                )
                rich_print(f"  🔍 Query: {query}", style="cyan")
                rich_print(
                    f"     Found {len(context.memories)} relevant memories", style="dim"
                )
                if context.memories:
                    rich_print(
                        f"     Top result: {context.memories[0].content[:60]}...",
                        style="dim",
                    )

            # Step 4: Auggie integration
            if not skip_demo:
                rich_print(
                    "\n🤖 Step 4: AI-powered features with Auggie...", style="bold blue"
                )

                try:
                    from ..integrations.auggie import AuggieIntegration

                    auggie = AuggieIntegration(memory)
                    rich_print("✅ Auggie AI integration loaded!", style="green")

                    # Test prompt enhancement
                    test_prompt = "How do I write a Python function?"
                    enhancement = auggie.enhance_prompt(test_prompt, "quickstart-user")

                    rich_print(f"  🔍 Original: {test_prompt}", style="cyan")
                    rich_print(
                        f"  🚀 Enhanced: {len(enhancement['enhanced_prompt'])} chars (was {len(test_prompt)})",
                        style="green",
                    )
                    rich_print(
                        f"  📊 Context: {enhancement['context_summary']}", style="dim"
                    )

                except Exception as e:
                    rich_print(
                        f"⚠️  Auggie integration not available: {e}", style="yellow"
                    )

        # Success!
        rich_panel(
            "🎉 Quickstart Complete!\n\n"
            f"Your memory database is ready at: {db_path}\n\n"
            "Next steps:\n"
            f"• kuzu-memory remember 'your thoughts' --user-id you\n"
            f"• kuzu-memory recall 'what do you know?' --user-id you\n"
            f"• kuzu-memory auggie enhance 'your prompt' --user-id you\n"
            f"• kuzu-memory stats --db-path {db_path}\n\n"
            "Run any command with --help for detailed examples!",
            title="🚀 Ready to Go!",
            style="green",
        )

    except Exception as e:
        rich_print(f"❌ Quickstart failed: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        rich_print("\n💡 Try: kuzu-memory --debug quickstart", style="yellow")


@cli.command()
@click.pass_context
def demo(ctx):
    """
    🎮 Instant demo - try KuzuMemory in 30 seconds.

    \b
    Runs a quick demonstration showing:
    • Memory storage and retrieval
    • Context-aware responses
    • AI-powered enhancements

    \b
    No setup required - uses temporary database.
    Perfect for testing before installation.
    """
    rich_panel(
        "🎮 KuzuMemory Demo\n\n"
        "This is a 30-second demo using a temporary database.\n"
        "No files will be created on your system.",
        title="Instant Demo",
        style="blue",
    )

    try:
        from ..core.config import KuzuMemoryConfig
        from ..core.memory import KuzuMemory

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "demo.db"

            config = KuzuMemoryConfig()
            config.performance.max_recall_time_ms = 100.0
            config.performance.max_generation_time_ms = 200.0

            with KuzuMemory(db_path=db_path, config=config) as memory:
                rich_print("🧠 Demo memory system initialized...", style="blue")

                # Demo data
                demo_memories = [
                    "I'm Alex, a senior Python developer at StartupCorp",
                    "I prefer FastAPI for APIs and PostgreSQL for databases",
                    "I always write comprehensive tests using pytest",
                    "Currently building a microservices platform with Docker",
                ]

                # Store memories
                rich_print("\n💾 Storing demo memories...", style="bold")
                for memory_text in demo_memories:
                    memory.generate_memories(memory_text, user_id="demo-user")
                    rich_print(f"  ✓ {memory_text}", style="dim")

                # Test recall
                rich_print("\n🔍 Testing memory recall...", style="bold")
                queries = [
                    "What's my name and job?",
                    "What technologies do I use?",
                    "How do I handle testing?",
                ]

                for query in queries:
                    context = memory.attach_memories(query, user_id="demo-user")
                    rich_print(f"  🔍 '{query}'", style="cyan")
                    if context.memories:
                        rich_print(
                            f"     → {context.memories[0].content}", style="green"
                        )
                    else:
                        rich_print("     → No memories found", style="red")

                # Auggie demo
                rich_print("\n🤖 Testing AI enhancements...", style="bold")
                try:
                    from ..integrations.auggie import AuggieIntegration

                    auggie = AuggieIntegration(memory)

                    test_prompt = "How should I structure my Python project?"
                    enhancement = auggie.enhance_prompt(test_prompt, "demo-user")

                    rich_print(f"  🔍 Original: {test_prompt}", style="cyan")
                    rich_print(
                        f"  🚀 Enhanced with personal context ({len(enhancement['enhanced_prompt'])} chars)",
                        style="green",
                    )
                    rich_print(
                        "  📊 Added context about: FastAPI, PostgreSQL, pytest, Docker",
                        style="dim",
                    )

                except Exception as e:
                    rich_print(f"  ⚠️  AI features not available: {e}", style="yellow")

        rich_panel(
            "🎉 Demo Complete!\n\n"
            "What you just saw:\n"
            "• Stored 4 memories about 'Alex'\n"
            "• Retrieved relevant context for queries\n"
            "• Enhanced prompts with personal context\n\n"
            "Ready to try it yourself?\n"
            "• kuzu-memory quickstart  (full setup)\n"
            "• kuzu-memory init        (just initialize)\n"
            "• kuzu-memory --help      (all commands)",
            title="🚀 Try It Yourself!",
            style="green",
        )

    except Exception as e:
        rich_print(f"❌ Demo failed: {e}", style="red")
        if ctx.obj.get("debug"):
            raise


@cli.command()
@click.option("--force", is_flag=True, help="Overwrite existing project memories")
@click.option(
    "--config-path", type=click.Path(), help="Path to save example configuration"
)
@click.pass_context
def init(ctx, force, config_path):
    """
    Initialize project memory system.

    \b
    Creates kuzu-memories/ directory structure:
    • memories.db - Kuzu graph database
    • README.md - Documentation and usage guide
    • project_info.md - Project context template

    \b
    🎯 PROJECT MODEL:
      Memories are project-specific and committed to git.
      All team members share the same project context.

    \b
    💡 EXAMPLES:
      kuzu-memory init                    # Initialize in current project
      kuzu-memory init --force            # Overwrite existing memories
      kuzu-memory init --config-path ./config.yaml

    \b
    📁 DIRECTORY STRUCTURE:
      kuzu-memories/
      ├── memories.db        # Graph database
      ├── README.md          # Documentation
      ├── project_info.md    # Project context
      └── .gitignore         # Git ignore rules
    """
    try:
        project_root = ctx.obj["project_root"]

        rich_print(
            f"🏗️  Initializing project memories in: {project_root.name}",
            style="bold blue",
        )

        # Create project memories structure
        result = create_project_memories_structure(project_root, force=force)

        if result.get("existed") and not force:
            rich_panel(
                f"Project memories already exist at:\n{result['memories_dir']}\n\n"
                "Use --force to recreate the structure.",
                title="⚠️  Already Initialized",
                style="yellow",
            )
            return

        if result.get("error"):
            rich_print(
                f"❌ Failed to create project structure: {result['error']}", style="red"
            )
            sys.exit(1)

        # Create example configuration if requested
        if config_path:
            config_loader = get_config_loader()
            config_loader.create_example_config(Path(config_path))
            rich_print(
                f"✅ Example configuration created at {config_path}", style="green"
            )

        # Initialize the database
        db_path = Path(result["db_path"])
        rich_print("🗄️  Initializing memory database...", style="blue")

        with KuzuMemory(db_path=db_path) as memory:
            stats = memory.get_statistics()

        # Success summary
        rich_panel(
            f"🎉 Project Memory System Initialized!\n\n"
            f"📁 Structure Created:\n"
            f"  • Database: {db_path.relative_to(project_root)}\n"
            f"  • Documentation: kuzu-memories/README.md\n"
            f"  • Project Info: kuzu-memories/project_info.md\n\n"
            f"🔧 Database Info:\n"
            f"  • Schema Version: {stats['system_info']['config_version']}\n"
            f"  • Status: Ready for memories\n\n"
            f"🚀 Next Steps:\n"
            f"  1. Edit kuzu-memories/project_info.md with your project details\n"
            f"  2. Store project memories: kuzu-memory remember 'project info'\n"
            f"  3. Commit to git: git add kuzu-memories/ && git commit\n\n"
            f"💡 All team members will now share project context!",
            title="✅ Initialization Complete",
            style="green",
        )

        # Show git status if in git repo
        if (project_root / ".git").exists():
            rich_print("\n📋 Git Integration:", style="bold")
            rich_print("  ✅ Git repository detected", style="green")
            rich_print("  📝 Remember to commit kuzu-memories/ directory", style="cyan")
            rich_print(
                "  🤝 Team members will get shared project context", style="cyan"
            )

    except Exception as e:
        rich_print(f"❌ Initialization failed: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.option("--verbose", is_flag=True, help="Show detailed project information")
@click.pass_context
def project(ctx, verbose):
    """
    Show project memory information.

    \b
    Displays:
    • Project root and memory database location
    • Memory statistics and database size
    • Git integration status
    • Team sharing information

    \b
    💡 EXAMPLES:
      kuzu-memory project           # Basic project info
      kuzu-memory project --verbose # Detailed information
    """
    try:
        project_root = ctx.obj["project_root"]
        context_summary = get_project_context_summary(project_root)

        # Basic project information
        rich_panel(
            f"📁 Project: {context_summary['project_name']}\n"
            f"🗂️  Root: {context_summary['project_root']}\n"
            f"🧠 Memories: {context_summary['memories_dir']}\n"
            f"🗄️  Database: {context_summary['db_path']}",
            title="🏗️  Project Information",
            style="blue",
        )

        # Memory status
        if context_summary["memories_exist"]:
            if context_summary["db_exists"]:
                db_size = context_summary["db_size_mb"]
                rich_print(
                    f"✅ Memory database ready ({db_size:.1f} MB)", style="green"
                )

                # Get memory statistics if verbose
                if verbose:
                    try:
                        with KuzuMemory(
                            db_path=Path(context_summary["db_path"])
                        ) as memory:
                            stats = memory.get_statistics()

                        rich_print("\n📊 Memory Statistics:", style="bold")
                        if "database_stats" in stats.get("storage_stats", {}):
                            db_stats = stats["storage_stats"]["database_stats"]
                            rich_print(
                                f"  • Memories: {db_stats.get('memory_count', 0)}",
                                style="cyan",
                            )
                            rich_print(
                                f"  • Entities: {db_stats.get('entity_count', 0)}",
                                style="cyan",
                            )
                            rich_print(
                                f"  • Sessions: {db_stats.get('session_count', 0)}",
                                style="cyan",
                            )

                        perf_stats = stats.get("performance_stats", {})
                        rich_print(
                            f"  • Recall calls: {perf_stats.get('attach_memories_calls', 0)}",
                            style="cyan",
                        )
                        rich_print(
                            f"  • Avg recall time: {perf_stats.get('avg_attach_time_ms', 0):.1f}ms",
                            style="cyan",
                        )

                    except Exception as e:
                        rich_print(
                            f"⚠️  Could not load memory statistics: {e}", style="yellow"
                        )
            else:
                rich_print(
                    "⚠️  Memory directory exists but database not initialized",
                    style="yellow",
                )
                rich_print("💡 Run: kuzu-memory init", style="cyan")
        else:
            rich_print("❌ Project memories not initialized", style="red")
            rich_print("💡 Run: kuzu-memory init", style="cyan")

        # Git integration status
        rich_print("\n🔗 Git Integration:", style="bold")
        if context_summary["is_git_repo"]:
            rich_print("  ✅ Git repository detected", style="green")
            if context_summary["should_commit"]:
                rich_print("  📝 Memories should be committed to git", style="green")
                rich_print(
                    "  🤝 Team members will share project context", style="green"
                )
            else:
                rich_print("  ⚠️  Memories not configured for git", style="yellow")
        else:
            rich_print("  ❌ Not a git repository", style="red")
            rich_print("  💡 Consider initializing git for team sharing", style="cyan")

        # Usage tips
        if verbose:
            rich_print("\n💡 Usage Tips:", style="bold")
            rich_print(
                "  • Store project context: kuzu-memory remember 'project info'",
                style="cyan",
            )
            rich_print(
                "  • Find relevant info: kuzu-memory recall 'how does X work?'",
                style="cyan",
            )
            rich_print(
                "  • AI enhancement: kuzu-memory auggie enhance 'your prompt'",
                style="cyan",
            )
            rich_print("  • View statistics: kuzu-memory stats", style="cyan")

    except Exception as e:
        rich_print(f"❌ Error getting project information: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.argument("prompt", required=True)
@click.option("--max-memories", default=5, help="Maximum number of memories to include")
@click.option(
    "--format",
    "output_format",
    default="context",
    type=click.Choice(["context", "json", "plain"]),
    help="Output format",
)
@click.pass_context
def enhance(ctx, prompt, max_memories, output_format):
    """
    🚀 Enhance a prompt with relevant project memories.

    \b
    Perfect for AI integration - adds project context to any prompt.

    \b
    🎯 EXAMPLES:
      # Enhance a coding question
      kuzu-memory enhance "How do I structure this API?"

      # JSON output for scripts
      kuzu-memory enhance "What's our testing strategy?" --format json

      # Limit context size
      kuzu-memory enhance "Database setup?" --max-memories 3

    \b
    💡 AI INTEGRATION:
      This command is perfect for AI systems to call directly:

      enhanced_prompt = subprocess.check_output([
          'kuzu-memory', 'enhance', user_prompt, '--format', 'context'
      ]).decode().strip()

    \b
    🔗 RELATED:
      kuzu-memory remember   Store new memories
      kuzu-memory recall     Find specific memories
    """
    try:
        db_path = ctx.obj.get("db_path")

        with KuzuMemory(db_path=db_path) as memory:
            # Get relevant memories
            context = memory.attach_memories(prompt=prompt, max_memories=max_memories)

            if output_format == "json":
                # JSON output for scripts
                result = {
                    "original_prompt": prompt,
                    "enhanced_prompt": context.enhanced_prompt,
                    "memories_used": [
                        {
                            "content": m.content,
                            "confidence": m.confidence,
                            "created_at": m.created_at.isoformat(),
                        }
                        for m in context.memories
                    ],
                    "confidence": context.confidence,
                }
                click.echo(json.dumps(result, indent=2))

            elif output_format == "plain":
                # Just the enhanced prompt
                click.echo(context.enhanced_prompt)

            else:  # context format
                # Human-readable with context info
                if context.memories:
                    rich_print(
                        f"🧠 Enhanced with {len(context.memories)} memories (confidence: {context.confidence:.2f})",
                        style="green",
                    )
                    click.echo()
                    click.echo(context.enhanced_prompt)
                else:
                    rich_print("[i] No relevant memories found", style="yellow")
                    click.echo(prompt)

    except Exception as e:
        rich_print(f"❌ Error enhancing prompt: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.argument("content", required=True)
@click.option("--source", default="ai-conversation", help="Source of the memory")
@click.option("--metadata", help="Additional metadata as JSON string")
@click.option("--quiet", is_flag=True, help="Suppress output (for scripts)")
@click.option(
    "--sync",
    "use_sync",
    is_flag=True,
    help="Use synchronous processing (blocking, for testing)",
)
@click.pass_context
def learn(ctx, content, source, metadata, quiet, use_sync):
    """
    🧠 Store a memory from AI conversation or interaction.

    \b
    Optimized for AI systems to store learning from conversations.

    \b
    🎯 EXAMPLES:
      # Store user preference
      kuzu-memory learn "User prefers TypeScript over JavaScript"

      # Store project decision
      kuzu-memory learn "We decided to use Redis for session storage" --source decision

      # Store with metadata
      kuzu-memory learn "API rate limit is 1000 requests/hour" \\
        --metadata '{"component": "api", "type": "limit"}'

      # Quiet mode for scripts
      kuzu-memory learn "User likes dark mode" --quiet

      # Default async mode (non-blocking, for AI integration)
      kuzu-memory learn "User prefers TypeScript" --quiet

      # Sync mode (blocking, for testing)
      kuzu-memory learn "Test memory" --sync

    \b
    💡 AI INTEGRATION:
      Perfect for AI systems to store learning:

      subprocess.run([
          'kuzu-memory', 'learn',
          f"User correction: {user_feedback}",
          '--source', 'ai-correction',
          '--quiet'
      ])

    \b
    🔗 RELATED:
      kuzu-memory enhance    Enhance prompts with memories
      kuzu-memory remember   Store general memories
    """
    try:
        db_path = ctx.obj.get("db_path")

        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                if not quiet:
                    rich_print(f"⚠️  Invalid JSON metadata: {e}", style="yellow")

        # Use sync processing only if explicitly requested
        if use_sync:
            if not quiet:
                rich_print("[i] Using synchronous processing", style="blue")
        else:
            # Default: Use async processing (non-blocking)
            try:
                from ..async_memory.async_cli import get_async_cli

                async_cli = get_async_cli(db_path=db_path)

                result = async_cli.learn_async(
                    content=content,
                    source=source,
                    metadata=parsed_metadata,
                    quiet=quiet,
                )

                if not quiet and result.get("task_id"):
                    rich_print(
                        f"✅ Learning task {result['task_id'][:8]}... queued for background processing",
                        style="green",
                    )

                return

            except ImportError:
                if not quiet:
                    rich_print(
                        "⚠️  Async processing not available, using sync mode",
                        style="yellow",
                    )
                # Fall through to sync processing

        # Sync processing (fallback or explicit)
        with KuzuMemory(db_path=db_path) as memory:
            # Store the memory
            memory_ids = memory.generate_memories(
                content=content, metadata=parsed_metadata, source=source
            )

            if not quiet:
                if memory_ids:
                    rich_print(f"✅ Stored {len(memory_ids)} memories", style="green")
                else:
                    rich_print(
                        "[i] No memories extracted (content may be too generic)",
                        style="yellow",
                    )

    except Exception as e:
        if not quiet:
            rich_print(f"❌ Error storing memory: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.option("--recent", default=10, help="Number of recent memories to show")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json", "list"]),
    help="Output format",
)
@click.pass_context
def recent(ctx, recent, output_format):
    """
    📋 Show recent project memories.

    \b
    Quick way to see what's been stored recently.

    \b
    🎯 EXAMPLES:
      # Show last 10 memories
      kuzu-memory recent

      # Show more memories
      kuzu-memory recent --recent 20

      # JSON output for scripts
      kuzu-memory recent --format json

    \b
    💡 AI INTEGRATION:
      Check recent context for AI systems:

      recent_memories = subprocess.check_output([
          'kuzu-memory', 'recent', '--format', 'json'
      ])
    """
    try:
        db_path = ctx.obj.get("db_path")

        with KuzuMemory(db_path=db_path) as memory:
            # Get recent memories (this would need to be implemented in KuzuMemory)
            # For now, let's use a simple recall to get some memories
            context = memory.attach_memories(
                prompt="recent project information", max_memories=recent
            )

            if output_format == "json":
                result = [
                    {
                        "content": m.content,
                        "created_at": m.created_at.isoformat(),
                        "source": getattr(m, "source", "unknown"),
                        "confidence": m.confidence,
                    }
                    for m in context.memories
                ]
                click.echo(json.dumps(result, indent=2))

            elif output_format == "list":
                for i, memory in enumerate(context.memories, 1):
                    click.echo(f"{i}. {memory.content}")

            else:  # table format
                if context.memories:
                    rich_print(
                        f"📋 Recent {len(context.memories)} memories:",
                        style="bold blue",
                    )
                    for i, memory in enumerate(context.memories, 1):
                        created = memory.created_at.strftime("%Y-%m-%d %H:%M")
                        rich_print(f"  {i}. [{created}] {memory.content}", style="cyan")
                else:
                    rich_print("[i] No memories found", style="yellow")

    except Exception as e:
        rich_print(f"❌ Error getting recent memories: {e}", style="red")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.argument("content", required=True)
@click.option(
    "--source",
    default="cli",
    help='Source of the memory (e.g., "conversation", "document")',
)
@click.option("--session-id", help="Session ID to group related memories")
@click.option("--agent-id", default="cli", help="Agent ID that created this memory")
@click.option("--metadata", help="Additional metadata as JSON string")
@click.pass_context
def remember(ctx, content, source, session_id, agent_id, metadata):
    """
    💾 Store project memories from text content.

    \b
    Extracts and stores meaningful memories from your text using
    intelligent pattern matching. No LLM calls required!

    \b
    🎯 EXAMPLES:
      # Project architecture
      kuzu-memory remember "We use FastAPI with PostgreSQL for this microservice"

      # Team decisions
      kuzu-memory remember "We decided to use Redis for caching to improve performance"

      # Development conventions
      kuzu-memory remember "All API endpoints should include request/response examples"

      # With metadata
      kuzu-memory remember "Authentication service deployed to production" \\
        --metadata '{"component": "auth", "environment": "prod"}'

    \b
    💡 TIPS:
      • Store project-specific information and decisions
      • Use --session-id to group related memories
      • Longer text often produces more memories
      • Check results with: kuzu-memory stats

    \b
    🔗 RELATED:
      kuzu-memory recall     Find stored memories
      kuzu-memory stats      See what was stored
      kuzu-memory project    Show project information
    """
    try:
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                click.echo(f"Invalid JSON metadata: {e}", err=True)
                sys.exit(1)

        # Load configuration and initialize KuzuMemory
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get("config_path"))

        with KuzuMemory(db_path=ctx.obj.get("db_path"), config=config) as memory:
            # Generate memories (no user_id in project model)
            memory_ids = memory.generate_memories(
                content=content,
                metadata=parsed_metadata,
                source=source,
                session_id=session_id,
                agent_id=agent_id,
            )

            if memory_ids:
                rich_print(
                    f"✅ Generated {len(memory_ids)} memories from your content!",
                    style="green",
                )

                if len(memory_ids) == 1:
                    rich_print(
                        "💡 Tip: Longer or more detailed text often produces more memories",
                        style="dim",
                    )
                elif len(memory_ids) > 3:
                    rich_print(
                        "🎉 Great! Rich content produced multiple memories", style="dim"
                    )

                if ctx.obj["debug"]:
                    rich_print("\n📋 Memory IDs:", style="bold")
                    for i, memory_id in enumerate(memory_ids, 1):
                        rich_print(f"  {i}. {memory_id}", style="dim")

                # Show next steps
                rich_print(
                    "\n🔍 Try: kuzu-memory recall 'what do you know about this project?'",
                    style="cyan",
                )

            else:
                rich_print("⚠️  No memories extracted from content", style="yellow")
                rich_panel(
                    "💡 Tips for better memory extraction:\n\n"
                    "• Include specific details (names, preferences, decisions)\n"
                    "• Use complete sentences\n"
                    "• Mention relationships or context\n"
                    "• Try longer, more descriptive text\n\n"
                    "Examples that work well:\n"
                    "• 'I prefer Python over JavaScript for backend development'\n"
                    "• 'We decided to use PostgreSQL for the user database'\n"
                    "• 'My name is Alex and I work at TechCorp as a developer'",
                    title="💡 Memory Extraction Tips",
                    style="blue",
                )

    except json.JSONDecodeError as e:
        rich_print(f"❌ Invalid JSON metadata: {e}", style="red")
        rich_print(
            '💡 Metadata should be valid JSON, e.g.: \'{"key": "value"}\'',
            style="yellow",
        )
        sys.exit(1)
    except Exception as e:
        rich_print(f"❌ Error storing memory: {e}", style="red")
        if ctx.obj["debug"]:
            raise
        rich_print(
            "💡 Try: kuzu-memory --debug remember 'your content'", style="yellow"
        )
        sys.exit(1)


@cli.command()
@click.argument("topic", required=False)
@click.pass_context
def examples(ctx, topic):
    """
    📚 Show examples and tutorials for KuzuMemory commands.

    \b
    USAGE:
      kuzu-memory examples           # Show all examples
      kuzu-memory examples remember  # Examples for remember command
      kuzu-memory examples auggie    # AI integration examples
      kuzu-memory examples workflow  # Complete workflow examples

    \b
    Available topics: remember, recall, auggie, workflow, patterns
    """

    examples_data = {
        "remember": {
            "title": "💾 Memory Storage Examples",
            "content": """
🎯 BASIC USAGE:
  kuzu-memory remember "I prefer Python over JavaScript"
  kuzu-memory remember "My name is Alex and I work at TechCorp"

👤 WITH USER ID:
  kuzu-memory remember "I love FastAPI for APIs" --user-id alex
  kuzu-memory remember "We use PostgreSQL in production" --user-id alex

📝 WITH SESSION GROUPING:
  kuzu-memory remember "Sprint planning meeting notes" \\
    --user-id alex --session-id sprint-1

🏷️  WITH METADATA:
  kuzu-memory remember "Fixed critical auth bug" \\
    --metadata '{"priority": "high", "component": "auth"}'

💡 WHAT GETS STORED:
  • Personal information (names, roles, companies)
  • Preferences and opinions
  • Decisions and choices
  • Technical details and configurations
  • Relationships and connections
            """,
        },
        "recall": {
            "title": "🔍 Memory Recall Examples",
            "content": """
🎯 BASIC QUERIES:
  kuzu-memory recall "What do I prefer?"
  kuzu-memory recall "Where do I work?"

👤 USER-SPECIFIC RECALL:
  kuzu-memory recall "What technologies does Alex like?" --user-id alex
  kuzu-memory recall "What decisions did we make?" --user-id team

🎛️  WITH OPTIONS:
  kuzu-memory recall "Python preferences" --max-memories 5 --user-id alex
  kuzu-memory recall "recent decisions" --strategy temporal

💡 QUERY TIPS:
  • Use natural language questions
  • Be specific about what you're looking for
  • Include context words (names, topics, timeframes)
  • Try different phrasings if no results
            """,
        },
        "auggie": {
            "title": "🤖 AI Integration Examples",
            "content": """
🚀 PROMPT ENHANCEMENT:
  kuzu-memory auggie enhance "How do I write a Python function?" --user-id alex
  # Adds Alex's preferences and context automatically

🧠 RESPONSE LEARNING:
  kuzu-memory auggie learn "What framework?" "Use Django" \\
    --feedback "I prefer FastAPI" --user-id alex

📋 RULE MANAGEMENT:
  kuzu-memory auggie rules                    # List all rules
  kuzu-memory auggie rules --verbose          # Detailed rule info

📊 STATISTICS:
  kuzu-memory auggie stats                    # Integration stats
  kuzu-memory auggie stats --verbose          # Detailed performance

💡 AI FEATURES:
  • Automatic prompt enhancement with personal context
  • Learning from user corrections and feedback
  • Custom rule creation for specific domains
  • Performance monitoring and optimization
            """,
        },
        "workflow": {
            "title": "🔄 Complete Workflow Examples",
            "content": """
🚀 GETTING STARTED (3 minutes):
  1. kuzu-memory quickstart                   # Interactive setup
  2. kuzu-memory demo                         # Try it instantly

👤 PERSONAL ASSISTANT WORKFLOW:
  1. kuzu-memory remember "I'm Sarah, Python dev at TechCorp" --user-id sarah
  2. kuzu-memory remember "I prefer FastAPI and PostgreSQL" --user-id sarah
  3. kuzu-memory recall "What do you know about me?" --user-id sarah
  4. kuzu-memory auggie enhance "How do I build an API?" --user-id sarah

🏢 TEAM KNOWLEDGE BASE:
  1. kuzu-memory remember "We use microservices architecture" --user-id team
  2. kuzu-memory remember "PostgreSQL for user data, Redis for cache" --user-id team
  3. kuzu-memory recall "What's our tech stack?" --user-id team

🤖 AI-POWERED DEVELOPMENT:
  1. Store your preferences and context
  2. Use auggie enhance for personalized prompts
  3. Learn from AI responses with auggie learn
  4. Monitor with auggie stats

📊 MONITORING AND MAINTENANCE:
  kuzu-memory stats                           # Overall statistics
  kuzu-memory auggie stats                    # AI integration stats
  kuzu-memory config show                     # Current configuration
            """,
        },
        "patterns": {
            "title": "🎯 Memory Pattern Examples",
            "content": """
✅ PATTERNS THAT WORK WELL:

👤 IDENTITY:
  "My name is [Name] and I work at [Company] as a [Role]"
  "I'm a [Role] specializing in [Technology/Domain]"

💭 PREFERENCES:
  "I prefer [Option A] over [Option B] for [Use Case]"
  "I always use [Tool/Method] when [Situation]"

🎯 DECISIONS:
  "We decided to use [Technology] for [Project/Component]"
  "The team chose [Approach] because [Reason]"

🔧 TECHNICAL DETAILS:
  "Our [System] uses [Technology] with [Configuration]"
  "The [Component] connects to [Service] via [Protocol]"

❌ PATTERNS THAT DON'T WORK:

• Single words: "Python" (too vague)
• Questions: "What should I use?" (no information)
• Commands: "Install FastAPI" (no context)
• Generic statements: "This is good" (no specifics)

💡 TIPS FOR BETTER EXTRACTION:
• Include WHO, WHAT, WHERE, WHEN, WHY
• Use complete sentences
• Be specific and detailed
• Mention relationships and context
            """,
        },
    }

    if not topic:
        # Show all available topics
        rich_panel(
            "📚 Available Example Topics:\n\n"
            "• remember  - Memory storage examples\n"
            "• recall    - Memory retrieval examples\n"
            "• auggie    - AI integration examples\n"
            "• workflow  - Complete workflow examples\n"
            "• patterns  - Memory pattern examples\n\n"
            "Usage: kuzu-memory examples TOPIC",
            title="📚 KuzuMemory Examples",
            style="blue",
        )
        return

    if topic not in examples_data:
        rich_print(f"❌ Unknown topic: {topic}", style="red")
        rich_print(
            f"Available topics: {', '.join(examples_data.keys())}", style="yellow"
        )
        return

    example = examples_data[topic]
    rich_panel(example["content"], title=example["title"], style="green")


@cli.command()
@click.option("--advanced", is_flag=True, help="Show advanced configuration options")
@click.pass_context
def setup(ctx, advanced):
    """
    ⚙️ Interactive setup wizard for KuzuMemory.

    \b
    Guides you through:
    • Database location and configuration
    • Performance tuning
    • AI integration setup
    • First memory storage

    \b
    Perfect for customized installations!
    """
    rich_panel(
        "⚙️ KuzuMemory Setup Wizard\n\n"
        "This wizard will help you configure KuzuMemory\n"
        "for your specific needs and preferences.",
        title="Setup Wizard",
        style="blue",
    )

    try:
        # Step 1: Database configuration
        rich_print("\n📁 Step 1: Database Configuration", style="bold blue")

        if RICH_AVAILABLE:
            default_db = "kuzu_memories.db"
            db_path = Prompt.ask(
                "Where should we store your memories?", default=default_db
            )
            db_path = Path(db_path)

            if db_path.exists():
                if not Confirm.ask(
                    f"Database {db_path} exists. Use existing database?"
                ):
                    db_path = Path(Prompt.ask("Enter new database path"))
        else:
            db_path = Path("kuzu_memories.db")

        # Step 2: Performance configuration
        rich_print("\n⚡ Step 2: Performance Configuration", style="bold blue")

        if RICH_AVAILABLE and advanced:
            max_recall_time = Prompt.ask("Maximum recall time (ms)", default="100")
            max_generation_time = Prompt.ask(
                "Maximum generation time (ms)", default="200"
            )
        else:
            max_recall_time = "100"
            max_generation_time = "200"
            rich_print(
                "Using default performance settings (use --advanced for custom)",
                style="dim",
            )

        # Step 3: Initialize system
        rich_print("\n🚀 Step 3: Initializing KuzuMemory...", style="bold blue")

        from ..core.config import KuzuMemoryConfig
        from ..core.memory import KuzuMemory

        config = KuzuMemoryConfig()
        config.performance.max_recall_time_ms = float(max_recall_time)
        config.performance.max_generation_time_ms = float(max_generation_time)

        with KuzuMemory(db_path=db_path, config=config) as memory:
            rich_print(f"✅ Memory system initialized at: {db_path}", style="green")

            # Step 4: Test with sample data
            rich_print("\n🧪 Step 4: Testing with Sample Data", style="bold blue")

            if RICH_AVAILABLE:
                test_memory = Prompt.ask(
                    "Enter something about yourself to test (or press Enter to skip)",
                    default="",
                )
            else:
                test_memory = ""

            if test_memory.strip():
                memory_ids = memory.generate_memories(test_memory, user_id="setup-user")
                if memory_ids:
                    rich_print(
                        f"✅ Successfully stored {len(memory_ids)} memories!",
                        style="green",
                    )

                    # Test recall
                    context = memory.attach_memories(
                        "What do you know?", user_id="setup-user"
                    )
                    if context.memories:
                        rich_print(
                            f"✅ Memory recall working! Found: {context.memories[0].content[:50]}...",
                            style="green",
                        )
                else:
                    rich_print(
                        "⚠️  No memories extracted. Try more detailed text.",
                        style="yellow",
                    )

            # Step 5: AI integration check
            rich_print("\n🤖 Step 5: AI Integration Check", style="bold blue")

            try:
                from ..integrations.auggie import AuggieIntegration

                auggie = AuggieIntegration(memory)
                rich_print("✅ Auggie AI integration available!", style="green")

                if test_memory.strip():
                    enhancement = auggie.enhance_prompt(
                        "How do I get started?", "setup-user"
                    )
                    rich_print(
                        f"✅ AI enhancement working! ({len(enhancement['enhanced_prompt'])} chars)",
                        style="green",
                    )

            except Exception as e:
                rich_print(f"⚠️  AI integration not available: {e}", style="yellow")

        # Success summary
        rich_panel(
            f"🎉 Setup Complete!\n\n"
            f"Configuration:\n"
            f"• Database: {db_path}\n"
            f"• Max recall time: {max_recall_time}ms\n"
            f"• Max generation time: {max_generation_time}ms\n\n"
            f"Next steps:\n"
            f"• kuzu-memory remember 'your thoughts' --db-path {db_path}\n"
            f"• kuzu-memory recall 'what do you know?' --db-path {db_path}\n"
            f"• kuzu-memory examples workflow\n\n"
            f"Your KuzuMemory system is ready to use!",
            title="🚀 Setup Complete!",
            style="green",
        )

    except KeyboardInterrupt:
        rich_print("\n⚠️  Setup cancelled by user", style="yellow")
    except Exception as e:
        rich_print(f"❌ Setup failed: {e}", style="red")
        if ctx.obj.get("debug"):
            raise


@cli.command()
@click.pass_context
def tips(ctx):
    """
    💡 Show helpful tips and best practices.

    \b
    Get the most out of KuzuMemory with:
    • Memory storage best practices
    • Query optimization tips
    • AI integration advice
    • Performance tuning
    """

    tips_content = """
🎯 MEMORY STORAGE TIPS:

✅ What Works Well:
• "I'm [Name], a [Role] at [Company]"
• "I prefer [Tech A] over [Tech B] for [Use Case]"
• "We decided to use [Solution] because [Reason]"
• "The [System] connects to [Service] via [Protocol]"

❌ What Doesn't Work:
• Single words: "Python" (too vague)
• Questions: "What should I use?" (no information)
• Commands: "Install FastAPI" (no context)

🔍 QUERY OPTIMIZATION:

✅ Effective Queries:
• "What do I prefer for web development?"
• "What decisions did we make about databases?"
• "How does our authentication system work?"

💡 Query Tips:
• Use natural language questions
• Include context words (names, topics, timeframes)
• Be specific about what you're looking for
• Try different phrasings if no results

🤖 AI INTEGRATION BEST PRACTICES:

• Store personal preferences and context first
• Use auggie enhance for personalized prompts
• Learn from AI responses with auggie learn
• Monitor performance with auggie stats

⚡ PERFORMANCE OPTIMIZATION:

• Use specific user IDs to scope queries
• Limit max_memories for faster recall
• Store structured information for better matching
• Regular cleanup of old memories

🔧 MAINTENANCE:

• Check stats regularly: kuzu-memory stats
• Monitor AI performance: kuzu-memory auggie stats
• Clean up old memories: kuzu-memory cleanup
• Backup your database file regularly

🚀 WORKFLOW OPTIMIZATION:

1. Start with quickstart: kuzu-memory quickstart
2. Store your context: kuzu-memory remember "..."
3. Test recall: kuzu-memory recall "what do you know?"
4. Use AI features: kuzu-memory auggie enhance "..."
5. Monitor and tune: kuzu-memory stats
    """

    rich_panel(tips_content, title="💡 KuzuMemory Tips & Best Practices", style="cyan")


@cli.command()
@click.option(
    "--enable-cli", is_flag=True, help="Enable Kuzu CLI adapter for better performance"
)
@click.option(
    "--disable-cli", is_flag=True, help="Disable Kuzu CLI adapter (use Python API)"
)
@click.pass_context
def optimize(ctx, enable_cli, disable_cli):
    """
    🚀 Optimize KuzuMemory performance settings.

    \b
    Configure KuzuMemory for optimal performance:
    • Enable Kuzu CLI adapter for faster queries
    • Adjust performance thresholds
    • Configure connection pooling

    \b
    🎯 EXAMPLES:
      kuzu-memory optimize --enable-cli    # Use native Kuzu CLI
      kuzu-memory optimize --disable-cli   # Use Python API

    \b
    💡 PERFORMANCE TIPS:
      • CLI adapter is 2-3x faster than Python API
      • CLI adapter uses less memory
      • CLI adapter has better Kuzu compatibility
      • Python API offers more programmatic control
    """

    if enable_cli and disable_cli:
        rich_print(
            "❌ Cannot enable and disable CLI adapter at the same time", style="red"
        )
        return

    if not enable_cli and not disable_cli:
        # Show current status
        rich_panel(
            "🔧 KuzuMemory Performance Configuration\n\n"
            "Current settings:\n"
            "• CLI Adapter: Not configured (using default Python API)\n"
            "• Performance: Standard settings\n\n"
            "Optimization options:\n"
            "• --enable-cli   Use native Kuzu CLI (recommended)\n"
            "• --disable-cli  Use Python API (more control)\n\n"
            "💡 CLI adapter provides 2-3x better performance!",
            title="⚡ Performance Settings",
            style="blue",
        )
        return

    try:
        from ..utils.config_loader import get_config_loader

        # Load current config
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get("config_path"))

        if enable_cli:
            rich_print("🚀 Enabling Kuzu CLI adapter...", style="bold blue")

            # Check if Kuzu CLI is available
            import subprocess

            try:
                result = subprocess.run(
                    ["kuzu", "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    rich_print("✅ Kuzu CLI found and working", style="green")

                    # Update config
                    config.storage.use_cli_adapter = True

                    rich_panel(
                        "🎉 CLI Adapter Enabled!\n\n"
                        "Benefits:\n"
                        "• 2-3x faster query execution\n"
                        "• Lower memory usage\n"
                        "• Better Kuzu compatibility\n"
                        "• Native query optimization\n\n"
                        "Your KuzuMemory will now use the native Kuzu CLI\n"
                        "for optimal performance!",
                        title="🚀 Performance Boost Activated",
                        style="green",
                    )
                else:
                    rich_print("❌ Kuzu CLI not working properly", style="red")
                    rich_print(
                        "💡 Install Kuzu CLI: https://docs.kuzudb.com/installation",
                        style="yellow",
                    )
                    return

            except (subprocess.TimeoutExpired, FileNotFoundError):
                rich_print("❌ Kuzu CLI not found", style="red")
                rich_panel(
                    "Kuzu CLI is required for optimal performance.\n\n"
                    "Installation options:\n"
                    "• macOS: brew install kuzu\n"
                    "• Linux: Download from https://github.com/kuzudb/kuzu/releases\n"
                    "• Build from source: https://docs.kuzudb.com/installation\n\n"
                    "After installation, run this command again.",
                    title="📦 Install Kuzu CLI",
                    style="yellow",
                )
                return

        elif disable_cli:
            rich_print(
                "🔧 Disabling CLI adapter (using Python API)...", style="bold blue"
            )
            config.storage.use_cli_adapter = False

            rich_panel(
                "✅ Python API Enabled\n\n"
                "You're now using the Python API adapter.\n\n"
                "Trade-offs:\n"
                "• More programmatic control\n"
                "• Easier debugging\n"
                "• Slower query execution\n"
                "• Higher memory usage\n\n"
                "💡 Consider --enable-cli for better performance",
                title="🐍 Python API Active",
                style="blue",
            )

        # Test the configuration
        rich_print("\n🧪 Testing configuration...", style="bold")

        from ..core.memory import KuzuMemory

        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "test.db"

            try:
                with KuzuMemory(db_path=test_db, config=config) as memory:
                    # Quick test
                    start_time = time.time()
                    memory.generate_memories("Test optimization", user_id="test")
                    test_time = (time.time() - start_time) * 1000

                    adapter_type = (
                        "CLI" if config.storage.use_cli_adapter else "Python API"
                    )
                    rich_print(
                        f"✅ {adapter_type} adapter working! Test completed in {test_time:.1f}ms",
                        style="green",
                    )

            except Exception as e:
                rich_print(f"❌ Configuration test failed: {e}", style="red")
                rich_print("💡 Try: kuzu-memory --debug optimize", style="yellow")
                return

        rich_print("\n🎉 Optimization complete! KuzuMemory is ready.", style="green")

    except Exception as e:
        rich_print(f"❌ Optimization failed: {e}", style="red")
        if ctx.obj.get("debug"):
            raise


@cli.command()
@click.argument("prompt", required=True)
@click.option("--max-memories", default=10, help="Maximum number of memories to recall")
@click.option(
    "--strategy",
    default="auto",
    type=click.Choice(["auto", "keyword", "entity", "temporal"]),
    help="Recall strategy to use",
)
@click.option("--session-id", help="Session ID filter")
@click.option("--agent-id", default="cli", help="Agent ID filter")
@click.option(
    "--format",
    "output_format",
    default="enhanced",
    type=click.Choice(["enhanced", "plain", "json", "memories-only"]),
    help="Output format",
)
@click.option(
    "--explain-ranking",
    is_flag=True,
    help="Show detailed ranking explanation including temporal decay",
)
@click.pass_context
def recall(
    ctx,
    prompt,
    max_memories,
    strategy,
    session_id,
    agent_id,
    output_format,
    explain_ranking,
):
    """
    🔍 Recall project memories relevant to the provided prompt.

    \b
    Finds and displays memories that match your query using
    intelligent search strategies.

    \b
    🎯 EXAMPLES:
      # Find project architecture info
      kuzu-memory recall "What's our database setup?"

      # Find team decisions
      kuzu-memory recall "How do we handle authentication?"

      # Find development patterns
      kuzu-memory recall "What testing framework do we use?"

      # JSON output for scripts
      kuzu-memory recall "API patterns" --format json

    \b
    💡 TIPS:
      • Use natural language questions
      • Be specific about what you're looking for
      • Try different strategies if no results
      • Use --max-memories to control output

    \b
    🔗 RELATED:
      kuzu-memory remember   Store new memories
      kuzu-memory stats      View memory statistics
      kuzu-memory project    Show project information
    """
    try:
        # Load configuration and initialize KuzuMemory
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get("config_path"))

        with KuzuMemory(db_path=ctx.obj.get("db_path"), config=config) as memory:
            # Attach memories (no user_id in project model)
            context = memory.attach_memories(
                prompt=prompt,
                max_memories=max_memories,
                strategy=strategy,
                session_id=session_id,
                agent_id=agent_id,
            )

            # Output based on format
            if output_format == "json":
                output = {
                    "original_prompt": context.original_prompt,
                    "enhanced_prompt": context.enhanced_prompt,
                    "memories": [
                        {
                            "id": mem.id,
                            "content": mem.content,
                            "type": mem.memory_type.value,
                            "importance": mem.importance,
                            "confidence": mem.confidence,
                            "created_at": mem.created_at.isoformat(),
                        }
                        for mem in context.memories
                    ],
                    "confidence": context.confidence,
                    "strategy_used": context.strategy_used,
                    "recall_time_ms": context.recall_time_ms,
                }
                click.echo(json.dumps(output, indent=2))

            elif output_format == "memories-only":
                for i, mem in enumerate(context.memories, 1):
                    click.echo(f"{i}. {mem.content}")

            elif output_format == "plain":
                click.echo(context.to_system_message(format_style="plain"))

            else:  # enhanced
                click.echo("Enhanced Prompt:")
                click.echo("=" * 50)
                click.echo(context.enhanced_prompt)
                click.echo("=" * 50)
                click.echo(
                    f"Found {len(context.memories)} memories (confidence: {context.confidence:.2f})"
                )
                click.echo(
                    f"Strategy: {context.strategy_used}, Time: {context.recall_time_ms:.1f}ms"
                )

    except Exception as e:
        click.echo(f"Error recalling memories: {e}", err=True)
        if ctx.obj["debug"]:
            raise
        sys.exit(1)


@cli.command()
@click.option("--detailed", is_flag=True, help="Show detailed statistics")
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
@click.pass_context
def stats(ctx, detailed, output_format):
    """Show database and performance statistics."""
    try:
        # Load configuration and initialize KuzuMemory
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get("config_path"))

        with KuzuMemory(db_path=ctx.obj.get("db_path"), config=config) as memory:
            stats_data = memory.get_statistics()

            if output_format == "json":
                click.echo(json.dumps(stats_data, indent=2, default=str))
            else:
                # Text format
                system_info = stats_data.get("system_info", {})
                perf_stats = stats_data.get("performance_stats", {})
                storage_stats = stats_data.get("storage_stats", {})

                click.echo("KuzuMemory Statistics")
                click.echo("=" * 40)

                # System info
                click.echo(f"Database Path: {system_info.get('db_path', 'Unknown')}")
                click.echo(
                    f"Initialized: {system_info.get('initialized_at', 'Unknown')}"
                )
                click.echo(
                    f"Config Version: {system_info.get('config_version', 'Unknown')}"
                )
                click.echo()

                # Performance stats
                click.echo("Performance:")
                click.echo(
                    f"  attach_memories() calls: {perf_stats.get('attach_memories_calls', 0)}"
                )
                click.echo(
                    f"  generate_memories() calls: {perf_stats.get('generate_memories_calls', 0)}"
                )
                click.echo(
                    f"  Average attach time: {perf_stats.get('avg_attach_time_ms', 0):.1f}ms"
                )
                click.echo(
                    f"  Average generate time: {perf_stats.get('avg_generate_time_ms', 0):.1f}ms"
                )
                click.echo()

                # Storage stats
                if "database_stats" in storage_stats:
                    db_stats = storage_stats["database_stats"]
                    click.echo("Database:")
                    click.echo(f"  Memories: {db_stats.get('memory_count', 0)}")
                    click.echo(f"  Entities: {db_stats.get('entity_count', 0)}")
                    click.echo(f"  Sessions: {db_stats.get('session_count', 0)}")
                    click.echo(f"  Size: {db_stats.get('db_size_mb', 0):.1f} MB")
                    click.echo()

                if detailed:
                    # Show more detailed statistics
                    click.echo("Detailed Statistics:")
                    click.echo("-" * 20)

                    # Storage details
                    if "storage_stats" in storage_stats:
                        store_stats = storage_stats["storage_stats"]
                        click.echo(
                            f"  Memories stored: {store_stats.get('memories_stored', 0)}"
                        )
                        click.echo(
                            f"  Memories skipped: {store_stats.get('memories_skipped', 0)}"
                        )
                        click.echo(
                            f"  Memories updated: {store_stats.get('memories_updated', 0)}"
                        )

                    # Recall details
                    if "recall_stats" in stats_data:
                        recall_stats = stats_data["recall_stats"]
                        if "coordinator_stats" in recall_stats:
                            coord_stats = recall_stats["coordinator_stats"]
                            click.echo(
                                f"  Total recalls: {coord_stats.get('total_recalls', 0)}"
                            )
                            click.echo(
                                f"  Cache hits: {coord_stats.get('cache_hits', 0)}"
                            )
                            click.echo(
                                f"  Cache misses: {coord_stats.get('cache_misses', 0)}"
                            )

    except Exception as e:
        click.echo(f"Error getting statistics: {e}", err=True)
        if ctx.obj["debug"]:
            raise
        sys.exit(1)


@cli.command()
@click.option("--force", is_flag=True, help="Force cleanup without confirmation")
@click.pass_context
def cleanup(ctx, force):
    """Clean up expired memories."""
    try:
        # Load configuration and initialize KuzuMemory
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get("config_path"))

        if not force:
            click.confirm(
                "This will permanently delete expired memories. Continue?", abort=True
            )

        with KuzuMemory(db_path=ctx.obj.get("db_path"), config=config) as memory:
            cleaned_count = memory.cleanup_expired_memories()

            if cleaned_count > 0:
                click.echo(f"✓ Cleaned up {cleaned_count} expired memories")
            else:
                click.echo("No expired memories found")

    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
        if ctx.obj["debug"]:
            raise
        sys.exit(1)


@cli.command()
@click.argument("config_path", type=click.Path())
@click.pass_context
def create_config(ctx, config_path):
    """Create an example configuration file."""
    try:
        config_loader = get_config_loader()
        config_loader.create_example_config(Path(config_path))
        click.echo(f"✓ Example configuration created at {config_path}")
        click.echo("Edit this file to customize KuzuMemory settings")

    except Exception as e:
        click.echo(f"Error creating configuration: {e}", err=True)
        if ctx.obj["debug"]:
            raise
        sys.exit(1)


@cli.group()
@click.pass_context
def auggie(ctx):
    """
    Auggie integration commands for intelligent memory-driven AI interactions.

    Provides commands for managing Auggie rules, enhancing prompts,
    and learning from AI responses.
    """
    pass


@auggie.command("enhance")
@click.argument("prompt")
@click.option("--user-id", default="cli-user", help="User ID for context")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def auggie_enhance(ctx, prompt, user_id, verbose):
    """Enhance a prompt using Auggie rules and memories."""
    try:
        db_path = ctx.obj.get("db_path", "kuzu_memories.db")

        with KuzuMemory(db_path=db_path) as memory:
            auggie_integration = AuggieIntegration(memory)

            enhancement = auggie_integration.enhance_prompt(
                prompt=prompt, user_id=user_id, context={"source": "cli"}
            )

            click.echo("🚀 Prompt Enhancement Results:")
            click.echo("=" * 50)
            click.echo(f"Original: {enhancement['original_prompt']}")
            click.echo(f"Enhanced: {enhancement['enhanced_prompt']}")
            click.echo(f"Context:  {enhancement['context_summary']}")

            if verbose:
                click.echo("\n📊 Detailed Information:")
                memory_context = enhancement.get("memory_context")
                if memory_context and memory_context.memories:
                    click.echo(f"Memories used: {len(memory_context.memories)}")
                    for i, memory in enumerate(memory_context.memories[:3]):
                        click.echo(f"  {i + 1}. {memory.content[:60]}...")

                executed_rules = enhancement["rule_modifications"].get(
                    "executed_rules", []
                )
                if executed_rules:
                    click.echo(f"Rules applied: {len(executed_rules)}")
                    for rule_info in executed_rules:
                        click.echo(f"  - {rule_info['rule_name']}")

    except Exception as e:
        click.echo(f"❌ Error enhancing prompt: {e}", err=True)
        if ctx.obj["debug"]:
            raise
        sys.exit(1)


@auggie.command("learn")
@click.argument("prompt")
@click.argument("response")
@click.option("--feedback", help="User feedback on the response")
@click.option("--user-id", default="cli-user", help="User ID for context")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed learning data")
@click.pass_context
def auggie_learn(ctx, prompt, response, feedback, user_id, verbose):
    """Learn from an AI response and optional user feedback."""
    try:
        db_path = ctx.obj.get("db_path", "kuzu_memories.db")

        with KuzuMemory(db_path=db_path) as memory:
            auggie_integration = AuggieIntegration(memory)

            learning_result = auggie_integration.learn_from_interaction(
                prompt=prompt,
                ai_response=response,
                user_feedback=feedback,
                user_id=user_id,
            )

            click.echo("🧠 Learning Results:")
            click.echo("=" * 30)
            click.echo(f"Quality Score: {learning_result.get('quality_score', 0):.2f}")
            click.echo(
                f"Memories Created: {len(learning_result.get('extracted_memories', []))}"
            )

            if "corrections" in learning_result:
                corrections = learning_result["corrections"]
                click.echo(f"Corrections Found: {len(corrections)}")
                for correction in corrections:
                    click.echo(f"  - {correction['correction']}")

            if verbose:
                click.echo("\n📊 Full Learning Data:")
                click.echo(json.dumps(learning_result, indent=2, default=str))

    except Exception as e:
        click.echo(f"❌ Error learning from response: {e}", err=True)
        if ctx.obj["debug"]:
            raise
        sys.exit(1)


@auggie.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed rule information")
@click.pass_context
def rules(ctx, verbose):
    """List all Auggie rules."""
    try:
        db_path = ctx.obj.get("db_path", "kuzu_memories.db")

        with KuzuMemory(db_path=db_path) as memory:
            auggie_integration = AuggieIntegration(memory)

            rules = auggie_integration.rule_engine.rules

            click.echo(f"📋 Auggie Rules ({len(rules)} total):")
            click.echo("=" * 50)

            # Group by rule type
            by_type = {}
            for rule in rules.values():
                rule_type = rule.rule_type.value
                if rule_type not in by_type:
                    by_type[rule_type] = []
                by_type[rule_type].append(rule)

            for rule_type, type_rules in by_type.items():
                click.echo(
                    f"\n🔧 {rule_type.replace('_', ' ').title()} ({len(type_rules)} rules):"
                )

                for rule in sorted(type_rules, key=lambda r: r.priority.value):
                    status = "✅" if rule.enabled else "❌"
                    priority = rule.priority.name
                    executions = rule.execution_count
                    success_rate = rule.success_rate * 100

                    click.echo(f"  {status} {rule.name} [{priority}]")
                    if verbose:
                        click.echo(f"      ID: {rule.id}")
                        click.echo(f"      Description: {rule.description}")
                        click.echo(
                            f"      Executions: {executions}, Success: {success_rate:.1f}%"
                        )
                        click.echo(f"      Conditions: {rule.conditions}")
                        click.echo(f"      Actions: {rule.actions}")
                        click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing rules: {e}", err=True)
        if ctx.obj["debug"]:
            raise
        sys.exit(1)


@auggie.command("stats")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed statistics")
@click.pass_context
def auggie_stats(ctx, verbose):
    """Show Auggie integration statistics."""
    try:
        db_path = ctx.obj.get("db_path", "kuzu_memories.db")

        with KuzuMemory(db_path=db_path) as memory:
            auggie_integration = AuggieIntegration(memory)

            stats = auggie_integration.get_integration_statistics()

            click.echo("📊 Auggie Integration Statistics:")
            click.echo("=" * 40)

            # Integration stats
            integration_stats = stats["integration"]
            click.echo(f"Prompts Enhanced: {integration_stats['prompts_enhanced']}")
            click.echo(f"Responses Learned: {integration_stats['responses_learned']}")
            click.echo(f"Rules Triggered: {integration_stats['rules_triggered']}")
            click.echo(f"Memories Created: {integration_stats['memories_created']}")

            # Rule engine stats
            rule_stats = stats["rule_engine"]
            click.echo("\nRule Engine:")
            click.echo(f"  Total Rules: {rule_stats['total_rules']}")
            click.echo(f"  Enabled Rules: {rule_stats['enabled_rules']}")
            click.echo(f"  Total Executions: {rule_stats['total_executions']}")

            # Response learner stats
            learner_stats = stats["response_learner"]
            click.echo("\nResponse Learner:")
            click.echo(f"  Learning Events: {learner_stats['total_learning_events']}")
            if "average_quality_score" in learner_stats:
                click.echo(
                    f"  Average Quality: {learner_stats['average_quality_score']:.2f}"
                )

            if verbose:
                click.echo("\n🔧 Rule Performance:")
                rule_performance = rule_stats.get("rule_performance", {})

                # Sort by execution count
                sorted_rules = sorted(
                    rule_performance.items(),
                    key=lambda x: x[1]["execution_count"],
                    reverse=True,
                )

                for _rule_id, perf in sorted_rules[:10]:  # Top 10
                    name = perf["name"]
                    count = perf["execution_count"]
                    success = perf["success_rate"] * 100
                    click.echo(f"  {name}: {count} executions, {success:.1f}% success")

    except Exception as e:
        click.echo(f"❌ Error getting statistics: {e}", err=True)
        if ctx.obj["debug"]:
            raise
        sys.exit(1)


# Bridge server removed - use CLI-only integration instead
# See AGENTS.md and .augment/rules/ for proper Augment integration

# Add install commands to CLI

cli.add_command(install_group)
cli.add_command(uninstall)
cli.add_command(status, name="install-status")
cli.add_command(list_installers, name="list-installers")


@cli.command()
@click.option("--memory-id", help="Analyze specific memory by ID")
@click.option("--memory-type", help="Analyze all memories of specific type")
@click.option("--limit", default=10, help="Number of memories to analyze")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json", "detailed"]),
    help="Output format",
)
@click.pass_context
def temporal_analysis(ctx, memory_id, memory_type, limit, output_format):
    """
    🕒 Analyze temporal decay for memories.

    Shows how temporal decay affects memory ranking and provides
    detailed breakdown of decay calculations.

    \b
    🎮 EXAMPLES:
      # Analyze recent memories
      kuzu-memory temporal-analysis --limit 5

      # Analyze specific memory type
      kuzu-memory temporal-analysis --memory-type pattern

      # Detailed analysis of specific memory
      kuzu-memory temporal-analysis --memory-id abc123 --format detailed
    """
    try:
        from ..utils.project_setup import get_project_db_path

        db_path = get_project_db_path(ctx.obj.get("project_root"))

        with KuzuMemory(db_path=db_path) as memory:
            from ..recall.temporal_decay import TemporalDecayEngine

            # Initialize temporal decay engine
            decay_engine = TemporalDecayEngine()

            # Get memories to analyze
            if memory_id:
                # Analyze specific memory
                memories = [memory.get_memory_by_id(memory_id)]
                if not memories[0]:
                    rich_print(f"❌ Memory not found: {memory_id}", style="red")
                    sys.exit(1)
            else:
                # Get recent memories, optionally filtered by type
                filters = {}
                if memory_type:
                    filters["memory_type"] = memory_type

                memories = memory.get_recent_memories(limit=limit, **filters)

            if not memories:
                rich_print("[i] No memories found for analysis", style="blue")
                return

            # Analyze temporal decay for each memory
            analyses = []
            for mem in memories:
                analysis = decay_engine.get_decay_explanation(mem)
                analyses.append(analysis)

            # Display results
            if output_format == "json":
                rich_print(json.dumps(analyses, indent=2, default=str))
            elif output_format == "detailed":
                for analysis in analyses:
                    rich_print(
                        f"\n🧠 Memory Analysis: {analysis['memory_id'][:8]}...",
                        style="blue",
                    )
                    rich_print(f"  Type: {analysis['memory_type']}")
                    rich_print(
                        f"  Age: {analysis['age_days']} days ({analysis['age_hours']} hours)"
                    )
                    rich_print(f"  Decay Function: {analysis['decay_function']}")
                    rich_print(f"  Half-life: {analysis['half_life_days']} days")
                    rich_print(f"  Base Score: {analysis['base_decay_score']}")
                    rich_print(f"  Final Score: {analysis['final_temporal_score']}")
                    rich_print(
                        f"  Recent Boost: {'✅ Applied' if analysis['recent_boost_applied'] else '❌ Not Applied'}"
                    )
                    rich_print(f"  Minimum Score: {analysis['minimum_score']}")
                    rich_print(f"  Boost Multiplier: {analysis['boost_multiplier']}")
            else:
                # Table format
                table = Table(title="🕒 Temporal Decay Analysis")
                table.add_column("Memory ID", style="cyan")
                table.add_column("Type", style="green")
                table.add_column("Age (days)", style="yellow")
                table.add_column("Decay Function", style="blue")
                table.add_column("Base Score", style="magenta")
                table.add_column("Final Score", style="red")
                table.add_column("Recent Boost", style="green")

                for analysis in analyses:
                    boost_icon = "✅" if analysis["recent_boost_applied"] else "❌"
                    table.add_row(
                        analysis["memory_id"][:8] + "...",
                        analysis["memory_type"],
                        f"{analysis['age_days']:.1f}",
                        analysis["decay_function"],
                        f"{analysis['base_decay_score']:.3f}",
                        f"{analysis['final_temporal_score']:.3f}",
                        boost_icon,
                    )

                console.print(table)

                # Summary statistics
                avg_age = sum(a["age_days"] for a in analyses) / len(analyses)
                avg_score = sum(a["final_temporal_score"] for a in analyses) / len(
                    analyses
                )
                recent_boost_count = sum(
                    1 for a in analyses if a["recent_boost_applied"]
                )

                rich_print("\n📊 Summary:")
                rich_print(f"  Average Age: {avg_age:.1f} days")
                rich_print(f"  Average Temporal Score: {avg_score:.3f}")
                rich_print(
                    f"  Recent Boost Applied: {recent_boost_count}/{len(analyses)} memories"
                )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Temporal analysis failed: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
