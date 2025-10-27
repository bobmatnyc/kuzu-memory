"""
Abstract interface for performance monitoring.

Defines the contract for tracking performance metrics, timing operations,
and monitoring system health throughout KuzuMemory.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    """Types of metrics that can be tracked."""

    COUNTER = "counter"  # Incrementing values
    GAUGE = "gauge"  # Point-in-time values
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"  # Time-based measurements


class IPerformanceMonitor(ABC):
    """
    Abstract interface for performance monitoring.

    Tracks metrics, timings, and system health with support for
    different metric types and aggregation periods.
    """

    @abstractmethod
    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.COUNTER,
        tags: dict[str, str] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """
        Record a performance metric.

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags for grouping/filtering
            timestamp: When metric was recorded (default: now)
        """
        pass

    @abstractmethod
    async def increment_counter(
        self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            value: Amount to increment by
            tags: Optional tags
        """
        pass

    @abstractmethod
    async def set_gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """
        Set a gauge metric value.

        Args:
            name: Gauge name
            value: Current value
            tags: Optional tags
        """
        pass

    @abstractmethod
    async def record_timing(
        self, name: str, duration_ms: float, tags: dict[str, str] | None = None
    ) -> None:
        """
        Record a timing measurement.

        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            tags: Optional tags
        """
        pass

    @abstractmethod
    async def time_async_operation(
        self, name: str, tags: dict[str, str] | None = None
    ) -> AbstractAsyncContextManager[None]:
        """
        Time an async operation using context manager.

        Args:
            name: Operation name
            tags: Optional tags

        Usage:
            async with monitor.time_async_operation("database_query"):
                await execute_query()
        """
        pass

    @abstractmethod
    def time_operation(
        self, name: str, tags: dict[str, str] | None = None
    ) -> AbstractContextManager[None]:
        """
        Time a synchronous operation using context manager.

        Args:
            name: Operation name
            tags: Optional tags

        Usage:
            with monitor.time_operation("memory_processing"):
                process_memories()
        """
        pass

    @abstractmethod
    def time_function(
        self, name: str | None = None, tags: dict[str, str] | None = None
    ) -> Callable[..., Any]:
        """
        Decorator to time function execution.

        Args:
            name: Operation name (default: function name)
            tags: Optional tags

        Usage:
            @monitor.time_function("database_operation")
            async def query_database():
                pass
        """
        pass

    @abstractmethod
    async def get_metrics(
        self,
        names: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Retrieve recorded metrics.

        Args:
            names: Metric names to retrieve (default: all)
            start_time: Start of time range
            end_time: End of time range
            tags: Filter by tags

        Returns:
            Dictionary mapping metric names to lists of metric data points
        """
        pass

    @abstractmethod
    async def get_summary(self, period: timedelta = timedelta(hours=1)) -> dict[str, Any]:
        """
        Get summary statistics for recent metrics.

        Args:
            period: Time period to summarize

        Returns:
            Dictionary containing metric summaries and system health
        """
        pass

    @abstractmethod
    async def check_performance_thresholds(self) -> dict[str, Any]:
        """
        Check if any performance thresholds are being violated.

        Returns:
            Dictionary containing threshold violations and recommendations
        """
        pass

    @abstractmethod
    async def reset_metrics(
        self, names: list[str] | None = None, older_than: datetime | None = None
    ) -> int:
        """
        Reset/clear metrics.

        Args:
            names: Metric names to reset (default: all)
            older_than: Only reset metrics older than this time

        Returns:
            Number of metrics reset
        """
        pass

    @abstractmethod
    async def export_metrics(
        self,
        format: str = "json",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> str:
        """
        Export metrics in the specified format.

        Args:
            format: Export format ("json", "csv", "prometheus")
            start_time: Start of export range
            end_time: End of export range

        Returns:
            Formatted metrics data
        """
        pass
