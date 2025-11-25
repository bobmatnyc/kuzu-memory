"""
Lightweight Message Queue Manager for Memory Operations

Provides async task queuing for memory operations that don't need to block
AI responses. Uses threading and queue for simple, reliable operation.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Empty, Queue
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of memory tasks."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Types of memory tasks."""

    LEARN = "learn"
    STORE = "store"
    CLEANUP = "cleanup"
    OPTIMIZE = "optimize"


@dataclass
class MemoryTask:
    """A memory operation task for async processing."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.LEARN
    content: str = ""
    source: str = "async"
    metadata: dict[str, Any] = field(default_factory=dict)

    # Task management
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    result: dict[str, Any] | None = None
    error: str | None = None

    # Priority (lower number = higher priority)
    priority: int = 5

    def __post_init__(self) -> None:
        """Validate task after creation."""
        if not self.content.strip():
            raise ValueError("Task content cannot be empty")

    def start_processing(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.now()

    def complete(self, result: dict[str, Any]) -> None:
        """Mark task as completed with result."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def fail(self, error: str) -> None:
        """Mark task as failed with error."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error

    def cancel(self) -> None:
        """Cancel the task."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()

    @property
    def duration_ms(self) -> float | None:
        """Get task duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None

    @property
    def age_seconds(self) -> float:
        """Get task age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


class MemoryQueueManager:
    """
    Lightweight message queue manager for memory operations.

    Provides async task processing without blocking AI responses.
    Uses threading and queue for simple, reliable operation.
    """

    def __init__(self, max_workers: int = 2, max_queue_size: int = 100) -> None:
        """
        Initialize the queue manager.

        Args:
            max_workers: Maximum number of worker threads
            max_queue_size: Maximum number of queued tasks
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size

        # Task queue and tracking
        self.task_queue: Queue[MemoryTask] = Queue(maxsize=max_queue_size)
        self.tasks: dict[str, MemoryTask] = {}
        self.completed_tasks: list[MemoryTask] = []

        # Worker management
        self.workers: list[threading.Thread] = []
        self.running = False
        self._started = False  # Track if start() has been called
        self.lock = threading.Lock()

        # Task processors
        self.processors: dict[TaskType, Callable[[MemoryTask], dict[str, Any]]] = {}

        # Statistics
        self.stats = {
            "tasks_queued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_processing_time_ms": 0.0,
        }

        logger.info(f"Initialized MemoryQueueManager with {max_workers} workers")

    def register_processor(
        self, task_type: TaskType, processor: Callable[[MemoryTask], dict[str, Any]]
    ) -> None:
        """Register a processor function for a task type."""
        self.processors[task_type] = processor
        logger.debug(f"Registered processor for {task_type.value}")

    def start(self) -> None:
        """Start the worker threads."""
        with self.lock:
            if self._started:
                return

            self.running = True
            self._started = True

            # Start worker threads
            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_loop, name=f"MemoryWorker-{i + 1}", daemon=True
                )
                worker.start()
                self.workers.append(worker)
                logger.debug(f"Started worker thread: {worker.name}")

            logger.info(f"Started {len(self.workers)} memory worker threads")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the worker threads."""
        if not self.running:
            return

        self.running = False

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=timeout)

        self.workers.clear()
        logger.info("Stopped memory worker threads")

    def submit_task(self, task: MemoryTask) -> bool:
        """
        Submit a task for async processing.

        Args:
            task: Memory task to process

        Returns:
            bool: True if task was queued, False if queue is full
        """
        # Ensure workers are started
        if not self._started:
            self.start()

        try:
            # Check if queue is full
            if self.task_queue.qsize() >= self.max_queue_size:
                logger.warning("Memory task queue is full, dropping task")
                return False

            # Add to queue and tracking
            self.task_queue.put(task, block=False)

            with self.lock:
                self.tasks[task.task_id] = task
                self.stats["tasks_queued"] += 1

            logger.info(
                f"Queued task {task.task_id} ({task.task_type.value}) - Queue size: {self.task_queue.qsize()}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to queue task: {e}")
            return False

    def get_task_status(self, task_id: str) -> MemoryTask | None:
        """Get the status of a task."""
        with self.lock:
            return self.tasks.get(task_id)

    def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        with self.lock:
            return {
                **self.stats,
                "queue_size": self.task_queue.qsize(),
                "active_tasks": len(
                    [t for t in self.tasks.values() if t.status == TaskStatus.PROCESSING]
                ),
                "total_tasks": len(self.tasks),
                "avg_processing_time_ms": (
                    self.stats["total_processing_time_ms"] / max(1, self.stats["tasks_completed"])
                ),
            }

    def cleanup_completed_tasks(self, max_age_seconds: int = 300) -> None:
        """Clean up old completed tasks."""
        with self.lock:
            current_time = datetime.now()
            to_remove = []

            for task_id, task in self.tasks.items():
                if (
                    task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                    and task.completed_at
                    and (current_time - task.completed_at).total_seconds() > max_age_seconds
                ):
                    to_remove.append(task_id)

            for task_id in to_remove:
                del self.tasks[task_id]

            if to_remove:
                logger.debug(f"Cleaned up {len(to_remove)} old tasks")

    def _worker_loop(self) -> None:
        """Main worker loop for processing tasks."""
        worker_name = threading.current_thread().name
        logger.info(f"Started worker thread {worker_name}")

        while self.running:
            try:
                # Get next task (with timeout to check running flag)
                task = self.task_queue.get(timeout=1.0)

                logger.info(
                    f"[{worker_name}] Processing task {task.task_id} ({task.task_type.value})"
                )

                # Process the task
                self._process_task(task)

                # Mark task as done in queue
                self.task_queue.task_done()

                logger.info(f"[{worker_name}] Completed task {task.task_id}")

            except Empty:
                # Timeout - continue loop to check running flag
                continue
            except Exception as e:
                logger.error(f"[{worker_name}] Worker error: {e}")

        logger.info(f"Stopped worker thread {worker_name}")

    def _process_task(self, task: MemoryTask) -> None:
        """Process a single task."""
        try:
            # Mark as processing
            task.start_processing()

            # Get processor for task type
            processor = self.processors.get(task.task_type)
            if not processor:
                raise ValueError(f"No processor registered for {task.task_type.value}")

            # Process the task
            result = processor(task)

            # Mark as completed
            task.complete(result or {})

            # Update statistics
            with self.lock:
                self.stats["tasks_completed"] += 1
                if task.duration_ms:
                    self.stats["total_processing_time_ms"] += task.duration_ms

            logger.debug(f"Completed task {task.task_id} in {task.duration_ms:.1f}ms")

        except Exception as e:
            # Mark as failed
            error_msg = str(e)
            task.fail(error_msg)

            # Update statistics
            with self.lock:
                self.stats["tasks_failed"] += 1

            logger.error(f"Task {task.task_id} failed: {error_msg}")


# Global queue manager instance
_queue_manager: MemoryQueueManager | None = None


def get_queue_manager() -> MemoryQueueManager:
    """Get the global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = MemoryQueueManager()
        # Auto-start when getting the manager
        _queue_manager.start()
    elif not _queue_manager._started:
        # Ensure it's started even if instance exists
        _queue_manager.start()
    return _queue_manager


def shutdown_queue_manager() -> None:
    """Shutdown the global queue manager."""
    global _queue_manager
    if _queue_manager:
        _queue_manager.stop()
        _queue_manager = None
