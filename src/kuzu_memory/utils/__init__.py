"""Utility components for KuzuMemory."""

from .exceptions import (
    KuzuMemoryError,
    DatabaseError,
    DatabaseLockError,
    CorruptedDatabaseError,
    DatabaseVersionError,
    ConfigurationError,
    ExtractionError,
    RecallError,
    PerformanceError,
    ValidationError,
)

from .error_recovery import (
    raise_if_empty_text,
    raise_if_invalid_path,
    raise_if_performance_exceeded,
)

from .validation import (
    validate_text_input,
    validate_memory_id,
    validate_confidence_score,
    validate_database_path,
    validate_config_dict,
    validate_entity_name,
    validate_memory_list,
    sanitize_for_database,
)

from .deduplication import DeduplicationEngine
from .performance import PerformanceMonitor, performance_timer, get_performance_monitor
from .config_loader import ConfigLoader, get_config_loader, load_config_from_file, load_config_auto

__all__ = [
    # Exceptions
    "KuzuMemoryError",
    "DatabaseError",
    "DatabaseLockError",
    "CorruptedDatabaseError",
    "DatabaseVersionError",
    "ConfigurationError",
    "ExtractionError",
    "RecallError",
    "PerformanceError",
    "ValidationError",
    "raise_if_empty_text",
    "raise_if_invalid_path",
    "raise_if_performance_exceeded",
    # Validation
    "validate_text_input",
    "validate_memory_id",
    "validate_confidence_score",
    "validate_database_path",
    "validate_config_dict",
    "validate_entity_name",
    "validate_memory_list",
    "sanitize_for_database",
    # Deduplication
    "DeduplicationEngine",
    # Performance monitoring
    "PerformanceMonitor",
    "performance_timer",
    "get_performance_monitor",
    # Configuration loading
    "ConfigLoader",
    "get_config_loader",
    "load_config_from_file",
    "load_config_auto",
]
