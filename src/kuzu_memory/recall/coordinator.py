"""
Memory recall coordinator for KuzuMemory.

Coordinates multiple recall strategies, ranks results, and builds
the final MemoryContext for the attach_memories() method.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from ..core.config import KuzuMemoryConfig
from ..core.models import Memory, MemoryContext, MemoryType
from ..storage.cache import MemoryCache
from ..storage.kuzu_adapter import KuzuAdapter
from ..utils.exceptions import PerformanceError, PerformanceThresholdError, RecallError
from ..utils.validation import validate_text_input
from .strategies import (
    EntityRecallStrategy,
    KeywordRecallStrategy,
    TemporalRecallStrategy,
)

logger = logging.getLogger(__name__)


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

        # Initialize recall strategies
        self.strategies = {
            "keyword": KeywordRecallStrategy(db_adapter, config),
            "entity": EntityRecallStrategy(db_adapter, config),
            "temporal": TemporalRecallStrategy(db_adapter, config),
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
        self._coordinator_stats = {
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

            # Execute recall strategy
            if strategy == "auto":
                memories = self._auto_recall(
                    clean_prompt, max_memories, user_id, session_id, agent_id
                )
                strategy_used = "auto"
            else:
                memories = self._single_strategy_recall(
                    strategy, clean_prompt, max_memories, user_id, session_id, agent_id
                )
                strategy_used = strategy

            # Rank and filter memories
            ranked_memories = self._rank_memories(memories, clean_prompt)
            final_memories = ranked_memories[:max_memories]

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

            # Check performance requirement
            if (
                self.config.performance.enable_performance_monitoring
                and context.recall_time_ms > self.config.performance.max_recall_time_ms
            ):
                raise PerformanceThresholdError(
                    operation="attach_memories",
                    actual_time=context.recall_time_ms / 1000.0,  # Convert to seconds
                    threshold=self.config.performance.max_recall_time_ms / 1000.0,
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
    ) -> list[Memory]:
        """Execute automatic strategy selection and combination."""

        all_memories = []
        strategy_weights = self.config.recall.strategy_weights

        # Run all enabled strategies in parallel
        for strategy_name in self.config.recall.strategies:
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

    def _rank_memories(self, memories: list[Memory], prompt: str) -> list[Memory]:
        """
        Rank memories by relevance to the prompt.

        Args:
            memories: List of memories to rank
            prompt: Original prompt for relevance scoring

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

        # Calculate relevance scores
        scored_memories = []
        prompt_lower = prompt.lower()

        for memory in memories:
            score = self._calculate_relevance_score(memory, prompt_lower)
            scored_memories.append((memory, score))

        # Sort by score (highest first)
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        return [memory for memory, score in scored_memories]

    def _calculate_relevance_score(self, memory: Memory, prompt_lower: str) -> float:
        """Calculate relevance score for a memory given the prompt."""
        score = 0.0

        # Base score from memory importance and confidence
        score += memory.importance * 0.3
        score += memory.confidence * 0.2

        # Boost score for memory type relevance
        type_boosts = {
            MemoryType.SEMANTIC: 0.9,  # Facts/knowledge (was IDENTITY)
            MemoryType.PREFERENCE: 0.8,
            MemoryType.EPISODIC: 0.7,  # Events/experiences (was DECISION)
            MemoryType.PROCEDURAL: 0.8,  # Instructions/how-to (was PATTERN/SOLUTION)
            MemoryType.WORKING: 0.3,  # Current tasks (was STATUS)
            MemoryType.SENSORY: 0.4,  # Sensory descriptions
        }
        score += type_boosts.get(memory.memory_type, 0.5) * 0.2

        # Boost score for content similarity
        memory_content_lower = memory.content.lower()

        # Simple word overlap scoring
        prompt_words = set(prompt_lower.split())
        memory_words = set(memory_content_lower.split())

        if prompt_words and memory_words:
            overlap = len(prompt_words.intersection(memory_words))
            union = len(prompt_words.union(memory_words))
            similarity = overlap / union if union > 0 else 0
            score += similarity * 0.3

        # Boost for entity matches
        if memory.entities:
            for entity in memory.entities:
                # Handle both string and dict entity types
                entity_str = entity if isinstance(entity, str) else str(entity.get("name", ""))
                if entity_str.lower() in prompt_lower:
                    score += 0.1

        # Recency boost (more recent memories get slight boost)
        days_old = (datetime.now() - memory.created_at).days
        recency_boost = max(0, (30 - days_old) / 30) * 0.1
        score += recency_boost

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
