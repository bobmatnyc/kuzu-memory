"""
Core exception classes and error codes for KuzuMemory.

Provides structured exception hierarchy with error codes and recovery suggestions.
Refactored to separate core exceptions from error recovery logic.
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
            context_info = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_info}")

        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "message": self.message,
            "error_code": self.error_code.value if self.error_code else None,
            "suggestion": self.suggestion,
            "recovery_actions": [action.value for action in self.recovery_actions],
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }


# Database Exceptions
class DatabaseError(KuzuMemoryError):
    """Base exception for database-related errors."""

    pass


class DatabaseLockError(DatabaseError):
    """Database is locked and cannot be accessed."""

    def __init__(self, message: str = "Database is locked", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_LOCK,
            suggestion="Wait for other operations to complete or restart the application",
            recovery_actions=[
                RecoveryAction.WAIT_AND_RETRY,
                RecoveryAction.REINITIALIZE,
            ],
            **kwargs,
        )


class CorruptedDatabaseError(DatabaseError):
    """Database file is corrupted or unreadable."""

    def __init__(self, message: str = "Database is corrupted", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_CORRUPTED,
            suggestion="Restore from backup or reinitialize database",
            recovery_actions=[
                RecoveryAction.REINITIALIZE,
                RecoveryAction.CONTACT_SUPPORT,
            ],
            **kwargs,
        )


class DatabaseVersionError(DatabaseError):
    """Database version is incompatible."""

    def __init__(self, current_version: str, expected_version: str, **kwargs: Any) -> None:
        message = (
            f"Database version mismatch: current={current_version}, expected={expected_version}"
        )
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_VERSION,
            suggestion="Upgrade database or downgrade application",
            recovery_actions=[RecoveryAction.REINITIALIZE, RecoveryAction.CHECK_CONFIG],
            context={
                "current_version": current_version,
                "expected_version": expected_version,
            },
            **kwargs,
        )


class DatabaseConnectionError(DatabaseError):
    """Failed to connect to database."""

    def __init__(self, message: str = "Failed to connect to database", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_CONNECTION,
            suggestion="Check database service and connection parameters",
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.CHECK_CONFIG],
            **kwargs,
        )


class DatabaseTimeoutError(DatabaseError):
    """Database operation timed out."""

    def __init__(self, operation: str, timeout: float, **kwargs: Any) -> None:
        message = f"Database operation '{operation}' timed out after {timeout}s"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.DATABASE_TIMEOUT,
            suggestion="Increase timeout or optimize query",
            recovery_actions=[
                RecoveryAction.OPTIMIZE_QUERY,
                RecoveryAction.INCREASE_RESOURCES,
            ],
            context={"operation": operation, "timeout": timeout},
            **kwargs,
        )


# Configuration Exceptions
class ConfigurationError(KuzuMemoryError):
    """Configuration-related error."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CONFIG_INVALID,
            suggestion="Check configuration file and settings",
            recovery_actions=[RecoveryAction.CHECK_CONFIG],
            **kwargs,
        )


# Memory Operation Exceptions
class ExtractionError(KuzuMemoryError):
    """Error during memory extraction."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.MEMORY_EXTRACTION,
            suggestion="Check input content and extraction settings",
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.CHECK_CONFIG],
            **kwargs,
        )


class RecallError(KuzuMemoryError):
    """Error during memory recall."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.MEMORY_RECALL,
            suggestion="Check query parameters and database connection",
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.OPTIMIZE_QUERY],
            **kwargs,
        )


class ValidationError(KuzuMemoryError):
    """Input validation error."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Handle both old signature (field, value, description) and new signature (message)
        if len(args) == 3:
            field, value, description = args
            message = f"{field} {description}: {value}"
        elif len(args) == 1:
            message = args[0]
        else:
            message = kwargs.get("message", "Validation error")

        super().__init__(
            message=message,
            error_code=MemoryErrorCode.MEMORY_VALIDATION,
            suggestion="Check input parameters and format",
            recovery_actions=[RecoveryAction.CHECK_CONFIG],
            **kwargs,
        )


# Performance Exceptions
class PerformanceError(KuzuMemoryError):
    """Performance threshold exceeded."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.PERFORMANCE_RECALL_TIMEOUT,
            suggestion="Optimize operations or increase performance limits",
            recovery_actions=[
                RecoveryAction.OPTIMIZE_QUERY,
                RecoveryAction.INCREASE_RESOURCES,
            ],
            **kwargs,
        )


class PerformanceThresholdError(PerformanceError):
    """Specific performance threshold violation."""

    def __init__(self, operation: str, actual_time: float, threshold: float, **kwargs: Any) -> None:
        message = (
            f"Performance threshold exceeded for {operation}: {actual_time:.3f}s > {threshold:.3f}s"
        )
        super().__init__(
            message=message,
            context={
                "operation": operation,
                "actual_time": actual_time,
                "threshold": threshold,
                "overhead": actual_time - threshold,
            },
            **kwargs,
        )


# Cache Exceptions
class CacheError(KuzuMemoryError):
    """Base exception for cache-related errors."""

    pass


class CacheFullError(CacheError):
    """Cache is full and cannot store more entries."""

    def __init__(self, message: str = "Cache is full", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CACHE_FULL,
            suggestion="Clear cache or increase cache size",
            recovery_actions=[
                RecoveryAction.REINITIALIZE,
                RecoveryAction.INCREASE_RESOURCES,
            ],
            **kwargs,
        )


class CacheCorruptionError(CacheError):
    """Cache data is corrupted."""

    def __init__(self, message: str = "Cache corruption detected", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CACHE_CORRUPTION,
            suggestion="Clear corrupted cache and reinitialize",
            recovery_actions=[RecoveryAction.REINITIALIZE],
            **kwargs,
        )


class CacheTimeoutError(CacheError):
    """Cache operation timed out."""

    def __init__(self, operation: str, timeout: float, **kwargs: Any) -> None:
        message = f"Cache operation '{operation}' timed out after {timeout}s"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CACHE_TIMEOUT,
            suggestion="Increase cache timeout or optimize cache operations",
            recovery_actions=[
                RecoveryAction.OPTIMIZE_QUERY,
                RecoveryAction.INCREASE_RESOURCES,
            ],
            context={"operation": operation, "timeout": timeout},
            **kwargs,
        )


# Connection Pool Exceptions
class ConnectionPoolError(KuzuMemoryError):
    """Base exception for connection pool errors."""

    pass


class PoolExhaustedError(ConnectionPoolError):
    """Connection pool has no available connections."""

    def __init__(self, message: str = "Connection pool exhausted", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.POOL_EXHAUSTED,
            suggestion="Increase pool size or optimize connection usage",
            recovery_actions=[
                RecoveryAction.WAIT_AND_RETRY,
                RecoveryAction.INCREASE_RESOURCES,
            ],
            **kwargs,
        )


class PoolTimeoutError(ConnectionPoolError):
    """Timed out waiting for connection from pool."""

    def __init__(self, timeout: float, **kwargs: Any) -> None:
        message = f"Connection pool timeout after {timeout}s"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.POOL_TIMEOUT,
            suggestion="Increase pool timeout or connection limit",
            recovery_actions=[
                RecoveryAction.WAIT_AND_RETRY,
                RecoveryAction.INCREASE_RESOURCES,
            ],
            context={"timeout": timeout},
            **kwargs,
        )


class PoolConnectionFailedError(ConnectionPoolError):
    """Failed to create connection in pool."""

    def __init__(self, message: str = "Failed to create connection", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.POOL_CONNECTION_FAILED,
            suggestion="Check database connectivity and configuration",
            recovery_actions=[RecoveryAction.CHECK_CONFIG, RecoveryAction.RETRY],
            **kwargs,
        )


# Integration Exceptions
class AsyncOperationError(KuzuMemoryError):
    """Error in asynchronous operation."""

    def __init__(self, operation: str, **kwargs: Any) -> None:
        message = f"Asynchronous operation failed: {operation}"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.ASYNC_OPERATION,
            suggestion="Check async operation status and retry if needed",
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.CHECK_CONFIG],
            context={"operation": operation},
            **kwargs,
        )


class AIIntegrationError(KuzuMemoryError):
    """Error in AI system integration."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.AI_INTEGRATION,
            suggestion="Check AI system connection and configuration",
            recovery_actions=[RecoveryAction.CHECK_CONFIG, RecoveryAction.RETRY],
            **kwargs,
        )


class CLIIntegrationError(KuzuMemoryError):
    """Error in CLI integration."""

    def __init__(self, command: str, exit_code: int, **kwargs: Any) -> None:
        message = f"CLI command failed: {command} (exit code: {exit_code})"
        super().__init__(
            message=message,
            error_code=MemoryErrorCode.CLI_INTEGRATION,
            suggestion="Check CLI installation and permissions",
            recovery_actions=[RecoveryAction.CHECK_CONFIG, RecoveryAction.RETRY],
            context={"command": command, "exit_code": exit_code},
            **kwargs,
        )
