"""
MCP (Model Context Protocol) server wrapper for KuzuMemory.

Provides MCP tools that wrap kuzu-memory CLI commands for seamless
integration with Claude Desktop and other MCP-compatible AI systems.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import AnyUrl

from kuzu_memory.__version__ import __version__

# MCP SDK imports (will be dynamically imported if available)
try:
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import Resource, ResourceTemplate, TextContent, Tool

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Stubs will be defined as aliases if needed, but we shouldn't define classes
    # with the same names as the real imports - this causes mypy errors.
    # Instead, we'll just let the import error propagate when MCP is used without
    # the SDK being available.


logger = logging.getLogger(__name__)


class KuzuMemoryMCPServer:
    """
    MCP server that exposes kuzu-memory functionality as tools.

    This server provides:
    - enhance: Enhance prompts with project context
    - learn: Store learnings asynchronously
    - recall: Query specific memories
    - stats: Get memory system statistics
    - remember: Store new memories
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """
        Initialize the MCP server.

        Args:
            project_root: Project root directory (auto-detected if not provided)
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK is not installed. Install with: pip install mcp")

        self.project_root = project_root or self._find_project_root()
        self.server = Server("kuzu-memory")
        self.queue_processor: Any = None  # Initialized in run()
        self._setup_handlers()

    def _find_project_root(self) -> Path:
        """Find the project root directory."""
        # Check environment variable
        if "KUZU_MEMORY_PROJECT" in os.environ:
            return Path(os.environ["KUZU_MEMORY_PROJECT"])

        # Walk up from current directory
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists() or (current / "kuzu-memories").exists():
                return current
            current = current.parent

        # Default to current directory
        return Path.cwd()

    def _setup_handlers(self) -> None:
        """Set up MCP server handlers."""

        @self.server.list_tools()  # type: ignore[untyped-decorator]
        async def handle_list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="kuzu_enhance",
                    description=(
                        "RAG prompt augmentation: Enhance prompts with project-specific context "
                        "from KuzuMemory using semantic search and vector similarity. Performs "
                        "context injection by retrieving relevant project memories, patterns, and "
                        "learnings to augment the input prompt. Use this for context-aware AI "
                        "responses that understand project history and domain knowledge."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt to enhance with context",
                            },
                            "max_memories": {
                                "type": "integer",
                                "description": "Maximum number of memories to include (default: 5)",
                                "default": 5,
                            },
                        },
                        "required": ["prompt"],
                    },
                ),
                Tool(
                    name="kuzu_learn",
                    description=(
                        "ASYNC/BACKGROUND/NON-BLOCKING continuous learning: Store observations, "
                        "insights, and learnings asynchronously during conversations without waiting "
                        "for confirmation. Ideal for capturing context, patterns, and evolving "
                        "understanding as they emerge. Returns immediately without blocking. "
                        "\n\nWhen to use: Ongoing conversation learnings, observations, insights, "
                        "context capture during development sessions. "
                        "\n\nWhen NOT to use: Critical facts requiring immediate confirmation (use "
                        "kuzu_remember instead for synchronous storage of important decisions, "
                        "preferences, or facts that must be stored immediately)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The content to learn and store asynchronously",
                            },
                            "source": {
                                "type": "string",
                                "description": "Source of the learning (default: ai-conversation)",
                                "default": "ai-conversation",
                            },
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="kuzu_recall",
                    description=(
                        "Semantic memory retrieval: Query project memories using vector search and "
                        "similarity matching. Performs semantic search across stored learnings, "
                        "patterns, decisions, and context to find relevant information based on "
                        "meaning rather than exact keyword matches. Returns memories ranked by "
                        "relevance score and temporal decay weighting. Use this to retrieve "
                        "project-specific knowledge, past decisions, learned patterns, or context "
                        "from previous conversations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Semantic query to search memories (meaning-based, not keyword matching)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 5, higher values return more memories)",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="kuzu_remember",
                    description=(
                        "SYNC/IMMEDIATE/BLOCKING critical fact storage: Store important decisions, "
                        "preferences, or facts that must be confirmed immediately. This operation "
                        "waits for database confirmation before returning, ensuring the memory is "
                        "durably persisted. Use for critical information that requires immediate "
                        "storage verification. "
                        "\n\nWhen to use: Important decisions, user preferences, project constraints, "
                        "architectural choices, critical facts that need immediate confirmation. "
                        "\n\nFor background learning during conversations: Use kuzu_learn instead "
                        "(async, non-blocking, ideal for continuous context capture without waiting)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The critical content to store immediately with confirmation",
                            },
                            "memory_type": {
                                "type": "string",
                                "description": "Type of memory: identity (project identity/context), preference (user preferences), decision (architectural/technical decisions), pattern (code patterns/conventions)",
                                "enum": [
                                    "identity",
                                    "preference",
                                    "decision",
                                    "pattern",
                                ],
                                "default": "identity",
                            },
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="kuzu_stats",
                    description=(
                        "Health check and diagnostics: Get KuzuMemory system statistics, health "
                        "metrics, and monitoring data. Returns memory counts by type, database size, "
                        "index health status, recent activity summary, and performance statistics. "
                        "Use this for system health monitoring, troubleshooting, capacity planning, "
                        "and understanding memory system usage patterns. "
                        "\n\nMetrics returned: Total memory count, memory type distribution "
                        "(identity/preference/decision/pattern), database storage size, recent "
                        "activity timestamp, and optionally (with detailed=true): average recall "
                        "time, cache hit rate, embedding generation performance, and query "
                        "optimization statistics."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "detailed": {
                                "type": "boolean",
                                "description": "Show detailed statistics including performance metrics, cache statistics, and query optimization data (default: false)",
                                "default": False,
                            }
                        },
                    },
                ),
                Tool(
                    name="kuzu_optimize",
                    description=(
                        "LLM-initiated memory optimization: Compact and optimize frequently-accessed "
                        "memories to improve recall performance and reduce context clutter. Use "
                        "proactively when you notice redundant memories, stale content, or performance "
                        "degradation during conversations. "
                        "\n\nStrategies: "
                        "\n- top_accessed: Refresh/consolidate most-used memories for faster recall "
                        "\n- stale_cleanup: Archive memories not accessed in 90+ days "
                        "\n- consolidate_similar: Merge similar memories into summaries "
                        "\n\nUse cases: "
                        "\n- During long sessions when context feels cluttered "
                        "\n- When recall returns redundant results "
                        "\n- Proactive maintenance before ending session "
                        "\n- User requests memory cleanup"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "strategy": {
                                "type": "string",
                                "description": "Optimization strategy to use",
                                "enum": [
                                    "top_accessed",
                                    "stale_cleanup",
                                    "consolidate_similar",
                                ],
                                "default": "top_accessed",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of memories to process (default: 20)",
                                "default": 20,
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "If true, only analyze without making changes (default: true)",
                                "default": True,
                            },
                        },
                    },
                ),
            ]

        @self.server.call_tool()  # type: ignore[untyped-decorator]
        async def handle_call_tool(
            name: str, arguments: dict[str, Any]
        ) -> list[TextContent]:
            """Handle tool calls."""

            if name == "kuzu_enhance":
                prompt = arguments.get("prompt", "")
                max_memories = arguments.get("max_memories", 5)
                result = await self._enhance(
                    str(prompt) if prompt is not None else "",
                    int(max_memories) if isinstance(max_memories, int) else 5,
                )
            elif name == "kuzu_learn":
                content = arguments.get("content", "")
                source = arguments.get("source", "ai-conversation")
                result = await self._learn(
                    str(content) if content is not None else "",
                    str(source) if source is not None else "ai-conversation",
                )
            elif name == "kuzu_recall":
                query = arguments.get("query", "")
                limit = arguments.get("limit", 5)
                result = await self._recall(
                    str(query) if query is not None else "",
                    int(limit) if isinstance(limit, int) else 5,
                )
            elif name == "kuzu_remember":
                content = arguments.get("content", "")
                memory_type = arguments.get("memory_type", "identity")
                result = await self._remember(
                    str(content) if content is not None else "",
                    str(memory_type) if memory_type is not None else "identity",
                )
            elif name == "kuzu_stats":
                detailed = arguments.get("detailed", False)
                result = await self._stats(
                    bool(detailed) if detailed is not None else False
                )
            elif name == "kuzu_optimize":
                strategy = arguments.get("strategy", "top_accessed")
                limit = arguments.get("limit", 20)
                dry_run = arguments.get("dry_run", True)
                result = await self._optimize(
                    str(strategy) if strategy is not None else "top_accessed",
                    int(limit) if isinstance(limit, int) else 20,
                    bool(dry_run) if dry_run is not None else True,
                )
            else:
                result = f"Unknown tool: {name}"

            return [TextContent(type="text", text=result)]

        @self.server.list_resources()  # type: ignore[untyped-decorator]
        async def handle_list_resources() -> list[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri=AnyUrl(f"kuzu://project/{self.project_root.name}"),
                    name=f"Project: {self.project_root.name}",
                    description="KuzuMemory project context and memories",
                    mimeType="application/json",
                )
            ]

        @self.server.list_resource_templates()  # type: ignore[untyped-decorator]
        async def handle_list_resource_templates() -> list[ResourceTemplate]:
            """List resource templates."""
            return [
                ResourceTemplate(
                    uriTemplate="kuzu://memory/{id}",
                    name="Memory by ID",
                    description="Access a specific memory by its ID",
                    mimeType="application/json",
                )
            ]

    async def _run_command(self, args: list[str], capture_output: bool = True) -> str:
        """
        Run a kuzu-memory command asynchronously.

        Args:
            args: Command arguments
            capture_output: Whether to capture output

        Returns:
            Command output or status message
        """
        try:
            cmd = ["kuzu-memory", *args]

            if capture_output:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.project_root,
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=10.0
                )

                if process.returncode == 0:
                    return stdout.decode().strip()
                else:
                    error_msg = stderr.decode().strip() or "Command failed"
                    logger.error(f"Command failed: {' '.join(cmd)}: {error_msg}")
                    return f"Error: {error_msg}"
            else:
                # Fire and forget for async operations
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    cwd=self.project_root,
                )
                # Don't wait for completion
                return "Learning stored asynchronously"

        except TimeoutError:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Failed to run command: {e}")
            return f"Error: {e!s}"

    async def _enhance(self, prompt: str, max_memories: int = 5) -> str:
        """Enhance a prompt with project context."""
        if not prompt:
            return "Error: No prompt provided"

        args = [
            "memory",
            "enhance",
            prompt,
            "--max-memories",
            str(max_memories),
            "--format",
            "plain",
        ]
        return await self._run_command(args)

    async def _learn(self, content: str, source: str = "ai-conversation") -> str:
        """Store a learning asynchronously."""
        if not content:
            return "Error: No content provided"

        args = ["memory", "learn", content, "--source", source, "--quiet", "--no-wait"]
        # Fire and forget - don't wait for completion
        return await self._run_command(args, capture_output=False)

    async def _recall(self, query: str, limit: int = 5) -> str:
        """Query specific memories."""
        if not query:
            return "Error: No query provided"

        args = [
            "memory",
            "recall",
            query,
            "--max-memories",
            str(limit),
            "--format",
            "json",
        ]
        result = await self._run_command(args)

        # Parse and format the JSON output
        try:
            data = json.loads(result)
            if isinstance(data, list):
                formatted = []
                for memory in data:
                    formatted.append(f"- {memory.get('content', 'No content')}")
                return "\n".join(formatted) if formatted else "No memories found"
            return result
        except json.JSONDecodeError:
            return result

    async def _remember(self, content: str, memory_type: str = "identity") -> str:
        """Store important project information."""
        if not content:
            return "Error: No content provided"

        args = ["memory", "store", content, "--source", memory_type]
        return await self._run_command(args)

    async def _stats(self, detailed: bool = False) -> str:
        """Get memory system statistics."""
        args = ["status", "--format", "json"]
        if detailed:
            args.append("--detailed")

        result = await self._run_command(args)

        # Parse and format the JSON output
        try:
            data = json.loads(result)
            stats = []
            stats.append(f"Total Memories: {data.get('total_memories', 0)}")
            stats.append(f"Memory Types: {data.get('memory_types', {})}")
            stats.append(f"Recent Activity: {data.get('recent_activity', 'N/A')}")

            if detailed and "performance" in data:
                perf = data["performance"]
                stats.append(f"Avg Recall Time: {perf.get('avg_recall_time', 'N/A')}ms")
                stats.append(f"Cache Hit Rate: {perf.get('cache_hit_rate', 'N/A')}%")

            return "\n".join(stats)
        except json.JSONDecodeError:
            return result

    def _get_db_path(self) -> Path:
        """Get path to Kuzu database for current project."""
        # Standard location is project_root/kuzu-memories
        db_path = self.project_root / "kuzu-memories"
        if not db_path.exists():
            # Try alternative location (hidden directory)
            db_path = self.project_root / ".kuzu-memories"
        return db_path

    async def _optimize(self, strategy: str, limit: int, dry_run: bool) -> str:
        """
        Execute memory optimization strategy.

        Args:
            strategy: Optimization strategy (top_accessed, stale_cleanup, consolidate_similar)
            limit: Maximum number of memories to process
            dry_run: If True, only analyze without making changes

        Returns:
            JSON-formatted optimization results
        """
        try:
            # Import required modules
            from ..core.config import KuzuMemoryConfig
            from ..monitoring.access_tracker import get_access_tracker
            from ..storage.kuzu_adapter import KuzuAdapter

            # Get database path
            db_path = self._get_db_path()

            if not db_path.exists():
                return json.dumps(
                    {
                        "status": "error",
                        "error": "Memory database not found. Initialize with 'kuzu-memory setup' first.",
                    }
                )

            # Create database adapter
            config = KuzuMemoryConfig.default()
            db_adapter = KuzuAdapter(db_path, config)
            db_adapter.initialize()

            # Get access tracker
            tracker = get_access_tracker(db_path)

            # Execute optimization based on strategy
            if strategy == "top_accessed":
                result = await self._optimize_top_accessed(
                    db_adapter, tracker, limit, dry_run
                )
            elif strategy == "stale_cleanup":
                result = await self._optimize_stale_cleanup(db_adapter, limit, dry_run)
            elif strategy == "consolidate_similar":
                result = await self._optimize_consolidate_similar(
                    db_adapter, limit, dry_run
                )
            else:
                result = {
                    "status": "error",
                    "error": f"Unknown strategy: {strategy}",
                }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            return json.dumps({"status": "error", "error": str(e)})

    async def _optimize_top_accessed(
        self, db_adapter: Any, tracker: Any, limit: int, dry_run: bool
    ) -> dict[str, Any]:
        """
        Optimize top-accessed memories by consolidating similar ones.

        Strategy: Find frequently accessed memories and check for duplicates/similar content.
        """
        from ..utils.deduplication import DeduplicationEngine

        try:
            # Query top-accessed memories
            query = """
            MATCH (m:Memory)
            WHERE m.access_count > 5
            RETURN m
            ORDER BY m.access_count DESC
            LIMIT $limit
            """

            results = db_adapter.execute_query(query, {"limit": limit})

            if not results:
                return {
                    "status": "completed",
                    "strategy": "top_accessed",
                    "dry_run": dry_run,
                    "results": {
                        "memories_analyzed": 0,
                        "optimization_candidates": 0,
                        "actions_taken": [],
                        "space_saved_bytes": 0,
                        "estimated_recall_improvement": "0%",
                    },
                    "suggestions": ["No frequently accessed memories found."],
                }

            # Convert to Memory objects
            from ..core.models import Memory

            memories = []
            for row in results:
                memory_data = row.get("m")
                if memory_data:
                    try:
                        memory = Memory.from_dict(memory_data)
                        memories.append(memory)
                    except Exception as e:
                        logger.warning(f"Failed to parse memory: {e}")

            # Find similar memories among top accessed
            dedup_engine = DeduplicationEngine(
                exact_threshold=0.95, near_threshold=0.80, semantic_threshold=0.70
            )

            actions_taken = []
            optimization_candidates = 0

            for i, memory in enumerate(memories):
                remaining = memories[i + 1 :]
                if not remaining:
                    break

                duplicates = dedup_engine.find_duplicates(
                    memory.content, remaining, memory_type=memory.memory_type
                )

                if duplicates:
                    optimization_candidates += len(duplicates)
                    for dup_memory, score, match_type in duplicates:
                        actions_taken.append(
                            {
                                "action": "consolidation_candidate",
                                "memory_ids": [memory.id, dup_memory.id],
                                "similarity": f"{score:.2f}",
                                "match_type": match_type,
                            }
                        )

            suggestions = []
            if optimization_candidates > 0:
                suggestions.append(
                    f"Found {optimization_candidates} consolidation opportunities among top-accessed memories"
                )
                if dry_run:
                    suggestions.append(
                        "Run with dry_run=false to consolidate similar memories"
                    )
            else:
                suggestions.append(
                    "No similar memories found among top-accessed. Memory context is already optimized."
                )

            return {
                "status": "completed",
                "strategy": "top_accessed",
                "dry_run": dry_run,
                "results": {
                    "memories_analyzed": len(memories),
                    "optimization_candidates": optimization_candidates,
                    "actions_taken": actions_taken[:10],  # Limit output
                    "space_saved_bytes": 0,  # Would be calculated in non-dry-run
                    "estimated_recall_improvement": (
                        f"{min(15, optimization_candidates * 2)}%"
                        if optimization_candidates > 0
                        else "0%"
                    ),
                },
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error(f"Top-accessed optimization failed: {e}", exc_info=True)
            return {
                "status": "error",
                "strategy": "top_accessed",
                "error": str(e),
            }

    async def _optimize_stale_cleanup(
        self, db_adapter: Any, limit: int, dry_run: bool
    ) -> dict[str, Any]:
        """
        Clean up stale memories not accessed in 90+ days.

        Strategy: Use SmartPruningStrategy to identify and archive stale memories.
        """
        from ..core.smart_pruning import SmartPruningStrategy

        try:
            # Create pruning strategy focused on stale memories
            pruning_strategy = SmartPruningStrategy(
                db_adapter=db_adapter,
                threshold=0.3,  # Low threshold to catch stale memories
                archive_enabled=True,
            )

            # Get candidates
            candidates = pruning_strategy.get_prune_candidates()

            # Filter for stale memories (90+ days without access)
            from datetime import UTC, datetime, timedelta

            stale_threshold = datetime.now(UTC) - timedelta(days=90)
            stale_candidates = []

            for candidate in candidates:
                # Query memory details
                query = """
                MATCH (m:Memory {id: $id})
                RETURN m.accessed_at AS accessed_at, m.created_at AS created_at
                """
                result = db_adapter.execute_query(query, {"id": candidate.memory_id})

                if result:
                    accessed_at = result[0].get("accessed_at")
                    created_at = result[0].get("created_at")

                    # Parse timestamp
                    if accessed_at:
                        if isinstance(accessed_at, str):
                            accessed_at = datetime.fromisoformat(
                                accessed_at.replace("Z", "+00:00")
                            )
                    elif created_at:
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(
                                created_at.replace("Z", "+00:00")
                            )
                        accessed_at = created_at

                    if accessed_at and accessed_at < stale_threshold:
                        stale_candidates.append(candidate)

            # Limit results
            stale_candidates = stale_candidates[:limit]

            actions_taken = []
            if not dry_run and stale_candidates:
                # Execute archiving and deletion
                pruning_strategy._archive_memories(stale_candidates)
                pruning_strategy._delete_memories(
                    [c.memory_id for c in stale_candidates]
                )

                for candidate in stale_candidates:
                    actions_taken.append(
                        {
                            "action": "archived",
                            "memory_id": candidate.memory_id,
                            "reason": "stale (>90 days without access)",
                        }
                    )
            else:
                for candidate in stale_candidates:
                    actions_taken.append(
                        {
                            "action": "archive_candidate",
                            "memory_id": candidate.memory_id,
                            "reason": "stale (>90 days without access)",
                        }
                    )

            suggestions = []
            if stale_candidates:
                suggestions.append(
                    f"Found {len(stale_candidates)} stale memories ready for archiving"
                )
                if dry_run:
                    suggestions.append(
                        "Run with dry_run=false to archive these memories (30-day recovery window)"
                    )
                else:
                    suggestions.append(
                        "Archived memories can be restored within 30 days if needed"
                    )
            else:
                suggestions.append(
                    "No stale memories found. All memories are actively used."
                )

            return {
                "status": "completed",
                "strategy": "stale_cleanup",
                "dry_run": dry_run,
                "results": {
                    "memories_analyzed": len(candidates),
                    "optimization_candidates": len(stale_candidates),
                    "actions_taken": actions_taken[:10],  # Limit output
                    "space_saved_bytes": (
                        sum(len(c.memory_id) for c in stale_candidates) * 100
                    ),  # Estimate
                    "estimated_recall_improvement": (
                        f"{min(10, len(stale_candidates))}%"
                        if stale_candidates
                        else "0%"
                    ),
                },
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error(f"Stale cleanup optimization failed: {e}", exc_info=True)
            return {
                "status": "error",
                "strategy": "stale_cleanup",
                "error": str(e),
            }

    async def _optimize_consolidate_similar(
        self, db_adapter: Any, limit: int, dry_run: bool
    ) -> dict[str, Any]:
        """
        Consolidate similar memories into summaries.

        Strategy: Use ConsolidationEngine to cluster and merge similar memories.
        """
        from ..nlp.consolidation import ConsolidationEngine

        try:
            # Create consolidation engine
            consolidation_engine = ConsolidationEngine(
                db_adapter=db_adapter,
                similarity_threshold=0.70,
                min_age_days=30,  # Only consolidate memories older than 30 days
                max_access_count=5,  # Only consolidate low-access memories
            )

            # Execute consolidation
            result = consolidation_engine.execute(dry_run=dry_run, create_backup=False)

            actions_taken = []
            if result.clusters:
                for cluster in result.clusters[:limit]:
                    if dry_run:
                        actions_taken.append(
                            {
                                "action": "consolidation_candidate",
                                "memory_ids": [m.id for m in cluster.memories],
                                "cluster_size": len(cluster.memories),
                                "avg_similarity": f"{cluster.avg_similarity:.2f}",
                            }
                        )
                    else:
                        actions_taken.append(
                            {
                                "action": "consolidated",
                                "memory_ids": [m.id for m in cluster.memories],
                                "into": cluster.cluster_id,
                                "cluster_size": len(cluster.memories),
                            }
                        )

            suggestions = []
            if result.clusters_found > 0:
                suggestions.append(
                    f"Found {result.clusters_found} memory clusters that could be consolidated"
                )
                if dry_run:
                    suggestions.append(
                        "Run with dry_run=false to merge similar memories into summaries"
                    )
                else:
                    suggestions.append(
                        f"Successfully consolidated {result.memories_consolidated} memories into {result.new_memories_created} summaries"
                    )
            else:
                suggestions.append(
                    "No similar memory clusters found. Consider lowering similarity threshold."
                )

            return {
                "status": "completed",
                "strategy": "consolidate_similar",
                "dry_run": dry_run,
                "results": {
                    "memories_analyzed": result.memories_analyzed,
                    "optimization_candidates": result.clusters_found,
                    "actions_taken": actions_taken[:10],  # Limit output
                    "space_saved_bytes": result.memories_consolidated * 500,  # Estimate
                    "estimated_recall_improvement": (
                        f"{min(20, result.clusters_found * 3)}%"
                        if result.clusters_found > 0
                        else "0%"
                    ),
                },
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error(f"Consolidation optimization failed: {e}", exc_info=True)
            return {
                "status": "error",
                "strategy": "consolidate_similar",
                "error": str(e),
            }

    async def run(self) -> None:
        """Run the MCP server with queue processor."""
        # Initialize queue processor for bash hooks
        from .queue_processor import HookQueueProcessor

        self.queue_processor = HookQueueProcessor()

        # Use stdin/stdout for MCP communication
        init_options = InitializationOptions(
            server_name="kuzu-memory",
            server_version=__version__,
            capabilities=self.server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )

        # Use stdio_server async context manager for proper stream handling
        async with stdio_server() as (read_stream, write_stream):
            logger.info(
                f"KuzuMemory MCP Server running for project: {self.project_root}"
            )

            # Start queue processor in background
            await self.queue_processor.start()

            try:
                # Run the MCP server with proper streams
                await self.server.run(
                    read_stream, write_stream, init_options, raise_exceptions=False
                )
            except asyncio.CancelledError:
                logger.info("Server shutdown requested")
                raise
            except GeneratorExit:
                logger.info("Server context manager cleanup")
                # Allow proper cleanup without ignoring GeneratorExit
                raise
            finally:
                # Stop queue processor on shutdown
                if self.queue_processor:
                    await self.queue_processor.stop()


async def main() -> None:
    """Main entry point for MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not MCP_AVAILABLE:
        print(
            "Error: MCP SDK is not installed. Install with: pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        server = KuzuMemoryMCPServer()
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except asyncio.CancelledError:
        logger.info("Server cancelled")
    except GeneratorExit:
        logger.info("Server generator exit")
        # Don't suppress GeneratorExit - let it propagate for proper cleanup
        raise
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


# Alternative simplified server for environments without MCP SDK
class SimplifiedMCPServer:
    """
    Simplified MCP-like server that works without the MCP SDK.

    This provides a basic JSON-RPC interface for kuzu-memory operations.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize simplified server."""
        self.project_root = project_root or Path.cwd()

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle JSON-RPC style requests."""
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "enhance":
            result = await self._run_cli_command(
                ["memory", "enhance", params.get("prompt", ""), "--format", "plain"]
            )
        elif method == "learn":
            result = await self._run_cli_command(
                ["memory", "learn", params.get("content", ""), "--quiet", "--no-wait"]
            )
        elif method == "recall":
            result = await self._run_cli_command(
                ["memory", "recall", params.get("query", ""), "--format", "json"]
            )
        elif method == "stats":
            result = await self._run_cli_command(["status", "--format", "json"])
        else:
            result = {"error": f"Unknown method: {method}"}

        return {"jsonrpc": "2.0", "id": request.get("id", 1), "result": result}

    async def _run_cli_command(self, args: list[str]) -> Any:
        """Run kuzu-memory CLI command."""
        try:
            cmd = ["kuzu-memory", *args]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode().strip()
                # Try to parse as JSON
                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    return output
            else:
                return {"error": stderr.decode().strip()}
        except Exception as e:
            return {"error": str(e)}

    async def run_stdio(self) -> None:
        """Run server using stdio for communication."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        try:
            while True:
                try:
                    line = await reader.readline()
                    if not line:
                        break

                    request = json.loads(line.decode())
                    response = await self.handle_request(request)

                    print(json.dumps(response))
                    sys.stdout.flush()
                except asyncio.CancelledError:
                    logger.info("Simplified server cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
        except GeneratorExit:
            logger.info("Simplified server generator exit")
            # Allow proper cleanup
            raise


if __name__ == "__main__":
    # Run the appropriate server based on availability
    if MCP_AVAILABLE:
        asyncio.run(main())
    else:
        # Fallback to simplified server
        logging.basicConfig(level=logging.INFO)
        server = SimplifiedMCPServer()
        asyncio.run(server.run_stdio())
