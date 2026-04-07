"""
Memory recall coordinator for KuzuMemory.

Coordinates multiple recall strategies, ranks results, and builds
the final MemoryContext for the attach_memories() method.
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from ..core.config import KuzuMemoryConfig
from ..core.models import KnowledgeType, Memory, MemoryContext, MemoryType
from ..enrichment.hnsw_index import HNSW_INDEX_NAME
from ..storage.cache import MemoryCache
from ..storage.kuzu_adapter import KuzuAdapter
from ..utils.exceptions import PerformanceError, RecallError
from ..utils.validation import validate_text_input
from .strategies import (
    EntityRecallStrategy,
    GraphRelatedRecallStrategy,
    KeywordRecallStrategy,
    TemporalRecallStrategy,
)
from .temporal_decay import TemporalDecayEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Semantic scoring helper
# ---------------------------------------------------------------------------

try:
    from sentence_transformers import SentenceTransformer

    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc,unused-ignore]
    _SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.debug(
        "sentence-transformers not available; semantic search will fall back to Jaccard scoring"
    )


class _SemanticScorer:
    """
    Thin wrapper around SentenceTransformer for in-process cosine similarity.

    Lazily initialises the model on first use so that importing this module
    does not trigger a heavy model load.  A module-level singleton is reused
    across all RecallCoordinator instances so the model is only loaded once
    per process.

    Falls back gracefully to returning ``None`` when sentence-transformers is
    unavailable, allowing callers to fall back to Jaccard scoring.
    """

    _instance: _SemanticScorer | None = None  # module-level singleton
    _model: Any  # SentenceTransformer | None
    # In-process embedding cache: content -> np.ndarray
    _cache: dict[str, Any]

    def __init__(self) -> None:
        self._model = None
        self._cache: dict[str, Any] = {}

    @classmethod
    def get(cls) -> _SemanticScorer:
        """Return (and lazily create) the module-level singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_model(self) -> bool:
        """Load the model if not already loaded. Returns True on success."""
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            return False
        if self._model is None:
            try:
                self._model = SentenceTransformer("all-MiniLM-L6-v2")  # type: ignore[misc,unused-ignore]
                logger.debug("Loaded SentenceTransformer model for semantic recall")
            except Exception as exc:
                logger.warning("Failed to load SentenceTransformer model: %s", exc)
                return False
        return True

    def embed(self, text: str) -> Any | None:
        """
        Return a unit-norm numpy embedding for *text*, or ``None`` on failure.

        Results are cached by exact text so repeated calls within the same
        recall session are free.
        """
        if not self._ensure_model():
            return None
        if text in self._cache:
            return self._cache[text]
        try:
            import numpy as np

            vec = self._model.encode(text, normalize_embeddings=True)
            arr: Any = np.asarray(vec, dtype=np.float32)
            self._cache[text] = arr
            return arr
        except Exception as exc:
            logger.warning("Embedding failed for text: %s", exc)
            return None

    def cosine(self, a: Any, b: Any) -> float:
        """
        Cosine similarity between two *already-normalised* vectors.

        Both vectors are assumed to have unit L2 norm (produced by
        ``encode(normalize_embeddings=True)``), so the similarity is just the
        dot product, clamped to [0, 1].
        """
        import numpy as np

        result: float = float(np.dot(a, b))
        return max(0.0, min(1.0, result))


class RecallCoordinator:
    """
    Coordinates multiple recall strategies to find the most relevant memories.

    Implements the core logic for attach_memories() with strategy selection,
    result ranking, and performance optimization.
    """

    def __init__(self, db_adapter: KuzuAdapter, config: KuzuMemoryConfig) -> None:
        """
        Initialize recall coordinator.

        Args:
            db_adapter: Database adapter for queries
            config: Configuration object
        """
        self.db_adapter = db_adapter
        self.config = config

        # Temporal decay engine — used only when apply_temporal_decay=True
        self._temporal_decay_engine = TemporalDecayEngine()

        # Semantic scorer — used only when use_semantic_search=True (MCP paths only)
        self._semantic_scorer = _SemanticScorer.get()

        # Initialize recall strategies
        self.strategies = {
            "keyword": KeywordRecallStrategy(db_adapter, config),
            "entity": EntityRecallStrategy(db_adapter, config),
            "temporal": TemporalRecallStrategy(db_adapter, config),
            "graph_related": GraphRelatedRecallStrategy(db_adapter, config),
        }

        # Initialize cache
        self.cache = (
            MemoryCache(
                maxsize=config.recall.cache_size,
                ttl_seconds=config.recall.cache_ttl_seconds,
            )
            if config.recall.enable_caching
            else None
        )

        # Statistics
        self._coordinator_stats: dict[str, Any] = {
            "total_recalls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "strategy_usage": defaultdict(int),
            "avg_recall_time_ms": 0.0,
        }

    def attach_memories(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto",
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
        apply_temporal_decay: bool = False,
        use_semantic_search: bool = False,
    ) -> MemoryContext:
        """
        Attach relevant memories to a prompt.

        Args:
            prompt: User prompt to find memories for
            max_memories: Maximum number of memories to return
            strategy: Recall strategy to use ('auto', 'keyword', 'entity', 'temporal')
            user_id: Optional user ID filter
            session_id: Optional session ID filter
            agent_id: Agent ID filter
            apply_temporal_decay: When True, multiplies relevance scores by a temporal
                decay factor so that recent memories rank higher than old ones.
                Must be False for hook-triggered recall paths (pure graph traversal,
                no scoring overhead). Defaults to False.
            use_semantic_search: When True, replaces Jaccard word-overlap scoring with
                cosine similarity from sentence-transformers embeddings.  Must be False
                for hook-triggered recall paths (pure graph traversal, no model overhead).
                Falls back to Jaccard scoring when sentence-transformers is unavailable.
                Defaults to False.

        Returns:
            MemoryContext with enhanced prompt and relevant memories

        Raises:
            RecallError: If recall fails
            PerformanceError: If operation exceeds time limit
        """
        start_time = time.time()

        try:
            # Validate input
            clean_prompt = validate_text_input(prompt, "attach_memories_prompt")

            # Check cache first
            if self.cache:
                cached_context = self.cache.get_recall_result(clean_prompt, strategy, max_memories)
                if cached_context:
                    self._coordinator_stats["cache_hits"] += 1
                    return cached_context
                else:
                    self._coordinator_stats["cache_misses"] += 1

            # When semantic search is enabled (MCP path only), attempt to use the
            # Kùzu native HNSW vector index.  On success the HNSW candidates are
            # merged with graph-strategy candidates so structural signals (entity
            # matches, temporal decay) can still influence the final ranking.
            # On failure (index absent, column missing, model unavailable) we fall
            # through to the pure graph-strategy path transparently.
            hnsw_memories: list[Memory] | None = None
            if use_semantic_search:
                hnsw_memories = self._recall_with_hnsw(clean_prompt, max_memories)

            # Execute recall strategy
            if strategy == "auto":
                memories = self._auto_recall(
                    clean_prompt,
                    max_memories,
                    user_id,
                    session_id,
                    agent_id,
                    use_semantic_search=use_semantic_search,
                )
                strategy_used = "auto"
            else:
                memories = self._single_strategy_recall(
                    strategy, clean_prompt, max_memories, user_id, session_id, agent_id
                )
                strategy_used = strategy

            # Merge HNSW candidates into the graph-strategy candidates so the
            # ranking layer sees both.  HNSW results are inserted at the front
            # so they are not dropped when deduplication runs; duplicates by ID
            # are removed inside _rank_memories.
            if hnsw_memories:
                memories = hnsw_memories + memories
                strategy_used = f"{strategy_used}+hnsw"

            # Rank and filter memories
            ranked_memories = self._rank_memories(
                memories,
                clean_prompt,
                apply_temporal_decay=apply_temporal_decay,
                use_semantic_search=use_semantic_search,
            )
            final_memories = ranked_memories[:max_memories]

            # Track memory access for analytics (zero-latency)
            if final_memories and self.config.analytics.enabled:
                from ..monitoring.access_tracker import get_access_tracker

                tracker = get_access_tracker(self.db_adapter.db_path)
                tracker.track_batch([m.id for m in final_memories], context="recall")

            # Calculate confidence score
            confidence = self._calculate_confidence(final_memories, clean_prompt)

            # Build enhanced prompt
            enhanced_prompt = self._build_enhanced_prompt(clean_prompt, final_memories)

            # Create memory context
            context = MemoryContext(
                original_prompt=clean_prompt,
                enhanced_prompt=enhanced_prompt,
                memories=final_memories,
                confidence=confidence,
                strategy_used=strategy_used,
                recall_time_ms=(time.time() - start_time) * 1000,
                total_memories_found=len(memories),
                memories_filtered=len(memories) - len(final_memories),
            )

            # Cache the result
            if self.cache:
                self.cache.put_recall_result(clean_prompt, strategy, max_memories, context)

            # Update statistics
            self._update_coordinator_stats(strategy_used, context.recall_time_ms)

            # Check performance requirement — warn only, never discard valid results
            if (
                self.config.performance.enable_performance_monitoring
                and context.recall_time_ms > self.config.performance.max_recall_time_ms
            ):
                logger.warning(
                    "attach_memories exceeded performance threshold: "
                    f"{context.recall_time_ms:.1f}ms > "
                    f"{self.config.performance.max_recall_time_ms:.0f}ms "
                    "(results returned)"
                )

            logger.debug(
                f"Recalled {len(final_memories)} memories in {context.recall_time_ms:.1f}ms"
            )

            return context

        except Exception as e:
            if isinstance(e, RecallError | PerformanceError):
                raise
            raise RecallError(f"Recall failed for prompt '{prompt}': {e!s}")

    def _auto_recall(
        self,
        prompt: str,
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
        use_semantic_search: bool = False,
    ) -> list[Memory]:
        """Execute automatic strategy selection and combination.

        When ``use_semantic_search=True`` the ``graph_related`` strategy is
        skipped because the HNSW index already surfaces semantically related
        memories — running graph traversal on top would produce redundant results
        with higher latency.
        """
        all_memories = []
        strategy_weights = self.config.recall.strategy_weights

        # Build the effective strategy list for this call.
        # graph_related runs only on graph-only paths (HNSW inactive).
        effective_strategies = list(self.config.recall.strategies)
        if not use_semantic_search and "graph_related" not in effective_strategies:
            # Append graph_related after entity so it has seeds to traverse.
            # Insert after "entity" if present, otherwise append at end.
            try:
                insert_pos = effective_strategies.index("entity") + 1
            except ValueError:
                insert_pos = len(effective_strategies)
            effective_strategies.insert(insert_pos, "graph_related")

        # Run all enabled strategies
        for strategy_name in effective_strategies:
            # Skip graph_related when HNSW is active (redundant + slower).
            if strategy_name == "graph_related" and use_semantic_search:
                continue
            if strategy_name in self.strategies:
                try:
                    strategy_memories = self.strategies[strategy_name].recall(
                        prompt,
                        max_memories * 2,  # Get more to allow for ranking
                        user_id,
                        session_id,
                        agent_id,
                    )

                    # Weight memories based on strategy confidence
                    weight = strategy_weights.get(strategy_name, 1.0)
                    for memory in strategy_memories:
                        memory.confidence *= weight

                    all_memories.extend(strategy_memories)

                except Exception as e:
                    logger.warning(f"Strategy {strategy_name} failed: {e}")
                    continue

        return all_memories

    def _single_strategy_recall(
        self,
        strategy_name: str,
        prompt: str,
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> list[Memory]:
        """Execute a single recall strategy."""

        if strategy_name not in self.strategies:
            raise RecallError(
                f"Unknown recall strategy: {strategy_name}",
                context={
                    "prompt": prompt,
                    "strategy": strategy_name,
                    "available_strategies": list(self.strategies.keys()),
                },
            )

        return self.strategies[strategy_name].recall(
            prompt, max_memories, user_id, session_id, agent_id
        )

    def _recall_with_hnsw(self, query: str, limit: int) -> list[Memory] | None:
        """Query the Kùzu native HNSW vector index for approximate nearest neighbours.

        Replaces the brute-force O(N) NumPy cosine scan with an O(log N) index
        look-up when the index is available and the embedding column is populated.

        This method is MCP path ONLY (called only when use_semantic_search=True).
        Hooks must never reach this code path.

        Kùzu 0.11.3 confirmed QUERY_VECTOR_INDEX syntax::

            CALL QUERY_VECTOR_INDEX("Memory", "memory_hnsw_idx", $embedding, $k)
            RETURN node, distance

        Args:
            query: The recall prompt text to embed and search with.
            limit: Maximum number of candidates to return (we over-fetch by 2x
                   to give the ranking layer enough material).

        Returns:
            List of Memory objects sorted by ascending HNSW distance (most similar
            first), or ``None`` if HNSW is unavailable / fails (signals fallback).
        """
        query_emb = self._semantic_scorer.embed(query)
        if query_emb is None:
            # sentence-transformers not available — signal fallback.
            return None

        try:
            result_rows = self.db_adapter.execute_query(
                f'CALL QUERY_VECTOR_INDEX("Memory", "{HNSW_INDEX_NAME}", $embedding, $k) '
                "RETURN node, distance",
                parameters={"embedding": query_emb.tolist(), "k": limit * 2},
            )
        except Exception as exc:
            # Index absent, column missing, or any other HNSW error → fallback.
            logger.debug("_recall_with_hnsw: HNSW query failed, will fall back to NumPy: %s", exc)
            return None

        if not result_rows:
            return []

        memories: list[Memory] = []
        for row in result_rows:
            node_data = row.get("node")
            if node_data is None:
                continue
            try:
                memory = Memory.from_dict(node_data)
                memories.append(memory)
            except Exception as parse_exc:
                logger.debug("_recall_with_hnsw: failed to parse node: %s", parse_exc)

        return memories

    def _rank_memories(
        self,
        memories: list[Memory],
        prompt: str,
        apply_temporal_decay: bool = False,
        use_semantic_search: bool = False,
    ) -> list[Memory]:
        """
        Rank memories by relevance to the prompt.

        Args:
            memories: List of memories to rank
            prompt: Original prompt for relevance scoring
            apply_temporal_decay: When True, multiplies each relevance score by the
                temporal decay factor from TemporalDecayEngine so that recent memories
                rank higher than old ones.  Must remain False for hook-triggered paths.
            use_semantic_search: When True, uses cosine similarity from
                sentence-transformers embeddings as the primary relevance signal.
                Falls back to Jaccard scoring when sentence-transformers is
                unavailable.  Must remain False for hook-triggered paths.

        Returns:
            Ranked list of memories
        """
        if not memories:
            return []

        # Remove duplicates by ID
        unique_memories = {}
        for memory in memories:
            if memory.id not in unique_memories:
                unique_memories[memory.id] = memory
            else:
                # Keep the one with higher confidence
                if memory.confidence > unique_memories[memory.id].confidence:
                    unique_memories[memory.id] = memory

        memories = list(unique_memories.values())

        # Pre-compute query embedding once when semantic search is requested.
        # If the model is unavailable, query_emb is None and we fall back to Jaccard.
        query_emb: Any = None
        if use_semantic_search:
            query_emb = self._semantic_scorer.embed(prompt)
            if query_emb is None:
                logger.debug(
                    "Semantic search requested but embedding unavailable; "
                    "falling back to Jaccard scoring"
                )

        # Calculate relevance scores
        scored_memories = []
        prompt_lower = prompt.lower()

        for memory in memories:
            if query_emb is not None:
                # Semantic path: cosine similarity is the primary signal.
                # We still blend in importance/confidence/type weights so that
                # high-importance memories get a small boost when similarity is tied.
                mem_emb = self._semantic_scorer.embed(memory.content)
                if mem_emb is not None:
                    semantic_sim = self._semantic_scorer.cosine(query_emb, mem_emb)
                    # Blend: 70% semantic similarity + 30% structural score
                    structural = (
                        memory.importance * 0.15
                        + memory.confidence * 0.10
                        + self._type_boost(memory) * 0.05
                    )
                    score = semantic_sim * 0.70 + structural
                else:
                    # Embedding failed for this particular memory — fall back
                    score = self._calculate_relevance_score(memory, prompt_lower)
            else:
                # Jaccard path (default, or fallback when model unavailable)
                score = self._calculate_relevance_score(memory, prompt_lower)

            if apply_temporal_decay:
                # Multiply by decay factor: recent = ~1.0, very old = ~0.1
                decay = self._temporal_decay_engine.calculate_temporal_score(memory)
                score = score * decay

            scored_memories.append((memory, score))

        # Sort by score (highest first)
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        return [memory for memory, _ in scored_memories]

    def _type_boost(self, memory: Memory) -> float:
        """Return the memory-type boost factor for a single memory (0-1 scale)."""
        type_boosts = {
            MemoryType.SEMANTIC: 0.9,
            MemoryType.PREFERENCE: 0.8,
            MemoryType.EPISODIC: 0.7,
            MemoryType.PROCEDURAL: 0.8,
            MemoryType.WORKING: 0.3,
            MemoryType.SENSORY: 0.4,
        }
        return type_boosts.get(memory.memory_type, 0.5)

    def _knowledge_type_boost(self, memory: Memory) -> float:
        """Return a boost based on the memory's knowledge_type field.

        Higher-signal knowledge types (rules, gotchas, architecture) receive
        larger boosts so they surface above generic notes during graph-only recall.
        Uses getattr() with a default so memories lacking the attribute degrade
        gracefully to 0.0 rather than raising AttributeError.

        Returns:
            Boost value in range [0.0, 0.25].
        """
        knowledge_type_boosts: dict[KnowledgeType, float] = {
            KnowledgeType.RULE: 0.25,
            KnowledgeType.GOTCHA: 0.20,
            KnowledgeType.ARCHITECTURE: 0.20,
            KnowledgeType.PATTERN: 0.15,
            KnowledgeType.CONVENTION: 0.10,
            KnowledgeType.NOTE: 0.00,
        }
        kt = getattr(memory, "knowledge_type", None)
        return knowledge_type_boosts.get(kt, 0.0)  # type: ignore[arg-type]

    def _access_count_boost(self, memory: Memory) -> float:
        """Return a log-scaled boost based on the memory's access_count field.

        Memories that have been frequently retrieved are likely more useful.
        The boost is capped at 0.15 to avoid overwhelming other scoring factors.
        Uses getattr() with a default of 0 so memories lacking the attribute
        degrade gracefully.

        Returns:
            Boost value in range [0.0, 0.15].
        """
        count = getattr(memory, "access_count", 0) or 0
        return min(0.15, math.log1p(count) * 0.05)

    def _graph_score_boost(self, memory: Memory) -> float:
        """Return a boost derived from the memory's graph_score centrality value.

        ``graph_score`` is populated by :class:`~kuzu_memory.enrichment.CentralityEnricher`
        and represents a normalised in-degree proxy (entity-mention count).
        Memories with many entity connections are more likely to be relevant
        and receive up to a 0.10 boost.

        Uses ``getattr()`` with a default of ``None`` so memories that were
        stored before the enricher ran degrade gracefully to 0.0.

        Returns:
            Boost value in range [0.0, 0.10].
        """
        score = getattr(memory, "graph_score", None)
        if score is None:
            return 0.0
        return min(0.10, float(score) * 0.10)

    def _calculate_relevance_score(self, memory: Memory, prompt_lower: str) -> float:
        """Calculate relevance score for a memory given the prompt.

        Scoring breakdown (approximate weights at 1.0 cap):
        - importance:       0.25  (was 0.30; reduced slightly to make room)
        - confidence:       0.15  (was 0.20; reduced slightly)
        - memory_type:      0.15
        - content overlap:  0.25
        - entity match:     0.10 per hit (capped by overall 1.0 ceiling)
        - recency:          0.08
        - knowledge_type:   0.00-0.25 additive boost
        - access_count:     0.00-0.15 additive boost
        """
        score = 0.0

        # Base score from memory importance and confidence
        score += memory.importance * 0.25
        score += memory.confidence * 0.15

        # Boost score for memory type relevance
        type_boosts = {
            MemoryType.SEMANTIC: 0.9,  # Facts/knowledge (was IDENTITY)
            MemoryType.PREFERENCE: 0.8,
            MemoryType.EPISODIC: 0.7,  # Events/experiences (was DECISION)
            MemoryType.PROCEDURAL: 0.8,  # Instructions/how-to (was PATTERN/SOLUTION)
            MemoryType.WORKING: 0.3,  # Current tasks (was STATUS)
            MemoryType.SENSORY: 0.4,  # Sensory descriptions
        }
        score += type_boosts.get(memory.memory_type, 0.5) * 0.15

        # Boost score for content similarity
        memory_content_lower = memory.content.lower()

        # Simple word overlap scoring
        prompt_words = set(prompt_lower.split())
        memory_words = set(memory_content_lower.split())

        if prompt_words and memory_words:
            overlap = len(prompt_words.intersection(memory_words))
            union = len(prompt_words.union(memory_words))
            similarity = overlap / union if union > 0 else 0
            score += similarity * 0.25

        # Boost for entity matches
        if memory.entities:
            for entity in memory.entities:
                # Handle both string and dict entity types
                entity_str = entity if isinstance(entity, str) else str(entity.get("name", ""))
                if entity_str.lower() in prompt_lower:
                    score += 0.1

        # Recency boost (more recent memories get slight boost)
        days_old = (datetime.now() - memory.created_at).days
        recency_boost = max(0, (30 - days_old) / 30) * 0.08
        score += recency_boost

        # Knowledge-type boost: rules/gotchas/architecture rank above generic notes.
        # Accounts for ~0-15% of the final score when other factors are average.
        score += self._knowledge_type_boost(memory)

        # Access-count boost: frequently-retrieved memories are more useful.
        # Log-scaled and capped at 0.15 to prevent dominating other signals.
        score += self._access_count_boost(memory)

        # Graph-score boost: memories with high entity centrality are better connected.
        # Populated by CentralityEnricher; degrades gracefully to 0.0 when absent.
        score += self._graph_score_boost(memory)

        return min(score, 1.0)  # Cap at 1.0

    def _calculate_confidence(self, memories: list[Memory], prompt: str) -> float:
        """Calculate overall confidence score for the recall result."""
        if not memories:
            return 0.0

        # Average confidence of selected memories
        avg_confidence = sum(memory.confidence for memory in memories) / len(memories)

        # Boost confidence if we have high-importance memories
        importance_boost = sum(memory.importance for memory in memories) / len(memories)

        # Reduce confidence if we have very few memories
        count_factor = min(len(memories) / 5, 1.0)  # Optimal around 5 memories

        confidence = (avg_confidence * 0.6 + importance_boost * 0.3) * count_factor

        return min(confidence, 1.0)

    def _build_enhanced_prompt(self, original_prompt: str, memories: list[Memory]) -> str:
        """Build enhanced prompt with memory context."""
        if not memories:
            return original_prompt

        # Group memories by type for better organization
        memory_groups = defaultdict(list)
        for memory in memories:
            memory_groups[memory.memory_type].append(memory)

        # Build context sections
        context_parts = ["## Relevant Context:"]

        # Prioritize memory types
        type_priority = [
            MemoryType.SEMANTIC,  # Facts/knowledge (was IDENTITY)
            MemoryType.PREFERENCE,
            MemoryType.EPISODIC,  # Events/experiences (was DECISION/CONTEXT)
            MemoryType.PROCEDURAL,  # Instructions/how-to (was PATTERN/SOLUTION)
            MemoryType.WORKING,  # Current tasks (was STATUS)
            MemoryType.SENSORY,  # Sensory descriptions
        ]

        for memory_type in type_priority:
            if memory_type in memory_groups:
                type_memories = memory_groups[memory_type]

                # Add section header for multiple memories of same type
                if len(type_memories) > 1:
                    context_parts.append(f"\n### {memory_type.value.title()}:")

                for memory in type_memories:
                    context_parts.append(f"- {memory.content}")

        # Add any remaining memory types
        for memory_type, type_memories in memory_groups.items():
            if memory_type not in type_priority:
                for memory in type_memories:
                    context_parts.append(f"- {memory.content}")

        context = "\n".join(context_parts)

        return f"{context}\n\n{original_prompt}"

    def _update_coordinator_stats(self, strategy_used: str, recall_time_ms: float) -> None:
        """Update coordinator statistics."""
        self._coordinator_stats["total_recalls"] += 1
        self._coordinator_stats["strategy_usage"][strategy_used] += 1

        # Update average recall time
        total_time = (
            self._coordinator_stats["avg_recall_time_ms"]
            * (self._coordinator_stats["total_recalls"] - 1)
            + recall_time_ms
        )
        self._coordinator_stats["avg_recall_time_ms"] = (
            total_time / self._coordinator_stats["total_recalls"]
        )

    def get_recall_statistics(self) -> dict[str, Any]:
        """Get comprehensive recall statistics."""
        strategy_stats = {}
        for name, strategy in self.strategies.items():
            strategy_stats[name] = strategy.get_statistics()

        return {
            "coordinator_stats": self._coordinator_stats,
            "strategy_stats": strategy_stats,
            "cache_stats": self.cache.get_stats() if self.cache else None,
        }
