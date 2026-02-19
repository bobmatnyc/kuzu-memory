"""
Integration test for fail-fast hooks behavior with locked database.

Tests that hooks helper functions skip gracefully when database is locked,
preventing indefinite blocking in multi-session scenarios.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from kuzu_memory.cli.hooks_commands import _get_memories_with_lock
from kuzu_memory.core.memory import KuzuMemory
from kuzu_memory.utils.file_lock import try_lock_database
from kuzu_memory.utils.project_setup import get_project_db_path


def test_get_memories_with_lock_fails_fast(tmp_path: Path) -> None:
    """Test that _get_memories_with_lock returns immediately when database is locked."""
    # Create a project with database
    db_path = get_project_db_path(tmp_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database with some content
    memory = KuzuMemory(db_path=db_path, auto_sync=False)
    memory.remember("FastAPI with PostgreSQL", source="test")
    memory.close()

    # Hold lock in background thread
    lock_acquired = threading.Event()
    lock_released = threading.Event()

    def hold_lock():
        """Thread that holds database lock."""
        with try_lock_database(db_path, timeout=0.0):
            lock_acquired.set()
            time.sleep(2.0)  # Hold for 2 seconds
        lock_released.set()

    lock_thread = threading.Thread(target=hold_lock, daemon=True)
    lock_thread.start()

    # Wait for lock to be acquired
    assert lock_acquired.wait(timeout=2.0), "Lock thread failed to acquire lock"

    # Try to get memories (should return immediately)
    start_time = time.time()
    memories, error = _get_memories_with_lock(db_path, "How to build API?", strategy="keyword")
    elapsed = time.time() - start_time

    # Should complete quickly (< 0.1 seconds)
    assert elapsed < 0.1, f"get_memories_with_lock took too long: {elapsed}s"

    # Should indicate database is locked
    assert error == "locked"
    assert memories is None

    # Wait for lock to be released
    assert lock_released.wait(timeout=3.0), "Lock thread didn't release lock"
    lock_thread.join()


def test_get_memories_with_lock_works_when_unlocked(tmp_path: Path) -> None:
    """Test that _get_memories_with_lock works normally when database is not locked."""
    # Create a project with database
    db_path = get_project_db_path(tmp_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database with some content
    memory = KuzuMemory(db_path=db_path, auto_sync=False)
    memory.remember("FastAPI with PostgreSQL", source="test")
    memory.close()

    # Get memories (should succeed)
    memories, error = _get_memories_with_lock(db_path, "How to build API?", strategy="keyword")

    # Should not have error
    assert error is None

    # Should have memories (or empty list if query doesn't match)
    assert memories is not None
    assert isinstance(memories, list)


def test_multiple_sessions_concurrent_access(tmp_path: Path) -> None:
    """Test that multiple concurrent lock attempts fail fast."""
    db_path = get_project_db_path(tmp_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database
    memory = KuzuMemory(db_path=db_path, auto_sync=False)
    memory.remember("Test memory", source="test")
    memory.close()

    # Hold lock in first thread
    lock1_acquired = threading.Event()
    lock1_released = threading.Event()

    def hold_lock1():
        with try_lock_database(db_path, timeout=0.0):
            lock1_acquired.set()
            time.sleep(1.0)
        lock1_released.set()

    thread1 = threading.Thread(target=hold_lock1, daemon=True)
    thread1.start()

    # Wait for first lock to be acquired
    assert lock1_acquired.wait(timeout=1.0)

    # Try to get memories from multiple threads (should all fail fast)
    results: list[tuple] = []

    def try_get_memories():
        start = time.time()
        memories, error = _get_memories_with_lock(db_path, "test", strategy="keyword")
        elapsed = time.time() - start
        results.append((memories, error, elapsed))

    threads = [threading.Thread(target=try_get_memories, daemon=True) for _ in range(5)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all threads
    for t in threads:
        t.join(timeout=1.0)

    # All should have failed fast
    assert len(results) == 5
    for memories, error, elapsed in results:
        assert error == "locked"
        assert memories is None
        assert elapsed < 0.1  # Each should fail in < 100ms

    # Wait for lock to be released
    assert lock1_released.wait(timeout=2.0)
    thread1.join()
