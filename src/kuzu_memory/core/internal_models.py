"""
Internal data structures using dataclasses for high-performance operations.

These models are used internally within KuzuMemory for core operations,
providing better performance than Pydantic models while maintaining
type safety and validation.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from .models import MemoryType


@dataclass(slots=True, frozen=False)
class InternalMemory:
    """
    High-performance internal representation of a memory.

    Uses dataclasses with slots for memory efficiency and speed.
    Optimized for internal operations without validation overhead.
    """

    # Core content
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    content_hash: str = ""

    # Temporal information
    created_at: datetime = field(default_factory=datetime.now)
    valid_from: datetime = field(default_factory=datetime.now)
    valid_to: datetime | None = None
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    # Classification
    memory_type: MemoryType = MemoryType.EPISODIC
    importance: float = 0.5
    confidence: float = 1.0

    # Source tracking
    source_type: str = "conversation"
    agent_id: str = "default"
    user_id: str | None = None
    session_id: str | None = None

    # Metadata and relationships
    metadata: dict[str, Any] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize computed fields after object creation."""
        # Generate content hash if not provided
        if not self.content_hash and self.content:
            normalized = self.content.lower().strip()
            self.content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        # Set default importance based on memory type
        if self.importance == 0.5:  # Default value
            self.importance = MemoryType.get_default_importance(self.memory_type)

        # Set default expiration based on memory type
        if self.valid_to is None:
            retention = MemoryType.get_default_retention(self.memory_type)
            if retention:
                self.valid_to = self.valid_from + retention

    def is_valid(self, at_time: datetime | None = None) -> bool:
        """Check if memory is currently valid."""
        check_time = at_time or datetime.now()

        if check_time < self.valid_from:
            return False

        if self.valid_to and check_time > self.valid_to:
            return False

        return True

    def is_expired(self, at_time: datetime | None = None) -> bool:
        """Check if memory has expired."""
        return not self.is_valid(at_time)

    def update_access(self) -> None:
        """Update access tracking information."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "content": self.content,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "confidence": self.confidence,
            "source_type": self.source_type,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": json.dumps(self.metadata) if self.metadata else "{}",
            "entities": json.dumps(self.entities) if self.entities else "[]",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InternalMemory":
        """Create InternalMemory from dictionary."""
        # Parse datetime fields
        for field_name in ["created_at", "valid_from", "valid_to", "accessed_at"]:
            if data.get(field_name):
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])

        # Parse JSON fields
        if isinstance(data.get("metadata"), str):
            data["metadata"] = json.loads(data["metadata"])
        if isinstance(data.get("entities"), str):
            data["entities"] = json.loads(data["entities"])

        # Convert memory_type string to enum
        if isinstance(data.get("memory_type"), str):
            data["memory_type"] = MemoryType(data["memory_type"])

        return cls(**data)


@dataclass(slots=True, frozen=False)
class InternalMemoryContext:
    """
    High-performance internal representation of memory context.

    Used for internal operations where validation overhead is not needed.
    """

    # Core content
    original_prompt: str = ""
    enhanced_prompt: str = ""
    memories: list[InternalMemory] = field(default_factory=list)

    # Metadata
    confidence: float = 0.0
    token_count: int = 0
    strategy_used: str = "auto"
    recall_time_ms: float = 0.0

    # Statistics
    total_memories_found: int = 0
    memories_filtered: int = 0

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        # Calculate token count (rough estimate: 1 token ≈ 4 characters)
        self.token_count = len(self.enhanced_prompt) // 4

        # Calculate average confidence from memories
        if self.memories:
            avg_confidence = sum(mem.confidence for mem in self.memories) / len(self.memories)
            self.confidence = min(avg_confidence, self.confidence or 1.0)

    def to_system_message(self, format_style: str = "markdown") -> str:
        """Format as system message for LLM integration."""
        if not self.memories:
            return self.original_prompt

        if format_style == "markdown":
            context = "## Relevant Context:\n"
            for mem in self.memories:
                context += f"- {mem.content}\n"
            return f"{context}\n{self.original_prompt}"

        elif format_style == "plain":
            context = "Relevant context:\n"
            for i, mem in enumerate(self.memories, 1):
                context += f"{i}. {mem.content}\n"
            return f"{context}\nUser query: {self.original_prompt}"

        elif format_style == "json":
            return json.dumps(
                {
                    "context": [mem.content for mem in self.memories],
                    "query": self.original_prompt,
                    "confidence": self.confidence,
                }
            )

        else:
            raise ValueError(f"Unknown format_style: {format_style}")

    def get_memory_summary(self) -> dict[str, Any]:
        """Get summary statistics about retrieved memories."""
        if not self.memories:
            return {
                "count": 0,
                "types": {},
                "avg_importance": 0.0,
                "avg_confidence": 0.0,
                "entities": [],
            }

        # Count by type
        type_counts: dict[str, int] = {}
        for mem in self.memories:
            type_counts[mem.memory_type.value] = type_counts.get(mem.memory_type.value, 0) + 1

        # Calculate averages
        avg_importance = sum(mem.importance for mem in self.memories) / len(self.memories)
        avg_confidence = sum(mem.confidence for mem in self.memories) / len(self.memories)

        # Collect unique entities
        all_entities = set()
        for mem in self.memories:
            all_entities.update(mem.entities)

        return {
            "count": len(self.memories),
            "types": type_counts,
            "avg_importance": round(avg_importance, 3),
            "avg_confidence": round(avg_confidence, 3),
            "entities": sorted(all_entities),
        }


@dataclass(slots=True, frozen=False)
class InternalExtractedMemory:
    """
    High-performance internal representation of extracted memory.

    Used during the extraction process for candidate memories.
    """

    content: str = ""
    confidence: float = 0.0
    memory_type: MemoryType = MemoryType.EPISODIC
    pattern_used: str = ""
    entities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_internal_memory(
        self,
        source_type: str = "extraction",
        agent_id: str = "default",
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> InternalMemory:
        """Convert to a full InternalMemory object."""
        return InternalMemory(
            content=self.content,
            memory_type=self.memory_type,
            importance=MemoryType.get_default_importance(self.memory_type),
            confidence=self.confidence,
            source_type=source_type,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            entities=self.entities.copy(),
            metadata={
                **self.metadata,
                "pattern_used": self.pattern_used,
                "extraction_confidence": self.confidence,
            },
        )


@dataclass(slots=True, frozen=True)
class QueryResult:
    """
    High-performance result container for database queries.

    Immutable result object that can be cached efficiently.
    """

    memories: list[InternalMemory]
    total_count: int
    query_time_ms: float
    cached: bool = False
    cache_key: str | None = None

    @property
    def count(self) -> int:
        """Number of memories in this result."""
        return len(self.memories)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "memories": [mem.to_dict() for mem in self.memories],
            "total_count": self.total_count,
            "query_time_ms": self.query_time_ms,
            "cached": self.cached,
            "cache_key": self.cache_key,
        }


@dataclass(slots=True, frozen=False)
class PerformanceMetric:
    """
    High-performance metric data structure.

    Used for tracking performance metrics throughout the system.
    """

    name: str
    value: float
    metric_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage or export."""
        return {
            "name": self.name,
            "value": self.value,
            "metric_type": self.metric_type,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformanceMetric":
        """Create from dictionary."""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


# Conversion functions between Pydantic and internal models
def pydantic_to_internal_memory(pydantic_memory: Any) -> InternalMemory:
    """Convert a Pydantic Memory to InternalMemory."""
    return InternalMemory(
        id=pydantic_memory.id,
        content=pydantic_memory.content,
        content_hash=pydantic_memory.content_hash,
        created_at=pydantic_memory.created_at,
        valid_from=pydantic_memory.valid_from,
        valid_to=pydantic_memory.valid_to,
        accessed_at=pydantic_memory.accessed_at,
        access_count=pydantic_memory.access_count,
        memory_type=pydantic_memory.memory_type,
        importance=pydantic_memory.importance,
        confidence=pydantic_memory.confidence,
        source_type=pydantic_memory.source_type,
        agent_id=pydantic_memory.agent_id,
        user_id=pydantic_memory.user_id,
        session_id=pydantic_memory.session_id,
        metadata=pydantic_memory.metadata.copy(),
        entities=pydantic_memory.entities.copy(),
    )


def internal_to_pydantic_memory(internal_memory: InternalMemory) -> Any:
    """Convert InternalMemory to Pydantic Memory."""
    from .models import Memory

    return Memory(
        id=internal_memory.id,
        content=internal_memory.content,
        content_hash=internal_memory.content_hash,
        created_at=internal_memory.created_at,
        valid_from=internal_memory.valid_from,
        valid_to=internal_memory.valid_to,
        accessed_at=internal_memory.accessed_at,
        access_count=internal_memory.access_count,
        memory_type=internal_memory.memory_type,
        importance=internal_memory.importance,
        confidence=internal_memory.confidence,
        source_type=internal_memory.source_type,
        agent_id=internal_memory.agent_id,
        user_id=internal_memory.user_id,
        session_id=internal_memory.session_id,
        metadata=internal_memory.metadata.copy(),
        entities=internal_memory.entities.copy(),
    )
