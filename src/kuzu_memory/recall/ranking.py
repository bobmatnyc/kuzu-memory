"""
Memory ranking utilities for KuzuMemory.

Provides sophisticated ranking algorithms for memory relevance scoring
and result optimization.
"""

import logging
import math
from collections import Counter
from datetime import datetime
from typing import Any

from ..core.models import Memory, MemoryType
from .temporal_decay import TemporalDecayEngine

logger = logging.getLogger(__name__)


class MemoryRanker:
    """
    Advanced memory ranking system with multiple scoring algorithms.

    Provides sophisticated relevance scoring based on content similarity,
    temporal relevance, importance, and user interaction patterns.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize memory ranker.

        Args:
            config: Optional configuration for ranking parameters
        """
        self.config = config or {}

        # Initialize enhanced temporal decay engine
        self.temporal_decay_engine = TemporalDecayEngine(self.config.get("temporal_decay", {}))

        # Ranking weights (can be configured)
        # Note: recency weight is now managed by temporal decay engine
        self.weights = {
            "content_similarity": self.config.get(
                "content_similarity_weight", 0.30
            ),  # Reduced slightly
            "importance": self.config.get("importance_weight", 0.25),
            "confidence": self.config.get("confidence_weight", 0.15),
            "recency": self.temporal_decay_engine.decay_config[
                "base_weight"
            ],  # Dynamic from decay engine
            "type_relevance": self.config.get("type_relevance_weight", 0.10),
            "access_frequency": self.config.get("access_frequency_weight", 0.05),
        }

        # Memory type relevance scores for different contexts
        self.type_relevance_scores = {
            MemoryType.SEMANTIC: {
                "personal": 1.0,
                "identity": 1.0,
                "profile": 0.9,
                "general": 0.7,
                "decision": 1.0,
                "planning": 0.9,
                "architecture": 0.9,
            },
            MemoryType.PREFERENCE: {
                "preference": 1.0,
                "settings": 0.9,
                "personal": 0.8,
                "general": 0.6,
            },
            MemoryType.PROCEDURAL: {
                "code": 1.0,
                "pattern": 1.0,
                "development": 0.9,
                "general": 0.6,
                "problem": 1.0,
                "solution": 1.0,
                "troubleshooting": 0.9,
            },
            MemoryType.WORKING: {
                "status": 1.0,
                "current": 0.9,
                "progress": 0.8,
                "general": 0.3,
            },
            MemoryType.EPISODIC: {
                "context": 0.8,
                "general": 0.5,
                "background": 0.6,
                "session": 0.7,
            },
            MemoryType.SENSORY: {
                "ui": 0.8,
                "visual": 0.7,
                "feedback": 0.6,
                "general": 0.3,
            },
        }

    def rank_memories(
        self,
        memories: list[Memory],
        query: str,
        context_type: str = "general",
        user_preferences: dict[str, Any] | None = None,
    ) -> list[tuple[Memory, float]]:
        """
        Rank memories by relevance to query.

        Args:
            memories: List of memories to rank
            query: Query string for relevance calculation
            context_type: Type of context for type relevance scoring
            user_preferences: Optional user preferences for personalized ranking

        Returns:
            List of (memory, score) tuples sorted by relevance score
        """
        if not memories:
            return []

        scored_memories = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for memory in memories:
            score = self._calculate_memory_score(
                memory, query_lower, query_words, context_type, user_preferences
            )
            scored_memories.append((memory, score))

        # Sort by score (highest first)
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        return scored_memories

    def _calculate_memory_score(
        self,
        memory: Memory,
        query_lower: str,
        query_words: set[str],
        context_type: str,
        user_preferences: dict[str, Any] | None = None,
    ) -> float:
        """Calculate comprehensive relevance score for a memory."""

        scores = {}

        # Content similarity score
        scores["content_similarity"] = self._calculate_content_similarity(
            memory, query_lower, query_words
        )

        # Importance score (normalized)
        scores["importance"] = memory.importance

        # Confidence score (normalized)
        scores["confidence"] = memory.confidence

        # Enhanced temporal decay score
        scores["recency"] = self.temporal_decay_engine.calculate_temporal_score(memory)

        # Type relevance score
        scores["type_relevance"] = self._calculate_type_relevance_score(memory, context_type)

        # Access frequency score
        scores["access_frequency"] = self._calculate_access_frequency_score(memory)

        # Apply user preferences if provided
        if user_preferences:
            scores = self._apply_user_preferences(scores, memory, user_preferences)

        # Calculate weighted final score
        final_score = sum(scores[component] * self.weights[component] for component in scores)

        return min(final_score, 1.0)  # Cap at 1.0

    def _calculate_content_similarity(
        self, memory: Memory, query_lower: str, query_words: set[str]
    ) -> float:
        """Calculate content similarity between memory and query."""
        memory_content_lower = memory.content.lower()
        memory_words = set(memory_content_lower.split())

        if not query_words or not memory_words:
            return 0.0

        # Jaccard similarity (intersection over union)
        intersection = len(query_words.intersection(memory_words))
        union = len(query_words.union(memory_words))
        jaccard_score = intersection / union if union > 0 else 0.0

        # Exact phrase matching bonus
        phrase_bonus = 0.0
        if len(query_lower) > 10:  # Only for longer queries
            if query_lower in memory_content_lower:
                phrase_bonus = 0.3
            else:
                # Check for partial phrase matches
                query_phrases = [phrase.strip() for phrase in query_lower.split(",")]
                for phrase in query_phrases:
                    if len(phrase) > 5 and phrase in memory_content_lower:
                        phrase_bonus += 0.1

        # Entity matching bonus
        entity_bonus = 0.0
        if memory.entities:
            for entity in memory.entities:
                # Handle both string and dict entity types
                entity_str = entity if isinstance(entity, str) else str(entity.get("name", ""))
                if entity_str.lower() in query_lower:
                    entity_bonus += 0.05

        # TF-IDF-like scoring for important terms
        tfidf_score = self._calculate_tfidf_similarity(memory_content_lower, query_lower)

        # Combine scores
        similarity_score = (
            jaccard_score * 0.4 + phrase_bonus * 0.3 + entity_bonus * 0.2 + tfidf_score * 0.1
        )

        return min(similarity_score, 1.0)

    def _calculate_tfidf_similarity(self, memory_content: str, query: str) -> float:
        """Calculate TF-IDF-like similarity score."""
        # Simple TF-IDF approximation
        memory_words = memory_content.split()
        query_words = query.split()

        if not memory_words or not query_words:
            return 0.0

        # Term frequency in memory
        memory_tf = Counter(memory_words)
        memory_length = len(memory_words)

        # Calculate score for query terms
        score = 0.0
        for word in set(query_words):
            if word in memory_tf:
                tf = memory_tf[word] / memory_length
                # Simple IDF approximation (longer words get higher scores)
                idf = math.log(len(word) + 1)
                score += tf * idf

        return min(score, 1.0)

    def _calculate_recency_score(self, memory: Memory) -> float:
        """Calculate recency score based on memory age."""
        now = datetime.now()
        age = now - memory.created_at

        # Different decay rates for different memory types
        decay_rates = {
            MemoryType.SENSORY: 0.25,  # Very fast decay (6 hours)
            MemoryType.WORKING: 1,  # Fast decay (1 day)
            MemoryType.EPISODIC: 30,  # Medium decay (30 days)
            MemoryType.PROCEDURAL: 365,  # Slow decay (no expiry but age matters)
            MemoryType.SEMANTIC: 365,  # Almost no decay
            MemoryType.PREFERENCE: 365,  # Almost no decay
        }

        decay_period = decay_rates.get(memory.memory_type, 30)
        age_days = age.total_seconds() / (24 * 3600)

        # Exponential decay
        recency_score = math.exp(-age_days / decay_period)

        return recency_score

    def _calculate_type_relevance_score(self, memory: Memory, context_type: str) -> float:
        """Calculate type relevance score based on context."""
        type_scores = self.type_relevance_scores.get(memory.memory_type, {})
        return type_scores.get(context_type, type_scores.get("general", 0.5))

    def _calculate_access_frequency_score(self, memory: Memory) -> float:
        """Calculate score based on how frequently the memory is accessed."""
        # Normalize access count (assuming max reasonable access count is 100)
        normalized_access = min(memory.access_count / 100.0, 1.0)

        # Apply logarithmic scaling to prevent over-weighting highly accessed memories
        if memory.access_count > 0:
            log_score = math.log(memory.access_count + 1) / math.log(101)  # log base 101
            return (normalized_access + log_score) / 2

        return 0.0

    def _apply_user_preferences(
        self, scores: dict[str, float], memory: Memory, user_preferences: dict[str, Any]
    ) -> dict[str, float]:
        """Apply user-specific preferences to scoring."""

        # Boost scores for preferred memory types
        preferred_types = user_preferences.get("preferred_memory_types", [])
        if memory.memory_type.value in preferred_types:
            scores["type_relevance"] *= 1.2

        # Boost scores for memories from preferred sources
        preferred_sources = user_preferences.get("preferred_sources", [])
        if memory.source_type in preferred_sources:
            scores["importance"] *= 1.1

        # Apply recency preference
        recency_preference = user_preferences.get("recency_preference", "balanced")
        if recency_preference == "recent":
            scores["recency"] *= 1.5
        elif recency_preference == "historical":
            scores["recency"] *= 0.7

        return scores

    def get_ranking_explanation(
        self, memory: Memory, query: str, context_type: str = "general"
    ) -> dict[str, Any]:
        """Get detailed explanation of how a memory was ranked."""

        query_lower = query.lower()
        query_words = set(query_lower.split())

        scores = {}
        scores["content_similarity"] = self._calculate_content_similarity(
            memory, query_lower, query_words
        )
        scores["importance"] = memory.importance
        scores["confidence"] = memory.confidence
        scores["recency"] = self.temporal_decay_engine.calculate_temporal_score(memory)
        scores["type_relevance"] = self._calculate_type_relevance_score(memory, context_type)
        scores["access_frequency"] = self._calculate_access_frequency_score(memory)

        # Calculate weighted contributions
        weighted_scores = {
            component: scores[component] * self.weights[component] for component in scores
        }

        final_score = sum(weighted_scores.values())

        return {
            "memory_id": memory.id,
            "final_score": final_score,
            "component_scores": scores,
            "weighted_contributions": weighted_scores,
            "weights_used": self.weights.copy(),
            "memory_type": memory.memory_type.value,
            "memory_age_days": (datetime.now() - memory.created_at).days,
            "access_count": memory.access_count,
            "temporal_decay_details": self.temporal_decay_engine.get_decay_explanation(memory),
        }
