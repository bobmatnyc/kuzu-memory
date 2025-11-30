"""
Async CLI Interface for KuzuMemory

Provides CLI commands that use async memory operations for better performance.
Learning operations are non-blocking while enhancement remains synchronous.
"""

import json
import time
from pathlib import Path
from typing import Any

from ..core.memory import KuzuMemory
from ..core.models import MemoryType
from .background_learner import get_background_learner
from .queue_manager import get_queue_manager
from .status_reporter import get_status_reporter


class AsyncMemoryCLI:
    """
    Async CLI interface for memory operations.

    Provides both sync (for enhancement) and async (for learning) operations
    optimized for AI integration.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize async CLI interface.

        Args:
            db_path: Path to KuzuMemory database
        """
        self.db_path = db_path
        self.background_learner = get_background_learner(db_path)
        self.status_reporter = get_status_reporter()
        self.queue_manager = get_queue_manager()

    def enhance_sync(self, prompt: str, max_memories: int = 5, output_format: str = "plain") -> str:
        """
        Synchronous prompt enhancement (needed for immediate AI response).

        Args:
            prompt: Prompt to enhance
            max_memories: Maximum memories to include
            output_format: Output format (plain, json, context)

        Returns:
            str: Enhanced prompt or JSON string
        """
        try:
            with KuzuMemory(db_path=self.db_path) as memory:
                context = memory.attach_memories(prompt=prompt, max_memories=max_memories)

                if output_format == "json":
                    result = {
                        "original_prompt": prompt,
                        "enhanced_prompt": context.enhanced_prompt,
                        "memories_used": [
                            {
                                "content": m.content,
                                "confidence": m.confidence,
                                "created_at": m.created_at.isoformat(),
                            }
                            for m in context.memories
                        ],
                        "confidence": context.confidence,
                    }
                    return json.dumps(result, indent=2)

                elif output_format == "plain":
                    return context.enhanced_prompt

                else:  # context format
                    if context.memories:
                        return f"🧠 Enhanced with {len(context.memories)} memories (confidence: {context.confidence:.2f})\n\n{context.enhanced_prompt}"
                    else:
                        return f"(i) No relevant memories found\n\n{prompt}"

        except Exception:
            # Return original prompt on error
            return prompt

    def learn_async(
        self,
        content: str,
        source: str = "async-cli",
        metadata: dict[str, Any] | None = None,
        quiet: bool = True,
        wait_for_completion: bool = False,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """
        Asynchronous learning with optional wait for completion.

        Args:
            content: Content to learn
            source: Source of the learning
            metadata: Additional metadata
            quiet: Whether to suppress output
            wait_for_completion: Whether to wait for task to complete
            timeout: Max time to wait for completion (seconds)

        Returns:
            Dict with task information
        """
        try:
            # Submit for async processing
            task_id = self.background_learner.learn_async(
                content=content, source=source, metadata=metadata
            )

            result = {
                "task_id": task_id,
                "status": "queued",
                "message": "Learning task submitted for background processing",
            }

            if not quiet:
                print(f"✅ Learning task queued (ID: {task_id[:8]}...)")
                print(f"   Processing: {content[:60]}{'...' if len(content) > 60 else ''}")

            # Optionally wait for completion
            if wait_for_completion:
                final_status = self.wait_for_task(task_id, timeout_seconds=timeout)
                result.update(final_status)

                if not quiet:
                    if final_status["status"] == "completed":
                        print("   ✅ Task completed successfully")
                        if "result" in final_status and "memories_count" in final_status.get(
                            "result", {}
                        ):
                            count = final_status["result"]["memories_count"]
                            print(f"   📝 Extracted {count} memories")
                    elif final_status["status"] == "failed":
                        print(f"   ❌ Task failed: {final_status.get('error', 'Unknown error')}")
                    elif final_status["status"] == "timeout":
                        print(f"   ⏱️  Task is still processing (timeout after {timeout}s)")
            elif not quiet:
                print("   Note: Memories are extracted from pattern-matching phrases")

            return result

        except Exception as e:
            result: dict[str, Any] = {
                "task_id": None,
                "status": "failed",
                "error": str(e),
                "message": f"Failed to submit learning task: {e}",
            }

            if not quiet:
                print(f"❌ Learning failed: {e}")

            return result

    def store_async(
        self,
        content: str,
        memory_type: str = "procedural",
        source: str = "async-cli",
        metadata: dict[str, Any] | None = None,
        quiet: bool = True,
    ) -> dict[str, Any]:
        """
        Asynchronous storage (non-blocking).

        Args:
            content: Content to store
            memory_type: Type of memory (procedural, semantic, episodic, etc.)
            source: Source of the memory
            metadata: Additional metadata
            quiet: Whether to suppress output

        Returns:
            Dict with task information
        """
        try:
            # Convert memory type
            mem_type = MemoryType(memory_type)

            # Submit for async processing
            task_id = self.background_learner.store_async(
                content=content, memory_type=mem_type, source=source, metadata=metadata
            )

            result = {
                "task_id": task_id,
                "status": "queued",
                "message": "Storage task submitted for background processing",
            }

            if not quiet:
                print(f"✅ Storage task {task_id} queued")

            return result

        except Exception as e:
            result: dict[str, Any] = {
                "task_id": None,
                "status": "failed",
                "error": str(e),
                "message": f"Failed to submit storage task: {e}",
            }

            if not quiet:
                print(f"❌ Storage failed: {e}")

            return result

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Get the status of an async task.

        Args:
            task_id: Task ID to check

        Returns:
            Dict with task status information
        """
        task = self.queue_manager.get_task_status(task_id)

        if not task:
            return {
                "task_id": task_id,
                "status": "not_found",
                "message": "Task not found",
            }

        result: dict[str, Any] = {
            "task_id": task_id,
            "status": task.status.value,
            "task_type": task.task_type.value,
            "content": (task.content[:100] + "..." if len(task.content) > 100 else task.content),
            "source": task.source,
            "created_at": task.created_at.isoformat(),
            "age_seconds": task.age_seconds,
        }

        if task.started_at:
            result["started_at"] = task.started_at.isoformat()

        if task.completed_at:
            result["completed_at"] = task.completed_at.isoformat()
            result["duration_ms"] = task.duration_ms

        if task.result:
            result["result"] = task.result

        if task.error:
            result["error"] = task.error

        return result

    def get_queue_status(self) -> dict[str, Any]:
        """Get overall queue status."""
        queue_stats = self.queue_manager.get_queue_stats()
        learning_stats = self.background_learner.get_learning_stats()

        return {
            "queue_stats": queue_stats,
            "learning_stats": learning_stats,
            "status_summary": {
                "queue_size": queue_stats.get("queue_size", 0),
                "tasks_completed": queue_stats.get("tasks_completed", 0),
                "tasks_failed": queue_stats.get("tasks_failed", 0),
                "memories_learned": learning_stats.get("memories_learned", 0),
                "avg_processing_time_ms": queue_stats.get("avg_processing_time_ms", 0),
            },
        }

    def wait_for_task(self, task_id: str, timeout_seconds: float = 30.0) -> dict[str, Any]:
        """
        Wait for a task to complete (useful for testing).

        Args:
            task_id: Task ID to wait for
            timeout_seconds: Maximum time to wait

        Returns:
            Dict with final task status
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            status = self.get_task_status(task_id)

            if status["status"] in ["completed", "failed", "cancelled", "not_found"]:
                return status

            time.sleep(0.1)  # Check every 100ms

        return {
            "task_id": task_id,
            "status": "timeout",
            "message": f"Task did not complete within {timeout_seconds} seconds",
        }


# Global async CLI instance
_async_cli: AsyncMemoryCLI | None = None


def get_async_cli(db_path: Path | None = None) -> AsyncMemoryCLI:
    """Get the global async CLI instance."""
    global _async_cli
    if _async_cli is None:
        _async_cli = AsyncMemoryCLI(db_path=db_path)
        # Ensure queue manager is started
        _async_cli.queue_manager.start()
    return _async_cli
