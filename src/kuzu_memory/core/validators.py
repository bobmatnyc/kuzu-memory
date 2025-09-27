"""
Input validation schemas for KuzuMemory using Pydantic.

Provides validated models for API inputs and configurations.
"""

from typing import Any

from pydantic import BaseModel, Field, confloat, conint, validator

from .constants import (
    DEFAULT_AGENT_ID,
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_RECALL_STRATEGY,
    MAX_CONFIDENCE,
    MAX_CONTENT_LENGTH,
    MAX_DECAY_FACTOR,
    MAX_ID_LENGTH,
    MAX_IMPORTANCE,
    MAX_MEMORY_LIMIT,
    MIN_CONFIDENCE,
    MIN_DECAY_FACTOR,
    MIN_IMPORTANCE,
)
from .models import MemoryType


class AttachMemoriesRequest(BaseModel):
    """Validated input for attach_memories method."""

    prompt: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    max_memories: conint(ge=1, le=MAX_MEMORY_LIMIT) = DEFAULT_MEMORY_LIMIT
    strategy: str = Field(
        DEFAULT_RECALL_STRATEGY, regex="^(auto|keyword|entity|temporal)$"
    )
    user_id: str | None = Field(None, max_length=MAX_ID_LENGTH)
    session_id: str | None = Field(None, max_length=MAX_ID_LENGTH)
    agent_id: str = Field(DEFAULT_AGENT_ID, max_length=MAX_ID_LENGTH)

    @validator("prompt")
    def validate_prompt(cls, v):
        """Ensure prompt is not just whitespace."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or just whitespace")
        return v


class GenerateMemoriesRequest(BaseModel):
    """Validated input for generate_memories method."""

    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    source_type: str = Field("conversation", max_length=50)
    user_id: str | None = Field(None, max_length=MAX_ID_LENGTH)
    session_id: str | None = Field(None, max_length=MAX_ID_LENGTH)
    agent_id: str = Field(DEFAULT_AGENT_ID, max_length=MAX_ID_LENGTH)
    metadata: dict[str, Any] | None = Field(None)

    @validator("content")
    def validate_content(cls, v):
        """Ensure content is not just whitespace."""
        if not v.strip():
            raise ValueError("Content cannot be empty or just whitespace")
        return v

    @validator("metadata")
    def validate_metadata(cls, v):
        """Ensure metadata is serializable and not too large."""
        if v is not None:
            import json

            try:
                serialized = json.dumps(v)
                if len(serialized) > 5000:  # 5KB limit
                    raise ValueError("Metadata too large (max 5KB)")
            except (TypeError, ValueError) as e:
                raise ValueError(f"Metadata must be JSON serializable: {e}")
        return v


class MemoryCreationRequest(BaseModel):
    """Validated input for creating a new memory."""

    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    memory_type: MemoryType
    importance: confloat(ge=MIN_IMPORTANCE, le=MAX_IMPORTANCE) = 0.5
    confidence: confloat(ge=MIN_CONFIDENCE, le=MAX_CONFIDENCE) = 1.0
    source_type: str = Field("manual", max_length=50)
    user_id: str | None = Field(None, max_length=MAX_ID_LENGTH)
    session_id: str | None = Field(None, max_length=MAX_ID_LENGTH)
    agent_id: str = Field(DEFAULT_AGENT_ID, max_length=MAX_ID_LENGTH)
    metadata: dict[str, Any] | None = None
    entities: list[str] | None = None

    @validator("entities")
    def validate_entities(cls, v):
        """Ensure entities are valid strings."""
        if v is not None:
            cleaned = []
            for entity in v:
                if isinstance(entity, str) and entity.strip():
                    cleaned.append(entity.strip())
            return cleaned if cleaned else None
        return v


class RecallRequest(BaseModel):
    """Validated input for memory recall operations."""

    query: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    limit: conint(ge=1, le=MAX_MEMORY_LIMIT) = DEFAULT_MEMORY_LIMIT
    decay_factor: confloat(ge=MIN_DECAY_FACTOR, le=MAX_DECAY_FACTOR) = 0.9
    user_id: str | None = Field(None, max_length=MAX_ID_LENGTH)
    session_id: str | None = Field(None, max_length=MAX_ID_LENGTH)
    memory_types: list[MemoryType] | None = None
    time_range_days: conint(ge=1, le=365) | None = None

    @validator("query")
    def validate_query(cls, v):
        """Ensure query is not just whitespace."""
        if not v.strip():
            raise ValueError("Query cannot be empty or just whitespace")
        return v


class BatchMemoryRequest(BaseModel):
    """Validated input for batch memory operations."""

    memories: list[MemoryCreationRequest] = Field(..., min_items=1, max_items=1000)
    deduplicate: bool = Field(True, description="Whether to check for duplicates")
    merge_similar: bool = Field(False, description="Whether to merge similar memories")

    @validator("memories")
    def validate_batch_size(cls, v):
        """Ensure batch size is reasonable."""
        if len(v) > 100:
            import logging

            logging.getLogger(__name__).warning(
                f"Large batch size ({len(v)} memories) may impact performance"
            )
        return v


def validate_memory_id(memory_id: str) -> str:
    """
    Validate a memory ID format.

    Args:
        memory_id: Memory ID to validate

    Returns:
        Validated memory ID

    Raises:
        ValueError: If ID is invalid
    """
    if not memory_id or not isinstance(memory_id, str):
        raise ValueError("Memory ID must be a non-empty string")

    if len(memory_id) > MAX_ID_LENGTH:
        raise ValueError(f"Memory ID too long (max {MAX_ID_LENGTH} characters)")

    # Basic format validation (alphanumeric with hyphens/underscores)
    import re

    if not re.match(r"^[a-zA-Z0-9_-]+$", memory_id):
        raise ValueError(
            "Memory ID must contain only alphanumeric characters, hyphens, and underscores"
        )

    return memory_id
