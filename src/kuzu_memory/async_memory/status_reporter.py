"""
Memory Status Reporter for Async Operations

Provides background reporting of memory operation results.
Allows monitoring of async learning and storage tasks.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from .queue_manager import MemoryQueueManager, TaskStatus

if TYPE_CHECKING:
    from .background_learner import BackgroundLearner

logger = logging.getLogger(__name__)


class ReportLevel(Enum):
    """Levels for status reporting."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class StatusReport:
    """A status report for memory operations."""

    timestamp: datetime
    level: ReportLevel
    message: str
    task_id: str | None = None
    task_type: str | None = None
    details: dict[str, Any] | None = None


class MemoryStatusReporter:
    """
    Background status reporter for memory operations.

    Monitors async tasks and provides status updates without blocking
    the main application flow.
    """

    def __init__(
        self,
        report_interval_seconds: float = 5.0,
        max_reports: int = 100,
        min_report_level: ReportLevel = ReportLevel.INFO,
    ) -> None:
        """
        Initialize the status reporter.

        Args:
            report_interval_seconds: How often to check for status updates
            max_reports: Maximum number of reports to keep in memory
            min_report_level: Minimum level for reports
        """
        self.report_interval = report_interval_seconds
        self.max_reports = max_reports
        self.min_report_level = min_report_level

        # Components - lazy initialized to avoid circular imports
        self._queue_manager: MemoryQueueManager | None = None
        self._background_learner: BackgroundLearner | None = None

        # Reporting state
        self.reports: list[StatusReport] = []
        self.running = False
        self.reporter_thread: threading.Thread | None = None
        self.lock = threading.Lock()

        # Callbacks for different report levels
        self.callbacks: dict[ReportLevel, list[Callable[..., Any]]] = {
            level: [] for level in ReportLevel
        }

        # Last seen task states (to detect changes)
        self.last_task_states: dict[str, TaskStatus] = {}

        # Statistics
        self.stats: dict[str, int | datetime | None] = {
            "reports_generated": 0,
            "tasks_monitored": 0,
            "last_report_time": None,
        }

        logger.info("Initialized MemoryStatusReporter")

    @property
    def queue_manager(self) -> MemoryQueueManager:
        """Lazy load queue manager to avoid circular imports."""
        if self._queue_manager is None:
            from .queue_manager import get_queue_manager

            self._queue_manager = get_queue_manager()
        return self._queue_manager

    @property
    def background_learner(self) -> BackgroundLearner:
        """Lazy load background learner to avoid circular imports."""
        if self._background_learner is None:
            from .background_learner import get_background_learner

            self._background_learner = get_background_learner()
        return self._background_learner

    def start(self) -> None:
        """Start the status reporter thread."""
        if self.running:
            return

        self.running = True
        self.reporter_thread = threading.Thread(
            target=self._reporter_loop, name="MemoryStatusReporter", daemon=True
        )
        self.reporter_thread.start()

        logger.info("Started memory status reporter")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the status reporter thread."""
        if not self.running:
            return

        self.running = False

        if self.reporter_thread:
            self.reporter_thread.join(timeout=timeout)
            self.reporter_thread = None

        logger.info("Stopped memory status reporter")

    def add_callback(self, level: ReportLevel, callback: Callable[[StatusReport], None]) -> None:
        """
        Add a callback for status reports at a specific level.

        Args:
            level: Report level to listen for
            callback: Function to call with StatusReport
        """
        self.callbacks[level].append(callback)
        logger.debug(f"Added callback for {level.value} reports")

    def get_recent_reports(self, count: int = 10) -> list[StatusReport]:
        """Get recent status reports."""
        with self.lock:
            return self.reports[-count:] if self.reports else []

    def get_reports_by_level(self, level: ReportLevel) -> list[StatusReport]:
        """Get all reports at a specific level."""
        with self.lock:
            return [r for r in self.reports if r.level == level]

    def get_task_reports(self, task_id: str) -> list[StatusReport]:
        """Get all reports for a specific task."""
        with self.lock:
            return [r for r in self.reports if r.task_id == task_id]

    def get_reporter_stats(self) -> dict[str, Any]:
        """Get reporter statistics."""
        with self.lock:
            queue_stats = self.queue_manager.get_queue_stats()
            learning_stats = self.background_learner.get_learning_stats()

            return {
                **self.stats,
                "total_reports": len(self.reports),
                "reports_by_level": {
                    level.value: len([r for r in self.reports if r.level == level])
                    for level in ReportLevel
                },
                "queue_stats": queue_stats,
                "learning_stats": learning_stats,
            }

    def _reporter_loop(self) -> None:
        """Main reporter loop."""
        logger.debug("Started status reporter loop")

        while self.running:
            try:
                # Check for task status changes
                self._check_task_updates()

                # Generate periodic reports
                self._generate_periodic_reports()

                # Clean up old reports
                self._cleanup_old_reports()

                # Sleep until next check
                time.sleep(self.report_interval)

            except Exception as e:
                logger.error(f"Status reporter error: {e}")
                time.sleep(self.report_interval)

        logger.debug("Stopped status reporter loop")

    def _check_task_updates(self) -> None:
        """Check for task status updates and generate reports."""
        # Get current tasks from queue manager

        # This would need to be implemented in queue_manager
        # For now, we'll simulate with a simple approach
        queue_stats = self.queue_manager.get_queue_stats()

        # Generate report for queue status if significant changes
        if queue_stats.get("queue_size", 0) > 10:
            self._add_report(
                ReportLevel.WARNING,
                f"Memory queue is getting full: {queue_stats['queue_size']} tasks",
                details=queue_stats,
            )

        # Check learning statistics
        learning_stats = self.background_learner.get_learning_stats()

        if learning_stats.get("learning_failures", 0) > 0:
            self._add_report(
                ReportLevel.ERROR,
                f"Learning failures detected: {learning_stats['learning_failures']} failures",
                details=learning_stats,
            )

    def _generate_periodic_reports(self) -> None:
        """Generate periodic status reports."""
        now = datetime.now()

        # Generate summary report every minute
        if (
            not self.stats["last_report_time"]
            or (now - self.stats["last_report_time"]).total_seconds() > 60
        ):
            queue_stats = self.queue_manager.get_queue_stats()
            learning_stats = self.background_learner.get_learning_stats()

            # Generate summary
            summary = (
                f"Memory system status: "
                f"{queue_stats.get('tasks_completed', 0)} tasks completed, "
                f"{queue_stats.get('queue_size', 0)} queued, "
                f"{learning_stats.get('memories_learned', 0)} memories learned"
            )

            self._add_report(
                ReportLevel.INFO,
                summary,
                details={
                    "queue_stats": queue_stats,
                    "learning_stats": learning_stats,
                },
            )

            self.stats["last_report_time"] = now

    def _cleanup_old_reports(self) -> None:
        """Clean up old reports to prevent memory growth."""
        with self.lock:
            if len(self.reports) > self.max_reports:
                # Keep only the most recent reports
                self.reports = self.reports[-self.max_reports :]

    def _add_report(
        self,
        level: ReportLevel,
        message: str,
        task_id: str | None = None,
        task_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a status report."""
        # Check if level meets minimum threshold
        level_values = {
            ReportLevel.DEBUG: 0,
            ReportLevel.INFO: 1,
            ReportLevel.WARNING: 2,
            ReportLevel.ERROR: 3,
        }

        if level_values[level] < level_values[self.min_report_level]:
            return

        # Create report
        report = StatusReport(
            timestamp=datetime.now(),
            level=level,
            message=message,
            task_id=task_id,
            task_type=task_type,
            details=details,
        )

        # Add to reports list
        with self.lock:
            self.reports.append(report)
            self.stats["reports_generated"] += 1

        # Call callbacks
        for callback in self.callbacks[level]:
            try:
                callback(report)
            except Exception as e:
                logger.error(f"Status report callback failed: {e}")

        # Log the report
        log_level = {
            ReportLevel.DEBUG: logging.DEBUG,
            ReportLevel.INFO: logging.INFO,
            ReportLevel.WARNING: logging.WARNING,
            ReportLevel.ERROR: logging.ERROR,
        }[level]

        logger.log(log_level, f"Memory Status: {message}")


# Global status reporter instance
_status_reporter: MemoryStatusReporter | None = None


def get_status_reporter() -> MemoryStatusReporter:
    """Get the global status reporter instance."""
    global _status_reporter
    if _status_reporter is None:
        _status_reporter = MemoryStatusReporter()
        _status_reporter.start()
    return _status_reporter


def add_status_callback(level: ReportLevel, callback: Callable[[StatusReport], None]) -> None:
    """Add a callback for status reports."""
    reporter = get_status_reporter()
    reporter.add_callback(level, callback)


def get_recent_status(count: int = 10) -> list[StatusReport]:
    """Get recent status reports."""
    reporter = get_status_reporter()
    return reporter.get_recent_reports(count)


def shutdown_status_reporter() -> None:
    """Shutdown the global status reporter."""
    global _status_reporter
    if _status_reporter:
        _status_reporter.stop()
        _status_reporter = None
