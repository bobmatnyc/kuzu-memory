"""
Unit tests for KuzuMemory core models.

Tests the Memory, MemoryContext, and related data models with
validation, serialization, and business logic using pytest best practices.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from kuzu_memory.core.models import ExtractedMemory, Memory, MemoryContext, MemoryType
from kuzu_memory.utils.exceptions import ValidationError


class TestMemory:
    """Test cases for Memory model."""

    def test_memory_creation_with_defaults(self):
        """Test creating a memory with minimal required fields."""
        memory = Memory(content="Test memory content")

        assert memory.content == "Test memory content"
        assert memory.id is not None
        assert memory.content_hash is not None
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.importance == 0.7  # Default for EPISODIC type
        assert memory.confidence == 1.0
        assert memory.created_at is not None
        assert memory.valid_from is not None
        assert memory.access_count == 0
        assert memory.entities == []
        assert memory.metadata == {}

    def test_memory_creation_with_all_fields(self):
        """Test creating a memory with all fields specified."""
        created_at = datetime.now()
        valid_from = datetime.now()
        valid_to = datetime.now() + timedelta(days=30)

        memory = Memory(
            id="test-memory-id",
            content="Test memory content",
            memory_type=MemoryType.SEMANTIC,
            importance=0.9,
            confidence=0.8,
            source_type="test",
            agent_id="test-agent",
            user_id="test-user",
            session_id="test-session",
            entities=["entity1", "entity2"],
            metadata={"key": "value"},
            created_at=created_at,
            valid_from=valid_from,
            valid_to=valid_to,
            access_count=5,
        )

        assert memory.id == "test-memory-id"
        assert memory.content == "Test memory content"
        assert memory.memory_type == MemoryType.SEMANTIC
        assert memory.importance == 0.9
        assert memory.confidence == 0.8
        assert memory.source_type == "test"
        assert memory.agent_id == "test-agent"
        assert memory.user_id == "test-user"
        assert memory.session_id == "test-session"
        assert set(memory.entities) == {"entity1", "entity2"}  # Order doesn't matter
        assert memory.metadata == {"key": "value"}
        assert memory.created_at == created_at
        assert memory.valid_from == valid_from
        assert memory.valid_to == valid_to
        assert memory.access_count == 5

    def test_memory_type_default_importance(self):
        """Test that memory types get correct default importance scores."""
        semantic_memory = Memory(content="Test", memory_type=MemoryType.SEMANTIC)
        assert semantic_memory.importance == 1.0

        preference_memory = Memory(content="Test", memory_type=MemoryType.PREFERENCE)
        assert preference_memory.importance == 0.9

        working_memory = Memory(content="Test", memory_type=MemoryType.WORKING)
        assert working_memory.importance == 0.5

    def test_memory_type_default_retention(self):
        """Test that memory types get correct default retention periods."""
        # Semantic memories never expire
        semantic_memory = Memory(content="Test", memory_type=MemoryType.SEMANTIC)
        assert semantic_memory.valid_to is None

        # Working memories expire quickly
        working_memory = Memory(content="Test", memory_type=MemoryType.WORKING)
        assert working_memory.valid_to is not None
        expected_expiry = working_memory.valid_from + timedelta(days=1)
        assert abs((working_memory.valid_to - expected_expiry).total_seconds()) < 1

    def test_content_hash_generation(self):
        """Test that content hash is generated correctly."""
        memory1 = Memory(content="Test content")
        memory2 = Memory(content="Test content")
        memory3 = Memory(content="Different content")

        # Same content should have same hash
        assert memory1.content_hash == memory2.content_hash

        # Different content should have different hash
        assert memory1.content_hash != memory3.content_hash

        # Hash should be consistent
        assert len(memory1.content_hash) == 64  # SHA256 hex length

    def test_memory_validity(self):
        """Test memory validity checking."""
        now = datetime.now()

        # Memory that never expires (use SEMANTIC type which has no retention period)
        permanent_memory = Memory(
            content="Test", memory_type=MemoryType.SEMANTIC, valid_to=None
        )
        assert permanent_memory.is_valid()
        assert permanent_memory.is_valid(now + timedelta(days=365))

        # Memory that expires in the future
        future_expiry = Memory(content="Test", valid_to=now + timedelta(hours=1))
        assert future_expiry.is_valid()
        assert future_expiry.is_valid(now + timedelta(minutes=30))
        assert not future_expiry.is_valid(now + timedelta(hours=2))

        # Memory that has already expired
        past_expiry = Memory(content="Test", valid_to=now - timedelta(hours=1))
        assert not past_expiry.is_valid()
        assert past_expiry.is_expired()

    def test_memory_access_tracking(self):
        """Test memory access tracking."""
        memory = Memory(content="Test")
        initial_access_time = memory.accessed_at
        initial_count = memory.access_count

        # Update access
        memory.update_access()

        assert memory.access_count == initial_count + 1
        assert memory.accessed_at > initial_access_time

    def test_memory_serialization(self):
        """Test memory to_dict and from_dict methods."""
        original_memory = Memory(
            content="Test content",
            memory_type=MemoryType.PREFERENCE,
            importance=0.8,
            entities=["entity1", "entity2"],
            metadata={"key": "value"},
        )

        # Serialize to dict
        memory_dict = original_memory.to_dict()

        # Check required fields are present
        assert "id" in memory_dict
        assert "content" in memory_dict
        assert "content_hash" in memory_dict
        assert "memory_type" in memory_dict
        assert memory_dict["memory_type"] == "preference"

        # Deserialize from dict
        restored_memory = Memory.from_dict(memory_dict)

        # Check that restored memory matches original
        assert restored_memory.id == original_memory.id
        assert restored_memory.content == original_memory.content
        assert restored_memory.content_hash == original_memory.content_hash
        assert restored_memory.memory_type == original_memory.memory_type
        assert restored_memory.importance == original_memory.importance
        assert restored_memory.entities == original_memory.entities
        assert restored_memory.metadata == original_memory.metadata

    def test_memory_validation(self):
        """Test memory content validation."""
        # Valid memory
        valid_memory = Memory(content="Valid content")
        assert valid_memory.content == "Valid content"

        # Empty content should raise error
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            Memory(content="")

        with pytest.raises(ValueError, match="Content cannot be empty"):
            Memory(content="   ")  # Whitespace only

    def test_entity_deduplication(self):
        """Test that duplicate entities are removed."""
        memory = Memory(
            content="Test",
            entities=["entity1", "entity2", "entity1", "entity3", "entity2"],
        )

        # Should remove duplicates and maintain order
        assert len(memory.entities) == 3
        assert set(memory.entities) == {"entity1", "entity2", "entity3"}


class TestMemoryContext:
    """Test cases for MemoryContext model."""

    def test_memory_context_creation(self):
        """Test creating a memory context."""
        memories = [
            Memory(content="Memory 1", importance=0.9),
            Memory(content="Memory 2", importance=0.7),
        ]

        context = MemoryContext(
            original_prompt="What is my name?",
            enhanced_prompt="## Context\n- Memory 1\n- Memory 2\n\nWhat is my name?",
            memories=memories,
            confidence=0.85,
            strategy_used="keyword",
            recall_time_ms=5.2,
        )

        assert context.original_prompt == "What is my name?"
        assert "## Context" in context.enhanced_prompt
        assert len(context.memories) == 2
        assert context.confidence == 0.85
        assert context.strategy_used == "keyword"
        assert context.recall_time_ms == 5.2

    def test_memory_context_token_count_calculation(self):
        """Test that token count is calculated correctly."""
        context = MemoryContext(
            original_prompt="Test prompt",
            enhanced_prompt="This is a longer enhanced prompt with more content",
            memories=[],
        )

        # Token count should be roughly length / 4
        expected_tokens = len(context.enhanced_prompt) // 4
        assert abs(context.token_count - expected_tokens) <= 1

    def test_memory_context_confidence_calculation(self):
        """Test confidence calculation from memories."""
        memories = [
            Memory(content="Memory 1", confidence=0.9),
            Memory(content="Memory 2", confidence=0.7),
            Memory(content="Memory 3", confidence=0.8),
        ]

        context = MemoryContext(
            original_prompt="Test", enhanced_prompt="Test", memories=memories
        )

        # Should calculate average confidence
        expected_confidence = (0.9 + 0.7 + 0.8) / 3
        assert abs(context.confidence - expected_confidence) < 0.01

    def test_memory_context_system_message_formats(self):
        """Test different system message formats."""
        memories = [
            Memory(content="User's name is Alice"),
            Memory(content="User prefers Python"),
        ]

        context = MemoryContext(
            original_prompt="What's my name?",
            enhanced_prompt="Enhanced prompt",
            memories=memories,
        )

        # Markdown format
        markdown_msg = context.to_system_message("markdown")
        assert "## Relevant Context:" in markdown_msg
        assert "- User's name is Alice" in markdown_msg
        assert "What's my name?" in markdown_msg

        # Plain format
        plain_msg = context.to_system_message("plain")
        assert "Relevant context:" in plain_msg
        assert "1. User's name is Alice" in plain_msg
        assert "User query: What's my name?" in plain_msg

        # JSON format
        json_msg = context.to_system_message("json")
        import json

        parsed = json.loads(json_msg)
        assert "context" in parsed
        assert "query" in parsed
        assert len(parsed["context"]) == 2

    def test_memory_context_summary(self):
        """Test memory summary generation."""
        memories = [
            Memory(
                content="Memory 1",
                memory_type=MemoryType.SEMANTIC,
                importance=0.9,
                confidence=0.8,
                entities=["Alice"],
            ),
            Memory(
                content="Memory 2",
                memory_type=MemoryType.PREFERENCE,
                importance=0.7,
                confidence=0.9,
                entities=["Python", "coding"],
            ),
            Memory(
                content="Memory 3",
                memory_type=MemoryType.SEMANTIC,
                importance=0.8,
                confidence=0.7,
                entities=["Alice"],
            ),
        ]

        context = MemoryContext(
            original_prompt="Test", enhanced_prompt="Test", memories=memories
        )

        summary = context.get_memory_summary()

        assert summary["count"] == 3
        assert summary["types"]["semantic"] == 2
        assert summary["types"]["preference"] == 1
        assert abs(summary["avg_importance"] - 0.8) < 0.01
        assert abs(summary["avg_confidence"] - 0.8) < 0.01
        assert set(summary["entities"]) == {"Alice", "Python", "coding"}


class TestExtractedMemory:
    """Test cases for ExtractedMemory model."""

    def test_extracted_memory_creation(self):
        """Test creating an extracted memory."""
        extracted = ExtractedMemory(
            content="Test extracted content",
            confidence=0.85,
            memory_type=MemoryType.PREFERENCE,
            pattern_used="preference_pattern",
            entities=["entity1"],
            metadata={"source": "test"},
        )

        assert extracted.content == "Test extracted content"
        assert extracted.confidence == 0.85
        assert extracted.memory_type == MemoryType.PREFERENCE
        assert extracted.pattern_used == "preference_pattern"
        assert extracted.entities == ["entity1"]
        assert extracted.metadata == {"source": "test"}

    def test_extracted_memory_to_memory_conversion(self):
        """Test converting extracted memory to full memory."""
        extracted = ExtractedMemory(
            content="Test content",
            confidence=0.8,
            memory_type=MemoryType.EPISODIC,
            pattern_used="decision_pattern",
            entities=["project", "decision"],
            metadata={"context": "meeting"},
        )

        memory = extracted.to_memory(
            source_type="extraction",
            agent_id="test-agent",
            user_id="test-user",
            session_id="test-session",
        )

        assert isinstance(memory, Memory)
        assert memory.content == extracted.content
        assert memory.memory_type == extracted.memory_type
        assert memory.confidence == extracted.confidence
        assert memory.source_type == "extraction"
        assert memory.agent_id == "test-agent"
        assert memory.user_id == "test-user"
        assert memory.session_id == "test-session"
        assert set(memory.entities) == set(extracted.entities)  # Order doesn't matter

        # Check that metadata includes extraction info
        assert "pattern_used" in memory.metadata
        assert "extraction_confidence" in memory.metadata
        assert "context" in memory.metadata  # Original metadata preserved
