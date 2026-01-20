"""
Test file-based database locking for concurrent access prevention.

Tests the fail-fast locking mechanism that prevents hooks from blocking
when multiple Claude sessions try to access the same database.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from kuzu_memory.utils.file_lock import DatabaseBusyError, try_lock_database


def test_lock_acquired_successfully(tmp_path: Path) -> None:
    """Test that lock can be acquired when no other process holds it."""
    db_path = tmp_path / "test.db"
    db_path.mkdir()

    # Should acquire lock successfully
    with try_lock_database(db_path, timeout=0.0):
        # Lock acquired
        assert True


def test_lock_blocks_second_process(tmp_path: Path) -> None:
    """Test that second process fails to acquire lock immediately."""
    db_path = tmp_path / "test.db"
    db_path.mkdir()

    # Hold lock in first context
    with try_lock_database(db_path, timeout=0.0):
        # Try to acquire lock in second context (should fail immediately)
        with pytest.raises(DatabaseBusyError, match="Database busy"):
            with try_lock_database(db_path, timeout=0.0):
                pass


def test_lock_released_after_context(tmp_path: Path) -> None:
    """Test that lock is released after context manager exits."""
    db_path = tmp_path / "test.db"
    db_path.mkdir()

    # Acquire and release lock
    with try_lock_database(db_path, timeout=0.0):
        pass

    # Should be able to acquire again
    with try_lock_database(db_path, timeout=0.0):
        assert True


def test_lock_timeout_behavior(tmp_path: Path) -> None:
    """Test lock timeout behavior with blocking mode."""
    db_path = tmp_path / "test.db"
    db_path.mkdir()

    # Hold lock
    with try_lock_database(db_path, timeout=0.0):
        start = time.time()
        # Try to acquire with timeout (should fail after timeout)
        with pytest.raises(DatabaseBusyError, match="Database busy after"):
            with try_lock_database(db_path, timeout=0.1):
                pass
        elapsed = time.time() - start

        # Should have waited approximately the timeout period
        assert elapsed >= 0.1
        assert elapsed < 0.3  # Allow some overhead


def test_lock_prevents_concurrent_access_threading(tmp_path: Path) -> None:
    """Test that lock prevents concurrent access from separate threads."""
    import threading

    db_path = tmp_path / "test.db"
    db_path.mkdir()

    acquired = threading.Event()
    released = threading.Event()

    def hold_lock():
        """Thread that holds lock for duration."""
        with try_lock_database(db_path, timeout=0.0):
            acquired.set()
            time.sleep(0.3)
        released.set()

    # Start thread that holds lock
    thread = threading.Thread(target=hold_lock)
    thread.start()

    # Wait for thread to acquire lock
    assert acquired.wait(timeout=1.0), "Thread failed to acquire lock"

    # Try to acquire lock immediately (should fail)
    with pytest.raises(DatabaseBusyError, match="Database busy"):
        with try_lock_database(db_path, timeout=0.0):
            pass

    # Wait for thread to release lock
    assert released.wait(timeout=1.0), "Thread failed to release lock"
    thread.join()

    # Now lock should be available
    with try_lock_database(db_path, timeout=0.0):
        assert True


def test_lock_file_created(tmp_path: Path) -> None:
    """Test that lock file is created in correct location."""
    db_path = tmp_path / "memories.db"
    db_path.mkdir()

    with try_lock_database(db_path, timeout=0.0):
        # Lock file should exist
        lock_file = tmp_path / ".memories.db.lock"
        assert lock_file.exists()


def test_lock_handles_missing_directory(tmp_path: Path) -> None:
    """Test that lock creates parent directory if missing."""
    db_path = tmp_path / "nested" / "dir" / "memories.db"

    # Parent directory doesn't exist yet
    with try_lock_database(db_path, timeout=0.0):
        # Lock should create parent directory for lock file
        lock_file = db_path.parent / ".memories.db.lock"
        assert lock_file.parent.exists()


def test_multiple_databases_independent_locks(tmp_path: Path) -> None:
    """Test that different databases have independent locks."""
    db1_path = tmp_path / "db1"
    db2_path = tmp_path / "db2"
    db1_path.mkdir()
    db2_path.mkdir()

    # Should be able to hold locks on both simultaneously
    with try_lock_database(db1_path, timeout=0.0):
        with try_lock_database(db2_path, timeout=0.0):
            assert True


def test_lock_robust_to_exceptions(tmp_path: Path) -> None:
    """Test that lock is released even when exception occurs."""
    db_path = tmp_path / "test.db"
    db_path.mkdir()

    # Acquire lock and raise exception
    try:
        with try_lock_database(db_path, timeout=0.0):
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Lock should be released, allowing reacquisition
    with try_lock_database(db_path, timeout=0.0):
        assert True


@pytest.mark.parametrize("timeout", [0.0, 0.1, 0.5])
def test_lock_timeout_values(tmp_path: Path, timeout: float) -> None:
    """Test various timeout values."""
    db_path = tmp_path / "test.db"
    db_path.mkdir()

    # Hold lock
    with try_lock_database(db_path, timeout=0.0):
        start = time.time()
        # Try to acquire with different timeouts
        with pytest.raises(DatabaseBusyError):
            with try_lock_database(db_path, timeout=timeout):
                pass
        elapsed = time.time() - start

        # Should have waited approximately the timeout period
        if timeout == 0.0:
            # Immediate failure
            assert elapsed < 0.1
        else:
            # Waited for timeout
            assert elapsed >= timeout
            assert elapsed < timeout + 0.2  # Allow overhead
