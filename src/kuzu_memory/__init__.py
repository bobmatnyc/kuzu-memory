"""
KuzuMemory - Lightweight, embedded graph-based memory system for AI applications.

A fast, offline memory system that stores and retrieves contextual memories
without requiring LLM calls, using pattern matching and local graph storage.

Key Features:
- No LLM dependencies - operates using pattern matching only
- Simple two-method API: attach_memories() and generate_memories()
- Embedded Kuzu graph database for local storage
- Git-friendly database files (<10MB)
- Fast performance (<10ms for memory operations)
- Works completely offline

Example Usage:
    >>> from kuzu_memory import KuzuMemory
    >>> memory = KuzuMemory()
    >>>
    >>> # Store memories from conversation
    >>> memory.generate_memories("My name is Alice and I prefer Python")
    >>>
    >>> # Retrieve relevant memories
    >>> context = memory.attach_memories("What's my name?")
    >>> print(context.enhanced_prompt)
"""

from pathlib import Path
from typing import Any

from .__version__ import DB_SCHEMA_VERSION, __version__, __version_info__

# Import main classes for public API
try:
    from .core.config import KuzuMemoryConfig
    from .core.memory import KuzuMemory
    from .core.models import Memory, MemoryContext, MemoryType

    # All imports successful
    _IMPORT_ERROR = None

except ImportError as e:
    # Graceful degradation during development/testing
    import warnings

    warnings.warn(f"Could not import core components: {e}", ImportWarning, stacklevel=2)

    _IMPORT_ERROR = e

    # Define placeholder classes to prevent import errors
    class KuzuMemory:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(f"KuzuMemory core components not available: {_IMPORT_ERROR}")

    class Memory:
        pass

    class MemoryContext:
        pass

    class MemoryType:
        pass

    class KuzuMemoryConfig:
        pass


# Public API
__all__ = [
    "DB_SCHEMA_VERSION",
    "KuzuMemory",
    "KuzuMemoryConfig",
    "Memory",
    "MemoryContext",
    "MemoryType",
    "__version__",
    "__version_info__",
    "create_memory_instance",
    "get_database_path",
    "is_available",
]

# Package metadata
__title__ = "kuzu-memory"
__description__ = "Lightweight, embedded graph-based memory system for AI applications"
__author__ = "KuzuMemory Team"
__author_email__ = "team@kuzu-memory.dev"
__license__ = "MIT"
__copyright__ = "Copyright 2024 KuzuMemory Team"


def get_version() -> str:
    """Get the current version string."""
    return __version__


def get_database_path(custom_path: Path | None = None) -> Path:
    """
    Get the default database path with proper initialization.

    Args:
        custom_path: Optional custom database path

    Returns:
        Path to database file with parent directories created
    """
    if custom_path:
        db_path = Path(custom_path)
    else:
        db_path = Path.home() / ".kuzu-memory" / "memories.db"

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return db_path


def create_memory_instance(
    db_path: Path | None = None, config: dict[str, Any] | None = None
) -> "KuzuMemory":
    """
    Factory function to create a KuzuMemory instance with error handling.

    Args:
        db_path: Optional path to database file
        config: Optional configuration dictionary

    Returns:
        Initialized KuzuMemory instance

    Raises:
        ImportError: If core components are not available
        RuntimeError: If initialization fails
    """
    if _IMPORT_ERROR:
        raise ImportError(
            f"KuzuMemory core components not available: {_IMPORT_ERROR}. "
            "Please ensure all dependencies are installed."
        )

    try:
        return KuzuMemory(db_path=db_path, config=config)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize KuzuMemory: {e}") from e


def is_available() -> bool:
    """
    Check if KuzuMemory is available and properly installed.

    Returns:
        True if all components are available, False otherwise
    """
    return _IMPORT_ERROR is None
