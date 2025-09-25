"""
Interface definitions for KuzuMemory components.

Defines abstract base classes that establish contracts for core components,
enabling better testing, mocking, and architectural flexibility.
"""

from .memory_store import IMemoryStore, IMemoryRecall
from .cache import ICache
from .connection_pool import IConnectionPool
from .performance_monitor import IPerformanceMonitor

__all__ = [
    "IMemoryStore",
    "IMemoryRecall",
    "ICache",
    "IConnectionPool",
    "IPerformanceMonitor",
]