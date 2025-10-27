"""
Unit tests for batch operations in KuzuMemory.

Tests the batch_store_memories and batch_get_memories_by_ids methods
to ensure efficient bulk operations work correctly.
"""

import uuid
from datetime import datetime
from pathlib import Path

import pytest

from kuzu_memory import KuzuMemory, Memory, MemoryType
from kuzu_memory.utils.exceptions import DatabaseError, ValidationError


class TestBatchOperations:
    """Test suite for batch memory operations."""

    @pytest.fixture
    def kuzu_memory(self, tmp_path):
        """Create a KuzuMemory instance for testing."""
        db_path = tmp_path / "test_batch.db"
        km = KuzuMemory(db_path=db_path)
        yield km
        km.close()

    @pytest.fixture
    def sample_memories(self) -> list[Memory]:
        """Create sample Memory objects for testing."""
        return [
            Memory(
                id=str(uuid.uuid4()),
                content=f"Memory {i}: Test content for batch operations",
                memory_type=MemoryType.SEMANTIC if i % 2 == 0 else MemoryType.EPISODIC,
                source_type="test",
                importance=min(0.5 + (i * 0.05), 1.0),  # Cap at 1.0
                confidence=0.9,
                created_at=datetime.now(),
                metadata={"index": i, "batch_test": True},
            )
            for i in range(10)
        ]

    def test_batch_store_memories_success(self, kuzu_memory, sample_memories):
        """Test successful batch storage of memories."""
        # Store memories
        stored_ids = kuzu_memory.batch_store_memories(sample_memories)

        # Verify all memories were stored
        assert len(stored_ids) == len(sample_memories)
        assert all(isinstance(id, str) for id in stored_ids)

        # Verify each memory can be retrieved
        for memory, stored_id in zip(sample_memories, stored_ids, strict=False):
            retrieved = kuzu_memory.get_memory_by_id(stored_id)
            assert retrieved is not None
            assert retrieved.content == memory.content
            assert retrieved.memory_type == memory.memory_type

    def test_batch_store_memories_empty_list(self, kuzu_memory):
        """Test batch storage with empty list."""
        result = kuzu_memory.batch_store_memories([])
        assert result == []

    def test_batch_store_memories_invalid_input(self, kuzu_memory):
        """Test batch storage with invalid input types."""
        with pytest.raises(ValidationError):
            kuzu_memory.batch_store_memories("not a list")

        with pytest.raises(ValidationError):
            kuzu_memory.batch_store_memories([{"not": "a memory"}])

    def test_batch_get_memories_by_ids_success(self, kuzu_memory, sample_memories):
        """Test successful batch retrieval of memories by IDs."""
        # First store the memories
        stored_ids = kuzu_memory.batch_store_memories(sample_memories)

        # Retrieve them in batch
        retrieved = kuzu_memory.batch_get_memories_by_ids(stored_ids)

        # Verify all memories were retrieved
        assert len(retrieved) == len(stored_ids)

        # Verify content matches
        retrieved_contents = {m.id: m.content for m in retrieved}
        for memory_id in stored_ids:
            assert memory_id in retrieved_contents

    def test_batch_get_memories_partial_results(self, kuzu_memory, sample_memories):
        """Test batch retrieval with mix of valid and invalid IDs."""
        # Store some memories
        stored_ids = kuzu_memory.batch_store_memories(sample_memories[:5])

        # Mix valid and invalid IDs
        mixed_ids = [*stored_ids[:3], "invalid-id-1", "invalid-id-2"]

        # Retrieve memories
        retrieved = kuzu_memory.batch_get_memories_by_ids(mixed_ids)

        # Should only get the valid memories
        assert len(retrieved) == 3
        retrieved_ids = {m.id for m in retrieved}
        assert all(id in retrieved_ids for id in stored_ids[:3])

    def test_batch_get_memories_empty_list(self, kuzu_memory):
        """Test batch retrieval with empty list."""
        result = kuzu_memory.batch_get_memories_by_ids([])
        assert result == []

    def test_batch_get_memories_invalid_input(self, kuzu_memory):
        """Test batch retrieval with invalid input types."""
        with pytest.raises(ValidationError):
            kuzu_memory.batch_get_memories_by_ids("not a list")

    def test_batch_operations_with_cache(self, kuzu_memory, sample_memories):
        """Test that batch operations work correctly with caching enabled."""
        # Store memories
        stored_ids = kuzu_memory.batch_store_memories(sample_memories[:3])

        # First retrieval (cache miss)
        retrieved1 = kuzu_memory.batch_get_memories_by_ids(stored_ids)
        assert len(retrieved1) == 3

        # Second retrieval (should hit cache)
        retrieved2 = kuzu_memory.batch_get_memories_by_ids(stored_ids)
        assert len(retrieved2) == 3

        # Verify content is identical
        for m1, m2 in zip(retrieved1, retrieved2, strict=False):
            assert m1.id == m2.id
            assert m1.content == m2.content

    def test_batch_store_duplicate_ids(self, kuzu_memory):
        """Test batch storage with duplicate IDs (should update)."""
        memory_id = str(uuid.uuid4())

        # Create two memories with same ID but different content
        memory1 = Memory(
            id=memory_id,
            content="Original content",
            memory_type=MemoryType.SEMANTIC,
            source_type="test",
            created_at=datetime.now(),
        )

        memory2 = Memory(
            id=memory_id,
            content="Updated content",
            memory_type=MemoryType.SEMANTIC,
            source_type="test",
            created_at=datetime.now(),
        )

        # Store first batch
        stored1 = kuzu_memory.batch_store_memories([memory1])
        assert len(stored1) == 1

        # Store second batch (should update)
        stored2 = kuzu_memory.batch_store_memories([memory2])
        assert len(stored2) == 1
        assert stored2[0] == memory_id

        # Verify the content was updated
        retrieved = kuzu_memory.get_memory_by_id(memory_id)
        assert retrieved.content == "Updated content"

    def test_batch_performance_stats(self, kuzu_memory, sample_memories):
        """Test that batch operations update performance statistics correctly."""
        # Get initial stats
        initial_stats = kuzu_memory.get_statistics()
        initial_generated = initial_stats["performance_stats"][
            "total_memories_generated"
        ]
        initial_recalled = initial_stats["performance_stats"]["total_memories_recalled"]

        # Store memories
        stored_ids = kuzu_memory.batch_store_memories(sample_memories)

        # Retrieve memories
        kuzu_memory.batch_get_memories_by_ids(stored_ids)

        # Get updated stats
        final_stats = kuzu_memory.get_statistics()
        final_generated = final_stats["performance_stats"]["total_memories_generated"]
        final_recalled = final_stats["performance_stats"]["total_memories_recalled"]

        # Verify stats were updated
        assert final_generated == initial_generated + len(sample_memories)
        assert final_recalled == initial_recalled + len(stored_ids)
