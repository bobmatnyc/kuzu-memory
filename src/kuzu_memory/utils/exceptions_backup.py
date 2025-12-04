"""
Enhanced custom exceptions for KuzuMemory with error codes and recovery actions.

Provides comprehensive error types for different failure scenarios with:
- Structured error codes for programmatic handling
- Clear error messages and recovery suggestions
- Context information for debugging
- Performance threshold enforcement
"""

from datetime import datetime
from enum import Enum
from typing import Any


class MemoryErrorCode(Enum):
    """Structured error codes for programmatic error handling."""

    # Database errors (1000-1999)
    DATABASE_LOCK = 1001
    DATABASE_CORRUPTED = 1002
    DATABASE_VERSION = 1003
    DATABASE_CONNECTION = 1004
    DATABASE_TIMEOUT = 1005

    # Configuration errors (2000-2999)
    CONFIG_INVALID = 2001
    CONFIG_MISSING = 2002
    CONFIG_PATH_INVALID = 2003

    # Memory operation errors (3000-3999)
    MEMORY_EXTRACTION = 3001
    MEMORY_RECALL = 3002
    MEMORY_VALIDATION = 3003
    MEMORY_STORAGE = 3004
    MEMORY_DUPLICATE = 3005

    # Performance errors (4000-4999)
    PERFORMANCE_RECALL_TIMEOUT = 4001
    PERFORMANCE_GENERATION_TIMEOUT = 4002
    PERFORMANCE_CACHE_MISS = 4003
    PERFORMANCE_DATABASE_SLOW = 4004

    # Cache errors (5000-5999)
    CACHE_FULL = 5001
    CACHE_CORRUPTION = 5002
    CACHE_TIMEOUT = 5003

    # Connection pool errors (6000-6999)
    POOL_EXHAUSTED = 6001
    POOL_TIMEOUT = 6002
    POOL_CONNECTION_FAILED = 6003

    # Integration errors (7000-7999)
    AI_INTEGRATION = 7001
    CLI_INTEGRATION = 7002
    ASYNC_OPERATION = 7003


class RecoveryAction(Enum):
    """Suggested recovery actions for different error types."""

    RETRY = "retry"
    WAIT_AND_RETRY = "wait_and_retry"
    REINITIALIZE = "reinitialize"
    CHECK_CONFIG = "check_config"
    OPTIMIZE_QUERY = "optimize_query"
    INCREASE_RESOURCES = "increase_resources"
    CONTACT_SUPPORT = "contact_support"


class KuzuMemoryError(Exception):
    """Enhanced base exception for all KuzuMemory operations."""

    def __init__(
        self,
        message: str,
        error_code: MemoryErrorCode | None = None,
        suggestion: str | None = None,
        recovery_actions: list[RecoveryAction] | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.suggestion = suggestion
        self.recovery_actions = recovery_actions or []
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.now()

        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format comprehensive error message."""
        parts = [self.message]

        if self.error_code:
            parts.append(f"Error Code: {self.error_code.value}")

        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")

        if self.recovery_actions:
            actions = ", ".join(action.value for action in self.recovery_actions)
            parts.append(f"Recovery Actions: {actions}")

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {self.cause}")

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "error_code": self.error_code.value if self.error_code else None,
            "suggestion": self.suggestion,
            "recovery_actions": [action.value for action in self.recovery_actions],
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }


class DatabaseError(KuzuMemoryError):
    """Base class for database-related errors."""

    pass


class DatabaseLockError(DatabaseError):
    """Database is locked by another process."""

    def __init__(self, db_path: str, timeout: float = 5.0, pid: int | None = None) -> None:
        message = f"Database at '{db_path}' is locked by another process"
        suggestion = f"Wait {timeout}s and try again, or check for other KuzuMemory instances"

        context = {"db_path": db_path, "timeout": timeout}
        if pid:
            context["locking_pid"] = pid

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_LOCK,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.WAIT_AND_RETRY],
            context=context,
        )


class CorruptedDatabaseError(DatabaseError):
    """Database file is corrupted or incompatible."""

    def __init__(
        self,
        db_path: str,
        error_details: str | None = None,
        backup_available: bool = False,
    ) -> None:
        message = f"Database at '{db_path}' is corrupted or incompatible"
        if error_details:
            message += f": {error_details}"

        suggestion = "Backup the file and reinitialize with KuzuMemory.init_database()"
        if backup_available:
            suggestion += " or restore from backup"

        recovery_actions = [RecoveryAction.REINITIALIZE]
        if backup_available:
            recovery_actions.append(RecoveryAction.RETRY)

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_CORRUPTED,
            suggestion=suggestion,
            recovery_actions=recovery_actions,
            context={"db_path": db_path, "backup_available": backup_available},
        )


class DatabaseVersionError(DatabaseError):
    """Database schema version is incompatible."""

    def __init__(
        self,
        current_version: str,
        required_version: str,
        migration_available: bool = False,
    ) -> None:
        message = f"Database schema version {current_version} is incompatible with required {required_version}"

        if migration_available:
            suggestion = "Run database migration to upgrade schema"
            recovery_actions = [RecoveryAction.RETRY]
        else:
            suggestion = "Reinitialize with a new database file"
            recovery_actions = [RecoveryAction.REINITIALIZE]

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_VERSION,
            suggestion=suggestion,
            recovery_actions=recovery_actions,
            context={
                "current_version": current_version,
                "required_version": required_version,
                "migration_available": migration_available,
            },
        )


class DatabaseConnectionError(DatabaseError):
    """Failed to connect to database."""

    def __init__(self, db_path: str, cause: Exception | None = None, retry_count: int = 0) -> None:
        message = f"Failed to connect to database at '{db_path}'"
        if retry_count > 0:
            message += f" after {retry_count} attempts"

        suggestion = "Check database path and permissions, or initialize new database"
        recovery_actions = [RecoveryAction.CHECK_CONFIG, RecoveryAction.REINITIALIZE]

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_CONNECTION,
            suggestion=suggestion,
            recovery_actions=recovery_actions,
            context={"db_path": db_path, "retry_count": retry_count},
            cause=cause,
        )


class DatabaseTimeoutError(DatabaseError):
    """Database operation timed out."""

    def __init__(self, operation: str, timeout_ms: float, query: str | None = None) -> None:
        message = f"Database operation '{operation}' timed out after {timeout_ms}ms"
        suggestion = "Consider optimizing the query or increasing timeout"

        context = {"operation": operation, "timeout_ms": timeout_ms}
        if query:
            context["query"] = query[:100] + "..." if len(query) > 100 else query

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_TIMEOUT,
            suggestion=suggestion,
            recovery_actions=[
                RecoveryAction.OPTIMIZE_QUERY,
                RecoveryAction.INCREASE_RESOURCES,
            ],
            context=context,
        )


class ConfigurationError(KuzuMemoryError):
    """Configuration is invalid or missing."""

    def __init__(self, config_issue: str) -> None:
        message = f"Configuration error: {config_issue}"
        suggestion = "Check your configuration file or initialization parameters"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CONFIG_INVALID,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.CHECK_CONFIG],
        )


class ExtractionError(KuzuMemoryError):
    """Error during memory extraction from text."""

    def __init__(self, text_length: int, error_details: str) -> None:
        message = f"Failed to extract memories from text ({text_length} chars): {error_details}"
        suggestion = "Check input text encoding and length limits"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.MEMORY_EXTRACTION,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.CHECK_CONFIG],
            context={"text_length": text_length},
        )


class RecallError(KuzuMemoryError):
    """Error during memory recall/retrieval."""

    def __init__(self, query: str, error_details: str) -> None:
        message = f"Failed to recall memories for query '{query[:50]}...': {error_details}"
        suggestion = "Try a simpler query or check database connectivity"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.MEMORY_RECALL,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.OPTIMIZE_QUERY],
            context={"query": query[:50]},
        )


class PerformanceError(KuzuMemoryError):
    """Operation exceeded performance requirements."""

    def __init__(self, operation: str, actual_time: float, max_time: float) -> None:
        message = f"Operation '{operation}' took {actual_time:.1f}ms (max: {max_time:.1f}ms)"
        suggestion = "Consider optimizing database indices or reducing query complexity"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.PERFORMANCE_RECALL_TIMEOUT,
            suggestion=suggestion,
            recovery_actions=[
                RecoveryAction.OPTIMIZE_QUERY,
                RecoveryAction.INCREASE_RESOURCES,
            ],
            context={
                "operation": operation,
                "actual_time": actual_time,
                "max_time": max_time,
            },
        )


class ValidationError(KuzuMemoryError):
    """Input validation failed."""

    def __init__(self, field: str, value: str, requirement: str) -> None:
        message = f"Validation failed for {field}='{value}': {requirement}"
        suggestion = "Check input parameters and their constraints"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.MEMORY_VALIDATION,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.CHECK_CONFIG],
            context={"field": field, "value": value},
        )


# Convenience functions for common error scenarios


def raise_if_empty_text(text: str, operation: str) -> None:
    """Raise ValidationError if text is empty or whitespace-only."""
    if not text or not text.strip():
        raise ValidationError("text", text, f"cannot be empty for {operation}")


def raise_if_invalid_path(path: str) -> None:
    """Raise ValidationError if path is invalid."""
    if not path or len(path.strip()) == 0:
        raise ValidationError("path", path, "cannot be empty")

    # Additional path validation could be added here
    if len(path) > 255:
        raise ValidationError("path", path[:50] + "...", "path too long (max 255 chars)")


def raise_if_performance_exceeded(operation: str, actual_time: float, max_time: float) -> None:
    """Raise PerformanceError if operation exceeded time limit."""
    if actual_time > max_time:
        raise PerformanceError(operation, actual_time, max_time)


# Enhanced exception classes for new components


class CacheError(KuzuMemoryError):
    """Base class for cache-related errors."""

    pass


class CacheFullError(CacheError):
    """Cache has reached capacity and cannot store more items."""

    def __init__(self, cache_type: str, current_size: int, max_size: int) -> None:
        message = f"{cache_type} cache is full ({current_size}/{max_size})"
        suggestion = "Increase cache size or reduce TTL to allow more frequent eviction"

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CACHE_FULL,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.INCREASE_RESOURCES],
            context={
                "cache_type": cache_type,
                "current_size": current_size,
                "max_size": max_size,
                "utilization": current_size / max_size,
            },
        )


class CacheCorruptionError(CacheError):
    """Cache data is corrupted or invalid."""

    def __init__(self, cache_type: str, corrupted_keys: list[str]) -> None:
        message = f"{cache_type} cache corruption detected"
        if corrupted_keys:
            message += f" in keys: {corrupted_keys[:5]}"
            if len(corrupted_keys) > 5:
                message += f" and {len(corrupted_keys) - 5} more"

        suggestion = "Clear cache to resolve corruption"

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CACHE_CORRUPTION,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.REINITIALIZE],
            context={
                "cache_type": cache_type,
                "corrupted_count": len(corrupted_keys),
                "corrupted_keys": corrupted_keys[:10],  # Limit for logging
            },
        )


class CacheTimeoutError(CacheError):
    """Cache operation timed out."""

    def __init__(self, operation: str, timeout_ms: float, cache_type: str) -> None:
        message = f"Cache {operation} on {cache_type} timed out after {timeout_ms}ms"
        suggestion = "Check cache performance or increase timeout"

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CACHE_TIMEOUT,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.INCREASE_RESOURCES],
            context={
                "operation": operation,
                "timeout_ms": timeout_ms,
                "cache_type": cache_type,
            },
        )


class ConnectionPoolError(KuzuMemoryError):
    """Base class for connection pool errors."""

    pass


class PoolExhaustedError(ConnectionPoolError):
    """Connection pool has no available connections."""

    def __init__(self, pool_size: int, active_connections: int, wait_time_ms: float) -> None:
        message = f"Connection pool exhausted ({active_connections}/{pool_size} active)"
        if wait_time_ms > 0:
            message += f" after waiting {wait_time_ms}ms"

        suggestion = "Increase pool size or reduce connection hold times"

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.POOL_EXHAUSTED,
            suggestion=suggestion,
            recovery_actions=[
                RecoveryAction.INCREASE_RESOURCES,
                RecoveryAction.WAIT_AND_RETRY,
            ],
            context={
                "pool_size": pool_size,
                "active_connections": active_connections,
                "utilization": active_connections / pool_size,
                "wait_time_ms": wait_time_ms,
            },
        )


class PoolTimeoutError(ConnectionPoolError):
    """Timed out waiting for connection from pool."""

    def __init__(self, timeout_ms: float, pool_stats: dict[str, Any]) -> None:
        message = f"Timed out waiting {timeout_ms}ms for connection from pool"
        suggestion = "Increase connection timeout or pool size"

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.POOL_TIMEOUT,
            suggestion=suggestion,
            recovery_actions=[
                RecoveryAction.INCREASE_RESOURCES,
                RecoveryAction.WAIT_AND_RETRY,
            ],
            context={"timeout_ms": timeout_ms, "pool_stats": pool_stats},
        )


class PoolConnectionFailedError(ConnectionPoolError):
    """Failed to create new connection in pool."""

    def __init__(self, db_path: str, cause: Exception | None = None, attempts: int = 1) -> None:
        message = f"Failed to create connection to {db_path}"
        if attempts > 1:
            message += f" after {attempts} attempts"

        suggestion = "Check database availability and connection parameters"

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.POOL_CONNECTION_FAILED,
            suggestion=suggestion,
            recovery_actions=[
                RecoveryAction.CHECK_CONFIG,
                RecoveryAction.WAIT_AND_RETRY,
            ],
            context={"db_path": db_path, "attempts": attempts},
            cause=cause,
        )


class PerformanceThresholdError(PerformanceError):
    """Operation exceeded performance threshold."""

    def __init__(
        self,
        operation: str,
        actual_time: float,
        threshold: float,
        severity: str = "warning",
        recommendations: list[str] | None = None,
    ) -> None:
        # Call PerformanceError's __init__ which expects (operation, actual_time, max_time)
        # PerformanceError will handle calling KuzuMemoryError.__init__ with proper args
        super().__init__(operation, actual_time, threshold)

        # Update context with additional fields
        if recommendations:
            self.context["recommendations"] = recommendations
        self.context["severity"] = severity
        self.context["performance_ratio"] = actual_time / threshold

        # Update error code based on operation type
        if "recall" in operation.lower():
            self.error_code = MemoryErrorCode.PERFORMANCE_RECALL_TIMEOUT
        elif "generation" in operation.lower():
            self.error_code = MemoryErrorCode.PERFORMANCE_GENERATION_TIMEOUT
        else:
            self.error_code = MemoryErrorCode.PERFORMANCE_DATABASE_SLOW


class AsyncOperationError(KuzuMemoryError):
    """Error in async operation management."""

    def __init__(
        self,
        operation: str,
        error_details: str,
        task_id: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        message = f"Async operation '{operation}' failed: {error_details}"
        suggestion = "Check async task management and error handling"

        context = {"operation": operation}
        if task_id:
            context["task_id"] = task_id

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.ASYNC_OPERATION,
            suggestion=suggestion,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.CHECK_CONFIG],
            context=context,
            cause=cause,
        )


# Enhanced validation functions with structured error handling


def validate_performance_requirements(
    operation: str,
    actual_time_ms: float,
    max_time_ms: float,
    recommendations: list[str] | None = None,
) -> None:
    """Validate operation meets performance requirements."""
    if actual_time_ms > max_time_ms:
        raise PerformanceThresholdError(
            operation=operation,
            actual_time=actual_time_ms,
            threshold=max_time_ms,
            severity="critical" if actual_time_ms > max_time_ms * 2 else "warning",
            recommendations=recommendations,
        )


def validate_cache_operation(
    cache_type: str, operation: str, success: bool, error_details: str | None = None
) -> None:
    """Validate cache operation success."""
    if not success:
        if "timeout" in (error_details or "").lower():
            raise CacheTimeoutError(operation, 1000.0, cache_type)  # Default timeout
        elif "full" in (error_details or "").lower():
            raise CacheFullError(cache_type, 0, 0)  # Will need actual values
        else:
            raise CacheCorruptionError(cache_type, [])


def validate_connection_pool_health(
    pool_size: int, active_connections: int, max_utilization: float = 0.95
) -> None:
    """Validate connection pool is healthy."""
    if pool_size == 0:
        raise PoolConnectionFailedError("unknown", None, 0)

    utilization = active_connections / pool_size
    if utilization > max_utilization:
        raise PoolExhaustedError(pool_size, active_connections, 0.0)


# Error recovery utilities


class ErrorRecoveryManager:
    """Manages automatic error recovery strategies."""

    @staticmethod
    def should_retry(error: KuzuMemoryError, attempt: int, max_attempts: int = 3) -> bool:
        """Determine if an error should trigger a retry."""
        if attempt >= max_attempts:
            return False

        # Retry for specific recovery actions
        retry_actions = {
            RecoveryAction.RETRY,
            RecoveryAction.WAIT_AND_RETRY,
            RecoveryAction.OPTIMIZE_QUERY,
        }

        return any(action in retry_actions for action in error.recovery_actions)

    @staticmethod
    def get_retry_delay(error: KuzuMemoryError, attempt: int) -> float:
        """Calculate retry delay in seconds."""
        base_delay = 1.0

        # Exponential backoff for certain error types
        if error.error_code in [
            MemoryErrorCode.DATABASE_LOCK,
            MemoryErrorCode.POOL_TIMEOUT,
            MemoryErrorCode.CACHE_TIMEOUT,
        ]:
            return float(base_delay * (2**attempt))

        # Linear backoff for performance issues
        if error.error_code in [
            MemoryErrorCode.PERFORMANCE_RECALL_TIMEOUT,
            MemoryErrorCode.PERFORMANCE_DATABASE_SLOW,
        ]:
            return float(base_delay * attempt)

        return base_delay

    @staticmethod
    def suggest_configuration_changes(error: KuzuMemoryError) -> dict[str, Any]:
        """Suggest configuration changes based on error."""
        suggestions = {}

        if error.error_code == MemoryErrorCode.POOL_EXHAUSTED:
            suggestions["connection_pool.max_connections"] = "increase"
            suggestions["connection_pool.timeout"] = "increase"

        elif error.error_code == MemoryErrorCode.CACHE_FULL:
            suggestions["cache.max_size"] = "increase"
            suggestions["cache.ttl"] = "decrease"

        elif error.error_code in [
            MemoryErrorCode.PERFORMANCE_RECALL_TIMEOUT,
            MemoryErrorCode.PERFORMANCE_DATABASE_SLOW,
        ]:
            suggestions["performance.enable_caching"] = "true"
            suggestions["database.connection_pool_size"] = "increase"

        return suggestions
