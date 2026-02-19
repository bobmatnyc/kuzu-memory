"""
File-based locking for database access.

Provides fail-fast locking mechanism to prevent hooks from blocking
when multiple Claude sessions are accessing the same project database.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseBusyError(Exception):
    """Raised when database is locked by another process."""

    pass


@contextmanager
def try_lock_database(db_path: Path, timeout: float = 0.0) -> Iterator[bool]:
    """
    Try to acquire exclusive lock on database.

    Uses platform-specific file locking to prevent concurrent writes.
    For hooks, timeout=0 means fail immediately if locked.
    For MCP tools, timeout>0 allows waiting for lock.

    Args:
        db_path: Path to the database directory
        timeout: Max seconds to wait (0 = fail immediately)

    Yields:
        True if lock acquired

    Raises:
        DatabaseBusyError: If lock cannot be acquired within timeout

    Usage:
        try:
            with try_lock_database(db_path):
                # Safe to access database
                memory = KuzuMemory(db_path)
        except DatabaseBusyError:
            # Another process has the lock
            pass
    """
    # Create lock file next to database directory
    # Example: .kuzu-memories/memories.db → .kuzu-memories/.memories.db.lock
    lock_file = db_path.parent / f".{db_path.name}.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    fd = None
    start_time = time.time()

    try:
        # Open lock file
        fd = os.open(str(lock_file), os.O_RDWR | os.O_CREAT, 0o644)

        # Platform-specific locking
        if sys.platform == "win32":
            # Windows: use msvcrt
            import msvcrt

            if timeout == 0:
                # Non-blocking: fail immediately if locked
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                except OSError:
                    raise DatabaseBusyError(f"Database busy: {db_path}")
            else:
                # Blocking with timeout
                while True:
                    try:
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.time() - start_time > timeout:
                            raise DatabaseBusyError(f"Database busy after {timeout}s: {db_path}")
                        time.sleep(0.01)  # 10ms sleep between retries
        else:
            # Unix: use fcntl
            import fcntl

            if timeout == 0:
                # Non-blocking: fail immediately if locked
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise DatabaseBusyError(f"Database busy: {db_path}")
            else:
                # Blocking with timeout
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError:
                        if time.time() - start_time > timeout:
                            raise DatabaseBusyError(f"Database busy after {timeout}s: {db_path}")
                        time.sleep(0.01)  # 10ms sleep between retries

        logger.debug(f"Acquired lock on {db_path}")
        yield True

    except DatabaseBusyError:
        logger.debug(f"Failed to acquire lock on {db_path} (timeout={timeout}s)")
        raise
    finally:
        # Release lock
        if fd is not None:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception as e:
                logger.warning(f"Error releasing lock: {e}")
            finally:
                try:
                    os.close(fd)
                except Exception as e:
                    logger.warning(f"Error closing lock file: {e}")


__all__ = ["DatabaseBusyError", "try_lock_database"]
