"""
High-performance monitoring system for KuzuMemory operations.

Tracks timing, throughput, error rates, and system health metrics
with minimal overhead and comprehensive reporting.
"""

import asyncio
import functools
import logging
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from typing import Any, TypeVar

from ..core.internal_models import PerformanceMetric
from ..interfaces.performance_monitor import IPerformanceMonitor, MetricType

T = TypeVar("T")

logger = logging.getLogger(__name__)


class PerformanceMonitor(IPerformanceMonitor):
    """
    High-performance monitoring system with low overhead.

    Features:
    - Sub-millisecond timing accuracy
    - Configurable retention periods
    - Real-time threshold monitoring
    - Memory-efficient circular buffers
    - Async-safe operations
    """

    def __init__(
        self,
        max_metrics_per_type: int = 10000,
        retention_period: timedelta = timedelta(hours=24),
        threshold_checks_enabled: bool = True,
    ):
        """
        Initialize performance monitor.

        Args:
            max_metrics_per_type: Maximum metrics to keep per type
            retention_period: How long to keep metrics
            threshold_checks_enabled: Whether to check performance thresholds
        """
        self.max_metrics_per_type = max_metrics_per_type
        self.retention_period = retention_period
        self.threshold_checks_enabled = threshold_checks_enabled

        # Metric storage using deques for efficient rotation
        self._metrics: dict[str, deque[PerformanceMetric]] = defaultdict(
            lambda: deque(maxlen=max_metrics_per_type)
        )

        # Aggregated statistics cache
        self._stats_cache: dict[str, dict[str, Any]] = {}
        self._stats_cache_ttl: dict[str, datetime] = {}

        # Performance thresholds
        self._thresholds = {
            "recall_time_ms": 100.0,  # <100ms recall target
            "generation_time_ms": 200.0,  # <200ms generation target
            "db_query_time_ms": 50.0,  # <50ms database queries
            "cache_hit_rate": 0.8,  # >80% cache hit rate
            "error_rate": 0.01,  # <1% error rate
        }

        # Thread safety
        self._lock = asyncio.Lock()

        # Background cleanup
        self._cleanup_task: asyncio.Task[None] | None = None
        self._last_cleanup = time.time()

    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.COUNTER,
        tags: dict[str, str] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            metric_type=metric_type.value,
            timestamp=timestamp or datetime.now(),
            tags=tags or {},
        )

        async with self._lock:
            self._metrics[name].append(metric)

            # Invalidate stats cache for this metric
            self._stats_cache.pop(name, None)
            self._stats_cache_ttl.pop(name, None)

        # Periodic cleanup
        await self._maybe_cleanup()

    async def increment_counter(
        self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        await self.record_metric(name, value, MetricType.COUNTER, tags)

    async def set_gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Set a gauge metric value."""
        await self.record_metric(name, value, MetricType.GAUGE, tags)

    async def record_timing(
        self, name: str, duration_ms: float, tags: dict[str, str] | None = None
    ) -> None:
        """Record a timing measurement."""
        await self.record_metric(name, duration_ms, MetricType.TIMER, tags)

        # Check thresholds if enabled
        if self.threshold_checks_enabled and name in self._thresholds:
            threshold = self._thresholds[name]
            if duration_ms > threshold:
                logger.warning(
                    f"Performance threshold exceeded: {name}={duration_ms:.2f}ms > {threshold}ms"
                )

    @asynccontextmanager
    async def time_async_operation(
        self, name: str, tags: dict[str, str] | None = None
    ) -> AsyncIterator[None]:
        """Time an async operation using context manager."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await self.record_timing(name, duration_ms, tags)

    @contextmanager
    def time_operation(self, name: str, tags: dict[str, str] | None = None) -> Iterator[None]:
        """Time a synchronous operation using context manager."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Use asyncio.create_task to record metric asynchronously
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.record_timing(name, duration_ms, tags))
            except RuntimeError:
                # No event loop running, record synchronously
                asyncio.run(self.record_timing(name, duration_ms, tags))

    def time_function(
        self, name: str | None = None, tags: dict[str, str] | None = None
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to time function execution."""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            metric_name = name or f"{func.__module__}.{func.__name__}"

            if asyncio.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    async with self.time_async_operation(metric_name, tags):
                        return await func(*args, **kwargs)

                return async_wrapper
            else:

                @functools.wraps(func)
                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with self.time_operation(metric_name, tags):
                        return func(*args, **kwargs)

                return sync_wrapper

        return decorator

    async def get_metrics(
        self,
        names: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Retrieve recorded metrics."""
        async with self._lock:
            result = {}

            metric_names = names or list(self._metrics.keys())

            for name in metric_names:
                metrics = self._metrics.get(name, deque())
                filtered_metrics = []

                for metric in metrics:
                    # Filter by time range
                    if start_time and metric.timestamp < start_time:
                        continue
                    if end_time and metric.timestamp > end_time:
                        continue

                    # Filter by tags
                    if tags:
                        if not all(metric.tags.get(k) == v for k, v in tags.items()):
                            continue

                    filtered_metrics.append(metric.to_dict())

                result[name] = filtered_metrics

            return result

    async def get_summary(self, period: timedelta = timedelta(hours=1)) -> dict[str, Any]:
        """Get summary statistics for recent metrics."""
        cutoff_time = datetime.now() - period
        metrics = await self.get_metrics(start_time=cutoff_time)

        summary = {
            "period_hours": period.total_seconds() / 3600,
            "metrics": {},
            "system_health": {},
            "threshold_violations": [],
        }

        # Calculate statistics for each metric
        for name, metric_list in metrics.items():
            if not metric_list:
                continue

            values = [m["value"] for m in metric_list]
            metric_type = metric_list[0]["metric_type"]

            stats = {
                "count": len(values),
                "type": metric_type,
                "latest": values[-1] if values else 0,
            }

            if metric_type in [MetricType.TIMER.value, MetricType.GAUGE.value]:
                stats.update(
                    {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99),
                    }
                )
            elif metric_type == MetricType.COUNTER.value:
                stats["total"] = sum(values)

            summary["metrics"][name] = stats

        # Check system health
        summary["system_health"] = await self._calculate_system_health(summary["metrics"])

        return summary

    async def check_performance_thresholds(self) -> dict[str, Any]:
        """Check if any performance thresholds are being violated."""
        violations = []
        recommendations = []

        # Get recent metrics for threshold checking
        recent_metrics = await self.get_summary(timedelta(minutes=10))

        for threshold_name, threshold_value in self._thresholds.items():
            metric_stats = recent_metrics["metrics"].get(threshold_name)
            if not metric_stats:
                continue

            current_value = metric_stats.get("avg", metric_stats.get("latest", 0))

            if threshold_name.endswith("_rate") and current_value < threshold_value:
                # Rate thresholds (higher is better)
                violations.append(
                    {
                        "metric": threshold_name,
                        "current": current_value,
                        "threshold": threshold_value,
                        "severity": (
                            "warning" if current_value > threshold_value * 0.8 else "critical"
                        ),
                    }
                )
            elif not threshold_name.endswith("_rate") and current_value > threshold_value:
                # Time thresholds (lower is better)
                violations.append(
                    {
                        "metric": threshold_name,
                        "current": current_value,
                        "threshold": threshold_value,
                        "severity": (
                            "warning" if current_value < threshold_value * 1.5 else "critical"
                        ),
                    }
                )

        # Generate recommendations based on violations
        for violation in violations:
            metric_name = violation["metric"]
            if "recall_time" in metric_name:
                recommendations.append("Consider enabling caching or optimizing recall strategies")
            elif "db_query" in metric_name:
                recommendations.append("Consider connection pooling or query optimization")
            elif "cache_hit" in metric_name:
                recommendations.append("Increase cache size or adjust TTL settings")

        return {
            "violations": violations,
            "recommendations": list(set(recommendations)),
            "overall_health": "good" if not violations else "degraded",
        }

    async def reset_metrics(
        self, names: list[str] | None = None, older_than: datetime | None = None
    ) -> int:
        """Reset/clear metrics."""
        reset_count = 0

        async with self._lock:
            metric_names = names or list(self._metrics.keys())

            for name in metric_names:
                if name in self._metrics:
                    if older_than:
                        # Remove only old metrics
                        metrics = self._metrics[name]
                        original_len = len(metrics)
                        self._metrics[name] = deque(
                            (m for m in metrics if m.timestamp >= older_than),
                            maxlen=self.max_metrics_per_type,
                        )
                        reset_count += original_len - len(self._metrics[name])
                    else:
                        # Remove all metrics for this name
                        reset_count += len(self._metrics[name])
                        self._metrics[name].clear()

                # Clear cache
                self._stats_cache.pop(name, None)
                self._stats_cache_ttl.pop(name, None)

        return reset_count

    async def export_metrics(
        self,
        format: str = "json",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> str:
        """Export metrics in the specified format."""
        metrics = await self.get_metrics(start_time=start_time, end_time=end_time)

        if format == "json":
            import json

            return json.dumps(metrics, default=str, indent=2)

        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(["metric_name", "timestamp", "value", "type", "tags"])

            # Write data
            for name, metric_list in metrics.items():
                for metric in metric_list:
                    writer.writerow(
                        [
                            name,
                            metric["timestamp"],
                            metric["value"],
                            metric["metric_type"],
                            str(metric["tags"]),
                        ]
                    )

            return output.getvalue()

        elif format == "prometheus":
            # Basic Prometheus format
            lines = []
            for name, metric_list in metrics.items():
                if metric_list:
                    latest = metric_list[-1]
                    metric_name = name.replace(".", "_").replace("-", "_")
                    lines.append(f"# TYPE {metric_name} gauge")
                    lines.append(f"{metric_name} {latest['value']}")

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(percentile / 100 * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

    async def _calculate_system_health(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Calculate overall system health metrics."""
        health: dict[str, Any] = {"status": "healthy", "issues": []}

        # Check recall performance
        recall_stats = metrics.get("recall_time_ms")
        if recall_stats and recall_stats.get("avg", 0) > 100:
            health["issues"].append("Recall performance degraded")
            health["status"] = "degraded"

        # Check error rates
        error_stats = metrics.get("error_count")
        success_stats = metrics.get("success_count")
        if error_stats and success_stats:
            error_rate = error_stats.get("total", 0) / max(1, success_stats.get("total", 1))
            if error_rate > 0.05:  # >5% error rate
                health["issues"].append("High error rate detected")
                health["status"] = "unhealthy"

        return health

    async def _maybe_cleanup(self) -> None:
        """Perform periodic cleanup of old metrics."""
        current_time = time.time()
        if (current_time - self._last_cleanup) > 300:  # Every 5 minutes
            await self._cleanup_expired_metrics()
            self._last_cleanup = current_time

    async def _cleanup_expired_metrics(self) -> int:
        """Remove expired metrics to free memory."""
        cutoff_time = datetime.now() - self.retention_period
        removed_count = 0

        async with self._lock:
            for name in list(self._metrics.keys()):
                metrics = self._metrics[name]
                original_len = len(metrics)

                # Keep only non-expired metrics
                self._metrics[name] = deque(
                    (m for m in metrics if m.timestamp >= cutoff_time),
                    maxlen=self.max_metrics_per_type,
                )

                removed_count += original_len - len(self._metrics[name])

                # Remove empty metric collections
                if not self._metrics[name]:
                    del self._metrics[name]

            # Clear expired cache entries
            expired_cache_keys = [
                key for key, expiry in self._stats_cache_ttl.items() if expiry < datetime.now()
            ]
            for key in expired_cache_keys:
                self._stats_cache.pop(key, None)
                self._stats_cache_ttl.pop(key, None)

        return removed_count
