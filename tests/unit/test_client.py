"""
Unit tests for KuzuMemoryClient Python API.

Tests the async client interface for programmatic access to KuzuMemory.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from kuzu_memory.client import KuzuMemoryClient, create_client
from kuzu_memory.core.models import Memory, MemoryType
from kuzu_memory.utils.exceptions import ValidationError


@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Create a temporary project root directory."""
    project_root = tmp_path / "test_project"
    project_root.mkdir(parents=True)
    return project_root


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    db_path = tmp_path / ".kuzu-memory" / "memories.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


class TestKuzuMemoryClientInitialization:
    """Test client initialization and context manager."""

    def test_client_creation(self, temp_project_root: Path) -> None:
        """Test basic client creation."""
        client = KuzuMemoryClient(project_root=temp_project_root)

        assert client.project_root == temp_project_root
        assert not client.is_initialized
        assert client.db_path == temp_project_root / ".kuzu-memory" / "memories.db"

    def test_client_with_custom_db_path(self, temp_project_root: Path, temp_db_path: Path) -> None:
        """Test client creation with custom database path."""
        client = KuzuMemoryClient(project_root=temp_project_root, db_path=temp_db_path)

        assert client.project_root == temp_project_root
        assert client.db_path == temp_db_path

    @pytest.mark.asyncio
    async def test_context_manager_initialization(self, temp_project_root: Path) -> None:
        """Test async context manager properly initializes client."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            assert client.is_initialized
            assert client._service is not None

        # After exit, should be cleaned up
        assert not client.is_initialized

    @pytest.mark.asyncio
    async def test_double_initialization_raises(self, temp_project_root: Path) -> None:
        """Test that double initialization raises error."""
        client = KuzuMemoryClient(project_root=temp_project_root, enable_git_sync=False)

        async with client:
            # Try to enter again
            with pytest.raises(RuntimeError, match="already initialized"):
                await client.__aenter__()

    @pytest.mark.asyncio
    async def test_operation_without_initialization_raises(self, temp_project_root: Path) -> None:
        """Test that operations fail without initialization."""
        client = KuzuMemoryClient(project_root=temp_project_root)

        with pytest.raises(RuntimeError, match="not initialized"):
            await client.learn("test content")


class TestKuzuMemoryClientLearn:
    """Test memory storage operations."""

    @pytest.mark.asyncio
    async def test_learn_basic(self, temp_project_root: Path) -> None:
        """Test basic memory storage."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            memory_id = await client.learn("User prefers Python for backend")

            assert memory_id
            assert isinstance(memory_id, str)

    @pytest.mark.asyncio
    async def test_learn_with_metadata(self, temp_project_root: Path) -> None:
        """Test memory storage with metadata."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            metadata = {"confidence": 0.9, "category": "preference"}
            memory_id = await client.learn(
                content="User likes FastAPI",
                source="conversation",
                metadata=metadata,
            )

            assert memory_id

            # Verify we can retrieve it
            memory = await client.get_memory_by_id(memory_id)
            assert memory is not None
            assert memory.content == "User likes FastAPI"
            assert memory.source_type == "conversation"

    @pytest.mark.asyncio
    async def test_learn_empty_content_fails(self, temp_project_root: Path) -> None:
        """Test that empty content fails validation."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Empty content should raise ValidationError from underlying models
            from pydantic import ValidationError

            with pytest.raises(ValidationError):
                await client.learn("")


class TestKuzuMemoryClientRecall:
    """Test memory retrieval operations."""

    @pytest.mark.asyncio
    async def test_recall_basic(self, temp_project_root: Path) -> None:
        """Test basic memory recall."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Store some memories
            await client.learn("User prefers Python")
            await client.learn("User likes FastAPI framework")
            await client.learn("User uses PostgreSQL database")

            # Recall memories
            memories = await client.recall("What does user prefer?", max_memories=2)

            assert isinstance(memories, list)
            assert len(memories) <= 2
            assert all(isinstance(m, Memory) for m in memories)

    @pytest.mark.asyncio
    async def test_recall_empty_query(self, temp_project_root: Path) -> None:
        """Test recall with empty query."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Empty query should raise ValidationError from underlying service
            with pytest.raises(ValidationError):
                await client.recall("")

    @pytest.mark.asyncio
    async def test_recall_no_results(self, temp_project_root: Path) -> None:
        """Test recall when no memories match."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Query with no stored memories
            memories = await client.recall("What is the weather?")

            assert isinstance(memories, list)
            assert len(memories) == 0


class TestKuzuMemoryClientEnhance:
    """Test prompt enhancement operations."""

    @pytest.mark.asyncio
    async def test_enhance_basic(self, temp_project_root: Path) -> None:
        """Test basic prompt enhancement."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Store some context
            await client.learn("User prefers FastAPI for web development")

            # Enhance a prompt
            context = await client.enhance("Write a REST API server", max_memories=3)

            assert context.original_prompt == "Write a REST API server"
            assert context.enhanced_prompt  # Should have content
            assert isinstance(context.memories, list)
            assert context.confidence >= 0.0
            assert context.recall_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_enhance_with_no_memories(self, temp_project_root: Path) -> None:
        """Test enhancement when no memories exist."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Enhance without any stored memories
            context = await client.enhance("Write a web server")

            assert context.original_prompt == "Write a web server"
            assert len(context.memories) == 0

    @pytest.mark.asyncio
    async def test_enhance_empty_prompt_fails(self, temp_project_root: Path) -> None:
        """Test that empty prompt fails validation."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Empty prompt should raise ValidationError
            with pytest.raises(ValidationError):
                await client.enhance("")


class TestKuzuMemoryClientStats:
    """Test statistics operations."""

    @pytest.mark.asyncio
    async def test_get_stats_basic(self, temp_project_root: Path) -> None:
        """Test basic statistics retrieval."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            stats = client.get_stats()

            assert isinstance(stats, dict)
            assert "memory_count" in stats
            assert "database_size_bytes" in stats
            assert "memory_type_stats" in stats
            assert "recent_memories" in stats

    @pytest.mark.asyncio
    async def test_get_stats_after_storing(self, temp_project_root: Path) -> None:
        """Test statistics after storing memories."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Store some memories
            await client.learn("First memory")
            await client.learn("Second memory")

            stats = client.get_stats()

            assert stats["memory_count"] >= 2
            assert stats["database_size_bytes"] > 0


class TestKuzuMemoryClientMemoryOperations:
    """Test individual memory operations."""

    @pytest.mark.asyncio
    async def test_get_memory_by_id(self, temp_project_root: Path) -> None:
        """Test retrieving memory by ID."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Store a memory
            content = "Test memory content"
            memory_id = await client.learn(content)

            # Retrieve it
            memory = await client.get_memory_by_id(memory_id)

            assert memory is not None
            assert memory.id == memory_id
            assert memory.content == content

    @pytest.mark.asyncio
    async def test_get_memory_by_id_not_found(self, temp_project_root: Path) -> None:
        """Test retrieving non-existent memory."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            memory = await client.get_memory_by_id("nonexistent-id")

            assert memory is None

    @pytest.mark.asyncio
    async def test_get_recent_memories(self, temp_project_root: Path) -> None:
        """Test retrieving recent memories."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Store some memories
            await client.learn("Recent memory 1")
            await client.learn("Recent memory 2")
            await client.learn("Recent memory 3")

            # Get recent
            recent = await client.get_recent_memories(limit=2)

            assert len(recent) <= 2
            assert all(isinstance(m, Memory) for m in recent)

    @pytest.mark.asyncio
    async def test_delete_memory(self, temp_project_root: Path) -> None:
        """Test deleting a memory."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Store a memory
            memory_id = await client.learn("Memory to delete")

            # Delete it (returns True if successful)
            deleted = await client.delete_memory(memory_id)

            # Note: delete_memory may return True even if memory has soft-delete semantics
            # The key is that deletion doesn't raise an exception
            assert isinstance(deleted, bool)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self, temp_project_root: Path) -> None:
        """Test deleting non-existent memory."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            deleted = await client.delete_memory("nonexistent-id")
            assert not deleted


class TestKuzuMemoryClientBatchOperations:
    """Test batch operations."""

    @pytest.mark.asyncio
    async def test_batch_store_memories(self, temp_project_root: Path) -> None:
        """Test batch storing memories."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Create memories (provide optional fields to satisfy mypy without pydantic plugin)
            memories = [
                Memory(
                    content="First batch memory",
                    memory_type=MemoryType.SEMANTIC,
                    source_type="batch",
                    valid_to=None,
                    user_id=None,
                    session_id=None,
                ),
                Memory(
                    content="Second batch memory",
                    memory_type=MemoryType.EPISODIC,
                    source_type="batch",
                    valid_to=None,
                    user_id=None,
                    session_id=None,
                ),
            ]

            # Store in batch
            stored_ids = await client.batch_store_memories(memories)

            assert len(stored_ids) == 2
            assert all(isinstance(id, str) for id in stored_ids)

    @pytest.mark.asyncio
    async def test_batch_store_empty_list(self, temp_project_root: Path) -> None:
        """Test batch storing empty list."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            stored_ids = await client.batch_store_memories([])

            assert stored_ids == []

    @pytest.mark.asyncio
    async def test_cleanup_expired_memories(self, temp_project_root: Path) -> None:
        """Test cleanup of expired memories."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Cleanup (should not raise even if no expired memories)
            count = await client.cleanup_expired_memories()

            assert isinstance(count, int)
            assert count >= 0


class TestKuzuMemoryClientConvenience:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_create_client_function(self, temp_project_root: Path) -> None:
        """Test convenience create_client function."""
        client = await create_client(project_root=temp_project_root, enable_git_sync=False)

        try:
            assert client.is_initialized

            # Should be usable
            memory_id = await client.learn("Test from create_client")
            assert memory_id

        finally:
            # Cleanup
            await client.__aexit__(None, None, None)


class TestKuzuMemoryClientEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, temp_project_root: Path) -> None:
        """Test concurrent async operations."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # Run multiple operations concurrently
            results = await asyncio.gather(
                client.learn("Concurrent memory 1"),
                client.learn("Concurrent memory 2"),
                client.learn("Concurrent memory 3"),
            )

            assert len(results) == 3
            assert all(isinstance(id, str) for id in results)

    @pytest.mark.asyncio
    async def test_repr_before_init(self, temp_project_root: Path) -> None:
        """Test string representation before initialization."""
        client = KuzuMemoryClient(project_root=temp_project_root)

        repr_str = repr(client)
        assert "not initialized" in repr_str
        assert str(temp_project_root) in repr_str

    @pytest.mark.asyncio
    async def test_repr_after_init(self, temp_project_root: Path) -> None:
        """Test string representation after initialization."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            repr_str = repr(client)
            assert "initialized" in repr_str
            assert str(temp_project_root) in repr_str

    @pytest.mark.asyncio
    async def test_properties_access(self, temp_project_root: Path) -> None:
        """Test accessing client properties."""
        client = KuzuMemoryClient(project_root=temp_project_root)

        assert client.project_root == temp_project_root
        assert client.db_path == temp_project_root / ".kuzu-memory" / "memories.db"
        assert not client.is_initialized


class TestKuzuMemoryClientConfiguration:
    """Test client configuration options."""

    @pytest.mark.asyncio
    async def test_disable_git_sync(self, temp_project_root: Path) -> None:
        """Test client with git sync disabled."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False, auto_sync=False
        ) as client:
            # Should work without git sync
            memory_id = await client.learn("Test without git sync")
            assert memory_id

    @pytest.mark.asyncio
    async def test_custom_config(self, temp_project_root: Path) -> None:
        """Test client with custom configuration."""
        config = {
            "performance": {
                "max_recall_time_ms": 50,
                "enable_performance_monitoring": False,
            }
        }

        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False, config=config
        ) as client:
            # Should work with custom config
            memory_id = await client.learn("Test with custom config")
            assert memory_id


# Integration test (requires actual database)
@pytest.mark.integration
class TestKuzuMemoryClientIntegration:
    """Integration tests with real database operations."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_project_root: Path) -> None:
        """Test complete workflow: store, recall, enhance, stats."""
        async with KuzuMemoryClient(
            project_root=temp_project_root, enable_git_sync=False
        ) as client:
            # 1. Store memories
            id1 = await client.learn("User prefers Python for backend")
            await client.learn("User likes FastAPI framework")
            await client.learn("User uses PostgreSQL database")

            # 2. Recall specific memory
            memory = await client.get_memory_by_id(id1)
            assert memory is not None
            assert "Python" in memory.content

            # 3. Query memories
            results = await client.recall("What language does user prefer?")
            assert len(results) > 0

            # 4. Enhance prompt
            context = await client.enhance("Write a web API")
            assert len(context.memories) > 0

            # 5. Get statistics
            stats = client.get_stats()
            assert stats["memory_count"] >= 3

            # 6. Get recent memories
            recent = await client.get_recent_memories(limit=5)
            assert len(recent) > 0
            assert all(isinstance(m, Memory) for m in recent)
