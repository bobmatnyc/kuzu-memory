"""
Interface definitions for KuzuMemory components.

Defines abstract base classes that establish contracts for core components,
enabling better testing, mocking, and architectural flexibility.
"""

from .cache import ICache
from .connection_pool import IConnectionPool
from .memory_store import IMemoryRecall, IMemoryStore
from .performance_monitor import IPerformanceMonitor

__all__ = [
    "ICache",
    "IConnectionPool",
    "IMemoryRecall",
    "IMemoryStore",
    "IPerformanceMonitor",
]
