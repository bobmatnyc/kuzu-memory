"""
Performance monitoring utilities for KuzuMemory.

Provides performance tracking, metrics collection, and optimization
recommendations for memory operations.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Represents a performance metric measurement."""

    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class PerformanceMonitor:
    """
    Performance monitoring system for KuzuMemory operations.

    Tracks operation times, identifies bottlenecks, and provides
    optimization recommendations.
    """

    def __init__(self, max_history: int = 10000, enable_detailed_metrics: bool = False) -> None:
        """
        Initialize performance monitor.

        Args:
            max_history: Maximum number of metrics to keep in history
            enable_detailed_metrics: Whether to collect detailed metrics
        """
        self.max_history = max_history
        self.enable_detailed_metrics = enable_detailed_metrics

        # Thread-safe storage
        self._lock = threading.RLock()

        # Metrics storage
        self._metrics_history: deque[PerformanceMetric] = deque(maxlen=max_history)
        self._operation_stats: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_time_ms": 0.0,
                "avg_time_ms": 0.0,
                "min_time_ms": float("inf"),
                "max_time_ms": 0.0,
                "success_count": 0,
                "error_count": 0,
                "recent_times": deque(maxlen=100),  # Last 100 measurements
            }
        )

        # Performance thresholds
        self.thresholds = {
            "attach_memories": 100.0,  # 100ms
            "generate_memories": 100.0,  # 100ms
            "database_query": 50.0,  # 50ms
            "pattern_extraction": 100.0,  # 100ms
            "entity_extraction": 100.0,  # 100ms
            "deduplication": 50.0,  # 50ms
        }

        # Alerts
        self._alerts: list[dict[str, Any]] = []
        self._alert_thresholds = {
            "slow_operation_count": 10,  # Alert if >10 slow operations in window
            "error_rate_threshold": 0.1,  # Alert if error rate >10%
            "avg_time_increase": 2.0,  # Alert if avg time increases by 2x
        }

    def record_operation(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record a performance metric for an operation.

        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether the operation succeeded
            metadata: Additional metadata about the operation
        """
        with self._lock:
            # Create metric
            metric = PerformanceMetric(
                operation=operation,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                success=success,
                metadata=metadata or {},
            )

            # Add to history
            self._metrics_history.append(metric)

            # Update operation statistics
            stats = self._operation_stats[operation]
            count = int(stats["count"]) + 1
            total_time_ms = float(stats["total_time_ms"]) + duration_ms
            stats["count"] = count
            stats["total_time_ms"] = total_time_ms
            stats["avg_time_ms"] = total_time_ms / count
            stats["min_time_ms"] = min(float(stats["min_time_ms"]), duration_ms)
            stats["max_time_ms"] = max(float(stats["max_time_ms"]), duration_ms)
            recent_times = stats["recent_times"]
            assert isinstance(recent_times, deque)
            recent_times.append(duration_ms)

            if success:
                stats["success_count"] = int(stats["success_count"]) + 1
            else:
                stats["error_count"] = int(stats["error_count"]) + 1

            # Check for performance issues
            self._check_performance_alerts(operation, duration_ms, success)

    def _check_performance_alerts(self, operation: str, duration_ms: float, success: bool) -> None:
        """Check for performance issues and generate alerts."""

        # Check if operation exceeded threshold
        threshold = self.thresholds.get(operation)
        if threshold and duration_ms > threshold:
            alert = {
                "type": "slow_operation",
                "operation": operation,
                "duration_ms": duration_ms,
                "threshold_ms": threshold,
                "timestamp": datetime.now(),
                "severity": "warning" if duration_ms < threshold * 2 else "critical",
            }
            self._alerts.append(alert)

            # Keep only recent alerts (last 1000)
            if len(self._alerts) > 1000:
                self._alerts = self._alerts[-1000:]

        # Check error rate
        if not success:
            stats = self._operation_stats[operation]
            error_rate = float(stats["error_count"]) / float(stats["count"])

            if error_rate > self._alert_thresholds["error_rate_threshold"]:
                alert = {
                    "type": "high_error_rate",
                    "operation": operation,
                    "error_rate": error_rate,
                    "threshold": self._alert_thresholds["error_rate_threshold"],
                    "timestamp": datetime.now(),
                    "severity": "critical",
                }
                self._alerts.append(alert)

    def get_operation_stats(self, operation: str) -> dict[str, Any]:
        """Get statistics for a specific operation."""
        with self._lock:
            if operation not in self._operation_stats:
                return {}

            stats = self._operation_stats[operation].copy()

            # Calculate additional metrics
            recent_times_obj = stats["recent_times"]
            if recent_times_obj:
                assert isinstance(recent_times_obj, deque)
                recent_times = list(recent_times_obj)
                stats["recent_avg_ms"] = sum(recent_times) / len(recent_times)
                stats["recent_min_ms"] = min(recent_times)
                stats["recent_max_ms"] = max(recent_times)

                # Calculate percentiles
                sorted_times = sorted(recent_times)
                n = len(sorted_times)
                stats["p50_ms"] = sorted_times[n // 2]
                stats["p95_ms"] = sorted_times[int(n * 0.95)]
                stats["p99_ms"] = sorted_times[int(n * 0.99)]

            # Calculate success rate
            count = int(stats["count"])
            if count > 0:
                stats["success_rate"] = float(stats["success_count"]) / count
                stats["error_rate"] = float(stats["error_count"]) / count

            return stats

    def get_all_stats(self) -> dict[str, Any]:
        """Get statistics for all operations."""
        with self._lock:
            all_stats = {}
            for operation in self._operation_stats:
                all_stats[operation] = self.get_operation_stats(operation)

            return {
                "operations": all_stats,
                "total_metrics": len(self._metrics_history),
                "alerts_count": len(self._alerts),
                "monitoring_since": (
                    self._metrics_history[0].timestamp.isoformat()
                    if self._metrics_history
                    else None
                ),
            }

    def get_recent_alerts(self, hours: int = 1) -> list[dict[str, Any]]:
        """Get alerts from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_alerts = [alert for alert in self._alerts if alert["timestamp"] > cutoff_time]

            return sorted(recent_alerts, key=lambda x: x["timestamp"], reverse=True)

    def get_performance_summary(self) -> dict[str, Any]:
        """Get a summary of overall performance."""
        with self._lock:
            if not self._metrics_history:
                return {"status": "no_data"}

            # Calculate overall metrics
            total_operations = len(self._metrics_history)
            successful_operations = sum(1 for m in self._metrics_history if m.success)

            # Recent performance (last hour)
            recent_cutoff = datetime.now() - timedelta(hours=1)
            recent_metrics = [m for m in self._metrics_history if m.timestamp > recent_cutoff]

            # Slow operations
            slow_operations = []
            for operation, threshold in self.thresholds.items():
                if operation in self._operation_stats:
                    stats = self._operation_stats[operation]
                    avg_time_ms = float(stats["avg_time_ms"])
                    if avg_time_ms > threshold:
                        slow_operations.append(
                            {
                                "operation": operation,
                                "avg_time_ms": avg_time_ms,
                                "threshold_ms": threshold,
                                "slowdown_factor": avg_time_ms / threshold,
                            }
                        )

            return {
                "status": "healthy" if not slow_operations else "degraded",
                "total_operations": total_operations,
                "success_rate": (
                    successful_operations / total_operations if total_operations > 0 else 0
                ),
                "recent_operations_count": len(recent_metrics),
                "slow_operations": slow_operations,
                "recent_alerts_count": len(self.get_recent_alerts(1)),
                "monitoring_duration_hours": (
                    (
                        self._metrics_history[-1].timestamp - self._metrics_history[0].timestamp
                    ).total_seconds()
                    / 3600
                    if len(self._metrics_history) > 1
                    else 0
                ),
            }

    def get_optimization_recommendations(self) -> list[dict[str, Any]]:
        """Get recommendations for performance optimization."""
        recommendations = []

        with self._lock:
            for operation, stats in self._operation_stats.items():
                count = int(stats["count"])
                if count < 10:  # Need sufficient data
                    continue

                threshold = self.thresholds.get(operation)
                if not threshold:
                    continue

                avg_time_ms = float(stats["avg_time_ms"])
                # Check if operation is consistently slow
                if avg_time_ms > threshold * 1.5:
                    recommendations.append(
                        {
                            "type": "slow_operation",
                            "operation": operation,
                            "issue": f"Average time ({avg_time_ms:.1f}ms) exceeds threshold ({threshold}ms)",
                            "recommendation": self._get_operation_recommendation(operation),
                            "priority": ("high" if avg_time_ms > threshold * 2 else "medium"),
                        }
                    )

                # Check for high error rates
                error_rate = float(stats["error_count"]) / count
                if error_rate > 0.05:  # >5% error rate
                    recommendations.append(
                        {
                            "type": "high_error_rate",
                            "operation": operation,
                            "issue": f"Error rate ({error_rate:.1%}) is high",
                            "recommendation": "Investigate error causes and add error handling",
                            "priority": "high",
                        }
                    )

                # Check for high variance in execution times
                recent_times_obj = stats["recent_times"]
                assert isinstance(recent_times_obj, deque)
                if len(recent_times_obj) > 10:
                    recent_times = list(recent_times_obj)
                    avg_time = sum(recent_times) / len(recent_times)
                    variance = sum((t - avg_time) ** 2 for t in recent_times) / len(recent_times)
                    std_dev = variance**0.5

                    if std_dev > avg_time * 0.5:  # High variance
                        recommendations.append(
                            {
                                "type": "high_variance",
                                "operation": operation,
                                "issue": f"High variance in execution times (std dev: {std_dev:.1f}ms)",
                                "recommendation": "Investigate causes of inconsistent performance",
                                "priority": "medium",
                            }
                        )

        return sorted(
            recommendations,
            key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]],
            reverse=True,
        )

    def _get_operation_recommendation(self, operation: str) -> str:
        """Get specific recommendation for an operation."""
        recommendations = {
            "attach_memories": "Consider enabling caching, optimizing database indices, or reducing max_memories",
            "generate_memories": "Consider optimizing pattern compilation, reducing entity extraction complexity, or improving deduplication",
            "database_query": "Consider adding database indices, optimizing query structure, or increasing connection pool size",
            "pattern_extraction": "Consider pre-compiling patterns, reducing pattern complexity, or limiting text length",
            "entity_extraction": "Consider optimizing entity patterns, reducing text length, or disabling entity extraction",
            "deduplication": "Consider adjusting similarity thresholds or optimizing comparison algorithms",
        }

        return recommendations.get(
            operation, "Investigate operation bottlenecks and optimize accordingly"
        )

    def clear_history(self) -> None:
        """Clear all performance history."""
        with self._lock:
            self._metrics_history.clear()
            self._operation_stats.clear()
            self._alerts.clear()


# Global performance monitor instance
_global_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def performance_timer(
    operation: str, metadata: dict[str, Any] | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for timing operations.

    Args:
        operation: Name of the operation being timed
        metadata: Additional metadata to record
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            success = True
            error = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000

                # Add error info to metadata if available
                final_metadata = metadata.copy() if metadata else {}
                if error:
                    final_metadata["error"] = error

                get_performance_monitor().record_operation(
                    operation, duration_ms, success, final_metadata
                )

        return wrapper

    return decorator
