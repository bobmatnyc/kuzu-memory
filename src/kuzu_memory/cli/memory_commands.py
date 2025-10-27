"""
Memory-related CLI commands for KuzuMemory.

Contains memory command group with subcommands for store, learn, recall, enhance operations.
"""

import json
import logging
import sys
from datetime import datetime

import click

from ..core.memory import KuzuMemory
from ..utils.project_setup import get_project_db_path
from .cli_utils import rich_panel, rich_print, rich_table
from .enums import OutputFormat, RecallStrategy

logger = logging.getLogger(__name__)


@click.group()
def memory():
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
@click.pass_context
def store(ctx, content, source, session_id, agent_id, metadata):
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
    """
    try:
        db_path = get_project_db_path(ctx.obj.get("project_root"))

        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                rich_print(
                    f"⚠️  Invalid JSON in metadata, ignoring: {e}", style="yellow"
                )

        # Add CLI context
        parsed_metadata.update(
            {
                "cli_timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "agent_id": agent_id,
            }
        )

        with KuzuMemory(db_path=db_path) as memory:
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
def learn(ctx, content, source, metadata, quiet, no_wait, timeout):
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
                    rich_print(
                        f"⚠️  Invalid JSON in metadata, ignoring: {e}", style="yellow"
                    )

        # Add CLI context
        parsed_metadata.update(
            {"cli_timestamp": datetime.now().isoformat(), "cli_source": source}
        )

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
                rich_print(
                    f"❌ {result.get('message', 'Learning failed')}", style="red"
                )

        except ImportError as e:
            if not quiet:
                rich_print(
                    f"⚠️  Async learning not available ({e}), falling back to sync",
                    style="yellow",
                )

            # Fallback to synchronous learning
            db_path = get_project_db_path(ctx.obj.get("project_root"))

            with KuzuMemory(db_path=db_path) as memory:
                memory_id = memory.remember(
                    content, source=source, metadata=parsed_metadata
                )

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
    try:
        db_path = get_project_db_path(ctx.obj.get("project_root"))

        with KuzuMemory(db_path=db_path) as memory:
            # Build filters
            filters = {}
            if session_id:
                filters["session_id"] = session_id
            if agent_id != "cli":
                filters["agent_id"] = agent_id

            # Recall memories using the attach_memories API
            memory_context = memory.attach_memories(
                prompt, max_memories=max_memories, strategy=strategy, **filters
            )
            memories = memory_context.memories

            if not memories:
                rich_print(f"[i]  No memories found for: '{prompt}'", style="blue")
                return

            # Output results
            if output_format == "json":
                result = {
                    "prompt": prompt,
                    "strategy": strategy,
                    "memories_found": len(memories),
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
            else:
                # Enhanced format (default)
                rich_panel(
                    f"Found {len(memories)} memories for: '{prompt}'",
                    title="🔍 Recall Results",
                    style="blue",
                )

                for i, mem in enumerate(memories, 1):
                    style = "green" if i <= 3 else "yellow" if i <= 6 else "white"

                    content_preview = mem.content[:200] + (
                        "..." if len(mem.content) > 200 else ""
                    )
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
                        rich_print(
                            f"   🎯 Ranking: {mem.ranking_explanation}", style="cyan"
                        )

                    rich_print("")  # Empty line

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
@click.pass_context
def enhance(ctx, prompt, max_memories, output_format):
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
        db_path = get_project_db_path(ctx.obj.get("project_root"))

        with KuzuMemory(db_path=db_path) as memory:
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
                    rich_print(
                        f"[i]  No relevant memories found for: '{prompt}'", style="blue"
                    )
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
@click.option("--limit", default=10, help="Number of recent memories to show")
@click.option(
    "--format",
    "output_format",
    default=OutputFormat.TABLE.value,
    type=click.Choice(
        [OutputFormat.TABLE.value, OutputFormat.JSON.value, OutputFormat.LIST.value]
    ),
    help="Output format",
)
@click.pass_context
def recent(ctx, limit, output_format):
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
    try:
        db_path = get_project_db_path(ctx.obj.get("project_root"))

        with KuzuMemory(db_path=db_path) as memory:
            memories = memory.get_recent_memories(limit=limit)

            if not memories:
                rich_print("[i]  No memories found in this project", style="blue")
                return

            if output_format == "json":
                result = {
                    "total_memories": len(memories),
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

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Failed to retrieve recent memories: {e}", style="red")
        sys.exit(1)


__all__ = ["memory"]
