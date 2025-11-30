"""
LRU (Least Recently Used) cache implementation.

High-performance caching with automatic eviction based on usage patterns
and configurable size limits.
"""

import asyncio
import hashlib
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from threading import RLock
from typing import Any

from ..interfaces.cache import ICache


class LRUCache(ICache):
    """
    Thread-safe LRU cache implementation.

    Features:
    - Configurable maximum size with automatic eviction
    - TTL (time-to-live) support for entries
    - Thread-safe operations with RLock
    - Cache statistics and hit rate tracking
    - Bulk operations for efficiency
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: timedelta | None = None,
        cleanup_interval: timedelta = timedelta(minutes=5),
    ):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL for entries
            cleanup_interval: How often to clean up expired entries
        """
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval

        # Thread-safe cache storage
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = RLock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expired_cleanups = 0

        # Background cleanup
        self._cleanup_task: asyncio.Task[None] | None = None
        self._last_cleanup = time.time()

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Store a value in cache."""
        ttl = ttl or self._default_ttl
        expiry = datetime.now() + ttl if ttl else None

        with self._lock:
            # Create new entry
            entry = _CacheEntry(value, expiry)

            # Add to cache
            self._cache[key] = entry
            self._cache.move_to_end(key)

            # Evict if necessary
            while len(self._cache) > self._max_size:
                _oldest_key, _ = self._cache.popitem(last=False)
                self._evictions += 1

        # Periodic cleanup
        await self._maybe_cleanup()

    async def delete(self, key: str) -> bool:
        """Remove a value from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            if entry.is_expired():
                del self._cache[key]
                return False

            return True

    async def clear(self) -> None:
        """Remove all cached values."""
        with self._lock:
            self._cache.clear()

    async def get_multi(self, keys: list[str]) -> dict[str, Any]:
        """Retrieve multiple values from cache."""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_multi(self, items: dict[str, Any], ttl: timedelta | None = None) -> None:
        """Store multiple values in cache."""
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def delete_multi(self, keys: list[str]) -> int:
        """Remove multiple values from cache."""
        deleted = 0
        for key in keys:
            if await self.delete(key):
                deleted += 1
        return deleted

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 3),
                "evictions": self._evictions,
                "expired_cleanups": self._expired_cleanups,
                "utilization": len(self._cache) / self._max_size,
            }

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache."""
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

        self._expired_cleanups += len(expired_keys)
        return len(expired_keys)

    def get_sync(self, key: str) -> Any | None:
        """Synchronous version of get()."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value

    def set_sync(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Synchronous version of set()."""
        ttl = ttl or self._default_ttl
        expiry = datetime.now() + ttl if ttl else None

        with self._lock:
            # Create new entry
            entry = _CacheEntry(value, expiry)

            # Add to cache
            self._cache[key] = entry
            self._cache.move_to_end(key)

            # Evict if necessary
            while len(self._cache) > self._max_size:
                _oldest_key, _ = self._cache.popitem(last=False)
                self._evictions += 1

    async def _maybe_cleanup(self) -> None:
        """Perform cleanup if enough time has passed."""
        current_time = time.time()
        if (current_time - self._last_cleanup) > self._cleanup_interval.total_seconds():
            await self.cleanup_expired()
            self._last_cleanup = current_time

    def create_cache_key(self, *args: Any, **kwargs: Any) -> str:
        """Create a consistent cache key from arguments."""
        # Convert args and kwargs to a consistent string representation
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items()),  # Sort for consistency
        }
        key_string = str(key_data)

        # Create hash for consistent key length
        return hashlib.md5(key_string.encode()).hexdigest()


class _CacheEntry:
    """Internal cache entry with TTL support."""

    def __init__(self, value: Any, expiry: datetime | None = None) -> None:
        self.value = value
        self.expiry = expiry
        self.created_at = datetime.now()

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expiry is None:
            return False
        return datetime.now() > self.expiry

    def age_seconds(self) -> float:
        """Get age of this entry in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
