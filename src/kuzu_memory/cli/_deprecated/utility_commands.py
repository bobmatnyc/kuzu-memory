"""
Utility CLI commands for KuzuMemory.

Contains commands for optimize, setup, examples, tips, temporal_analysis operations.
"""

import json
import logging
import sys

import click

from ..core.memory import KuzuMemory
from ..integrations.auggie import AuggieIntegration
from ..utils.project_setup import find_project_root, get_project_db_path
from .cli_utils import (
    RICH_AVAILABLE,
    console,
    rich_confirm,
    rich_panel,
    rich_print,
    rich_prompt,
    rich_table,
)

logger = logging.getLogger(__name__)


@click.command()
@click.option("--enable-cli", is_flag=True, help="Enable Kuzu CLI adapter for better performance")
@click.option("--disable-cli", is_flag=True, help="Disable Kuzu CLI adapter (use Python API)")
@click.pass_context
def optimize(ctx: click.Context, enable_cli: bool, disable_cli: bool) -> None:
    """
    ⚡ Optimize KuzuMemory performance settings.

    Configures performance optimizations including CLI adapter usage,
    connection pooling, and caching strategies for better response times.

    \b
    🎮 EXAMPLES:
      # Enable CLI adapter for better performance
      kuzu-memory optimize --enable-cli

      # Disable CLI adapter (use Python API)
      kuzu-memory optimize --disable-cli

      # Interactive optimization
      kuzu-memory optimize
    """
    try:
        from ..utils.config_loader import get_config_loader

        project_root = ctx.obj.get("project_root") or find_project_root()
        config_loader = get_config_loader()
        current_config = config_loader.load_config(project_root)

        if enable_cli and disable_cli:
            rich_print("❌ Cannot enable and disable CLI adapter at the same time", style="red")
            sys.exit(1)

        changes_made = []

        if enable_cli:
            current_config.storage.use_cli_adapter = True
            changes_made.append("✅ Enabled Kuzu CLI adapter")

        elif disable_cli:
            current_config.storage.use_cli_adapter = False
            changes_made.append("❌ Disabled Kuzu CLI adapter")

        else:
            # Interactive optimization
            rich_print("⚡ KuzuMemory Performance Optimization")
            rich_print("Current settings:")
            rich_print(
                f"  CLI Adapter: {'✅ Enabled' if current_config.storage.use_cli_adapter else '❌ Disabled'}"
            )
            rich_print(f"  Connection Pool Size: {current_config.storage.connection_pool_size}")
            rich_print(f"  Cache TTL: {current_config.caching.ttl_seconds}s")

            # CLI Adapter optimization
            if rich_confirm(
                "Enable Kuzu CLI adapter for better performance?",
                default=not current_config.storage.use_cli_adapter,
            ):
                if not current_config.storage.use_cli_adapter:
                    current_config.storage.use_cli_adapter = True
                    changes_made.append("✅ Enabled Kuzu CLI adapter")

            # Connection pool optimization
            if rich_confirm("Optimize connection pool size?", default=True):
                new_pool_size = rich_prompt(
                    "Connection pool size",
                    default=str(current_config.storage.connection_pool_size),
                )
                try:
                    new_pool_size = int(new_pool_size)
                    if new_pool_size != current_config.storage.connection_pool_size:
                        current_config.storage.connection_pool_size = new_pool_size
                        changes_made.append(f"🔧 Set connection pool size to {new_pool_size}")
                except ValueError:
                    rich_print("⚠️  Invalid pool size, keeping current value", style="yellow")

            # Cache optimization
            if rich_confirm("Optimize caching settings?", default=True):
                new_ttl = rich_prompt(
                    "Cache TTL (seconds)",
                    default=str(current_config.caching.ttl_seconds),
                )
                try:
                    new_ttl = int(new_ttl)
                    if new_ttl != current_config.caching.ttl_seconds:
                        current_config.caching.ttl_seconds = new_ttl
                        changes_made.append(f"⏱️  Set cache TTL to {new_ttl}s")
                except ValueError:
                    rich_print("⚠️  Invalid TTL value, keeping current value", style="yellow")

        if changes_made:
            # Save configuration
            config_path = project_root / ".kuzu-memory" / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with config_path.open("w") as f:
                json.dump(current_config.to_dict(), f, indent=2)

            rich_print("\n⚡ Optimization Complete:")
            for change in changes_made:
                rich_print(f"  {change}")

            rich_print(f"\nConfiguration saved to: {config_path}")

            # Test performance
            if rich_confirm("Run performance test?", default=True):
                rich_print("\n🏃 Running performance test...")
                try:
                    db_path = get_project_db_path(project_root)
                    with KuzuMemory(db_path=db_path, config=current_config) as memory:
                        import time

                        start_time = time.time()
                        memory.get_recent_memories(limit=5)
                        end_time = time.time()

                        response_time = (end_time - start_time) * 1000  # Convert to ms
                        rich_print(f"⏱️  Query response time: {response_time:.1f}ms")

                        if response_time < 100:
                            rich_print("✅ Excellent performance!", style="green")
                        elif response_time < 200:
                            rich_print("👍 Good performance", style="yellow")
                        else:
                            rich_print("⚠️  Consider further optimization", style="red")

                except Exception as e:
                    rich_print(f"⚠️  Performance test failed: {e}", style="yellow")

        else:
            rich_print("[i]  No changes made", style="blue")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Optimization failed: {e}", style="red")
        sys.exit(1)


@click.command()
@click.option("--advanced", is_flag=True, help="Show advanced configuration options")
@click.pass_context
def setup(ctx: click.Context, advanced: bool) -> None:
    """
    🔧 Interactive setup and configuration guide.

    Provides step-by-step guidance for configuring KuzuMemory
    including database settings, performance options, and integrations.

    \b
    🎮 EXAMPLES:
      # Basic setup guide
      kuzu-memory setup

      # Advanced configuration
      kuzu-memory setup --advanced
    """
    try:
        from ..core.config import KuzuMemoryConfig

        rich_panel(
            "Welcome to KuzuMemory Setup! 🚀\n\n"
            "This guide will help you configure KuzuMemory for optimal performance\n"
            "in your project environment.",
            title="🔧 Setup Guide",
            style="blue",
        )

        project_root = ctx.obj.get("project_root") or find_project_root()
        db_path = get_project_db_path(project_root)

        # Check initialization status
        if not db_path.exists():
            rich_print("⚠️  Project not initialized. Let's start with initialization!")
            if rich_confirm("Initialize KuzuMemory for this project?", default=True):
                # Call init command logic
                from .project_commands import init

                ctx.invoke(init)
            else:
                rich_print("Setup cancelled. Run 'kuzu-memory init' first.")
                return

        # Configuration options
        config = KuzuMemoryConfig()

        rich_print("\n📋 Configuration Options:")

        # Basic configuration
        rich_print("1. Database Settings")
        if rich_confirm("   Configure database path and backup?", default=False):
            backup_enabled = rich_confirm("   Enable automatic backups?", default=True)
            config.storage.backup_enabled = backup_enabled

        rich_print("\n2. Memory Settings")
        if rich_confirm("   Configure memory limits and thresholds?", default=True):
            max_memories = rich_prompt("   Max memories per query", default="10")
            try:
                config.memory.max_memories_per_query = int(max_memories)
            except ValueError:
                rich_print("   ⚠️  Invalid value, using default", style="yellow")

        rich_print("\n3. Performance Settings")
        if rich_confirm("   Enable performance optimizations?", default=True):
            config.storage.use_cli_adapter = True
            config.caching.enabled = True
            rich_print("   ✅ Enabled CLI adapter and caching")

        if advanced:
            rich_print("\n🔬 Advanced Configuration:")

            rich_print("4. Temporal Decay")
            if rich_confirm("   Configure memory retention policies?", default=False):
                decay_enabled = rich_confirm("   Enable temporal decay?", default=True)
                config.temporal_decay.enabled = decay_enabled

                if decay_enabled:
                    boost_hours = rich_prompt("   Recent boost hours", default="24")
                    try:
                        config.temporal_decay.recent_boost_hours = int(boost_hours)
                    except ValueError:
                        rich_print("   ⚠️  Invalid value, using default", style="yellow")

            rich_print("\n5. Integration Settings")
            # Check for Auggie
            try:
                auggie = AuggieIntegration(project_root)
                if auggie.is_auggie_project():
                    rich_print("   🤖 Auggie project detected!")
                    if rich_confirm("   Configure Auggie integration?", default=True):
                        try:
                            auggie.setup_project_integration()
                            rich_print("   ✅ Auggie integration configured")
                        except Exception as e:
                            rich_print(f"   ⚠️  Auggie setup failed: {e}", style="yellow")
            except ImportError:
                rich_print("   [i]  Auggie integration not available")

        # Save configuration
        config_path = project_root / ".kuzu-memory" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with config_path.open("w") as f:
            json.dump(config.to_dict(), f, indent=2)

        rich_panel(
            f"Setup complete! 🎉\n\n"
            f"Configuration saved to: {config_path}\n\n"
            f"Next steps:\n"
            f"• Test your setup: kuzu-memory stats\n"
            f"• Store a memory: kuzu-memory remember 'Setup completed'\n"
            f"• Try enhancement: kuzu-memory enhance 'How do I use this?'\n",
            title="✅ Setup Complete",
            style="green",
        )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Setup failed: {e}", style="red")
        sys.exit(1)


@click.command()
@click.pass_context
def tips(ctx: click.Context) -> None:
    """
    💡 Show helpful tips and best practices for KuzuMemory.

    Provides practical advice on how to get the most out of KuzuMemory
    including usage patterns, performance optimization, and integration tips.
    """
    try:
        tips_content = [
            "🎯 **Getting Started**",
            "   • Initialize projects with 'kuzu-memory init'",
            "   • Store project context: 'kuzu-memory remember \"We use FastAPI\"'",
            "   • Test enhancement: 'kuzu-memory enhance \"How do I deploy?\"'",
            "",
            "⚡ **Performance Tips**",
            "   • Enable CLI adapter: 'kuzu-memory optimize --enable-cli'",
            "   • Use async learning: 'kuzu-memory learn \"info\" --quiet'",
            "   • Keep recalls under 100ms by limiting --max-memories",
            "",
            "🤖 **AI Integration**",
            "   • Use subprocess calls, not direct imports",
            "   • Always use --quiet flag for learning in AI workflows",
            "   • Enhance prompts before sending to AI models",
            "",
            "📚 **Memory Best Practices**",
            '   • Be specific: "Use PostgreSQL with asyncpg driver" vs "Use database"',
            '   • Include context: "Authentication uses JWT tokens with 24h expiry"',
            "   • Group related memories with --session-id",
            "",
            "🔧 **Configuration**",
            "   • Store config in .kuzu-memory/config.json",
            "   • Enable backup for important projects",
            "   • Adjust temporal decay for your workflow",
            "",
            "🧹 **Maintenance**",
            "   • Run cleanup regularly: 'kuzu-memory cleanup'",
            "   • Monitor stats: 'kuzu-memory stats --detailed'",
            "   • Check project health: 'kuzu-memory project --verbose'",
            "",
            "🚀 **Advanced Usage**",
            "   • Use different recall strategies: --strategy keyword|entity|temporal",
            "   • Analyze temporal decay: 'kuzu-memory temporal-analysis'",
            "   • Filter by source: --agent-id or --session-id",
        ]

        rich_panel(
            "\n".join(tips_content),
            title="💡 KuzuMemory Tips & Best Practices",
            style="blue",
        )

        # Interactive help
        if rich_confirm("\nWould you like specific help with any topic?", default=False):
            topic = rich_prompt(
                "Enter topic (getting-started, performance, ai-integration, config)",
                default="",
            )

            topic_help = {
                "getting-started": [
                    "🚀 Getting Started with KuzuMemory:",
                    "1. Initialize: kuzu-memory init",
                    "2. Store info: kuzu-memory remember 'Your project details'",
                    "3. Test recall: kuzu-memory recall 'your question'",
                    "4. Try enhancement: kuzu-memory enhance 'your prompt'",
                ],
                "performance": [
                    "⚡ Performance Optimization:",
                    "1. Enable CLI adapter: kuzu-memory optimize --enable-cli",
                    "2. Limit recalls: --max-memories 5",
                    "3. Use async learning: --quiet flag",
                    "4. Monitor response times: kuzu-memory stats",
                ],
                "ai-integration": [
                    "🤖 AI Integration Pattern:",
                    "result = subprocess.run(['kuzu-memory', 'enhance', prompt, '--format', 'plain'])",
                    "subprocess.run(['kuzu-memory', 'learn', content, '--quiet'])",
                    "Always use subprocess calls, never direct imports!",
                ],
                "config": [
                    "⚙️  Configuration Tips:",
                    "1. Save config: kuzu-memory create-config ./config.json",
                    "2. Enable features: CLI adapter, caching, temporal decay",
                    "3. Set memory limits: max_memories_per_query",
                    "4. Configure retention: temporal decay policies",
                ],
            }

            if topic in topic_help:
                rich_print("\n" + "\n".join(topic_help[topic]))
            else:
                rich_print(
                    "[i]  Topic not found. Available: getting-started, performance, ai-integration, config",
                    style="blue",
                )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Tips display failed: {e}", style="red")
        sys.exit(1)


@click.command()
@click.argument("topic", required=False)
@click.pass_context
def examples(ctx: click.Context, topic: str | None) -> None:
    """
    📚 Show practical examples of KuzuMemory usage.

    Displays example commands and usage patterns for different scenarios
    including basic usage, AI integration, and advanced workflows.

    \b
    🎮 USAGE:
      kuzu-memory examples              # Show all examples
      kuzu-memory examples basic        # Basic usage examples
      kuzu-memory examples ai           # AI integration examples
      kuzu-memory examples advanced     # Advanced usage examples
    """
    try:
        all_examples = {
            "basic": {
                "title": "📝 Basic Usage Examples",
                "examples": [
                    "# Initialize project",
                    "kuzu-memory init",
                    "",
                    "# Store memories",
                    "kuzu-memory remember 'We use FastAPI with PostgreSQL'",
                    "kuzu-memory remember 'Deploy using Docker' --source deployment",
                    "",
                    "# Recall information",
                    "kuzu-memory recall 'How do we deploy?'",
                    "kuzu-memory recall 'database setup' --max-memories 5",
                    "",
                    "# Enhance prompts",
                    "kuzu-memory enhance 'How do I structure the API?'",
                    "kuzu-memory enhance 'Performance tips' --format plain",
                ],
            },
            "ai": {
                "title": "🤖 AI Integration Examples",
                "examples": [
                    "# Python AI integration",
                    "import subprocess",
                    "",
                    "def enhance_prompt(prompt):",
                    "    result = subprocess.run([",
                    "        'kuzu-memory', 'enhance', prompt, '--format', 'plain'",
                    "    ], capture_output=True, text=True)",
                    "    return result.stdout.strip()",
                    "",
                    "def learn_async(content):",
                    "    subprocess.run([",
                    "        'kuzu-memory', 'learn', content, '--quiet'",
                    "    ], check=False)  # Fire and forget",
                    "",
                    "# Usage in conversation",
                    "enhanced = enhance_prompt('How do I authenticate users?')",
                    "ai_response = your_ai_model(enhanced)",
                    "learn_async(f'User asked about auth: {ai_response}')",
                ],
            },
            "advanced": {
                "title": "🚀 Advanced Usage Examples",
                "examples": [
                    "# Learning with metadata",
                    "kuzu-memory learn 'API rate limit is 1000/hour' \\",
                    '  --metadata \'{"priority": "high", "category": "limits"}\'',
                    "",
                    "# Session-based memories",
                    "kuzu-memory remember 'Bug in auth module' --session-id bug-123",
                    "kuzu-memory learn 'Fixed by updating JWT' --session-id bug-123",
                    "",
                    "# Different recall strategies",
                    "kuzu-memory recall 'performance' --strategy keyword",
                    "kuzu-memory recall 'user data' --strategy entity",
                    "kuzu-memory recall 'recent changes' --strategy temporal",
                    "",
                    "# Temporal analysis",
                    "kuzu-memory temporal-analysis --limit 10",
                    "kuzu-memory temporal-analysis --memory-type pattern",
                    "",
                    "# Batch operations",
                    "for info in project_info:",
                    '    kuzu-memory learn "$info" --quiet --source batch-import',
                ],
            },
            "performance": {
                "title": "⚡ Performance Examples",
                "examples": [
                    "# Enable optimizations",
                    "kuzu-memory optimize --enable-cli",
                    "",
                    "# Fast enhancement (< 100ms)",
                    "kuzu-memory enhance 'quick question' --max-memories 3",
                    "",
                    "# Async learning (non-blocking)",
                    "kuzu-memory learn 'user feedback' --quiet",
                    "",
                    "# Performance monitoring",
                    "time kuzu-memory recall 'test query'",
                    "kuzu-memory stats --detailed",
                    "",
                    "# Cleanup for performance",
                    "kuzu-memory cleanup --force",
                ],
            },
        }

        if topic:
            if topic in all_examples:
                example_set = all_examples[topic]
                rich_panel(
                    "\n".join(example_set["examples"]),
                    title=example_set["title"],
                    style="green",
                )
            else:
                rich_print(f"❌ Unknown topic: {topic}", style="red")
                rich_print(f"Available topics: {', '.join(all_examples.keys())}")
        else:
            # Show all examples
            for _topic_name, example_set in all_examples.items():
                rich_panel(
                    "\n".join(example_set["examples"]),
                    title=example_set["title"],
                    style="green",
                )
                rich_print("")  # Add spacing

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Examples display failed: {e}", style="red")
        sys.exit(1)


@click.command()
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
def temporal_analysis(
    ctx: click.Context,
    memory_id: str | None,
    memory_type: str | None,
    limit: int,
    output_format: str,
) -> None:
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
                rich_print("[i]  No memories found for analysis", style="blue")
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
                if RICH_AVAILABLE and console:
                    from rich.table import Table

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
                else:
                    # Fallback table format
                    headers = [
                        "ID",
                        "Type",
                        "Age",
                        "Function",
                        "Base",
                        "Final",
                        "Boost",
                    ]
                    rows = []
                    for analysis in analyses:
                        boost_icon = "✅" if analysis["recent_boost_applied"] else "❌"
                        rows.append(
                            [
                                analysis["memory_id"][:8] + "...",
                                analysis["memory_type"],
                                f"{analysis['age_days']:.1f}d",
                                analysis["decay_function"],
                                f"{analysis['base_decay_score']:.3f}",
                                f"{analysis['final_temporal_score']:.3f}",
                                boost_icon,
                            ]
                        )
                    rich_table(headers, rows, title="🕒 Temporal Decay Analysis")

                # Summary statistics
                avg_age = sum(a["age_days"] for a in analyses) / len(analyses)
                avg_score = sum(a["final_temporal_score"] for a in analyses) / len(analyses)
                recent_boost_count = sum(1 for a in analyses if a["recent_boost_applied"])

                rich_print("\n📊 Summary:")
                rich_print(f"  Average Age: {avg_age:.1f} days")
                rich_print(f"  Average Temporal Score: {avg_score:.3f}")
                rich_print(f"  Recent Boost Applied: {recent_boost_count}/{len(analyses)} memories")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Temporal analysis failed: {e}", style="red")
        sys.exit(1)
