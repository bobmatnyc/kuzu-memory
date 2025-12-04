"""
Memory-related CLI commands for KuzuMemory.

Contains memory command group with subcommands for store, learn, recall, enhance operations.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click

from ..core.memory import KuzuMemory
from ..utils.project_setup import get_project_db_path
from .cli_utils import rich_panel, rich_print, rich_table
from .enums import OutputFormat, RecallStrategy
from .service_manager import ServiceManager

logger = logging.getLogger(__name__)


@click.group()
def memory() -> None:
    """
    🧠 Memory operations (store, recall, enhance).

    Manage memory storage, retrieval, and context enhancement
    for AI applications.

    \b
    🎮 COMMANDS:
      store      Store a memory (synchronous)
      learn      Learn from content (async)
      recall     Query stored memories
      enhance    Enhance prompts with context
      recent     Show recent memories
      prune      Prune old or low-value memories

    Use 'kuzu-memory memory COMMAND --help' for detailed help.
    """
    pass


@memory.command()
@click.argument("content", required=True)
@click.option(
    "--source",
    default="cli",
    help='Source of the memory (e.g., "conversation", "document")',
)
@click.option("--session-id", help="Session ID to group related memories")
@click.option("--agent-id", default="cli", help="Agent ID that created this memory")
@click.option("--metadata", help="Additional metadata as JSON string")
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def store(
    ctx: click.Context,
    content: str,
    source: str,
    session_id: str | None,
    agent_id: str,
    metadata: str | None,
    db_path: str | None,
) -> None:
    """
    💾 Store a memory for future recall (synchronous).

    Immediately stores information in the project memory system.
    Use this for important information that needs to be stored right away.

    \b
    🎮 EXAMPLES:
      # Basic memory storage
      kuzu-memory memory store "We use FastAPI with PostgreSQL"

      # Memory with context
      kuzu-memory memory store "Deploy using Docker" --source deployment

      # Memory with session grouping
      kuzu-memory memory store "Bug fix completed" --session-id bug-123

      # Memory with metadata
      kuzu-memory memory store "Performance improved 40%" --metadata '{"metric": "response_time"}'

      # Custom database path
      kuzu-memory memory store "Custom location" --db-path /path/to/db
    """
    from pathlib import Path

    from kuzu_memory.cli.service_manager import ServiceManager

    try:
        # Convert db_path to Path object if provided
        db_path_obj = Path(db_path) if db_path else None

        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                rich_print(f"⚠️  Invalid JSON in metadata, ignoring: {e}", style="yellow")

        # Add CLI context
        parsed_metadata.update(
            {
                "cli_timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "agent_id": agent_id,
            }
        )

        # Use ServiceManager for memory service lifecycle
        with ServiceManager.memory_service(db_path_obj) as memory:
            memory_id = memory.remember(
                content=content,
                source=source,
                session_id=session_id,
                agent_id=agent_id,
                metadata=parsed_metadata,
            )

            rich_print(
                f"✅ Stored memory: {content[:100]}{'...' if len(content) > 100 else ''}",
                style="green",
            )
            if memory_id:
                rich_print(f"   Memory ID: {memory_id[:8]}...", style="dim")
            rich_print(f"   Source: {source}", style="dim")
            if session_id:
                rich_print(f"   Session: {session_id}", style="dim")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Memory storage failed: {e}", style="red")
        sys.exit(1)


@memory.command()
@click.argument("content", required=True)
@click.option("--source", default="ai-conversation", help="Source of the memory")
@click.option("--metadata", help="Additional metadata as JSON string")
@click.option("--quiet", is_flag=True, help="Suppress output (for scripts)")
@click.option(
    "--no-wait",
    "no_wait",
    is_flag=True,
    help="Don't wait for task completion (fire and forget)",
)
@click.option(
    "--timeout",
    default=5.0,
    type=float,
    help="Timeout for waiting on task completion (seconds)",
)
@click.pass_context
def learn(
    ctx: click.Context,
    content: str,
    source: str,
    metadata: str | None,
    quiet: bool,
    no_wait: bool,
    timeout: float,
) -> None:
    """
    🧠 Learn from content (with smart async processing).

    Stores new information in memory for future recall. By default,
    waits briefly for completion to ensure memories are stored.

    NOTE: Content must match specific patterns to be stored as memories:
    - "Remember that..." - Explicit memory instructions
    - "My name is..." - Identity information
    - "I prefer..." - User preferences
    - "We decided..." - Project decisions
    - "Always/Never..." - Patterns and rules
    - "To fix X, use Y" - Problem-solution pairs

    \b
    🎮 EXAMPLES:
      # Quick learning (waits for completion)
      kuzu-memory memory learn "Remember that the API rate limit is 1000/hour"

      # Fire and forget mode
      kuzu-memory memory learn "API rate limit is 1000/hour" --no-wait

      # User preference
      kuzu-memory memory learn "I prefer TypeScript over JavaScript for type safety"

      # Project decision
      kuzu-memory memory learn "We decided to use PostgreSQL for our database"

      # With custom timeout
      kuzu-memory memory learn "Complex content to process" --timeout 10
    """
    try:
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                if not quiet:
                    rich_print(f"⚠️  Invalid JSON in metadata, ignoring: {e}", style="yellow")

        # Add CLI context
        parsed_metadata.update({"cli_timestamp": datetime.now().isoformat(), "cli_source": source})

        # Asynchronous learning with smart waiting
        try:
            from ..async_memory.async_cli import get_async_cli

            async_cli = get_async_cli()

            # Queue the learning operation with wait by default
            result = async_cli.learn_async(
                content=content,
                source=source,
                metadata=parsed_metadata,
                quiet=quiet,
                wait_for_completion=not no_wait,
                timeout=timeout,
            )

            # Check if the operation was successful
            if result.get("status") == "completed" and not quiet:
                rich_print(
                    f"✅ Learning completed: {content[:100]}{'...' if len(content) > 100 else ''}",
                    style="green",
                )
                if "result" in result and "memories_count" in result.get("result", {}):
                    count = result["result"]["memories_count"]
                    rich_print(f"   📝 Extracted {count} memories", style="dim")
            elif result.get("status") == "queued" and not quiet:
                rich_print(
                    f"⏳ Learning queued (task {result['task_id'][:8]}...): {content[:100]}{'...' if len(content) > 100 else ''}",
                    style="yellow",
                )
                rich_print("   [i]  Task is processing in background", style="dim")
            elif result.get("status") == "failed" and not quiet:
                rich_print(f"❌ {result.get('message', 'Learning failed')}", style="red")

        except ImportError as e:
            if not quiet:
                rich_print(
                    f"⚠️  Async learning not available ({e}), falling back to sync",
                    style="yellow",
                )

            # Fallback to synchronous learning
            db_path = get_project_db_path(ctx.obj.get("project_root"))

            with KuzuMemory(db_path=db_path) as memory:
                memory_id = memory.remember(content, source=source, metadata=parsed_metadata)

                if not quiet:
                    rich_print(
                        f"✅ Learned (fallback sync): {content[:100]}{'...' if len(content) > 100 else ''}",
                        style="green",
                    )
                    if memory_id:
                        rich_print(f"   Memory ID: {memory_id[:8]}...", style="dim")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        if not quiet:
            rich_print(f"❌ Learning failed: {e}", style="red")
        sys.exit(1)


@memory.command()
@click.argument("prompt", required=True)
@click.option("--max-memories", default=10, help="Maximum number of memories to recall")
@click.option(
    "--strategy",
    default=RecallStrategy.AUTO.value,
    type=click.Choice([s.value for s in RecallStrategy]),
    help="Recall strategy to use",
)
@click.option("--session-id", help="Session ID filter")
@click.option("--agent-id", default="cli", help="Agent ID filter")
@click.option(
    "--format",
    "output_format",
    default="enhanced",
    type=click.Choice(["enhanced", "simple", OutputFormat.JSON.value, "raw"]),
    help="Output format",
)
@click.option(
    "--explain-ranking",
    is_flag=True,
    help="Show detailed ranking explanation including temporal decay",
)
@click.option("--db-path", type=click.Path(), help="Database path (overrides project default)")
@click.pass_context
def recall(
    ctx: click.Context,
    prompt: str,
    max_memories: int,
    strategy: str,
    session_id: str | None,
    agent_id: str,
    output_format: str,
    explain_ranking: bool,
    db_path: str | None,
) -> None:
    """
    🔍 Recall memories related to a topic or question.

    Searches through stored memories to find relevant information
    based on the provided prompt. Supports multiple search strategies.

    \b
    🎮 EXAMPLES:
      # Basic recall
      kuzu-memory memory recall "How do we handle authentication?"

      # Recall with specific strategy
      kuzu-memory memory recall "database setup" --strategy keyword

      # Recall from specific session
      kuzu-memory memory recall "bug fixes" --session-id bug-123

      # JSON output for scripts
      kuzu-memory memory recall "deployment process" --format json

      # Show ranking explanation
      kuzu-memory memory recall "API design" --explain-ranking
    """
    import time

    from .cli_utils import format_performance_stats

    try:
        # Resolve database path
        db_path_obj: Path | None = None
        if db_path:
            db_path_obj = Path(db_path)
        elif ctx.obj.get("project_root"):
            db_path_obj = get_project_db_path(ctx.obj["project_root"])

        # Disable git_sync for read-only recall operation (performance optimization)
        with ServiceManager.memory_service(db_path=db_path_obj, enable_git_sync=False) as memory:
            # Build filters
            filters = {}
            if session_id:
                filters["session_id"] = session_id
            if agent_id != "cli":
                filters["agent_id"] = agent_id

            # Track query performance
            start_time = time.time()
            # Recall memories using the attach_memories API
            memory_context = memory.attach_memories(
                prompt, max_memories=max_memories, strategy=strategy, **filters
            )
            memories = memory_context.memories
            query_time_ms = (time.time() - start_time) * 1000

            # Get statistics for performance display
            total_memories = memory.get_memory_count()
            db_size = memory.get_database_size()

            if not memories:
                rich_print(f"[i]  No memories found for: '{prompt}'", style="blue")
                return

            # Output results
            if output_format == "json":
                result = {
                    "prompt": prompt,
                    "strategy": strategy,
                    "memories_found": len(memories),
                    "query_time_ms": query_time_ms,
                    "total_in_database": total_memories,
                    "database_size_bytes": db_size,
                    "memories": [
                        {
                            "id": mem.id,
                            "content": mem.content,
                            "source": getattr(mem, "source_type", "unknown"),
                            "created_at": mem.created_at.isoformat(),
                            "memory_type": mem.memory_type,
                            "relevance": getattr(mem, "relevance_score", 0.0),
                        }
                        for mem in memories
                    ],
                }
                rich_print(json.dumps(result, indent=2))
            elif output_format == "raw":
                for mem in memories:
                    rich_print(mem.content)
                # Show performance stats for raw format too
                stats_result = format_performance_stats(
                    query_time_ms, total_memories, len(memories), db_size
                )
                stats_line, time_style, tip = stats_result
                rich_print(f"\n{stats_line}", style=time_style)
                if tip:
                    rich_print(tip, style="dim")
            elif output_format == "simple":
                rich_print(f"Found {len(memories)} memories for: {prompt}\n")
                for i, mem in enumerate(memories, 1):
                    rich_print(f"{i}. {mem.content}")
                    rich_print(
                        f"   Source: {getattr(mem, 'source_type', 'unknown')} | Created: {mem.created_at.strftime('%Y-%m-%d %H:%M')}"
                    )
                    if hasattr(mem, "relevance_score"):
                        rich_print(f"   Relevance: {mem.relevance_score:.3f}")
                    rich_print("")  # Empty line

                # Show performance stats
                stats_result = format_performance_stats(
                    query_time_ms, total_memories, len(memories), db_size
                )
                stats_line, time_style, tip = stats_result
                rich_print(f"\n{stats_line}", style=time_style)
                if tip:
                    rich_print(tip, style="dim")
            else:
                # Enhanced format (default)
                rich_panel(
                    f"Found {len(memories)} memories for: '{prompt}'",
                    title="🔍 Recall Results",
                    style="blue",
                )

                for i, mem in enumerate(memories, 1):
                    style = "green" if i <= 3 else "yellow" if i <= 6 else "white"

                    content_preview = mem.content[:200] + ("..." if len(mem.content) > 200 else "")
                    rich_print(f"{i}. {content_preview}", style=style)

                    # Show metadata
                    metadata_parts = [
                        f"ID: {mem.id[:8]}...",
                        f"Source: {getattr(mem, 'source_type', 'unknown')}",
                        f"Type: {mem.memory_type}",
                        f"Created: {mem.created_at.strftime('%Y-%m-%d %H:%M')}",
                    ]

                    if hasattr(mem, "relevance_score"):
                        metadata_parts.append(f"Relevance: {mem.relevance_score:.3f}")

                    rich_print(f"   {' | '.join(metadata_parts)}", style="dim")

                    # Show ranking explanation if requested
                    if explain_ranking and hasattr(mem, "ranking_explanation"):
                        rich_print(f"   🎯 Ranking: {mem.ranking_explanation}", style="cyan")

                    rich_print("")  # Empty line

                # Show performance stats after results
                stats_result = format_performance_stats(
                    query_time_ms, total_memories, len(memories), db_size
                )
                stats_line, time_style, tip = stats_result
                rich_print(f"{stats_line}", style=time_style)
                if tip:
                    rich_print(tip, style="dim")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Recall failed: {e}", style="red")
        sys.exit(1)


@memory.command()
@click.argument("prompt", required=True)
@click.option("--max-memories", default=5, help="Maximum number of memories to include")
@click.option(
    "--format",
    "output_format",
    default="context",
    type=click.Choice(["context", OutputFormat.PLAIN.value, OutputFormat.JSON.value]),
    help="Output format (context=enhanced prompt, plain=just context, json=raw)",
)
@click.option("--db-path", type=click.Path(), help="Database path (overrides project default)")
@click.pass_context
def enhance(
    ctx: click.Context,
    prompt: str,
    max_memories: int,
    output_format: str,
    db_path: str | None,
) -> None:
    """
    🚀 Enhance a prompt with relevant memory context.

    Takes a user prompt and adds relevant context from stored memories
    to improve AI responses. Perfect for AI integrations!

    \b
    🎮 EXAMPLES:
      # Basic enhancement
      kuzu-memory memory enhance "How do I deploy this application?"

      # Plain context only
      kuzu-memory memory enhance "What's our coding style?" --format plain

      # JSON output for scripts
      kuzu-memory memory enhance "Database questions" --format json
    """
    try:
        # Resolve database path
        db_path_obj: Path | None = None
        if db_path:
            db_path_obj = Path(db_path)
        elif ctx.obj.get("project_root"):
            db_path_obj = get_project_db_path(ctx.obj["project_root"])

        # Disable git_sync for read-only enhance operation (performance optimization)
        with ServiceManager.memory_service(db_path=db_path_obj, enable_git_sync=False) as memory:
            # Get relevant memories using the attach_memories API
            memory_context = memory.attach_memories(prompt, max_memories=max_memories)
            memories = memory_context.memories

            if not memories:
                if output_format == "json":
                    result = {
                        "original_prompt": memory_context.original_prompt,
                        "enhanced_prompt": memory_context.enhanced_prompt,
                        "context": "",
                        "memories_found": 0,
                        "confidence": memory_context.confidence,
                    }
                    rich_print(json.dumps(result, indent=2))
                else:
                    rich_print(f"[i]  No relevant memories found for: '{prompt}'", style="blue")
                    if output_format != "plain":
                        rich_print(memory_context.enhanced_prompt or prompt)
                return

            # Build context from memories
            context_parts = []
            for i, mem in enumerate(memories, 1):
                context_parts.append(f"{i}. {mem.content}")

            context = "\n".join(context_parts)

            if output_format == "json":
                result = {
                    "original_prompt": memory_context.original_prompt,
                    "enhanced_prompt": memory_context.enhanced_prompt,
                    "context": context,
                    "memories_found": len(memories),
                    "confidence": memory_context.confidence,
                    "memories": [
                        {
                            "id": mem.id,
                            "content": mem.content,
                            "source": getattr(mem, "source_type", "unknown"),
                            "created_at": mem.created_at.isoformat(),
                            "relevance": getattr(mem, "relevance_score", 0.0),
                        }
                        for mem in memories
                    ],
                }
                rich_print(json.dumps(result, indent=2))
            elif output_format == "plain":
                rich_print(memory_context.enhanced_prompt or context)
            else:
                # Default context format
                rich_panel(
                    f"Found {len(memories)} relevant memories:",
                    title="📚 Context",
                    style="green",
                )
                rich_print(f"\n{context}\n")
                rich_panel(
                    memory_context.enhanced_prompt or prompt,
                    title="🔍 Enhanced Prompt",
                    style="blue",
                )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Enhancement failed: {e}", style="red")
        sys.exit(1)


@memory.command()
@click.option(
    "--strategy",
    type=click.Choice(["safe", "intelligent", "aggressive"]),
    default="safe",
    help="Pruning strategy to use",
)
@click.option("--execute", is_flag=True, help="Actually prune memories (default is dry-run)")
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before pruning (default: yes)",
)
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.pass_context
def prune(
    ctx: click.Context,
    strategy: str,
    execute: bool,
    backup: bool,
    force: bool,
    db_path: str | None,
) -> None:
    """
    🧹 Prune old or low-value memories to optimize database size.

    Analyzes and optionally removes memories based on the selected strategy.
    By default runs in dry-run mode showing what would be pruned.

    \b
    🎯 STRATEGIES:
      safe        - Only old, minimal-impact git commits (>90d, <2 files or <200B)
                    Expected: ~7% reduction, very low risk
      intelligent - Value-based pruning excluding important commits
                    Expected: ~15-20% reduction, low risk
      aggressive  - Drastic pruning for critically large databases
                    Expected: ~30-50% reduction, moderate risk

    \b
    🛡️  PROTECTED MEMORIES (never pruned):
      - claude-code-hook memories
      - cli memories
      - project-initialization memories
      - Important commits (feat, fix, perf, BREAKING in intelligent/aggressive)

    \b
    🎮 EXAMPLES:
      # Dry-run with safe strategy (default)
      kuzu-memory memory prune

      # Analyze with intelligent strategy
      kuzu-memory memory prune --strategy intelligent

      # Execute pruning with backup
      kuzu-memory memory prune --strategy safe --execute

      # Execute without backup (not recommended)
      kuzu-memory memory prune --execute --no-backup --force

      # Aggressive pruning for large databases
      kuzu-memory memory prune --strategy aggressive --execute
    """
    import time
    from pathlib import Path

    from kuzu_memory.cli.service_manager import ServiceManager
    from kuzu_memory.core.prune import MemoryPruner

    try:
        # Convert db_path to Path object if provided
        db_path_obj = Path(db_path) if db_path else None

        # Use ServiceManager for memory service lifecycle (disable git sync for prune)
        with ServiceManager.memory_service(db_path_obj, enable_git_sync=False) as memory:
            # MemoryPruner needs access to underlying kuzu_memory
            # Use the kuzu_memory property exposed by MemoryService
            pruner = MemoryPruner(memory.kuzu_memory)

            # Get current database stats
            total_memories = memory.get_memory_count()
            db_size = memory.get_database_size()

            rich_print("\n📊 Analyzing memories for pruning...\n", style="blue")
            rich_print(
                f"   Database: {total_memories:,} memories, {db_size / (1024 * 1024):.1f} MB"
            )
            rich_print(f"   Strategy: {strategy}")
            rich_print(f"   Mode: {'EXECUTE' if execute else 'DRY-RUN'}\n")

            # Analyze what would be pruned
            start_time = time.time()
            stats = pruner.analyze(strategy)
            analysis_time_ms = (time.time() - start_time) * 1000

            # Display analysis results
            prune_percentage = (
                (stats.memories_to_prune / stats.total_memories * 100)
                if stats.total_memories > 0
                else 0
            )
            keep_percentage = (
                (stats.memories_to_keep / stats.total_memories * 100)
                if stats.total_memories > 0
                else 0
            )

            rich_panel(
                f"Analysis Complete ({analysis_time_ms:.0f}ms)",
                title="📋 Prune Report",
                style="green",
            )

            # Summary
            rich_print("\n🔍 Summary:", style="bold blue")
            rich_print(
                f"   Memories to prune: {stats.memories_to_prune:,} ({prune_percentage:.1f}%)",
                style="yellow",
            )
            rich_print(
                f"   Memories to keep: {stats.memories_to_keep:,} ({keep_percentage:.1f}%)",
                style="green",
            )
            rich_print(f"   Protected: {stats.protected_count:,}", style="cyan")

            # By age breakdown
            if any(stats.by_age.values()):
                rich_print("\n📅 By Age:", style="bold blue")
                for age_range, count in stats.by_age.items():
                    if count > 0:
                        rich_print(f"   {age_range}: {count:,} memories")

            # By size breakdown
            if any(stats.by_size.values()):
                rich_print("\n📏 By Size:", style="bold blue")
                for size_range, count in stats.by_size.items():
                    if count > 0:
                        rich_print(f"   {size_range}: {count:,} memories")

            # By source breakdown
            if stats.by_source:
                rich_print("\n📦 By Source:", style="bold blue")
                for source, count in sorted(
                    stats.by_source.items(), key=lambda x: x[1], reverse=True
                ):
                    rich_print(f"   {source}: {count:,} memories")

            # Savings estimate
            content_mb = stats.estimated_content_savings_bytes / (1024 * 1024)
            db_mb = stats.estimated_db_savings_bytes / (1024 * 1024)
            db_percentage = (stats.estimated_db_savings_bytes / db_size * 100) if db_size > 0 else 0

            rich_print("\n💾 Expected Savings:", style="bold blue")
            rich_print(f"   Content: {content_mb:.2f} MB")
            rich_print(f"   Database: ~{db_mb:.0f} MB (~{db_percentage:.1f}%, estimated)")

            # Execute or show dry-run message
            if execute:
                rich_print(
                    f"\n⚠️  WARNING: About to prune {stats.memories_to_prune:,} memories!",
                    style="bold red",
                )

                # Confirmation prompt unless --force
                if not force:
                    rich_print(f"\n   Strategy: {strategy}")
                    rich_print(f"   Backup: {'yes' if backup else 'NO'}")
                    confirm = click.confirm("\n   Do you want to continue?", default=False)
                    if not confirm:
                        rich_print("\n❌ Pruning cancelled by user", style="yellow")
                        return

                # Execute pruning
                rich_print("\n🚀 Executing prune...", style="blue")
                result = pruner.prune(strategy, execute=True, create_backup=backup)

                if result.success:
                    rich_print(
                        "\n✅ Pruning completed successfully!",
                        style="bold green",
                    )
                    rich_print(f"   Memories pruned: {result.memories_pruned:,}")
                    rich_print(f"   Execution time: {result.execution_time_ms:.0f}ms")
                    if result.backup_path:
                        rich_print(f"   Backup saved: {result.backup_path}")

                    # Show final stats
                    final_count = memory.get_memory_count()
                    final_size = memory.get_database_size()
                    actual_reduction = db_size - final_size
                    actual_percentage = (actual_reduction / db_size * 100) if db_size > 0 else 0

                    rich_print("\n📊 Final Database:", style="bold blue")
                    rich_print(f"   Memories: {final_count:,} (was {total_memories:,})")
                    rich_print(
                        f"   Size: {final_size / (1024 * 1024):.1f} MB (was {db_size / (1024 * 1024):.1f} MB)"
                    )
                    rich_print(
                        f"   Reduction: {actual_reduction / (1024 * 1024):.1f} MB ({actual_percentage:.1f}%)"
                    )
                else:
                    rich_print(f"\n❌ Pruning failed: {result.error}", style="red")
                    sys.exit(1)
            else:
                # Dry-run mode
                rich_print("\n⚠️  DRY RUN MODE - No changes made.", style="bold yellow")
                rich_print("   Use --execute to perform pruning.", style="dim")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Prune operation failed: {e}", style="red")
        sys.exit(1)


@memory.command()
@click.option("--limit", default=10, help="Number of recent memories to show")
@click.option(
    "--format",
    "output_format",
    default=OutputFormat.TABLE.value,
    type=click.Choice([OutputFormat.TABLE.value, OutputFormat.JSON.value, OutputFormat.LIST.value]),
    help="Output format",
)
@click.option("--db-path", type=click.Path(), help="Database path (overrides project default)")
@click.pass_context
def recent(ctx: click.Context, limit: int, output_format: str, db_path: str | None) -> None:
    """
    🕒 Show recent memories stored in the project.

    Displays the most recently stored memories to help you understand
    what information is available in your project's memory.

    \b
    🎮 EXAMPLES:
      # Show last 10 memories
      kuzu-memory memory recent

      # Show last 20 memories
      kuzu-memory memory recent --limit 20

      # JSON format for scripts
      kuzu-memory memory recent --format json

      # Simple list format
      kuzu-memory memory recent --format list
    """
    import time

    from .cli_utils import format_performance_stats

    try:
        # Resolve database path
        db_path_obj: Path | None = None
        if db_path:
            db_path_obj = Path(db_path)
        elif ctx.obj.get("project_root"):
            db_path_obj = get_project_db_path(ctx.obj["project_root"])

        # Disable git_sync for read-only recent operation (performance optimization)
        with ServiceManager.memory_service(db_path=db_path_obj, enable_git_sync=False) as memory:
            # Track query performance
            start_time = time.time()
            memories = memory.get_recent_memories(limit=limit)
            query_time_ms = (time.time() - start_time) * 1000

            # Get statistics for performance display
            total_memories = memory.get_memory_count()
            db_size = memory.get_database_size()

            if not memories:
                rich_print("[i]  No memories found in this project", style="blue")
                return

            if output_format == "json":
                result = {
                    "total_memories": len(memories),
                    "query_time_ms": query_time_ms,
                    "total_in_database": total_memories,
                    "database_size_bytes": db_size,
                    "memories": [
                        {
                            "id": mem.id,
                            "content": mem.content,
                            "source": getattr(mem, "source_type", "unknown"),
                            "memory_type": mem.memory_type,
                            "created_at": mem.created_at.isoformat(),
                        }
                        for mem in memories
                    ],
                }
                rich_print(json.dumps(result, indent=2))
            elif output_format == "list":
                rich_print(f"Recent {len(memories)} memories:\n")
                for i, mem in enumerate(memories, 1):
                    rich_print(f"{i}. {mem.content}")
                    rich_print(
                        f"   {getattr(mem, 'source_type', 'unknown')} | {mem.created_at.strftime('%Y-%m-%d %H:%M')}"
                    )
                    rich_print("")  # Empty line

                # Show performance stats
                stats_result = format_performance_stats(
                    query_time_ms, total_memories, len(memories), db_size
                )
                stats_line, time_style, tip = stats_result
                rich_print(f"\n{stats_line}", style=time_style)
                if tip:
                    rich_print(tip, style="dim")
            else:
                # Table format (default)
                rows = [
                    [
                        mem.id[:8] + "...",
                        mem.content[:80] + ("..." if len(mem.content) > 80 else ""),
                        getattr(mem, "source_type", "unknown"),
                        mem.memory_type,
                        mem.created_at.strftime("%m/%d %H:%M"),
                    ]
                    for mem in memories
                ]

                rich_table(
                    ["ID", "Content", "Source", "Type", "Created"],
                    rows,
                    title=f"🕒 Recent {len(memories)} Memories",
                )

                # Show performance stats after table
                stats_result = format_performance_stats(
                    query_time_ms, total_memories, len(memories), db_size
                )
                stats_line, time_style, tip = stats_result
                rich_print(f"\n{stats_line}", style=time_style)
                if tip:
                    rich_print(tip, style="dim")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Failed to retrieve recent memories: {e}", style="red")
        sys.exit(1)


__all__ = ["memory"]
