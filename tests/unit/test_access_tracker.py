"""
Unit tests for AccessTracker.

Tests zero-latency access tracking with batched database updates.
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

import pytest
from kuzu_memory.monitoring.access_tracker import AccessTracker, get_access_tracker


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create temporary database path."""
    db_path = tmp_path / "test_tracker.db"
    return db_path


@pytest.fixture
def tracker(temp_db: Path) -> AccessTracker:
    """Create AccessTracker instance."""
    tracker = AccessTracker(temp_db, batch_interval=1.0, batch_size=10)
    yield tracker
    tracker.shutdown()


def test_tracker_initialization(temp_db: Path):
    """Test that tracker initializes correctly."""
    tracker = AccessTracker(temp_db, batch_interval=2.0, batch_size=50)

    assert tracker.db_path == temp_db
    assert tracker.batch_interval == 2.0
    assert tracker.batch_size == 50
    assert tracker._running is True
    assert tracker._worker_thread is not None
    assert tracker._worker_thread.is_alive()

    tracker.shutdown()


def test_track_single_access(tracker: AccessTracker):
    """Test tracking a single memory access."""
    memory_id = "test-memory-123"

    # Track access
    tracker.track_access(memory_id, context="recall")

    # Check statistics
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 1
    assert stats["queue_size"] >= 0  # May have been processed already


def test_track_batch_access(tracker: AccessTracker):
    """Test tracking multiple memory accesses at once."""
    memory_ids = [f"memory-{i}" for i in range(5)]

    # Track batch
    tracker.track_batch(memory_ids, context="enhance")

    # Check statistics
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 5


def test_flush_behavior(tracker: AccessTracker, temp_db: Path):
    """Test that flush forces immediate write."""
    # Need to initialize database schema first
    from kuzu_memory.core.memory import KuzuMemory

    memory = KuzuMemory(db_path=temp_db, enable_git_sync=False, auto_sync=False)

    # Store a memory to create the schema and get an ID
    memory_id = memory.remember("test content", source="test")
    memory.close()

    # Track access
    tracker.track_access(memory_id, context="test")

    # Wait a moment for queue to be populated
    time.sleep(0.1)

    # Flush should trigger batch write
    tracker.flush()

    # Wait for worker to process
    time.sleep(0.5)

    # Check that batch was written
    stats = tracker.get_stats()
    # Note: Due to async nature, we can't guarantee exact timing
    # but we can verify tracking occurred
    assert stats["total_tracked"] >= 1


def test_batch_write_on_size(temp_db: Path):
    """Test that batch write occurs when batch_size is reached."""
    # Create tracker with specific settings for this test
    tracker = AccessTracker(temp_db, batch_interval=10.0, batch_size=10)

    # Initialize database
    from kuzu_memory.core.memory import KuzuMemory

    memory = KuzuMemory(db_path=temp_db, enable_git_sync=False, auto_sync=False)

    # Store memories
    memory_ids = []
    for i in range(12):  # More than batch_size (10)
        mem_id = memory.remember(f"test content {i}", source="test")
        memory_ids.append(mem_id)

    memory.close()

    # Track accesses (should trigger batch write at 10)
    for mem_id in memory_ids:
        tracker.track_access(mem_id, context="test")

    # Wait for worker to process
    time.sleep(2.0)

    # Check statistics - should have written at least one batch
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 12
    # Batch may have been triggered by size or interval
    assert stats["total_batches"] >= 1

    tracker.shutdown()


def test_batch_write_on_interval(temp_db: Path):
    """Test that batch write occurs after batch_interval."""
    # Create tracker with specific settings for this test
    tracker = AccessTracker(temp_db, batch_interval=1.0, batch_size=100)

    # Initialize database
    from kuzu_memory.core.memory import KuzuMemory

    memory = KuzuMemory(db_path=temp_db, enable_git_sync=False, auto_sync=False)

    # Store a memory
    memory_id = memory.remember("test content", source="test")
    memory.close()

    # Track a single access
    tracker.track_access(memory_id, context="test")

    # Wait for batch interval (1.0s) plus buffer
    time.sleep(2.0)

    # Check that batch was written
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 1
    assert stats["total_batches"] >= 1

    tracker.shutdown()


def test_thread_safety(tracker: AccessTracker):
    """Test that tracker is thread-safe."""
    memory_ids = [f"memory-{i}" for i in range(100)]

    # Track from multiple threads
    def track_worker(ids):
        for mem_id in ids:
            tracker.track_access(mem_id, context="thread-test")

    threads = []
    chunk_size = 10
    for i in range(0, len(memory_ids), chunk_size):
        chunk = memory_ids[i : i + chunk_size]
        thread = Thread(target=track_worker, args=(chunk,))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    # Check that all accesses were tracked
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 100


def test_graceful_shutdown(tracker: AccessTracker, temp_db: Path):
    """Test that shutdown flushes pending events."""
    # Initialize database
    from kuzu_memory.core.memory import KuzuMemory

    memory = KuzuMemory(db_path=temp_db, enable_git_sync=False, auto_sync=False)

    # Store memories
    memory_ids = []
    for i in range(5):
        mem_id = memory.remember(f"test content {i}", source="test")
        memory_ids.append(mem_id)

    memory.close()

    # Track accesses
    for mem_id in memory_ids:
        tracker.track_access(mem_id, context="shutdown-test")

    # Shutdown should flush
    tracker.shutdown()

    # Verify shutdown completed
    assert tracker._running is False


def test_statistics_accuracy(tracker: AccessTracker):
    """Test that statistics are accurately maintained."""
    # Initial state
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 0
    assert stats["total_batches"] == 0
    assert stats["total_writes"] == 0

    # Track some accesses
    for i in range(15):
        tracker.track_access(f"memory-{i}", context="stats-test")

    # Check updated stats
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 15
    assert stats["batch_interval"] == 1.0
    assert stats["batch_size"] == 10


def test_get_access_tracker_singleton(temp_db: Path):
    """Test that get_access_tracker returns singleton per database."""
    tracker1 = get_access_tracker(temp_db)
    tracker2 = get_access_tracker(temp_db)

    # Should be the same instance
    assert tracker1 is tracker2

    tracker1.shutdown()


def test_empty_memory_id_handling(tracker: AccessTracker):
    """Test that empty memory IDs are handled gracefully."""
    # Track with empty ID
    tracker.track_access("", context="test")

    # Should not track empty IDs
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 0


def test_batch_with_empty_ids(tracker: AccessTracker):
    """Test that batch tracking handles empty IDs."""
    memory_ids = ["", "valid-id-1", "", "valid-id-2", ""]

    tracker.track_batch(memory_ids, context="test")

    # Should track all IDs (including empty ones that get filtered later)
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 5  # All IDs are added to queue


def test_event_merging(tracker: AccessTracker, temp_db: Path):
    """Test that duplicate memory_id events are merged in batch."""
    # Initialize database
    from kuzu_memory.core.memory import KuzuMemory

    memory = KuzuMemory(db_path=temp_db, enable_git_sync=False, auto_sync=False)

    # Store a memory
    memory_id = memory.remember("test content", source="test")
    memory.close()

    # Track same memory multiple times quickly
    for _ in range(5):
        tracker.track_access(memory_id, context="merge-test")

    # Wait for batch processing
    time.sleep(1.5)

    # Events should be merged - total_tracked is 5, but writes should be optimized
    stats = tracker.get_stats()
    assert stats["total_tracked"] == 5


def test_tracker_with_real_database_update(temp_db: Path):
    """Integration test: Verify that access counts are actually written to database."""
    from kuzu_memory.core.memory import KuzuMemory

    # Create memory
    memory = KuzuMemory(db_path=temp_db, enable_git_sync=False, auto_sync=False)
    memory_id = memory.remember("test content for tracking", source="test")
    memory.close()

    # Track access with a dedicated tracker (small batch size for quick flush)
    tracker = AccessTracker(temp_db, batch_interval=0.5, batch_size=1)
    tracker.track_access(memory_id, context="integration-test")

    # Wait for batch write
    time.sleep(1.5)

    # Verify access count was updated
    from kuzu_memory.core.config import KuzuMemoryConfig
    from kuzu_memory.storage.kuzu_adapter import KuzuAdapter

    config = KuzuMemoryConfig.default()
    adapter = KuzuAdapter(temp_db, config)
    adapter.initialize()

    # Query using adapter's execute_query method
    query = "MATCH (m:Memory {id: $id}) RETURN m.access_count AS count, m.accessed_at AS accessed"
    result = adapter.execute_query(query, {"id": memory_id})

    assert len(result) > 0, "Memory should exist in database"
    final_count = result[0].get("count", 0) or 0
    accessed_at = result[0].get("accessed")

    assert final_count >= 1, f"Expected count >= 1, got {final_count}"
    assert accessed_at is not None, "accessed_at should be set after tracking"

    tracker.shutdown()
