"""
Unit tests for MemoryService with mocked KuzuMemory.

Tests the MemoryService thin wrapper implementation using mock objects
to verify correct delegation to KuzuMemory without requiring actual database.

Test Strategy:
- Mock KuzuMemory and all dependencies
- Verify method delegation with correct parameters
- Verify lifecycle management (initialize/cleanup)
- Verify error handling and edge cases
- Verify context manager behavior

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Task: 1M-420 (Implement MemoryService with Protocol interface)
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from kuzu_memory.core.models import Memory, MemoryContext, MemoryType
from kuzu_memory.services.memory_service import MemoryService


@pytest.fixture
def mock_memory_store():
    """Mock MemoryStore instance."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_kuzu_memory(mock_memory_store):
    """Mock KuzuMemory instance with all required attributes."""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    mock.memory_store = mock_memory_store
    return mock


@pytest.fixture
def memory_service(mock_kuzu_memory):
    """MemoryService instance with mocked KuzuMemory."""
    with patch("kuzu_memory.services.memory_service.KuzuMemory", return_value=mock_kuzu_memory):
        service = MemoryService(db_path=Path("/tmp/test.db"))
        service.initialize()
        yield service
        service.cleanup()


class TestMemoryServiceLifecycle:
    """Test lifecycle management (initialize/cleanup)."""

    def test_initialization_creates_kuzu_memory(self, mock_kuzu_memory):
        """Test initialization creates KuzuMemory instance."""
        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ) as mock_class:
            service = MemoryService(db_path=Path("/tmp/test.db"))
            service.initialize()

            # Verify KuzuMemory was created with correct args
            mock_class.assert_called_once_with(
                db_path=Path("/tmp/test.db"),
                enable_git_sync=True,
                config={},
            )
            # Verify context manager entered
            mock_kuzu_memory.__enter__.assert_called_once()

            service.cleanup()

    def test_initialization_with_custom_config(self, mock_kuzu_memory):
        """Test initialization with custom configuration."""
        custom_config = {"performance": {"max_recall_time_ms": 100}}

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ) as mock_class:
            service = MemoryService(
                db_path=Path("/tmp/test.db"),
                enable_git_sync=False,
                config=custom_config,
            )
            service.initialize()

            # Verify custom config passed through
            mock_class.assert_called_once_with(
                db_path=Path("/tmp/test.db"),
                enable_git_sync=False,
                config=custom_config,
            )

            service.cleanup()

    def test_cleanup_exits_kuzu_memory(self, mock_kuzu_memory):
        """Test cleanup exits KuzuMemory context manager."""
        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            service = MemoryService(db_path=Path("/tmp/test.db"))
            service.initialize()
            service.cleanup()

            # Verify context manager exited
            mock_kuzu_memory.__exit__.assert_called_once_with(None, None, None)

    def test_double_initialization_safe(self, mock_kuzu_memory):
        """Test double initialization is safe (no-op)."""
        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            service = MemoryService(db_path=Path("/tmp/test.db"))
            service.initialize()
            service.initialize()  # Second call should be no-op

            # Should only create KuzuMemory once
            mock_kuzu_memory.__enter__.assert_called_once()

            service.cleanup()

    def test_context_manager_lifecycle(self, mock_kuzu_memory):
        """Test MemoryService as context manager."""
        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            with MemoryService(db_path=Path("/tmp/test.db")) as service:
                assert service._initialized
                assert service._kuzu_memory == mock_kuzu_memory
                mock_kuzu_memory.__enter__.assert_called_once()

            # After exiting context, should be cleaned up
            mock_kuzu_memory.__exit__.assert_called_once()


class TestMemoryServiceDelegation:
    """Test method delegation to KuzuMemory."""

    def test_remember_delegates_to_kuzu_memory(self, memory_service, mock_kuzu_memory):
        """Test remember() delegates to KuzuMemory."""
        mock_kuzu_memory.remember.return_value = "memory-123"

        result = memory_service.remember("test content", "cli")

        assert result == "memory-123"
        mock_kuzu_memory.remember.assert_called_once_with(
            content="test content",
            source="cli",
            session_id=None,
            agent_id=None,
            metadata=None,
        )

    def test_remember_with_all_parameters(self, memory_service, mock_kuzu_memory):
        """Test remember() with all optional parameters."""
        mock_kuzu_memory.remember.return_value = "memory-456"

        result = memory_service.remember(
            content="test content",
            source="api",
            session_id="session-1",
            agent_id="agent-1",
            metadata={"key": "value"},
        )

        assert result == "memory-456"
        mock_kuzu_memory.remember.assert_called_once_with(
            content="test content",
            source="api",
            session_id="session-1",
            agent_id="agent-1",
            metadata={"key": "value"},
        )

    def test_attach_memories_delegates_to_kuzu_memory(self, memory_service, mock_kuzu_memory):
        """Test attach_memories() delegates to KuzuMemory."""
        mock_context = MemoryContext(original_prompt="test", enhanced_prompt="test", memories=[])
        mock_kuzu_memory.attach_memories.return_value = mock_context

        result = memory_service.attach_memories("test prompt", max_memories=5)

        assert result == mock_context
        mock_kuzu_memory.attach_memories.assert_called_once_with(
            prompt="test prompt", max_memories=5, strategy="auto"
        )

    def test_attach_memories_with_strategy(self, memory_service, mock_kuzu_memory):
        """Test attach_memories() with custom strategy."""
        mock_context = MemoryContext(original_prompt="test", enhanced_prompt="test", memories=[])
        mock_kuzu_memory.attach_memories.return_value = mock_context

        result = memory_service.attach_memories("test prompt", max_memories=10, strategy="entity")

        assert result == mock_context
        mock_kuzu_memory.attach_memories.assert_called_once_with(
            prompt="test prompt", max_memories=10, strategy="entity"
        )

    def test_attach_memories_with_filters(self, memory_service, mock_kuzu_memory):
        """Test attach_memories() with additional filters."""
        mock_context = MemoryContext(original_prompt="test", enhanced_prompt="test", memories=[])
        mock_kuzu_memory.attach_memories.return_value = mock_context

        memory_service.attach_memories("test prompt", user_id="user-1", session_id="session-1")

        mock_kuzu_memory.attach_memories.assert_called_once_with(
            prompt="test prompt",
            max_memories=10,
            strategy="auto",
            user_id="user-1",
            session_id="session-1",
        )

    def test_get_recent_memories_delegates_to_kuzu_memory(self, memory_service, mock_kuzu_memory):
        """Test get_recent_memories() delegates to KuzuMemory."""
        mock_memory = Mock(spec=Memory)
        mock_memories = [mock_memory]
        mock_kuzu_memory.get_recent_memories.return_value = mock_memories

        result = memory_service.get_recent_memories(limit=10)

        assert result == mock_memories
        mock_kuzu_memory.get_recent_memories.assert_called_once_with(limit=10, memory_type=None)

    def test_get_recent_memories_with_type_filter(self, memory_service, mock_kuzu_memory):
        """Test get_recent_memories() with memory type filter."""
        mock_memories = []
        mock_kuzu_memory.get_recent_memories.return_value = mock_memories

        result = memory_service.get_recent_memories(limit=20, memory_type=MemoryType.EPISODIC)

        assert result == mock_memories
        mock_kuzu_memory.get_recent_memories.assert_called_once_with(
            limit=20, memory_type=MemoryType.EPISODIC
        )

    def test_get_memory_count_delegates_to_kuzu_memory(self, memory_service, mock_kuzu_memory):
        """Test get_memory_count() delegates to KuzuMemory."""
        mock_kuzu_memory.get_memory_count.return_value = 42

        result = memory_service.get_memory_count()

        assert result == 42
        mock_kuzu_memory.get_memory_count.assert_called_once()

    def test_get_database_size_delegates_to_kuzu_memory(self, memory_service, mock_kuzu_memory):
        """Test get_database_size() delegates to KuzuMemory."""
        mock_kuzu_memory.get_database_size.return_value = 1024000

        result = memory_service.get_database_size()

        assert result == 1024000
        mock_kuzu_memory.get_database_size.assert_called_once()


class TestMemoryServiceCRUDOperations:
    """Test CRUD operations via memory_store."""

    def test_add_memory_creates_and_stores(
        self, memory_service, mock_kuzu_memory, mock_memory_store
    ):
        """Test add_memory() creates Memory and stores it."""
        result = memory_service.add_memory(
            content="test content",
            memory_type=MemoryType.SEMANTIC,
            entities=["entity1"],
            metadata={"key": "value"},
        )

        # Verify memory was created with correct attributes
        assert isinstance(result, Memory)
        assert result.content == "test content"
        assert result.memory_type == MemoryType.SEMANTIC
        assert "entity1" in result.entities
        assert result.metadata["key"] == "value"

        # Verify memory was stored
        mock_memory_store.store_memory.assert_called_once()

    def test_get_memory_delegates_to_memory_store(self, memory_service, mock_memory_store):
        """Test get_memory() delegates to memory_store."""
        mock_memory = Mock(spec=Memory)
        mock_memory_store.get_memory_by_id.return_value = mock_memory

        result = memory_service.get_memory("memory-123")

        assert result == mock_memory
        mock_memory_store.get_memory_by_id.assert_called_once_with("memory-123")

    def test_list_memories_delegates_to_memory_store(self, memory_service, mock_memory_store):
        """Test list_memories() delegates to memory_store."""
        mock_memories = [Mock(spec=Memory), Mock(spec=Memory), Mock(spec=Memory)]
        mock_memory_store.get_recent_memories.return_value = mock_memories

        result = memory_service.list_memories(limit=2, offset=1)

        # Should return sliced results
        assert len(result) == 2
        mock_memory_store.get_recent_memories.assert_called_once_with(limit=10000)

    def test_list_memories_with_type_filter(self, memory_service, mock_memory_store):
        """Test list_memories() with memory type filter."""
        # Create mock memories with different types
        mock_mem1 = Mock(spec=Memory)
        mock_mem1.memory_type = MemoryType.PREFERENCE
        mock_mem2 = Mock(spec=Memory)
        mock_mem2.memory_type = MemoryType.EPISODIC
        mock_mem3 = Mock(spec=Memory)
        mock_mem3.memory_type = MemoryType.PREFERENCE

        mock_memory_store.get_recent_memories.return_value = [
            mock_mem1,
            mock_mem2,
            mock_mem3,
        ]

        result = memory_service.list_memories(memory_type=MemoryType.PREFERENCE, limit=100)

        # Should filter to only PREFERENCE type
        assert len(result) == 2
        mock_memory_store.get_recent_memories.assert_called_once_with(limit=10000)

    def test_delete_memory_success(self, memory_service, mock_memory_store):
        """Test delete_memory() returns True on success."""
        mock_memory_store.delete_memory.return_value = True

        result = memory_service.delete_memory("memory-123")

        assert result is True
        mock_memory_store.delete_memory.assert_called_once_with("memory-123")

    def test_delete_memory_not_found(self, memory_service, mock_memory_store):
        """Test delete_memory() returns False when memory not found."""
        mock_memory_store.delete_memory.side_effect = Exception("Not found")

        result = memory_service.delete_memory("nonexistent")

        assert result is False

    def test_update_memory_success(self, memory_service, mock_memory_store):
        """Test update_memory() updates and returns memory."""
        # Mock existing memory
        existing_memory = Memory(
            content="old content",
            memory_type=MemoryType.EPISODIC,
            metadata={"old": "data"},
        )
        mock_memory_store.get_memory_by_id.return_value = existing_memory

        result = memory_service.update_memory(
            memory_id="memory-123",
            content="new content",
            metadata={"new": "data"},
        )

        # Verify memory was updated
        assert result is not None
        assert result.content == "new content"
        assert "new" in result.metadata
        assert "old" in result.metadata  # Metadata should be merged

        # Verify store_memory was called
        mock_memory_store.store_memory.assert_called_once()

    def test_update_memory_not_found(self, memory_service, mock_memory_store):
        """Test update_memory() returns None when memory not found."""
        mock_memory_store.get_memory_by_id.return_value = None

        result = memory_service.update_memory(memory_id="nonexistent", content="new content")

        assert result is None

    def test_update_memory_requires_parameters(self, memory_service):
        """Test update_memory() raises error when no parameters provided."""
        with pytest.raises(ValueError, match="At least one of"):
            memory_service.update_memory(memory_id="memory-123")


class TestMemoryServiceErrorHandling:
    """Test error handling and edge cases."""

    def test_kuzu_memory_property_access(self, memory_service, mock_kuzu_memory):
        """Test accessing underlying KuzuMemory instance."""
        assert memory_service.kuzu_memory == mock_kuzu_memory

    def test_kuzu_memory_property_raises_when_not_initialized(self):
        """Test kuzu_memory property raises when service not initialized."""
        service = MemoryService(db_path=Path("/tmp/test.db"))

        with pytest.raises(RuntimeError, match="MemoryService not initialized"):
            _ = service.kuzu_memory

    def test_methods_require_initialization(self):
        """Test methods raise error when service not initialized."""
        service = MemoryService(db_path=Path("/tmp/test.db"))

        with pytest.raises(RuntimeError, match="not initialized"):
            service.remember("content", "cli")

        with pytest.raises(RuntimeError, match="not initialized"):
            service.attach_memories("prompt")

        with pytest.raises(RuntimeError, match="not initialized"):
            service.get_recent_memories()

        with pytest.raises(RuntimeError, match="not initialized"):
            service.get_memory_count()

        with pytest.raises(RuntimeError, match="not initialized"):
            service.get_database_size()

    def test_cleanup_with_exception_still_completes(self, mock_kuzu_memory):
        """Test cleanup completes even if KuzuMemory.__exit__ raises."""
        mock_kuzu_memory.__exit__.side_effect = Exception("Cleanup error")

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            service = MemoryService(db_path=Path("/tmp/test.db"))
            service.initialize()

            # Cleanup should not raise, just log error
            service.cleanup()

            # Service should be marked as uninitialized
            assert not service._initialized
            assert service._kuzu_memory is None


class TestMemoryServiceIntegration:
    """Integration-style tests verifying end-to-end workflows."""

    def test_full_lifecycle_workflow(self, mock_kuzu_memory, mock_memory_store):
        """Test complete lifecycle: create, use, cleanup."""
        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            # Create and initialize
            service = MemoryService(db_path=Path("/tmp/test.db"))
            service.initialize()

            # Use service
            mock_kuzu_memory.remember.return_value = "memory-1"
            memory_id = service.remember("test", "cli")
            assert memory_id == "memory-1"

            # Cleanup
            service.cleanup()
            assert not service.is_initialized

    def test_context_manager_workflow(self, mock_kuzu_memory, mock_memory_store):
        """Test workflow using context manager."""
        mock_kuzu_memory.remember.return_value = "memory-2"
        mock_kuzu_memory.get_memory_count.return_value = 5

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            with MemoryService(db_path=Path("/tmp/test.db")) as service:
                # Service is auto-initialized
                assert service.is_initialized

                # Perform operations
                memory_id = service.remember("content", "cli")
                count = service.get_memory_count()

                assert memory_id == "memory-2"
                assert count == 5

            # Service is auto-cleaned up (verified by mock exit call)
            mock_kuzu_memory.__exit__.assert_called_once()

    def test_remember_and_recall_workflow(self, mock_kuzu_memory, mock_memory_store):
        """Test remember and recall workflow."""
        # Setup mocks
        mock_kuzu_memory.remember.return_value = "memory-3"
        mock_context = MemoryContext(
            original_prompt="test",
            enhanced_prompt="enhanced",
            memories=[Memory(content="recalled", memory_type=MemoryType.EPISODIC)],
        )
        mock_kuzu_memory.attach_memories.return_value = mock_context

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            with MemoryService(db_path=Path("/tmp/test.db")) as service:
                # Store memory
                memory_id = service.remember("important fact", "cli")
                assert memory_id == "memory-3"

                # Recall memory
                context = service.attach_memories("what was important?")
                assert len(context.memories) == 1
                assert context.memories[0].content == "recalled"


# Performance and edge case tests


class TestMemoryServicePerformance:
    """Test performance characteristics and edge cases."""

    def test_handles_large_memory_content(self, memory_service, mock_memory_store):
        """Test handling of large memory content."""
        large_content = "x" * 50000  # 50KB content

        result = memory_service.add_memory(content=large_content, memory_type=MemoryType.SEMANTIC)

        assert len(result.content) == 50000
        mock_memory_store.store_memory.assert_called_once()

    def test_handles_many_entities(self, memory_service, mock_memory_store):
        """Test handling of many entities."""
        many_entities = [f"entity{i}" for i in range(100)]

        result = memory_service.add_memory(
            content="test",
            memory_type=MemoryType.SEMANTIC,
            entities=many_entities,
        )

        assert len(result.entities) == 100

    def test_handles_complex_metadata(self, memory_service, mock_memory_store):
        """Test handling of complex nested metadata."""
        complex_metadata = {
            "nested": {"deep": {"value": "test"}},
            "list": [1, 2, 3],
            "mixed": {"a": [1, 2], "b": {"c": "d"}},
        }

        result = memory_service.add_memory(
            content="test",
            memory_type=MemoryType.SEMANTIC,
            metadata=complex_metadata,
        )

        assert result.metadata["nested"]["deep"]["value"] == "test"
        assert result.metadata["list"] == [1, 2, 3]
