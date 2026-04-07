"""
Multi-strategy memory recall system for KuzuMemory.

Implements keyword, entity, and temporal recall strategies with
ranking and performance optimization for fast memory retrieval.
"""

import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from ..core.config import KuzuMemoryConfig
from ..core.models import Memory
from ..extraction.entities import EntityExtractor
from ..storage.kuzu_adapter import KuzuAdapter
from ..utils.exceptions import RecallError
from ..utils.validation import validate_text_input

logger = logging.getLogger(__name__)


class RecallStrategy:
    """
    Base class for memory recall strategies.

    Provides common functionality for different recall approaches
    including performance monitoring and result ranking.
    """

    def __init__(self, db_adapter: KuzuAdapter, config: KuzuMemoryConfig) -> None:
        """
        Initialize recall strategy.

        Args:
            db_adapter: Database adapter for queries
            config: Configuration object
        """
        self.db_adapter = db_adapter
        self.config = config
        self.strategy_name = "base"

        # Performance tracking
        self._recall_stats = {
            "total_recalls": 0,
            "total_time_ms": 0.0,
            "avg_time_ms": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def recall(
        self,
        prompt: str,
        max_memories: int = 10,
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
    ) -> list[Memory]:
        """
        Recall memories relevant to the prompt.

        Args:
            prompt: User prompt to find memories for
            max_memories: Maximum number of memories to return
            user_id: Optional user ID filter
            session_id: Optional session ID filter
            agent_id: Agent ID filter

        Returns:
            List of relevant memories
        """
        start_time = time.time()

        try:
            # Validate input
            clean_prompt = validate_text_input(prompt, "recall_prompt")

            # Execute strategy-specific recall
            memories = self._execute_recall(
                clean_prompt, max_memories, user_id, session_id, agent_id
            )

            # Update statistics
            execution_time = (time.time() - start_time) * 1000
            self._update_stats(execution_time)

            # Check performance requirement
            if (
                self.config.performance.enable_performance_monitoring
                and execution_time > self.config.performance.max_recall_time_ms
            ):
                logger.warning(f"{self.strategy_name} recall took {execution_time:.1f}ms")

            return memories

        except Exception as e:
            raise RecallError(
                f"Recall failed for prompt: {prompt}",
                context={"prompt": prompt, "error": str(e)},
                cause=e,
            )

    def _execute_recall(
        self,
        prompt: str,
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> list[Memory]:
        """Execute strategy-specific recall logic. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _execute_recall")

    def _update_stats(self, execution_time_ms: float) -> None:
        """Update recall statistics."""
        self._recall_stats["total_recalls"] += 1
        self._recall_stats["total_time_ms"] += execution_time_ms
        self._recall_stats["avg_time_ms"] = (
            self._recall_stats["total_time_ms"] / self._recall_stats["total_recalls"]
        )

    def get_statistics(self) -> dict[str, Any]:
        """Get recall strategy statistics."""
        return {"strategy_name": self.strategy_name, "stats": self._recall_stats.copy()}


class KeywordRecallStrategy(RecallStrategy):
    """
    Keyword-based memory recall strategy.

    Finds memories by matching important keywords from the prompt
    with memory content using database text search.
    """

    def __init__(self, db_adapter: KuzuAdapter, config: KuzuMemoryConfig) -> None:
        super().__init__(db_adapter, config)
        self.strategy_name = "keyword"

        # Common stop words to filter out
        self.stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "what",
            "how",
            "when",
            "where",
            "who",
            "why",
            "do",
            "does",
            "did",
            "we",
            "our",
            "my",
            "your",
            "i",
            "you",
            "he",
            "she",
            "it",
            "they",
            "them",
            "this",
            "that",
            "these",
            "those",
            "and",
            "or",
            "but",
            "so",
            "if",
            "then",
            "can",
            "will",
            "would",
            "could",
            "should",
        }

    def _execute_recall(
        self,
        prompt: str,
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> list[Memory]:
        """Execute keyword-based recall.

        Tries the graph-based TF-IDF path first (O(1) graph lookup via
        HAS_KEYWORD edges).  Falls back to the legacy content scan if the
        graph path fails or returns no results (e.g. enricher has not yet run).
        """
        keywords = self._extract_keywords(prompt)
        if not keywords:
            return []

        # Graph-based path: O(1) lookup via HAS_KEYWORD edges.
        try:
            graph_results = self._recall_via_keyword_graph(
                keywords, max_memories, user_id, session_id, agent_id
            )
            if graph_results:
                return graph_results
        except Exception as exc:
            logger.debug(
                "KeywordRecallStrategy graph path failed (falling back to content scan): %s", exc
            )

        # Legacy content-scan fallback (O(N)).
        return self._recall_via_content_scan(keywords, max_memories, user_id, session_id, agent_id)

    def _recall_via_keyword_graph(
        self,
        keywords: list[str],
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> list[Memory]:
        """Recall memories via HAS_KEYWORD graph edges ordered by TF-IDF sum.

        Args:
            keywords: Pre-extracted keyword tokens from the query.
            max_memories: Maximum number of results to return.
            user_id: Optional user-ID filter.
            session_id: Optional session-ID filter.
            agent_id: Agent-ID filter (skipped when "default").

        Returns:
            List of Memory objects ordered by descending relevance (TF-IDF sum).
            Returns empty list when the Keyword table is empty (enricher not run).

        Raises:
            Exception: Propagated from execute_query on unexpected DB errors.
        """
        now = datetime.now().isoformat()
        parameters: dict[str, Any] = {
            "keywords": keywords,
            "current_time": now,
            "limit": max_memories,
        }

        query = """
            MATCH (m:Memory)-[hk:HAS_KEYWORD]->(k:Keyword)
            WHERE k.word IN $keywords
              AND (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($current_time))
        """

        if user_id:
            query += " AND m.user_id = $user_id"
            parameters["user_id"] = user_id

        if session_id:
            query += " AND m.session_id = $session_id"
            parameters["session_id"] = session_id

        if agent_id and agent_id != "default":
            query += " AND m.agent_id = $agent_id"
            parameters["agent_id"] = agent_id

        query += """
            RETURN DISTINCT m, SUM(hk.tfidf) AS relevance
            ORDER BY relevance DESC
            LIMIT $limit
        """

        rows = self.db_adapter.execute_query(query, parameters)
        if not rows:
            # Keyword table is empty — enricher has not run yet.
            return []

        memories: list[Memory] = []
        from ..storage.query_builder import QueryBuilder

        query_builder = QueryBuilder(self.db_adapter)
        for row in rows:
            try:
                memory = query_builder._convert_db_result_to_memory(row["m"])
                if memory:
                    memories.append(memory)
            except Exception as e:
                logger.warning("Failed to parse memory from graph keyword recall: %s", e)

        return memories

    def _recall_via_content_scan(
        self,
        keywords: list[str],
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> list[Memory]:
        """Legacy O(N) content-scan fallback.

        Used when the HAS_KEYWORD graph has not been populated yet, or when the
        graph query fails unexpectedly.

        Args:
            keywords: Pre-extracted keyword tokens from the query.
            max_memories: Maximum number of results to return.
            user_id: Optional user-ID filter.
            session_id: Optional session-ID filter.
            agent_id: Agent-ID filter (skipped when "default").

        Returns:
            List of Memory objects matched by content substring.
        """
        parameters: dict[str, Any] = {
            "current_time": datetime.now().isoformat(),
            "limit": max_memories,
        }

        query = """
            MATCH (m:Memory)
            WHERE (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($current_time))
        """

        if user_id:
            query += " AND m.user_id = $user_id"
            parameters["user_id"] = user_id

        if session_id:
            query += " AND m.session_id = $session_id"
            parameters["session_id"] = session_id

        if agent_id and agent_id != "default":
            query += " AND m.agent_id = $agent_id"
            parameters["agent_id"] = agent_id

        keyword_conditions = []
        for i, keyword in enumerate(keywords[:5]):
            param_name = f"keyword_{i}"
            keyword_conditions.append(f"LOWER(m.content) CONTAINS LOWER(${param_name})")
            parameters[param_name] = keyword

        if keyword_conditions:
            query += f" AND ({' OR '.join(keyword_conditions)})"

        query += """
            RETURN m
            ORDER BY m.created_at DESC, m.importance DESC
            LIMIT $limit
        """

        results = self.db_adapter.execute_query(query, parameters)

        memories: list[Memory] = []
        from ..storage.query_builder import QueryBuilder

        query_builder = QueryBuilder(self.db_adapter)
        for result in results:
            try:
                memory_data = result["m"]
                memory = query_builder._convert_db_result_to_memory(memory_data)
                if memory:
                    memories.append(memory)
            except Exception as e:
                logger.warning(f"Failed to parse memory from database: {e}")

        return memories

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract important keywords from text."""
        # Tokenize and clean
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

        # Filter out stop words and short words
        keywords = [word for word in words if word not in self.stop_words and len(word) > 2]

        # Count word frequency
        word_counts: dict[str, int] = defaultdict(int)
        for word in keywords:
            word_counts[word] += 1

        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

        return [word for word, _count in sorted_keywords[:10]]


class EntityRecallStrategy(RecallStrategy):
    """
    Entity-based memory recall strategy.

    Finds memories by matching entities extracted from the prompt
    with entities mentioned in stored memories.
    """

    # Instrumentation hook used by tests to track call counts per query type.
    # Production code never sets this attribute; it exists only to satisfy
    # type-checkers when tests assign ``strategy._call_count = {...}``.
    _call_count: dict[str, int]

    def __init__(self, db_adapter: KuzuAdapter, config: KuzuMemoryConfig) -> None:
        super().__init__(db_adapter, config)
        self.strategy_name = "entity"

        # Initialize entity extractor
        self.entity_extractor = EntityExtractor(
            enable_compilation=config.extraction.enable_pattern_compilation
        )

    def _execute_recall(
        self,
        prompt: str,
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> list[Memory]:
        """Execute entity-based recall with optional 2-hop CO_OCCURS_WITH expansion.

        Primary recall: finds memories directly mentioning entities extracted
        from the prompt.

        2-hop expansion: when primary results are sparse (fewer than
        ``max_memories``), follows CO_OCCURS_WITH edges from the matched
        entities to related entities and retrieves their memories.  Expanded
        results are returned alongside primary results; the caller's ranker
        applies any desired score penalty.
        """

        # Extract entities from prompt
        entities = self.entity_extractor.extract_entities(prompt)

        if not entities:
            return []

        # Get entity names for matching
        normalized_names = [entity.normalized_text for entity in entities]

        # Build query to find memories through entity relationships
        query = """
            MATCH (e:Entity)-[:MENTIONS]-(m:Memory)
            WHERE e.normalized_name IN $entity_names
            AND (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($current_time))
        """

        parameters: dict[str, Any] = {
            "entity_names": normalized_names,
            "current_time": datetime.now().isoformat(),
            "limit": max_memories,
        }

        # Add user/session/agent filters
        if user_id:
            query += " AND m.user_id = $user_id"
            parameters["user_id"] = user_id

        if session_id:
            query += " AND m.session_id = $session_id"
            parameters["session_id"] = session_id

        # Only filter by agent_id if it's not the default value
        # This allows recall to work across all agent contexts when not specified
        if agent_id and agent_id != "default":
            query += " AND m.agent_id = $agent_id"
            parameters["agent_id"] = agent_id

        # Return distinct memories ordered by importance
        query += """
            RETURN DISTINCT m
            ORDER BY m.importance DESC, m.created_at DESC
            LIMIT $limit
        """

        # Execute primary query
        results = self.db_adapter.execute_query(query, parameters)

        # Convert results to Memory objects using QueryBuilder
        memories: list[Memory] = []
        from ..storage.query_builder import QueryBuilder

        query_builder = QueryBuilder(self.db_adapter)

        for result in results:
            try:
                memory_data = result["m"]
                memory = query_builder._convert_db_result_to_memory(memory_data)
                if memory:
                    memories.append(memory)
            except Exception as e:
                logger.warning(f"Failed to parse memory from database: {e}")
                continue

        # 2-hop expansion via CO_OCCURS_WITH when primary results are sparse.
        # This uses the enriched entity co-occurrence graph to surface memories
        # that are indirectly related to the prompt entities.
        if len(memories) < max_memories:
            expanded = self._expand_via_cooccurrence(
                normalized_names=normalized_names,
                found_ids=[m.id for m in memories],
                remaining=max_memories - len(memories),
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
                query_builder=query_builder,
            )
            memories.extend(expanded)

        return memories

    def _expand_via_cooccurrence(
        self,
        normalized_names: list[str],
        found_ids: list[str],
        remaining: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
        query_builder: Any,
    ) -> list[Memory]:
        """Follow CO_OCCURS_WITH edges for 2-hop memory expansion.

        Returns at most ``remaining`` additional memories not already in
        ``found_ids``.  Returned memories are tagged with a reduced confidence
        (0.7x) by the caller's ranker to distinguish them from primary hits.

        If the CO_OCCURS_WITH relationship table does not yet exist (e.g. the
        enricher has never run), the query will fail gracefully and an empty
        list is returned — the primary results are never discarded.
        """
        if not normalized_names or remaining <= 0:
            return []

        params: dict[str, Any] = {
            "entity_names": normalized_names,
            "found_ids": found_ids,
            "current_time": datetime.now().isoformat(),
            "limit": remaining,
        }

        hop2_query = """
            MATCH (e1:Entity)-[:CO_OCCURS_WITH]-(e2:Entity)<-[:MENTIONS]-(m:Memory)
            WHERE e1.normalized_name IN $entity_names
            AND NOT m.id IN $found_ids
            AND (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($current_time))
        """

        if user_id:
            hop2_query += " AND m.user_id = $user_id"
            params["user_id"] = user_id

        if session_id:
            hop2_query += " AND m.session_id = $session_id"
            params["session_id"] = session_id

        if agent_id and agent_id != "default":
            hop2_query += " AND m.agent_id = $agent_id"
            params["agent_id"] = agent_id

        hop2_query += """
            RETURN DISTINCT m
            ORDER BY m.importance DESC, m.created_at DESC
            LIMIT $limit
        """

        try:
            rows = self.db_adapter.execute_query(hop2_query, params)
        except Exception as exc:
            # CO_OCCURS_WITH may not exist yet (enricher hasn't run) — silent fallback.
            logger.debug("2-hop expansion query failed (non-fatal, table may not exist): %s", exc)
            return []

        expanded: list[Memory] = []
        for row in rows:
            try:
                memory = query_builder._convert_db_result_to_memory(row["m"])
                if memory:
                    # Apply 0.7x confidence multiplier to mark as 2-hop result.
                    memory.confidence *= 0.7
                    expanded.append(memory)
            except Exception as e:
                logger.warning("Failed to parse 2-hop memory: %s", e)

        if expanded:
            logger.debug("2-hop expansion added %d memories", len(expanded))

        return expanded


class GraphRelatedRecallStrategy(RecallStrategy):
    """2-hop recall via RELATES_TO edges from seed memories.

    Finds a small set of seed memories using keyword matching, then traverses
    RELATES_TO edges to surface related memories that may not share keywords
    with the original query.

    Confidence scoring:
    - Base: 0.5 * (min(total_weight, 5.0) / 5.0)
    - kt_affinity bonus: +0.15 for edges marked with relationship_type='kt_affinity'
    - Overall cap: 1.0

    This strategy is intended for graph-only recall paths (use_semantic_search=False).
    When HNSW is active, it is skipped in the coordinator to avoid redundancy.
    """

    # Maximum number of seed memories to use for graph traversal.
    _MAX_SEEDS = 5

    def __init__(self, db_adapter: KuzuAdapter, config: KuzuMemoryConfig) -> None:
        super().__init__(db_adapter, config)
        self.strategy_name = "graph_related"

        # Reuse keyword extraction logic from KeywordRecallStrategy.
        self._keyword_strategy = KeywordRecallStrategy(db_adapter, config)

    def _execute_recall(
        self,
        prompt: str,
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> list[Memory]:
        """Execute 2-hop graph traversal recall.

        Step 1: find seed memories via keyword search on the prompt.
        Step 2: traverse RELATES_TO edges from those seeds.
        Step 3: score related memories by edge weight and relationship type.
        """
        # Step 1: seed memories via keyword match (up to _MAX_SEEDS).
        seed_memories = self._keyword_strategy._execute_recall(
            prompt, self._MAX_SEEDS, user_id, session_id, agent_id
        )
        if not seed_memories:
            return []

        seed_ids = [m.id for m in seed_memories]

        # Step 2: traverse RELATES_TO edges from seeds.
        traversal_query = """
            MATCH (seed:Memory)-[r:RELATES_TO]->(related:Memory)
            WHERE seed.id IN $seed_ids
              AND related.id NOT IN $seed_ids
            RETURN DISTINCT related,
                   SUM(r.weight) AS total_weight,
                   MAX(r.relationship_type) AS rel_type
            ORDER BY total_weight DESC
            LIMIT $limit
        """
        params: dict[str, Any] = {
            "seed_ids": seed_ids,
            "limit": max_memories,
        }

        try:
            rows = self.db_adapter.execute_query(traversal_query, params)
        except Exception as exc:
            # RELATES_TO may not exist yet (enricher hasn't run) — silent fallback.
            logger.debug(
                "GraphRelatedRecallStrategy traversal failed (non-fatal, table may not exist): %s",
                exc,
            )
            return []

        # Step 3: convert rows to Memory objects with weighted confidence.
        memories: list[Memory] = []
        from ..storage.query_builder import QueryBuilder

        query_builder = QueryBuilder(self.db_adapter)

        for row in rows:
            try:
                memory = query_builder._convert_db_result_to_memory(row["related"])
                if memory is None:
                    continue

                total_weight = float(row.get("total_weight") or 1.0)
                rel_type = row.get("rel_type") or ""

                # Confidence: 0.5 base scaled by capped weight, plus kt_affinity bonus.
                confidence = 0.5 * (min(total_weight, 5.0) / 5.0)
                if rel_type == "kt_affinity":
                    confidence += 0.15

                memory.confidence = min(confidence, 1.0)
                memories.append(memory)
            except Exception as parse_exc:
                logger.warning("GraphRelatedRecallStrategy: failed to parse row: %s", parse_exc)

        if memories:
            logger.debug(
                "GraphRelatedRecallStrategy: %d related memories via %d seeds",
                len(memories),
                len(seed_ids),
            )

        return memories


class TemporalRecallStrategy(RecallStrategy):
    """
    Temporal-based memory recall strategy.

    Finds memories based on temporal relevance, recency,
    and time-based patterns in the prompt.
    """

    def __init__(self, db_adapter: KuzuAdapter, config: KuzuMemoryConfig) -> None:
        super().__init__(db_adapter, config)
        self.strategy_name = "temporal"

        # Temporal keywords and their time ranges
        self.temporal_patterns = {
            "recent": timedelta(days=7),
            "recently": timedelta(days=7),
            "latest": timedelta(days=3),
            "today": timedelta(days=1),
            "yesterday": timedelta(days=2),
            "this week": timedelta(days=7),
            "last week": timedelta(days=14),
            "this month": timedelta(days=30),
            "last month": timedelta(days=60),
        }

    def _execute_recall(
        self,
        prompt: str,
        max_memories: int,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> list[Memory]:
        """Execute temporal-based recall."""

        # Detect temporal markers in prompt
        time_range = self._detect_time_range(prompt)

        # If no temporal patterns are detected, return empty list
        # The temporal strategy should only return results when temporal context is present
        if not time_range:
            return []

        # Build temporal query
        query = """
            MATCH (m:Memory)
            WHERE (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($current_time))
        """

        current_time = datetime.now()
        parameters = {"current_time": current_time.isoformat(), "limit": max_memories}

        # Add temporal filter (we know time_range exists now)
        since_time = current_time - time_range
        query += " AND m.created_at > TIMESTAMP($since_time)"
        parameters["since_time"] = since_time.isoformat()

        # Add user/session/agent filters
        if user_id:
            query += " AND m.user_id = $user_id"
            parameters["user_id"] = user_id

        if session_id:
            query += " AND m.session_id = $session_id"
            parameters["session_id"] = session_id

        # Only filter by agent_id if it's not the default value
        # This allows recall to work across all agent contexts when not specified
        if agent_id and agent_id != "default":
            query += " AND m.agent_id = $agent_id"
            parameters["agent_id"] = agent_id

        # Order by recency and importance
        query += """
            RETURN m
            ORDER BY m.created_at DESC, m.importance DESC
            LIMIT $limit
        """

        # Execute query
        results = self.db_adapter.execute_query(query, parameters)

        # Convert results to Memory objects using QueryBuilder
        memories = []
        from ..storage.query_builder import QueryBuilder

        query_builder = QueryBuilder(self.db_adapter)

        for result in results:
            try:
                memory_data = result["m"]
                memory = query_builder._convert_db_result_to_memory(memory_data)
                if memory:
                    memories.append(memory)
            except Exception as e:
                logger.warning(f"Failed to parse memory from database: {e}")
                continue

        return memories

    def _detect_time_range(self, prompt: str) -> timedelta | None:
        """Detect temporal markers in prompt and return appropriate time range."""
        prompt_lower = prompt.lower()

        for pattern, time_range in self.temporal_patterns.items():
            if pattern in prompt_lower:
                return time_range

        return None
