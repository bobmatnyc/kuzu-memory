"""
Custom exceptions for KuzuMemory.

Provides specific error types for different failure scenarios
with clear error messages and recovery suggestions.
"""

from typing import Optional


class KuzuMemoryError(Exception):
    """Base exception for all KuzuMemory operations."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message with optional suggestion."""
        if self.suggestion:
            return f"{self.message}\nSuggestion: {self.suggestion}"
        return self.message


class DatabaseError(KuzuMemoryError):
    """Base class for database-related errors."""
    pass


class DatabaseLockError(DatabaseError):
    """Database is locked by another process."""
    
    def __init__(self, db_path: str, timeout: float = 5.0):
        message = f"Database at '{db_path}' is locked by another process"
        suggestion = f"Wait {timeout}s and try again, or check for other KuzuMemory instances"
        super().__init__(message, suggestion)


class CorruptedDatabaseError(DatabaseError):
    """Database file is corrupted or incompatible."""
    
    def __init__(self, db_path: str, error_details: Optional[str] = None):
        message = f"Database at '{db_path}' is corrupted or incompatible"
        if error_details:
            message += f": {error_details}"
        suggestion = "Backup the file and reinitialize with KuzuMemory.init_database()"
        super().__init__(message, suggestion)


class DatabaseVersionError(DatabaseError):
    """Database schema version is incompatible."""
    
    def __init__(self, current_version: str, required_version: str):
        message = f"Database schema version {current_version} is incompatible with required {required_version}"
        suggestion = "Run database migration or reinitialize with a new database file"
        super().__init__(message, suggestion)


class ConfigurationError(KuzuMemoryError):
    """Configuration is invalid or missing."""
    
    def __init__(self, config_issue: str):
        message = f"Configuration error: {config_issue}"
        suggestion = "Check your configuration file or initialization parameters"
        super().__init__(message, suggestion)


class ExtractionError(KuzuMemoryError):
    """Error during memory extraction from text."""
    
    def __init__(self, text_length: int, error_details: str):
        message = f"Failed to extract memories from text ({text_length} chars): {error_details}"
        suggestion = "Check input text encoding and length limits"
        super().__init__(message, suggestion)


class RecallError(KuzuMemoryError):
    """Error during memory recall/retrieval."""
    
    def __init__(self, query: str, error_details: str):
        message = f"Failed to recall memories for query '{query[:50]}...': {error_details}"
        suggestion = "Try a simpler query or check database connectivity"
        super().__init__(message, suggestion)


class PerformanceError(KuzuMemoryError):
    """Operation exceeded performance requirements."""
    
    def __init__(self, operation: str, actual_time: float, max_time: float):
        message = f"Operation '{operation}' took {actual_time:.1f}ms (max: {max_time:.1f}ms)"
        suggestion = "Consider optimizing database indices or reducing query complexity"
        super().__init__(message, suggestion)


class ValidationError(KuzuMemoryError):
    """Input validation failed."""
    
    def __init__(self, field: str, value: str, requirement: str):
        message = f"Validation failed for {field}='{value}': {requirement}"
        suggestion = "Check input parameters and their constraints"
        super().__init__(message, suggestion)


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


def raise_if_performance_exceeded(
    operation: str, 
    actual_time: float, 
    max_time: float
) -> None:
    """Raise PerformanceError if operation exceeded time limit."""
    if actual_time > max_time:
        raise PerformanceError(operation, actual_time, max_time)
