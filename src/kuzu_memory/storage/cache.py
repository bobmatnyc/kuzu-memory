"""
LRU cache implementation for KuzuMemory.

Provides fast in-memory caching of frequently accessed memories
and query results to improve performance.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from typing import Any

from ..core.models import Memory, MemoryContext


class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache implementation.

    Provides fast access to cached items with automatic eviction
    of least recently used items when capacity is exceeded.
    """

    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 300) -> None:
        """
        Initialize LRU cache.

        Args:
            maxsize: Maximum number of items to cache
            ttl_seconds: Time-to-live for cached items in seconds
        """
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._timestamps: dict[str, float] = {}
        self._lock = threading.RLock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _is_expired(self, key: str) -> bool:
        """Check if a cached item has expired."""
        if key not in self._timestamps:
            return True

        age = time.time() - self._timestamps[key]
        return age > self.ttl_seconds

    def _evict_expired(self) -> None:
        """Remove expired items from cache."""
        current_time = time.time()
        expired_keys = []

        for key, timestamp in self._timestamps.items():
            if current_time - timestamp > self.ttl_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                self._evictions += 1

    def get(self, key: str) -> Any | None:
        """
        Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            # Check if key exists and is not expired
            if key in self._cache and not self._is_expired(key):
                # Move to end (most recently used)
                value = self._cache.pop(key)
                self._cache[key] = value
                self._timestamps[key] = time.time()
                self._hits += 1
                return value

            # Remove expired item if it exists
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                self._evictions += 1

            self._misses += 1
            return None

    def put(self, key: str, value: Any) -> None:
        """
        Put item in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            current_time = time.time()

            # Remove expired items periodically
            if len(self._cache) % 100 == 0:  # Every 100 operations
                self._evict_expired()

            # If key already exists, update it
            if key in self._cache:
                del self._cache[key]

            # If at capacity, remove least recently used item
            elif len(self._cache) >= self.maxsize:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
                self._evictions += 1

            # Add new item
            self._cache[key] = value
            self._timestamps[key] = current_time

    def delete(self, key: str) -> bool:
        """
        Delete item from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if item was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._evictions += len(self._cache)

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 3),
                "evictions": self._evictions,
                "ttl_seconds": self.ttl_seconds,
            }


class MemoryCache:
    """
    Specialized cache for KuzuMemory operations.

    Provides caching for memories, query results, and entity lookups
    with intelligent cache key generation and memory-specific optimizations.
    """

    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 300) -> None:
        """
        Initialize memory cache.

        Args:
            maxsize: Maximum number of items to cache
            ttl_seconds: Time-to-live for cached items
        """
        self._cache = LRUCache(maxsize, ttl_seconds)
        self._memory_cache = LRUCache(maxsize // 2, ttl_seconds * 2)  # Longer TTL for memories
        self._query_cache = LRUCache(maxsize // 2, ttl_seconds)

    def _generate_query_key(self, query: str, parameters: dict[str, Any] | None = None) -> str:
        """Generate cache key for query results."""
        key_data = query
        if parameters:
            # Sort parameters for consistent key generation
            sorted_params = sorted(parameters.items())
            key_data += str(sorted_params)

        return hashlib.md5(key_data.encode()).hexdigest()

    def _generate_memory_key(self, memory_id: str) -> str:
        """Generate cache key for memory objects."""
        return f"memory:{memory_id}"

    def _generate_recall_key(self, prompt: str, strategy: str, max_memories: int) -> str:
        """Generate cache key for recall results."""
        key_data = f"{prompt}:{strategy}:{max_memories}"
        return f"recall:{hashlib.md5(key_data.encode()).hexdigest()}"

    def get_memory(self, memory_id: str) -> Memory | None:
        """Get cached memory by ID."""
        key = self._generate_memory_key(memory_id)
        return self._memory_cache.get(key)

    def put_memory(self, memory: Memory) -> None:
        """Cache a memory object."""
        key = self._generate_memory_key(memory.id)
        self._memory_cache.put(key, memory)

    def get_query_result(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]] | None:
        """Get cached query result."""
        key = self._generate_query_key(query, parameters)
        return self._query_cache.get(key)

    def put_query_result(
        self,
        query: str,
        parameters: dict[str, Any] | None,
        result: list[dict[str, Any]],
    ) -> None:
        """Cache query result."""
        key = self._generate_query_key(query, parameters)
        self._query_cache.put(key, result)

    def get_recall_result(
        self, prompt: str, strategy: str, max_memories: int
    ) -> MemoryContext | None:
        """Get cached recall result."""
        key = self._generate_recall_key(prompt, strategy, max_memories)
        return self._cache.get(key)

    def get(self, key: str) -> Any | None:
        """Get item from general cache using raw key."""
        return self._cache.get(key)

    def put(self, key: str, value: Any) -> None:
        """Put item in general cache using raw key."""
        self._cache.put(key, value)

    def put_recall_result(
        self, prompt: str, strategy: str, max_memories: int, context: MemoryContext
    ) -> None:
        """Cache recall result."""
        key = self._generate_recall_key(prompt, strategy, max_memories)
        self._cache.put(key, context)

    def invalidate_memory(self, memory_id: str) -> None:
        """Invalidate cached memory and related queries."""
        # Remove memory from cache
        memory_key = self._generate_memory_key(memory_id)
        self._memory_cache.delete(memory_key)

        # Clear query cache since memory changes might affect query results
        # In a more sophisticated implementation, we could track which queries
        # are affected by which memories
        self._query_cache.clear()
        self._cache.clear()

    def clear_all(self) -> None:
        """Clear all caches."""
        self._cache.clear()
        self._memory_cache.clear()
        self._query_cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "general_cache": self._cache.get_stats(),
            "memory_cache": self._memory_cache.get_stats(),
            "query_cache": self._query_cache.get_stats(),
            "total_size": (
                self._cache.size() + self._memory_cache.size() + self._query_cache.size()
            ),
        }


class BloomFilter:
    """
    Simple Bloom filter for fast negative lookups.

    Used to quickly determine if an entity or content hash
    definitely doesn't exist in the database.
    """

    def __init__(self, capacity: int = 10000, error_rate: float = 0.01) -> None:
        """
        Initialize Bloom filter.

        Args:
            capacity: Expected number of items
            error_rate: Desired false positive rate
        """
        import math

        # Calculate optimal parameters
        self.capacity = capacity
        self.error_rate = error_rate

        # Calculate bit array size
        self.bit_size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))

        # Calculate number of hash functions
        self.hash_count = int(self.bit_size * math.log(2) / capacity)

        # Initialize bit array
        self.bit_array = [False] * self.bit_size
        self.item_count = 0

    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for item with given seed."""
        hash_value = hash(item + str(seed))
        return abs(hash_value) % self.bit_size

    def add(self, item: str) -> None:
        """Add item to Bloom filter."""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            self.bit_array[index] = True

        self.item_count += 1

    def contains(self, item: str) -> bool:
        """
        Check if item might be in the set.

        Returns:
            True if item might be in set (could be false positive)
            False if item is definitely not in set
        """
        for i in range(self.hash_count):
            index = self._hash(item, i)
            if not self.bit_array[index]:
                return False
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get Bloom filter statistics."""
        # Calculate current false positive rate
        bits_set = sum(self.bit_array)
        current_fpr = (bits_set / self.bit_size) ** self.hash_count

        return {
            "capacity": self.capacity,
            "item_count": self.item_count,
            "bit_size": self.bit_size,
            "hash_count": self.hash_count,
            "bits_set": bits_set,
            "fill_ratio": round(bits_set / self.bit_size, 3),
            "expected_fpr": self.error_rate,
            "current_fpr": round(current_fpr, 6),
        }
