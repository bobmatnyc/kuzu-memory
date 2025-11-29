"""
Core data models for KuzuMemory.

Defines the primary data structures used throughout the system,
including Memory, MemoryContext, and related types with full
validation and serialization support.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

# Removed circular import - using inline validation


class MemoryType(str, Enum):
    """
    Cognitive memory types based on human memory systems.

    Each type represents a different category of information storage:
    - EPISODIC: Personal experiences and events (30 days retention)
    - SEMANTIC: Facts and general knowledge (never expires)
    - PROCEDURAL: Instructions and how-to content (never expires)
    - WORKING: Tasks and current focus (1 day retention)
    - SENSORY: Sensory descriptions (6 hours retention)
    - PREFERENCE: User/team preferences (never expires)
    """

    EPISODIC = "episodic"  # Personal experiences and events
    SEMANTIC = "semantic"  # Facts and general knowledge
    PROCEDURAL = "procedural"  # Instructions and how-to content
    WORKING = "working"  # Tasks and current focus
    SENSORY = "sensory"  # Sensory descriptions
    PREFERENCE = "preference"  # User/team preferences

    @classmethod
    def get_default_retention(cls, memory_type: MemoryType) -> timedelta | None:
        """Get default retention period for memory type."""
        retention_map = {
            cls.EPISODIC: timedelta(days=30),  # Personal experiences fade
            cls.SEMANTIC: None,  # Facts don't expire
            cls.PROCEDURAL: None,  # Instructions don't expire
            cls.WORKING: timedelta(days=1),  # Tasks are short-lived
            cls.SENSORY: timedelta(hours=6),  # Sensory memories fade quickly
            cls.PREFERENCE: None,  # Preferences persist
        }
        return retention_map.get(memory_type)

    @classmethod
    def get_default_importance(cls, memory_type: MemoryType) -> float:
        """Get default importance score for memory type."""
        importance_map = {
            cls.EPISODIC: 0.7,  # Medium-high importance
            cls.SEMANTIC: 1.0,  # Highest importance (facts)
            cls.PROCEDURAL: 0.9,  # High importance (instructions)
            cls.WORKING: 0.5,  # Medium importance (temporary)
            cls.SENSORY: 0.3,  # Low importance (ephemeral)
            cls.PREFERENCE: 0.9,  # High importance (user preferences)
        }
        return importance_map.get(memory_type, 0.5)

    @classmethod
    def from_legacy_type(cls, legacy_type: str) -> MemoryType:
        """Convert legacy memory type to cognitive type."""
        migration_map = {
            "identity": cls.SEMANTIC,  # Facts about identity
            "preference": cls.PREFERENCE,  # Unchanged
            "decision": cls.EPISODIC,  # Decisions are events
            "pattern": cls.PROCEDURAL,  # Patterns are procedures
            "solution": cls.PROCEDURAL,  # Solutions are instructions
            "status": cls.WORKING,  # Status is current work
            "context": cls.EPISODIC,  # Context is experiential
        }
        return migration_map.get(legacy_type.lower(), cls.EPISODIC)


class Memory(BaseModel):
    """
    Core memory model representing a single piece of stored information.

    Includes temporal validity, classification, source tracking, and metadata
    with automatic hash generation for deduplication.
    """

    # Pydantic V2 configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "User prefers Python for backend development",
                "memory_type": "preference",
                "importance": 0.9,
                "entities": ["Python", "backend"],
                "metadata": {"extracted_by": "pattern_matcher"},
            }
        }
    )

    # Core content
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique memory identifier")
    content: str = Field(..., min_length=1, max_length=100_000, description="Memory content text")
    content_hash: str = Field(default="", description="SHA256 hash for deduplication")

    # Temporal information
    created_at: datetime = Field(
        default_factory=datetime.now, description="When memory was created"
    )
    valid_from: datetime | None = Field(
        default_factory=datetime.now, description="When memory becomes valid"
    )
    valid_to: datetime | None = Field(None, description="When memory expires (None = never)")
    accessed_at: datetime | None = Field(
        default_factory=datetime.now, description="Last access time"
    )
    access_count: int = Field(default=0, ge=0, description="Number of times accessed")

    # Classification
    memory_type: MemoryType = Field(default=MemoryType.EPISODIC, description="Type of memory")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance score (0-1)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score (0-1)")

    # Source tracking
    source_type: str = Field(default="conversation", description="Source of the memory")
    agent_id: str = Field(default="default", description="Agent that created the memory")
    user_id: str | None = Field(None, description="Associated user ID")
    session_id: str | None = Field(None, description="Associated session ID")

    # Metadata and relationships
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    entities: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Extracted entities"
    )

    # Pydantic V2 serializers for custom datetime formatting
    @field_serializer("created_at", "valid_from", "valid_to", "accessed_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO format."""
        return dt.isoformat() if dt else None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate and sanitize content."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        if len(v) > 100000:  # 100KB limit
            raise ValueError("Content exceeds maximum length")
        return v.strip()

    @field_validator("entities")
    @classmethod
    def validate_entities(cls, v: list[str | dict[str, Any]]) -> list[str | dict[str, Any]]:
        """Validate entity list."""
        if not isinstance(v, list):
            raise ValueError("Entities must be a list")
        # Remove duplicates and empty strings
        cleaned: set[str | tuple[tuple[str, Any], ...]] = set()
        result: list[str | dict[str, Any]] = []

        for entity in v:
            if isinstance(entity, str):
                entity_str = entity.strip()
                if entity_str and entity_str not in cleaned:
                    cleaned.add(entity_str)
                    result.append(entity_str)
            elif isinstance(entity, dict) and entity:
                # For dicts, create a hashable representation for deduplication
                entity_tuple = tuple(sorted(entity.items()))
                if entity_tuple not in cleaned:
                    cleaned.add(entity_tuple)
                    result.append(entity)

        return result

    @model_validator(mode="before")
    @classmethod
    def set_defaults_and_hash(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Set default values and generate content hash."""
        # Set default importance based on memory type
        if "importance" not in values or values["importance"] == 0.5:
            memory_type = values.get("memory_type", MemoryType.EPISODIC)
            values["importance"] = MemoryType.get_default_importance(memory_type)

        # Set default expiration based on memory type
        if "valid_to" not in values or values["valid_to"] is None:
            memory_type = values.get("memory_type", MemoryType.EPISODIC)
            retention = MemoryType.get_default_retention(memory_type)
            if retention:
                valid_from = values.get("valid_from", datetime.now())
                values["valid_to"] = valid_from + retention

        # Generate content hash for deduplication
        content = values.get("content", "")
        if content and not values.get("content_hash"):
            # Normalize content for hashing (lowercase, stripped)
            normalized = content.lower().strip()
            values["content_hash"] = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        return values

    def is_valid(self, at_time: datetime | None = None) -> bool:
        """
        Check if memory is currently valid.

        Args:
            at_time: Time to check validity at (default: now)

        Returns:
            True if memory is valid at the specified time
        """
        check_time = at_time or datetime.now()

        # Check if memory has started being valid
        if self.valid_from and check_time < self.valid_from:
            return False

        # Check if memory has expired
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
            "created_at": self.created_at,  # Keep as datetime for Kuzu
            "valid_from": self.valid_from,  # Keep as datetime for Kuzu
            "valid_to": self.valid_to,  # Keep as datetime for Kuzu
            "accessed_at": self.accessed_at,  # Keep as datetime for Kuzu
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
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        """Create Memory from dictionary (e.g., from database)."""
        # Parse datetime fields
        for field in ["created_at", "valid_from", "valid_to", "accessed_at"]:
            if data.get(field):
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field])

        # Parse JSON fields
        if isinstance(data.get("metadata"), str):
            data["metadata"] = json.loads(data["metadata"])
        if isinstance(data.get("entities"), str):
            data["entities"] = json.loads(data["entities"])

        # Convert memory_type string to enum
        if isinstance(data.get("memory_type"), str):
            data["memory_type"] = MemoryType(data["memory_type"])

        return cls(**data)


class MemoryContext(BaseModel):
    """
    Context object returned by attach_memories() containing the original prompt,
    enhanced prompt with memories, and metadata about the recall operation.
    """

    # Pydantic V2 configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "original_prompt": "What's my name?",
                "enhanced_prompt": "## Relevant Context:\n- User's name is Alice\n\nWhat's my name?",
                "memories": [],
                "confidence": 0.95,
                "strategy_used": "entity",
                "recall_time_ms": 3.2,
            }
        }
    )

    # Core content
    original_prompt: str = Field(..., description="Original user prompt")
    enhanced_prompt: str = Field(..., description="Prompt enhanced with memory context")
    memories: list[Memory] = Field(default_factory=list, description="Retrieved memories")

    # Metadata
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence score")
    token_count: int = Field(
        default=0, ge=0, description="Estimated token count of enhanced prompt"
    )
    strategy_used: str = Field(default="auto", description="Recall strategy that was used")
    recall_time_ms: float = Field(
        default=0.0, ge=0.0, description="Time taken for recall in milliseconds"
    )

    # Statistics
    total_memories_found: int = Field(
        default=0, ge=0, description="Total memories found before filtering"
    )
    memories_filtered: int = Field(default=0, ge=0, description="Number of memories filtered out")

    @field_validator("memories")
    @classmethod
    def validate_memories(cls, v: list[Memory]) -> list[Memory]:
        """Validate memories list."""
        if not isinstance(v, list):
            raise ValueError("Memories must be a list")
        return v

    @field_validator("enhanced_prompt")
    @classmethod
    def validate_enhanced_prompt(cls, v: str) -> str:
        """Validate enhanced prompt."""
        if not v or not v.strip():
            raise ValueError("Enhanced prompt cannot be empty")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def calculate_derived_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Calculate derived fields from memories."""
        memories = values.get("memories", [])

        # Calculate token count (rough estimate: 1 token ≈ 4 characters)
        enhanced_prompt = values.get("enhanced_prompt", "")
        values["token_count"] = len(enhanced_prompt) // 4

        # Calculate average confidence from memories
        if memories:
            avg_confidence = sum(mem.confidence for mem in memories) / len(memories)
            values["confidence"] = min(avg_confidence, values.get("confidence", 1.0))

        return values

    def to_system_message(self, format_style: str = "markdown") -> str:
        """
        Format as system message for LLM integration.

        Args:
            format_style: Formatting style ("markdown", "plain", "json")

        Returns:
            Formatted system message
        """
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
        all_entities: set[str] = set()
        for mem in self.memories:
            for entity in mem.entities:
                if isinstance(entity, str):
                    all_entities.add(entity)

        return {
            "count": len(self.memories),
            "types": type_counts,
            "avg_importance": round(avg_importance, 3),
            "avg_confidence": round(avg_confidence, 3),
            "entities": sorted(all_entities),
        }


class ExtractedMemory(BaseModel):
    """
    Temporary model for memories extracted from text before being stored.
    Used during the extraction process to hold candidate memories.
    """

    # Pydantic V2 configuration
    model_config = ConfigDict()

    content: str = Field(..., description="Extracted memory content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    memory_type: MemoryType = Field(..., description="Detected memory type")
    pattern_used: str = Field(..., description="Pattern that matched this memory")
    entities: list[str | dict[str, Any]] = Field(
        default_factory=list, description="Extracted entities"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extraction metadata")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

    def to_memory(
        self,
        source_type: str = "extraction",
        agent_id: str = "default",
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Memory:
        """
        Convert to a full Memory object.

        Args:
            source_type: Source type for the memory
            agent_id: Agent ID that extracted the memory
            user_id: Associated user ID
            session_id: Associated session ID

        Returns:
            Full Memory object ready for storage
        """
        return Memory(
            content=self.content,
            memory_type=self.memory_type,
            importance=MemoryType.get_default_importance(self.memory_type),
            confidence=self.confidence,
            source_type=source_type,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            entities=self.entities,
            valid_to=None,  # Will be set by model_validator based on memory_type
            metadata={
                **self.metadata,
                "pattern_used": self.pattern_used,
                "extraction_confidence": self.confidence,
            },
        )
