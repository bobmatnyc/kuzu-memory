"""
Abstract interface for caching implementations.

Defines the contract for caching systems used throughout KuzuMemory
for performance optimization.
"""

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any


class ICache(ABC):
    """
    Abstract interface for cache implementations.

    Supports both synchronous and asynchronous operations,
    TTL-based expiration, and bulk operations.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Retrieve a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """
        Store a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live for the cached value
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Remove a value from cache.

        Args:
            key: Cache key to remove

        Returns:
            True if key was deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists and is not expired
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Remove all cached values."""
        pass

    @abstractmethod
    async def get_multi(self, keys: list[str]) -> dict[str, Any]:
        """
        Retrieve multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key-value pairs for found keys
        """
        pass

    @abstractmethod
    async def set_multi(self, items: dict[str, Any], ttl: timedelta | None = None) -> None:
        """
        Store multiple values in cache.

        Args:
            items: Dictionary of key-value pairs to cache
            ttl: Time-to-live for all cached values
        """
        pass

    @abstractmethod
    async def delete_multi(self, keys: list[str]) -> int:
        """
        Remove multiple values from cache.

        Args:
            keys: List of cache keys to remove

        Returns:
            Number of keys actually deleted
        """
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary containing cache metrics like hit rate, size, etc.
        """
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        pass

    # Synchronous versions for performance-critical operations
    def get_sync(self, key: str) -> Any | None:
        """
        Synchronous version of get() for performance-critical paths.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        # Default implementation falls back to async
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(self.get(key))
        except RuntimeError:
            # No event loop running, create new one
            return asyncio.run(self.get(key))

    def set_sync(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """
        Synchronous version of set() for performance-critical paths.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live for the cached value
        """
        # Default implementation falls back to async
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(self.set(key, value, ttl))
        except RuntimeError:
            # No event loop running, create new one
            asyncio.run(self.set(key, value, ttl))
