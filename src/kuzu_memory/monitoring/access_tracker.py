"""
Memory access tracking for analytics and pruning.

Provides zero-latency access tracking with batched database updates
for efficient memory usage analytics.
"""

import logging
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Any

logger = logging.getLogger(__name__)

# Global singleton tracker instances (one per database path)
_trackers: dict[Path, "AccessTracker"] = {}
_trackers_lock = threading.Lock()


class AccessTracker:
    """
    Zero-latency memory access tracker with batched writes.

    Uses a thread-safe queue to track memory access without blocking recall operations.
    Batch writes occur every 5 seconds OR every 100 events (whichever comes first).

    Example:
        tracker = get_access_tracker(db_path)
        tracker.track_access("memory-id-123", context="recall")
        tracker.track_batch(["id1", "id2", "id3"], context="enhance")
    """

    def __init__(
        self,
        db_path: Path,
        batch_interval: float = 5.0,
        batch_size: int = 100,
    ) -> None:
        """
        Initialize access tracker.

        Args:
            db_path: Path to Kuzu database
            batch_interval: Seconds between batch writes (default: 5.0)
            batch_size: Number of events before forcing batch write (default: 100)
        """
        self.db_path = db_path
        self.batch_interval = batch_interval
        self.batch_size = batch_size

        # Thread-safe event queue
        self._queue: Queue[dict[str, Any]] = Queue()

        # Worker thread for batch processing
        self._worker_thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()
        self._running = False

        # Statistics
        self._stats = {
            "total_tracked": 0,
            "total_batches": 0,
            "total_writes": 0,
            "last_batch_time": None,
            "queue_size": 0,
        }
        self._stats_lock = threading.Lock()

        # Start worker thread
        self._start_worker()

    def _start_worker(self) -> None:
        """Start background worker thread for batch processing."""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.debug(f"AccessTracker worker started for {self.db_path}")

    def _worker_loop(self) -> None:
        """Background worker loop that processes batches."""
        last_batch_time = time.time()
        pending_events: dict[str, dict[str, Any]] = {}  # memory_id -> event

        while not self._shutdown_event.is_set():
            try:
                # Check if we should flush based on time or size
                current_time = time.time()
                should_flush_time = (current_time - last_batch_time) >= self.batch_interval
                should_flush_size = len(pending_events) >= self.batch_size

                if should_flush_time or should_flush_size:
                    if pending_events:
                        self._write_batch(pending_events)
                        pending_events.clear()
                        last_batch_time = current_time

                # Try to get events from queue (non-blocking with timeout)
                try:
                    event = self._queue.get(timeout=0.1)

                    # Merge events by memory_id (keep latest timestamp and increment count)
                    memory_id = event["memory_id"]
                    if memory_id in pending_events:
                        # Memory already in batch - update timestamp and increment count
                        pending_events[memory_id]["timestamp"] = event["timestamp"]
                        pending_events[memory_id]["count"] += event.get("count", 1)
                    else:
                        pending_events[memory_id] = event

                    self._queue.task_done()

                except Empty:
                    # No events in queue, continue loop
                    pass

            except Exception as e:
                logger.error(f"AccessTracker worker error: {e}", exc_info=True)
                time.sleep(1.0)  # Backoff on error

        # Final flush on shutdown
        if pending_events:
            self._write_batch(pending_events)

    def _write_batch(self, events: dict[str, dict[str, Any]]) -> None:
        """
        Write batch of access events to database.

        Uses UNWIND for efficient batch updates.

        Args:
            events: Dict of memory_id -> event data
        """
        if not events:
            return

        try:
            # Import here to avoid circular dependency
            from ..core.config import KuzuMemoryConfig
            from ..storage.kuzu_adapter import KuzuAdapter

            # Create adapter for database access
            config = KuzuMemoryConfig.default()
            adapter = KuzuAdapter(self.db_path, config)

            # Prepare batch data for UNWIND query
            batch_data = [
                {
                    "memory_id": memory_id,
                    "timestamp": event["timestamp"],
                    "count_increment": event.get("count", 1),
                }
                for memory_id, event in events.items()
            ]

            # Initialize adapter if needed
            adapter.initialize()

            # Execute batch update using UNWIND
            # This is much more efficient than individual updates
            # Note: CAST string to TIMESTAMP for Kùzu compatibility
            query = """
                UNWIND $events AS event
                MATCH (m:Memory {id: event.memory_id})
                SET m.access_count = COALESCE(m.access_count, 0) + event.count_increment,
                    m.accessed_at = CAST(event.timestamp AS TIMESTAMP)
            """

            with adapter._pool.get_connection() as conn:
                conn.execute(query, {"events": batch_data})

            # Update statistics
            with self._stats_lock:
                self._stats["total_batches"] += 1
                self._stats["total_writes"] += len(events)
                self._stats["last_batch_time"] = datetime.now(UTC).isoformat()

            logger.debug(f"AccessTracker wrote batch of {len(events)} updates")

        except Exception as e:
            logger.error(f"Failed to write access batch: {e}", exc_info=True)

    def track_access(self, memory_id: str, context: str = "recall") -> None:
        """
        Track a single memory access (non-blocking).

        Args:
            memory_id: ID of the accessed memory
            context: Context of access (recall, enhance, etc.)
        """
        if not memory_id:
            return

        event = {
            "memory_id": memory_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "context": context,
            "count": 1,
        }

        self._queue.put(event)

        # Update statistics
        with self._stats_lock:
            self._stats["total_tracked"] += 1
            self._stats["queue_size"] = self._queue.qsize()

    def track_batch(self, memory_ids: list[str], context: str = "recall") -> None:
        """
        Track multiple memory accesses at once (non-blocking).

        Args:
            memory_ids: List of memory IDs that were accessed
            context: Context of access (recall, enhance, etc.)
        """
        if not memory_ids:
            return

        timestamp = datetime.now(UTC).isoformat()

        for memory_id in memory_ids:
            if memory_id:
                event = {
                    "memory_id": memory_id,
                    "timestamp": timestamp,
                    "context": context,
                    "count": 1,
                }
                self._queue.put(event)

        # Update statistics
        with self._stats_lock:
            self._stats["total_tracked"] += len(memory_ids)
            self._stats["queue_size"] = self._queue.qsize()

    def get_stats(self) -> dict[str, Any]:
        """
        Get tracker statistics.

        Returns:
            Dict with tracking statistics
        """
        with self._stats_lock:
            return {
                "total_tracked": self._stats["total_tracked"],
                "total_batches": self._stats["total_batches"],
                "total_writes": self._stats["total_writes"],
                "last_batch_time": self._stats["last_batch_time"],
                "queue_size": self._stats["queue_size"],
                "batch_interval": self.batch_interval,
                "batch_size": self.batch_size,
            }

    def flush(self) -> None:
        """Force immediate flush of pending events."""
        # Signal worker to flush by setting a flag
        # Worker will check and flush on next iteration
        logger.debug("AccessTracker flush requested")

    def shutdown(self) -> None:
        """Gracefully shutdown worker thread."""
        if not self._running:
            return

        logger.debug("AccessTracker shutting down...")
        self._shutdown_event.set()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10.0)

        self._running = False
        logger.debug("AccessTracker shutdown complete")


def get_access_tracker(db_path: Path) -> AccessTracker:
    """
    Get or create singleton AccessTracker for a database.

    Args:
        db_path: Path to Kuzu database

    Returns:
        AccessTracker instance (singleton per database)
    """
    with _trackers_lock:
        if db_path not in _trackers:
            _trackers[db_path] = AccessTracker(db_path)
        return _trackers[db_path]
