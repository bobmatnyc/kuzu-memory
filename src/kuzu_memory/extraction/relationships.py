"""
Relationship detection for KuzuMemory.

Detects relationships between memories and entities using pattern matching
and proximity analysis without requiring LLM calls.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..core.models import Memory, MemoryType
from .entities import Entity

logger = logging.getLogger(__name__)


@dataclass
class Relationship:
    """Represents a relationship between two entities or memories."""

    source_id: str
    target_id: str
    relationship_type: str
    confidence: float
    context: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class RelationshipDetector:
    """
    Detects relationships between memories and entities.

    Uses pattern matching and proximity analysis to identify
    relationships without requiring LLM calls.
    """

    def __init__(self) -> None:
        """Initialize relationship detector."""
        self._define_relationship_patterns()
        self._compile_patterns()

        # Statistics
        self._detection_stats: dict[str, Any] = {
            "total_relationships": 0,
            "relationship_types": {},
            "patterns_matched": {},
        }

    def _define_relationship_patterns(self) -> None:
        """Define patterns for detecting relationships."""

        # Memory-Memory relationship patterns
        self.MEMORY_RELATIONSHIP_PATTERNS = [
            # Contradiction patterns
            (
                r"(?:actually|no|wait|correction)[,]?\s*(.*?)(?:\.|$)",
                "contradicts",
                0.95,
            ),
            (
                r"(?:that\'s wrong|incorrect|not right)[,]?\s*(.*?)(?:\.|$)",
                "contradicts",
                0.90,
            ),
            # Update patterns
            (r"(?:now|currently|as of now)[,]?\s*(.*?)(?:\.|$)", "updates", 0.85),
            (r"(?:changed to|updated to|now is)[,]?\s*(.*?)(?:\.|$)", "updates", 0.90),
            # Reference patterns
            (
                r"(?:as mentioned|as I said|like I told you)[,]?\s*(.*?)(?:\.|$)",
                "references",
                0.80,
            ),
            (r"(?:similar to|like|just like)[,]?\s*(.*?)(?:\.|$)", "similar_to", 0.75),
            # Elaboration patterns
            (
                r"(?:also|additionally|furthermore|moreover)[,]?\s*(.*?)(?:\.|$)",
                "elaborates",
                0.70,
            ),
            (r"(?:for example|such as|like)[,]?\s*(.*?)(?:\.|$)", "exemplifies", 0.75),
        ]

        # Entity-Entity relationship patterns
        self.ENTITY_RELATIONSHIP_PATTERNS = [
            # Work relationships
            (r"(\w+)\s+(?:works at|works for|is at|is with)\s+(\w+)", "works_at", 0.95),
            (r"(\w+)\s+(?:from|at)\s+(\w+)", "affiliated_with", 0.80),
            # Technology relationships
            (r"(\w+)\s+(?:uses|built with|using|in)\s+(\w+)", "uses", 0.85),
            (
                r"(\w+)\s+(?:written in|implemented in|coded in)\s+(\w+)",
                "implemented_in",
                0.90,
            ),
            (r"(\w+)\s+(?:version|v\.?)\s+(\d+\.\d+)", "has_version", 0.95),
            # Ownership/Creation relationships
            (r"(\w+)\s+(?:created|built|developed|made)\s+(\w+)", "created", 0.90),
            (r"(\w+)\s+(?:owns|maintains|manages)\s+(\w+)", "owns", 0.85),
            # Dependency relationships
            (r"(\w+)\s+(?:depends on|requires|needs)\s+(\w+)", "depends_on", 0.85),
            (r"(\w+)\s+(?:extends|inherits from|based on)\s+(\w+)", "extends", 0.90),
        ]

    def _compile_patterns(self) -> None:
        """Compile relationship patterns for performance."""
        self.compiled_memory_patterns = []
        for pattern, rel_type, confidence in self.MEMORY_RELATIONSHIP_PATTERNS:
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                self.compiled_memory_patterns.append((compiled, rel_type, confidence))
            except re.error as e:
                logger.warning(f"Failed to compile memory relationship pattern: {e}")

        self.compiled_entity_patterns = []
        for pattern, rel_type, confidence in self.ENTITY_RELATIONSHIP_PATTERNS:
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                self.compiled_entity_patterns.append((compiled, rel_type, confidence))
            except re.error as e:
                logger.warning(f"Failed to compile entity relationship pattern: {e}")

    def detect_memory_relationships(
        self, new_memory: Memory, existing_memories: list[Memory]
    ) -> list[Relationship]:
        """
        Detect relationships between a new memory and existing memories.

        Args:
            new_memory: New memory to analyze
            existing_memories: List of existing memories to compare against

        Returns:
            List of detected relationships
        """
        relationships = []

        for existing_memory in existing_memories:
            # Skip expired memories
            if not existing_memory.is_valid():
                continue

            # Detect pattern-based relationships
            pattern_relationships = self._detect_pattern_relationships(new_memory, existing_memory)
            relationships.extend(pattern_relationships)

            # Detect semantic relationships
            semantic_relationships = self._detect_semantic_relationships(
                new_memory, existing_memory
            )
            relationships.extend(semantic_relationships)

            # Detect temporal relationships
            temporal_relationships = self._detect_temporal_relationships(
                new_memory, existing_memory
            )
            relationships.extend(temporal_relationships)

        # Update statistics
        self._update_relationship_stats(relationships)

        return relationships

    def _detect_pattern_relationships(
        self, new_memory: Memory, existing_memory: Memory
    ) -> list[Relationship]:
        """Detect relationships using pattern matching."""
        relationships = []

        for pattern, rel_type, confidence in self.compiled_memory_patterns:
            matches = pattern.finditer(new_memory.content)

            for match in matches:
                # Check if the match context relates to the existing memory
                match_context = match.group(1) if match.groups() else match.group(0)

                if self._contexts_are_related(match_context, existing_memory.content):
                    relationship = Relationship(
                        source_id=new_memory.id,
                        target_id=existing_memory.id,
                        relationship_type=rel_type,
                        confidence=confidence,
                        context=match_context.strip(),
                    )
                    relationships.append(relationship)

        return relationships

    def _detect_semantic_relationships(
        self, new_memory: Memory, existing_memory: Memory
    ) -> list[Relationship]:
        """Detect relationships based on semantic similarity."""
        relationships = []

        # Calculate entity overlap
        new_entities = set(new_memory.entities)
        existing_entities = set(existing_memory.entities)

        if new_entities and existing_entities:
            overlap = new_entities.intersection(existing_entities)
            overlap_ratio = len(overlap) / len(new_entities.union(existing_entities))

            if overlap_ratio > 0.3:  # Significant entity overlap
                relationship = Relationship(
                    source_id=new_memory.id,
                    target_id=existing_memory.id,
                    relationship_type="related_to",
                    confidence=min(0.9, overlap_ratio * 2),  # Scale confidence
                    context=f"Shared entities: {', '.join(overlap)}",
                )
                relationships.append(relationship)

        # Check for topic similarity based on memory types
        if new_memory.memory_type == existing_memory.memory_type and new_memory.memory_type in [
            MemoryType.SEMANTIC,
            MemoryType.PROCEDURAL,
        ]:
            # Same type memories in specific categories are likely related
            relationship = Relationship(
                source_id=new_memory.id,
                target_id=existing_memory.id,
                relationship_type="same_topic",
                confidence=0.7,
                context=f"Both are {new_memory.memory_type.value} memories",
            )
            relationships.append(relationship)

        return relationships

    def _detect_temporal_relationships(
        self, new_memory: Memory, existing_memory: Memory
    ) -> list[Relationship]:
        """Detect relationships based on temporal proximity."""
        relationships = []

        # Check if memories are from the same session
        if (
            new_memory.session_id
            and existing_memory.session_id
            and new_memory.session_id == existing_memory.session_id
        ):
            # Check that both memories have created_at timestamps
            if new_memory.created_at and existing_memory.created_at:
                time_diff = abs(
                    (new_memory.created_at - existing_memory.created_at).total_seconds()
                )

                # If memories are within 5 minutes of each other in the same session
                if time_diff < 300:  # 5 minutes
                    relationship = Relationship(
                        source_id=new_memory.id,
                        target_id=existing_memory.id,
                        relationship_type="same_session",
                        confidence=0.8,
                        context=f"Same session, {time_diff:.0f}s apart",
                    )
                    relationships.append(relationship)

        return relationships

    def _contexts_are_related(self, context1: str, context2: str, threshold: float = 0.3) -> bool:
        """Check if two contexts are related based on word overlap."""
        if not context1 or not context2:
            return False

        # Tokenize and normalize
        words1 = {word.lower() for word in context1.split() if len(word) > 2}
        words2 = {word.lower() for word in context2.split() if len(word) > 2}

        if not words1 or not words2:
            return False

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold

    def detect_entity_relationships(self, entities: list[Entity], text: str) -> list[Relationship]:
        """
        Detect relationships between entities in text.

        Args:
            entities: List of entities to analyze
            text: Original text containing the entities

        Returns:
            List of detected relationships
        """
        relationships = []

        # Sort entities by position for proximity analysis
        sorted_entities = sorted(entities, key=lambda e: e.start_pos)

        for i, entity1 in enumerate(sorted_entities):
            for entity2 in sorted_entities[i + 1 :]:
                # Check proximity (entities within 100 characters)
                distance = entity2.start_pos - entity1.end_pos
                if distance > 100:
                    continue

                # Extract context between entities
                context = text[entity1.end_pos : entity2.start_pos]

                # Try to match relationship patterns
                for pattern, rel_type, confidence in self.compiled_entity_patterns:
                    full_context = text[entity1.start_pos : entity2.end_pos]
                    match = pattern.search(full_context)

                    if match:
                        relationship = Relationship(
                            source_id=entity1.text,
                            target_id=entity2.text,
                            relationship_type=rel_type,
                            confidence=confidence,
                            context=context.strip(),
                        )
                        relationships.append(relationship)
                        break

        return relationships

    def _update_relationship_stats(self, relationships: list[Relationship]) -> None:
        """Update relationship detection statistics."""
        self._detection_stats["total_relationships"] += len(relationships)

        for relationship in relationships:
            rel_type = relationship.relationship_type
            self._detection_stats["relationship_types"][rel_type] = (
                self._detection_stats["relationship_types"].get(rel_type, 0) + 1
            )

    def get_relationship_statistics(self) -> dict[str, any]:
        """Get relationship detection statistics."""
        return {
            "total_patterns": len(self.compiled_memory_patterns)
            + len(self.compiled_entity_patterns),
            "memory_patterns": len(self.compiled_memory_patterns),
            "entity_patterns": len(self.compiled_entity_patterns),
            "detection_stats": self._detection_stats.copy(),
            "top_relationship_types": sorted(
                self._detection_stats["relationship_types"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }
