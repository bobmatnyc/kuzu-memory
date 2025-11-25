"""
Error recovery management and strategies for KuzuMemory.

Provides automated error recovery, validation utilities, and recovery strategies.
"""

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def validate_performance_requirements(
    operation_time: float, max_time: float, operation_name: str = "operation"
) -> None:
    """
    Validate that operation meets performance requirements.

    Args:
        operation_time: Actual operation time in seconds
        max_time: Maximum allowed time in seconds
        operation_name: Name of the operation for error messages

    Raises:
        PerformanceThresholdError: If operation exceeds time limit
    """
    if operation_time > max_time:
        from .exceptions import (
            PerformanceThresholdError,
        )

        raise PerformanceThresholdError(
            operation=operation_name, actual_time=operation_time, threshold=max_time
        )


def validate_cache_operation(
    cache_size: int, max_size: int, operation: str = "cache operation"
) -> None:
    """
    Validate cache operation parameters.

    Args:
        cache_size: Current cache size
        max_size: Maximum allowed cache size
        operation: Operation being performed

    Raises:
        CacheFullError: If cache is at capacity
    """
    if cache_size >= max_size:
        from .exceptions import CacheFullError

        raise CacheFullError(
            message=f"Cache full during {operation}: {cache_size}/{max_size}",
            context={
                "operation": operation,
                "current_size": cache_size,
                "max_size": max_size,
                "utilization": (cache_size / max_size) * 100,
            },
        )


def validate_connection_pool_health(
    active_connections: int, max_connections: int, operation: str = "database operation"
) -> None:
    """
    Validate connection pool health.

    Args:
        active_connections: Number of active connections
        max_connections: Maximum allowed connections
        operation: Operation requiring connection

    Raises:
        PoolExhaustedError: If no connections available
    """
    if active_connections >= max_connections:
        from .exceptions import PoolExhaustedError

        raise PoolExhaustedError(
            message=f"Connection pool exhausted during {operation}: {active_connections}/{max_connections}",
            context={
                "operation": operation,
                "active_connections": active_connections,
                "max_connections": max_connections,
                "pool_utilization": (active_connections / max_connections) * 100,
            },
        )


def raise_if_empty_text(text: str, operation: str) -> None:
    """
    Raise ValidationError if text is empty or whitespace-only.

    Args:
        text: Text to validate
        operation: Operation name for error context

    Raises:
        ValidationError: If text is empty
    """
    if not text or not text.strip():
        from .exceptions import ValidationError

        raise ValidationError(
            message=f"Empty or whitespace-only text provided for {operation}",
            context={"operation": operation, "text_length": len(text) if text else 0},
        )


def raise_if_invalid_path(path: str) -> None:
    """
    Raise ConfigurationError if path is invalid.

    Args:
        path: Path to validate

    Raises:
        ConfigurationError: If path is invalid
    """
    if not path or not Path(path).exists():
        from .exceptions import ConfigurationError

        raise ConfigurationError(
            message=f"Invalid or non-existent path: {path}",
            context={"path": path, "exists": Path(path).exists() if path else False},
        )


def raise_if_performance_exceeded(
    actual_time: float, threshold: float, operation: str = "operation"
) -> None:
    """
    Raise PerformanceError if operation exceeds time threshold.

    Args:
        actual_time: Actual operation time
        threshold: Performance threshold
        operation: Operation name

    Raises:
        PerformanceError: If threshold exceeded
    """
    if actual_time > threshold:
        from .exceptions import PerformanceError

        raise PerformanceError(
            message=f"{operation} exceeded performance threshold: {actual_time:.3f}s > {threshold:.3f}s",
            context={
                "operation": operation,
                "actual_time": actual_time,
                "threshold": threshold,
                "overhead": actual_time - threshold,
            },
        )


class ErrorRecoveryManager:
    """
    Manages error recovery strategies and automatic retry logic.

    Provides centralized error recovery with configurable strategies,
    exponential backoff, and recovery action execution.
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0) -> None:
        """
        Initialize error recovery manager.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.recovery_stats: dict[str, int] = {
            "total_errors": 0,
            "recovered_errors": 0,
            "failed_recoveries": 0,
            "recovery_attempts": 0,
        }

        # Recovery strategies for different error types
        self.recovery_strategies: dict[str, Callable[[Exception, str, dict[str, Any]], bool]] = {
            "DatabaseError": self._recover_database_error,
            "PerformanceError": self._recover_performance_error,
            "CacheError": self._recover_cache_error,
            "ConnectionPoolError": self._recover_connection_error,
            "ConfigurationError": self._recover_configuration_error,
        }

    def execute_with_recovery(
        self,
        operation: Callable[[], Any],
        operation_name: str,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute operation with automatic error recovery.

        Args:
            operation: Function to execute
            operation_name: Name for logging and context
            context: Additional context information

        Returns:
            Operation result

        Raises:
            Exception: If all recovery attempts fail
        """
        self.recovery_stats["total_errors"] += 1
        last_exception = None

        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                if attempt > 0:
                    self.recovery_stats["recovery_attempts"] += 1
                    delay = self.base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(
                        f"Retrying {operation_name} (attempt {attempt + 1}/{self.max_retries + 1}) after {delay}s delay"
                    )
                    time.sleep(delay)

                result = operation()

                if attempt > 0:
                    self.recovery_stats["recovered_errors"] += 1
                    logger.info(
                        f"Successfully recovered from error in {operation_name} after {attempt} retries"
                    )

                return result

            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    # Try to apply recovery strategy
                    recovered = self._apply_recovery_strategy(e, operation_name, context or {})
                    if not recovered:
                        logger.warning(f"Recovery strategy failed for {operation_name}: {e}")
                else:
                    # Final attempt failed
                    self.recovery_stats["failed_recoveries"] += 1
                    logger.error(f"All recovery attempts failed for {operation_name}: {e}")

        # All attempts failed
        if last_exception:
            raise last_exception
        else:
            from .exceptions import KuzuMemoryError

            raise KuzuMemoryError(f"Operation {operation_name} failed after all recovery attempts")

    def _apply_recovery_strategy(
        self, error: Exception, operation_name: str, context: dict[str, Any]
    ) -> bool:
        """
        Apply appropriate recovery strategy for the error type.

        Args:
            error: Exception that occurred
            operation_name: Name of the operation
            context: Additional context

        Returns:
            True if recovery was attempted, False otherwise
        """
        try:
            error_type = type(error).__name__

            # Try exact match first
            if error_type in self.recovery_strategies:
                return self.recovery_strategies[error_type](error, operation_name, context)

            # Try parent class matches
            for base_class in error.__class__.__mro__[1:]:  # Skip the exact class
                base_name = base_class.__name__
                if base_name in self.recovery_strategies:
                    return self.recovery_strategies[base_name](error, operation_name, context)

            # No specific strategy found, apply general recovery
            return self._recover_general_error(error, operation_name, context)

        except Exception as recovery_error:
            logger.error(f"Error in recovery strategy: {recovery_error}")
            return False

    def _recover_database_error(
        self, error: Exception, operation_name: str, context: dict[str, Any]
    ) -> bool:
        """Recover from database errors."""
        try:
            logger.info(f"Applying database error recovery for {operation_name}")

            # Common database recovery actions
            # - Wait for locks to release
            # - Reinitialize connections
            # - Check database health

            # Simulate recovery actions
            time.sleep(0.5)  # Wait for locks

            # Could add specific database recovery logic here
            # such as connection pool reset, database health checks, etc.

            return True

        except Exception as recovery_error:
            logger.error(f"Database recovery failed: {recovery_error}")
            return False

    def _recover_performance_error(
        self, error: Exception, operation_name: str, context: dict[str, Any]
    ) -> bool:
        """Recover from performance errors."""
        try:
            logger.info(f"Applying performance error recovery for {operation_name}")

            # Performance recovery actions
            # - Clear caches
            # - Reduce query complexity
            # - Optimize parameters

            # Simulate cache clearing
            time.sleep(0.1)

            return True

        except Exception as recovery_error:
            logger.error(f"Performance recovery failed: {recovery_error}")
            return False

    def _recover_cache_error(
        self, error: Exception, operation_name: str, context: dict[str, Any]
    ) -> bool:
        """Recover from cache errors."""
        try:
            logger.info(f"Applying cache error recovery for {operation_name}")

            # Cache recovery actions
            # - Clear corrupted cache entries
            # - Reinitialize cache
            # - Fallback to non-cached operation

            return True

        except Exception as recovery_error:
            logger.error(f"Cache recovery failed: {recovery_error}")
            return False

    def _recover_connection_error(
        self, error: Exception, operation_name: str, context: dict[str, Any]
    ) -> bool:
        """Recover from connection pool errors."""
        try:
            logger.info(f"Applying connection pool error recovery for {operation_name}")

            # Connection recovery actions
            # - Reset connection pool
            # - Clear stale connections
            # - Adjust pool size

            time.sleep(1.0)  # Wait for connections to become available

            return True

        except Exception as recovery_error:
            logger.error(f"Connection recovery failed: {recovery_error}")
            return False

    def _recover_configuration_error(
        self, error: Exception, operation_name: str, context: dict[str, Any]
    ) -> bool:
        """Recover from configuration errors."""
        try:
            logger.info(f"Applying configuration error recovery for {operation_name}")

            # Configuration recovery actions
            # - Reload configuration
            # - Apply default settings
            # - Validate configuration paths

            return True

        except Exception as recovery_error:
            logger.error(f"Configuration recovery failed: {recovery_error}")
            return False

    def _recover_general_error(
        self, error: Exception, operation_name: str, context: dict[str, Any]
    ) -> bool:
        """Apply general recovery strategy for unknown error types."""
        try:
            logger.info(
                f"Applying general error recovery for {operation_name}: {type(error).__name__}"
            )

            # General recovery actions
            # - Brief wait
            # - Reset state if possible
            # - Log context for debugging

            time.sleep(0.2)
            logger.debug(f"Error context: {context}")

            return True

        except Exception as recovery_error:
            logger.error(f"General recovery failed: {recovery_error}")
            return False

    def get_recovery_statistics(self) -> dict[str, Any]:
        """
        Get recovery statistics.

        Returns:
            Dictionary with recovery stats and metrics
        """
        stats_dict: dict[str, Any] = self.recovery_stats.copy()

        # Calculate derived metrics
        if stats_dict["total_errors"] > 0:
            stats_dict["recovery_success_rate"] = float(
                (stats_dict["recovered_errors"] / stats_dict["total_errors"]) * 100
            )
        else:
            stats_dict["recovery_success_rate"] = 100.0

        if stats_dict["recovery_attempts"] > 0:
            stats_dict["avg_attempts_per_recovery"] = float(
                stats_dict["recovery_attempts"] / stats_dict["recovered_errors"]
                if stats_dict["recovered_errors"] > 0
                else 0
            )
        else:
            stats_dict["avg_attempts_per_recovery"] = 0.0

        stats_dict["total_operations"] = stats_dict["total_errors"] + stats_dict["recovered_errors"]

        return stats_dict

    def reset_statistics(self) -> None:
        """Reset recovery statistics."""
        self.recovery_stats = {
            "total_errors": 0,
            "recovered_errors": 0,
            "failed_recoveries": 0,
            "recovery_attempts": 0,
        }
        logger.info("Recovery statistics reset")

    def configure_strategy(
        self,
        error_type: str,
        strategy: Callable[[Exception, str, dict[str, Any]], bool],
    ) -> None:
        """
        Configure custom recovery strategy for specific error type.

        Args:
            error_type: Name of error class to handle
            strategy: Callable that implements recovery logic
        """
        self.recovery_strategies[error_type] = strategy
        logger.info(f"Configured custom recovery strategy for {error_type}")

    def get_recommended_actions(self, error: Exception) -> list[str]:
        """
        Get recommended recovery actions for an error.

        Args:
            error: Exception to analyze

        Returns:
            List of recommended action descriptions
        """
        from .exceptions import KuzuMemoryError

        if isinstance(error, KuzuMemoryError) and hasattr(error, "recovery_actions"):
            return [action.value for action in error.recovery_actions]
        else:
            # General recommendations based on error type
            error_type = type(error).__name__

            general_recommendations = {
                "DatabaseError": [
                    "Check database connection",
                    "Verify database integrity",
                    "Restart database service",
                ],
                "PerformanceError": [
                    "Optimize query",
                    "Increase resources",
                    "Check system load",
                ],
                "CacheError": [
                    "Clear cache",
                    "Restart cache service",
                    "Check cache configuration",
                ],
                "ConnectionPoolError": [
                    "Check network connectivity",
                    "Increase pool size",
                    "Restart service",
                ],
                "ConfigurationError": [
                    "Check configuration files",
                    "Verify paths",
                    "Reset to defaults",
                ],
            }

            return general_recommendations.get(
                error_type, ["Retry operation", "Check logs", "Contact support"]
            )
