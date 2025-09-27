"""Utility components for KuzuMemory."""

from .config_loader import (
    ConfigLoader,
    get_config_loader,
    load_config_auto,
    load_config_from_file,
)
from .deduplication import DeduplicationEngine
from .error_recovery import (
    raise_if_empty_text,
    raise_if_invalid_path,
    raise_if_performance_exceeded,
)
from .exceptions import (
    ConfigurationError,
    CorruptedDatabaseError,
    DatabaseError,
    DatabaseLockError,
    DatabaseVersionError,
    ExtractionError,
    KuzuMemoryError,
    PerformanceError,
    RecallError,
    ValidationError,
)
from .performance import PerformanceMonitor, get_performance_monitor, performance_timer
from .validation import (
    sanitize_for_database,
    validate_confidence_score,
    validate_config_dict,
    validate_database_path,
    validate_entity_name,
    validate_memory_id,
    validate_memory_list,
    validate_text_input,
)

__all__ = [
    # Configuration loading
    "ConfigLoader",
    "ConfigurationError",
    "CorruptedDatabaseError",
    "DatabaseError",
    "DatabaseLockError",
    "DatabaseVersionError",
    # Deduplication
    "DeduplicationEngine",
    "ExtractionError",
    # Exceptions
    "KuzuMemoryError",
    "PerformanceError",
    # Performance monitoring
    "PerformanceMonitor",
    "RecallError",
    "ValidationError",
    "get_config_loader",
    "get_performance_monitor",
    "load_config_auto",
    "load_config_from_file",
    "performance_timer",
    "raise_if_empty_text",
    "raise_if_invalid_path",
    "raise_if_performance_exceeded",
    "sanitize_for_database",
    "validate_confidence_score",
    "validate_config_dict",
    "validate_database_path",
    "validate_entity_name",
    "validate_memory_id",
    "validate_memory_list",
    # Validation
    "validate_text_input",
]
