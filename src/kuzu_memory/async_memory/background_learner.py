"""
Background Learning System for KuzuMemory

Provides async learning that doesn't block AI responses.
Processes learning tasks in background threads with status reporting.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.memory import KuzuMemory
from ..core.models import MemoryType
from .queue_manager import (
    MemoryTask,
    TaskType,
    get_queue_manager,
)

logger = logging.getLogger(__name__)


class BackgroundLearner:
    """
    Background learning system for async memory operations.

    Processes learning tasks without blocking AI responses.
    Integrates with the message queue system for reliable operation.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize the background learner.

        Args:
            db_path: Path to KuzuMemory database
        """
        self.db_path = db_path
        self.queue_manager = get_queue_manager()

        # Register processors
        self.queue_manager.register_processor(TaskType.LEARN, self._process_learn_task)
        self.queue_manager.register_processor(TaskType.STORE, self._process_store_task)

        # Learning statistics
        self.stats: dict[str, Any] = {
            "memories_learned": 0,
            "learning_failures": 0,
            "total_learning_time_ms": 0.0,
            "last_learning_time": None,
        }

        logger.info(f"Initialized BackgroundLearner with db_path: {db_path}")

    def learn_async(
        self,
        content: str,
        source: str = "async-learning",
        metadata: dict[str, Any] | None = None,
        priority: int = 5,
    ) -> str:
        """
        Submit content for async learning.

        Args:
            content: Content to learn
            source: Source of the learning
            metadata: Additional metadata
            priority: Task priority (lower = higher priority)

        Returns:
            str: Task ID for tracking
        """
        # Create learning task
        task = MemoryTask(
            task_type=TaskType.LEARN,
            content=content,
            source=source,
            metadata=metadata or {},
            priority=priority,
        )

        # Submit to queue
        success = self.queue_manager.submit_task(task)

        if success:
            logger.info(f"Submitted learning task {task.task_id} for: {content[:50]}...")
            return task.task_id
        else:
            logger.warning("Failed to submit learning task - queue full")
            raise RuntimeError("Learning queue is full")

    def store_async(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.PROCEDURAL,  # Patterns are procedures
        source: str = "async-storage",
        metadata: dict[str, Any] | None = None,
        priority: int = 3,
    ) -> str:
        """
        Submit content for async storage.

        Args:
            content: Content to store
            memory_type: Type of memory
            source: Source of the memory
            metadata: Additional metadata
            priority: Task priority (lower = higher priority)

        Returns:
            str: Task ID for tracking
        """
        # Create storage task
        task = MemoryTask(
            task_type=TaskType.STORE,
            content=content,
            source=source,
            metadata={"memory_type": memory_type.value, **(metadata or {})},
            priority=priority,
        )

        # Submit to queue
        success = self.queue_manager.submit_task(task)

        if success:
            logger.debug(f"Submitted storage task {task.task_id}")
            return task.task_id
        else:
            logger.warning("Failed to submit storage task - queue full")
            raise RuntimeError("Storage queue is full")

    def get_task_status(self, task_id: str) -> MemoryTask | None:
        """Get the status of a learning task."""
        return self.queue_manager.get_task_status(task_id)

    def get_learning_stats(self) -> dict[str, Any]:
        """Get learning statistics."""
        queue_stats = self.queue_manager.get_queue_stats()

        return {
            **self.stats,
            "queue_stats": queue_stats,
            "avg_learning_time_ms": (
                self.stats["total_learning_time_ms"] / max(1, self.stats["memories_learned"])
            ),
        }

    def _process_learn_task(self, task: MemoryTask) -> dict[str, Any]:
        """
        Process a learning task.

        Args:
            task: Learning task to process

        Returns:
            Dict with processing results
        """
        start_time = time.time()

        try:
            # Open KuzuMemory connection
            with KuzuMemory(db_path=self.db_path) as memory:
                # Generate memories from content
                memory_ids = memory.generate_memories(
                    content=task.content, metadata=task.metadata, source=task.source
                )

                # Update statistics
                processing_time_ms = (time.time() - start_time) * 1000
                self.stats["memories_learned"] += len(memory_ids)
                self.stats["total_learning_time_ms"] += processing_time_ms
                self.stats["last_learning_time"] = datetime.now()

                logger.info(
                    f"Learned {len(memory_ids)} memories from task {task.task_id} in {processing_time_ms:.1f}ms"
                )

                return {
                    "memory_ids": memory_ids,
                    "memories_count": len(memory_ids),
                    "processing_time_ms": processing_time_ms,
                    "source": task.source,
                }

        except Exception as e:
            # Update failure statistics
            self.stats["learning_failures"] += 1
            logger.error(f"Learning task {task.task_id} failed: {e}")
            raise

    def _process_store_task(self, task: MemoryTask) -> dict[str, Any]:
        """
        Process a storage task.

        Args:
            task: Storage task to process

        Returns:
            Dict with processing results
        """
        start_time = time.time()

        try:
            # Get memory type from metadata (default to PROCEDURAL, which replaced the old PATTERN type)
            memory_type_str = task.metadata.get("memory_type", "PROCEDURAL")
            memory_type = MemoryType(memory_type_str)

            # Open KuzuMemory connection
            with KuzuMemory(db_path=self.db_path) as memory_system:
                # Store the memory using remember() method
                # Note: remember() doesn't accept memory_type directly, it's in metadata
                task_metadata = task.metadata or {}
                task_metadata["memory_type"] = memory_type.value
                memory_id = memory_system.remember(
                    content=task.content,
                    metadata=task_metadata,
                    source=task.source,
                )

                # Update statistics
                processing_time_ms = (time.time() - start_time) * 1000
                self.stats["memories_learned"] += 1
                self.stats["total_learning_time_ms"] += processing_time_ms
                self.stats["last_learning_time"] = datetime.now()

                logger.debug(f"Stored memory {memory_id} from task {task.task_id}")

                return {
                    "memory_id": memory_id,
                    "memory_type": memory_type.value,
                    "processing_time_ms": processing_time_ms,
                    "source": task.source,
                }

        except Exception as e:
            # Update failure statistics
            self.stats["learning_failures"] += 1
            logger.error(f"Storage task {task.task_id} failed: {e}")
            raise


# Global background learner instance
_background_learner: BackgroundLearner | None = None


def get_background_learner(db_path: Path | None = None) -> BackgroundLearner:
    """Get the global background learner instance."""
    global _background_learner
    if _background_learner is None:
        logger.info("Creating global BackgroundLearner instance")
        _background_learner = BackgroundLearner(db_path=db_path)
    return _background_learner


def learn_async(
    content: str,
    source: str = "async-learning",
    metadata: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> str:
    """
    Convenience function for async learning.

    Args:
        content: Content to learn
        source: Source of the learning
        metadata: Additional metadata
        db_path: Database path (uses default if None)

    Returns:
        str: Task ID for tracking
    """
    learner = get_background_learner(db_path=db_path)
    return learner.learn_async(content, source, metadata)


def store_async(
    content: str,
    memory_type: MemoryType = MemoryType.PROCEDURAL,
    source: str = "async-storage",
    metadata: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> str:
    """
    Convenience function for async storage.

    Args:
        content: Content to store
        memory_type: Type of memory
        source: Source of the memory
        metadata: Additional metadata
        db_path: Database path (uses default if None)

    Returns:
        str: Task ID for tracking
    """
    learner = get_background_learner(db_path=db_path)
    return learner.store_async(content, memory_type, source, metadata)
