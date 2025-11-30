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
        """Execute keyword-based recall."""

        # Extract important keywords from prompt
        keywords = self._extract_keywords(prompt)

        if not keywords:
            return []

        # Build query with keyword matching
        parameters = {"current_time": datetime.now().isoformat(), "limit": max_memories}

        # Base query
        query = """
            MATCH (m:Memory)
            WHERE (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($current_time))
        """

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

        # Add keyword conditions with case-insensitive matching
        keyword_conditions = []
        for i, keyword in enumerate(keywords[:5]):  # Limit to top 5 keywords
            param_name = f"keyword_{i}"
            # Use LOWER() for case-insensitive matching
            keyword_conditions.append(f"LOWER(m.content) CONTAINS LOWER(${param_name})")
            parameters[param_name] = keyword

        if keyword_conditions:
            query += f" AND ({' OR '.join(keyword_conditions)})"

        # Order by a combination of recency and importance
        # Balance recency with importance - recent memories should be prioritized
        # but still consider importance for relevance
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

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract important keywords from text."""
        # Tokenize and clean
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

        # Filter out stop words and short words
        keywords = [word for word in words if word not in self.stop_words and len(word) > 2]

        # Count word frequency
        word_counts = defaultdict(int)
        for word in keywords:
            word_counts[word] += 1

        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

        return [word for word, count in sorted_keywords[:10]]


class EntityRecallStrategy(RecallStrategy):
    """
    Entity-based memory recall strategy.

    Finds memories by matching entities extracted from the prompt
    with entities mentioned in stored memories.
    """

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
        """Execute entity-based recall."""

        # Extract entities from prompt
        entities = self.entity_extractor.extract_entities(prompt)

        if not entities:
            return []

        # Get entity names for matching
        [entity.text for entity in entities]
        normalized_names = [entity.normalized_text for entity in entities]

        # Build query to find memories through entity relationships
        query = """
            MATCH (e:Entity)-[:MENTIONS]-(m:Memory)
            WHERE e.normalized_name IN $entity_names
            AND (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($current_time))
        """

        parameters = {
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
