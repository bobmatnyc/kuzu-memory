"""
Timing decorators for performance monitoring.

Provides convenient decorators for timing function execution
with automatic metric recording and threshold checking.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# Global performance monitor instance (set by application)
_global_monitor: Any | None = None

F = TypeVar("F", bound=Callable[..., Any])


def set_global_monitor(monitor: Any) -> None:
    """Set the global performance monitor instance."""
    global _global_monitor
    _global_monitor = monitor


def get_global_monitor() -> Any | None:
    """Get the global performance monitor instance."""
    return _global_monitor


def time_async(
    name: str | None = None,
    tags: dict[str, str] | None = None,
    threshold_ms: float | None = None,
    log_slow: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to time async function execution.

    Args:
        name: Metric name (default: module.function)
        tags: Additional tags for the metric
        threshold_ms: Log warning if execution exceeds this threshold
        log_slow: Whether to log slow operations

    Example:
        @time_async("database_query", tags={"operation": "select"})
        async def query_database():
            pass
    """

    def decorator(func: F) -> F:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"Function {func.__name__} is not async")

        metric_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                # Record error metric
                if _global_monitor:
                    await _global_monitor.increment_counter(
                        f"{metric_name}.errors",
                        tags={**(tags or {}), "error_type": type(e).__name__},
                    )
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Record timing metric
                if _global_monitor:
                    await _global_monitor.record_timing(metric_name, duration_ms, tags)

                # Log slow operations
                if log_slow and threshold_ms and duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow operation: {metric_name} took {duration_ms:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )

        return wrapper

    return decorator


def time_sync(
    name: str | None = None,
    tags: dict[str, str] | None = None,
    threshold_ms: float | None = None,
    log_slow: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to time synchronous function execution.

    Args:
        name: Metric name (default: module.function)
        tags: Additional tags for the metric
        threshold_ms: Log warning if execution exceeds this threshold
        log_slow: Whether to log slow operations

    Example:
        @time_sync("memory_processing", threshold_ms=50.0)
        def process_memories(memories) -> None:
            pass
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):
            raise TypeError(f"Function {func.__name__} is async, use @time_async instead")

        metric_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Record error metric asynchronously
                if _global_monitor:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(
                            _global_monitor.increment_counter(
                                f"{metric_name}.errors",
                                tags={**(tags or {}), "error_type": type(e).__name__},
                            )
                        )
                    except RuntimeError:
                        # No event loop, skip metric recording
                        pass
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Record timing metric asynchronously
                if _global_monitor:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(
                            _global_monitor.record_timing(metric_name, duration_ms, tags)
                        )
                    except RuntimeError:
                        # No event loop, skip metric recording
                        pass

                # Log slow operations
                if log_slow and threshold_ms and duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow operation: {metric_name} took {duration_ms:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )

        return wrapper

    return decorator


class performance_tracker:
    """
    Context manager for tracking performance of code blocks.

    Can be used as both sync and async context manager.

    Example:
        async with performance_tracker("database_operation"):
            await execute_query()

        with performance_tracker("memory_processing"):
            process_memories()
    """

    def __init__(
        self,
        name: str,
        tags: dict[str, str] | None = None,
        threshold_ms: float | None = None,
        log_slow: bool = True,
    ) -> None:
        self.name = name
        self.tags = tags or {}
        self.threshold_ms = threshold_ms
        self.log_slow = log_slow
        self.start_time: float | None = None

    def __enter__(self) -> "performance_tracker":
        self.start_time = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self.start_time is not None:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            self._record_metric(duration_ms, exc_type)

    async def __aenter__(self) -> "performance_tracker":
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self.start_time is not None:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            await self._record_metric_async(duration_ms, exc_type)

    def _record_metric(self, duration_ms: float, exc_type: type[BaseException] | None) -> None:
        """Record metric synchronously."""
        if not _global_monitor:
            return

        try:
            loop = asyncio.get_running_loop()

            # Record timing
            loop.create_task(_global_monitor.record_timing(self.name, duration_ms, self.tags))

            # Record error if exception occurred
            if exc_type:
                error_tags = {**self.tags, "error_type": exc_type.__name__}
                loop.create_task(
                    _global_monitor.increment_counter(f"{self.name}.errors", tags=error_tags)
                )

        except RuntimeError:
            # No event loop running, skip metric recording
            pass

        # Log slow operations
        if self.log_slow and self.threshold_ms and duration_ms > self.threshold_ms:
            logger.warning(
                f"Slow operation: {self.name} took {duration_ms:.2f}ms "
                f"(threshold: {self.threshold_ms}ms)"
            )

    async def _record_metric_async(
        self, duration_ms: float, exc_type: type[BaseException] | None
    ) -> None:
        """Record metric asynchronously."""
        if not _global_monitor:
            return

        # Record timing
        await _global_monitor.record_timing(self.name, duration_ms, self.tags)

        # Record error if exception occurred
        if exc_type:
            error_tags = {**self.tags, "error_type": exc_type.__name__}
            await _global_monitor.increment_counter(f"{self.name}.errors", tags=error_tags)

        # Log slow operations
        if self.log_slow and self.threshold_ms and duration_ms > self.threshold_ms:
            logger.warning(
                f"Slow operation: {self.name} took {duration_ms:.2f}ms "
                f"(threshold: {self.threshold_ms}ms)"
            )


# Convenience functions for common operations
def time_recall(func: F) -> F:
    """Decorator for memory recall operations (100ms threshold)."""
    return (
        time_async(name="memory.recall", threshold_ms=100.0, tags={"operation": "recall"})(func)
        if asyncio.iscoroutinefunction(func)
        else time_sync(name="memory.recall", threshold_ms=100.0, tags={"operation": "recall"})(func)
    )


def time_generation(func: F) -> F:
    """Decorator for memory generation operations (200ms threshold)."""
    return (
        time_async(
            name="memory.generation",
            threshold_ms=200.0,
            tags={"operation": "generation"},
        )(func)
        if asyncio.iscoroutinefunction(func)
        else time_sync(
            name="memory.generation",
            threshold_ms=200.0,
            tags={"operation": "generation"},
        )(func)
    )


def time_database(func: F) -> F:
    """Decorator for database operations (50ms threshold)."""
    return (
        time_async(name="database.query", threshold_ms=50.0, tags={"operation": "database"})(func)
        if asyncio.iscoroutinefunction(func)
        else time_sync(name="database.query", threshold_ms=50.0, tags={"operation": "database"})(
            func
        )
    )


def time_cache(func: F) -> F:
    """Decorator for cache operations (10ms threshold)."""
    return (
        time_async(name="cache.operation", threshold_ms=10.0, tags={"operation": "cache"})(func)
        if asyncio.iscoroutinefunction(func)
        else time_sync(name="cache.operation", threshold_ms=10.0, tags={"operation": "cache"})(func)
    )
