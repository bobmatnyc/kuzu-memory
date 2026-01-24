"""
Background queue processor for bash hook data.

This module processes queued hook data from fast bash hooks that were
written to the file queue. It runs asynchronously in the background
without blocking the hooks execution.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HookQueueProcessor:
    """
    Processes queued hook data from bash hooks.

    The bash hooks write JSON files to a queue directory for async processing.
    This processor runs in the background and processes those files without
    blocking the hook execution.
    """

    def __init__(self, queue_dir: str = "/tmp/kuzu-memory-queue") -> None:
        """
        Initialize the queue processor.

        Args:
            queue_dir: Directory where queued hook data is stored
        """
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start background queue processing."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info(f"Queue processor started, watching {self.queue_dir}")

    async def stop(self) -> None:
        """Stop queue processing."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                await self._process_queue()
                await asyncio.sleep(0.1)  # Check every 100ms
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)  # Back off on error

    async def _process_queue(self) -> None:
        """Process all queued files."""
        for file_path in sorted(self.queue_dir.glob("*.json")):
            try:
                await self._process_file(file_path)
                file_path.unlink()  # Delete after processing
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                # Move to error directory
                error_dir = self.queue_dir / "errors"
                error_dir.mkdir(exist_ok=True)
                file_path.rename(error_dir / file_path.name)

    async def _process_file(self, file_path: Path) -> None:
        """
        Process a single queued file.

        Args:
            file_path: Path to queued JSON file
        """
        data = json.loads(file_path.read_text())
        file_type = file_path.name.split("_")[0]  # learn, session, etc.

        if file_type == "learn":
            await self._handle_learn(data)
        elif file_type == "session":
            await self._handle_session(data)
        else:
            logger.warning(f"Unknown queue file type: {file_type}")

    async def _handle_learn(self, data: dict[str, Any]) -> None:
        """
        Handle learn hook data.

        This extracts content from hook data and stores it as a memory.
        Runs in background, no latency impact on hook execution.

        Args:
            data: Hook data from bash queue
        """
        # Import here to avoid circular dependencies
        from ..core.memory import KuzuMemory
        from ..utils.project_setup import find_project_root, get_project_db_path

        try:
            # Extract transcript path and find assistant message
            transcript_path = data.get("transcript_path")
            if not transcript_path:
                logger.warning("No transcript path in learn data")
                return

            # Find project root
            project_root = find_project_root()
            if not project_root:
                logger.warning("Project root not found, skipping learn")
                return

            db_path = get_project_db_path(project_root)
            if not db_path.exists():
                logger.warning("Database not initialized, skipping learn")
                return

            # Extract last assistant message from transcript
            from ..cli.hooks_commands import _find_last_assistant_message

            transcript_file = Path(transcript_path)
            if not transcript_file.exists():
                logger.warning(f"Transcript file not found: {transcript_path}")
                return

            assistant_text = _find_last_assistant_message(transcript_file)
            if not assistant_text or len(assistant_text) < 10:
                logger.info("No valid assistant message to store")
                return

            # Store the memory
            memory = KuzuMemory(db_path=db_path, enable_git_sync=False, auto_sync=False)
            memory.remember(
                content=assistant_text,
                source="claude-code-hook",
                metadata={"agent_id": "assistant", "via": "bash-queue"},
            )
            memory.close()

            logger.info("Learn memory stored successfully via queue")

        except Exception as e:
            logger.error(f"Error handling learn: {e}", exc_info=True)

    async def _handle_session(self, data: dict[str, Any]) -> None:
        """
        Handle session start hook data.

        Args:
            data: Hook data from bash queue
        """
        # Import here to avoid circular dependencies
        from ..core.memory import KuzuMemory
        from ..utils.project_setup import find_project_root, get_project_db_path

        try:
            # Find project root
            project_root = find_project_root()
            if not project_root:
                logger.warning("Project root not found, skipping session")
                return

            db_path = get_project_db_path(project_root)
            if not db_path.exists():
                logger.warning("Database not initialized, skipping session")
                return

            # Store session start memory
            memory = KuzuMemory(db_path=db_path, enable_git_sync=False, auto_sync=False)
            project_name = project_root.name
            memory.remember(
                content=f"Session started in {project_name}",
                source="claude-code-session",
                metadata={
                    "agent_id": "session-tracker",
                    "event_type": "session_start",
                    "via": "bash-queue",
                },
            )
            memory.close()

            logger.info(f"Session start memory stored for project: {project_name}")

        except Exception as e:
            logger.error(f"Error handling session: {e}", exc_info=True)
