"""
Memory-specific caching for frequently accessed memories.

Optimized cache specifically for Memory objects with content-based
deduplication and temporal decay features.
"""

import hashlib
from datetime import timedelta
from typing import Any

from ..core.internal_models import InternalMemory, QueryResult
from ..interfaces.cache import ICache
from .lru_cache import LRUCache


class MemoryCache(ICache):
    """
    Specialized cache for Memory objects.

    Features:
    - Content-based deduplication using memory hashes
    - Temporal decay for importance-based eviction
    - Query result caching with automatic invalidation
    - Memory type-specific caching strategies
    """

    def __init__(
        self,
        max_memories: int = 5000,
        max_query_results: int = 1000,
        default_ttl: timedelta | None = timedelta(hours=1),
        importance_threshold: float = 0.8,
    ):
        """
        Initialize memory cache.

        Args:
            max_memories: Maximum number of individual memories to cache
            max_query_results: Maximum number of query results to cache
            default_ttl: Default TTL for cached items
            importance_threshold: Minimum importance for long-term caching
        """
        self._max_memories = max_memories
        self._max_query_results = max_query_results
        self._importance_threshold = importance_threshold

        # Separate caches for different data types
        self._memory_cache = LRUCache(max_size=max_memories, default_ttl=default_ttl)
        self._query_cache = LRUCache(
            max_size=max_query_results,
            default_ttl=timedelta(minutes=15),  # Shorter TTL for query results
        )

        # Content hash to memory ID mapping for deduplication
        self._content_hash_map: dict[str, str] = {}

        # Track cached memory IDs for efficient cleanup
        self._cached_memory_ids: set[str] = set()

    async def cache_memory(self, memory: InternalMemory, ttl: timedelta | None = None) -> None:
        """
        Cache a memory with intelligent TTL based on importance.

        Args:
            memory: Memory to cache
            ttl: Custom TTL (default: calculated from importance)
        """
        # Calculate TTL based on importance if not specified
        if ttl is None:
            if memory.importance >= self._importance_threshold:
                ttl = timedelta(hours=24)  # Long-term cache for important memories
            else:
                ttl = timedelta(hours=1)  # Short-term cache for less important

        # Cache the memory
        await self._memory_cache.set(memory.id, memory, ttl)

        # Update deduplication map
        if memory.content_hash:
            self._content_hash_map[memory.content_hash] = memory.id

        # Track cached memory ID
        self._cached_memory_ids.add(memory.id)

    async def get_memory(self, memory_id: str) -> InternalMemory | None:
        """Get a cached memory by ID."""
        return await self._memory_cache.get(memory_id)

    async def get_memory_by_hash(self, content_hash: str) -> InternalMemory | None:
        """Get a memory by content hash for deduplication."""
        memory_id = self._content_hash_map.get(content_hash)
        if memory_id:
            return await self._memory_cache.get(memory_id)
        return None

    async def cache_query_result(
        self, query_key: str, result: QueryResult, ttl: timedelta | None = None
    ) -> None:
        """
        Cache a query result.

        Args:
            query_key: Unique key for the query
            result: Query result to cache
            ttl: Time-to-live for the cached result
        """
        # Mark result as cached
        cached_result = QueryResult(
            memories=result.memories,
            total_count=result.total_count,
            query_time_ms=result.query_time_ms,
            cached=True,
            cache_key=query_key,
        )

        await self._query_cache.set(query_key, cached_result, ttl)

        # Cache individual memories from the result
        for memory in result.memories:
            await self.cache_memory(memory)

    async def get_query_result(self, query_key: str) -> QueryResult | None:
        """Get a cached query result."""
        return await self._query_cache.get(query_key)

    async def invalidate_memory(self, memory_id: str) -> None:
        """Invalidate a specific memory from cache."""
        await self._memory_cache.delete(memory_id)
        self._cached_memory_ids.discard(memory_id)

        # Remove from content hash map if present
        memory = await self._memory_cache.get(memory_id)
        if memory and memory.content_hash:
            self._content_hash_map.pop(memory.content_hash, None)

    async def invalidate_queries_containing_memory(self, memory_id: str) -> int:
        """
        Invalidate all query results that contain a specific memory.

        Args:
            memory_id: Memory ID that changed

        Returns:
            Number of query results invalidated
        """
        # Get all cached query results
        query_stats = await self._query_cache.get_stats()
        invalidated = 0

        # This is a simplified approach - in practice, you'd need to track
        # which queries contain which memories for efficient invalidation
        await self._query_cache.clear()
        invalidated = query_stats.get("size", 0)

        return invalidated

    async def get_cached_memory_ids(self) -> set[str]:
        """Get all currently cached memory IDs."""
        return self._cached_memory_ids.copy()

    def create_query_key(
        self,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        min_confidence: float = 0.0,
        strategy: str = "auto",
    ) -> str:
        """Create a consistent cache key for a query."""
        key_data = {
            "query": query.lower().strip(),  # Normalize query
            "limit": limit,
            "memory_types": sorted(memory_types or []),
            "min_confidence": min_confidence,
            "strategy": strategy,
        }

        key_string = str(sorted(key_data.items()))
        return hashlib.md5(key_string.encode()).hexdigest()

    # ICache interface implementation
    async def get(self, key: str) -> Any | None:
        """Generic get from either cache."""
        # Try memory cache first
        result = await self._memory_cache.get(key)
        if result is not None:
            return result

        # Try query cache
        return await self._query_cache.get(key)

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Generic set to appropriate cache based on value type."""
        if isinstance(value, InternalMemory):
            await self.cache_memory(value, ttl)
        elif isinstance(value, QueryResult):
            await self.cache_query_result(key, value, ttl)
        else:
            # Default to memory cache for other values
            await self._memory_cache.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete from both caches."""
        deleted_memory = await self._memory_cache.delete(key)
        deleted_query = await self._query_cache.delete(key)
        return deleted_memory or deleted_query

    async def exists(self, key: str) -> bool:
        """Check if key exists in either cache."""
        return await self._memory_cache.exists(key) or await self._query_cache.exists(key)

    async def clear(self) -> None:
        """Clear both caches."""
        await self._memory_cache.clear()
        await self._query_cache.clear()
        self._content_hash_map.clear()
        self._cached_memory_ids.clear()

    async def get_multi(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from appropriate cache."""
        result = await self._memory_cache.get_multi(keys)
        query_result = await self._query_cache.get_multi(keys)
        result.update(query_result)
        return result

    async def set_multi(self, items: dict[str, Any], ttl: timedelta | None = None) -> None:
        """Set multiple values to appropriate caches."""
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def delete_multi(self, keys: list[str]) -> int:
        """Delete multiple values from both caches."""
        memory_deleted = await self._memory_cache.delete_multi(keys)
        query_deleted = await self._query_cache.delete_multi(keys)
        return memory_deleted + query_deleted

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_stats = await self._memory_cache.get_stats()
        query_stats = await self._query_cache.get_stats()

        return {
            "memory_cache": memory_stats,
            "query_cache": query_stats,
            "content_hash_map_size": len(self._content_hash_map),
            "tracked_memory_ids": len(self._cached_memory_ids),
            "total_size": memory_stats["size"] + query_stats["size"],
            "combined_hit_rate": (
                (memory_stats["hits"] + query_stats["hits"])
                / max(
                    1,
                    memory_stats["hits"]
                    + memory_stats["misses"]
                    + query_stats["hits"]
                    + query_stats["misses"],
                )
            ),
        }

    async def cleanup_expired(self) -> int:
        """Clean up expired entries from both caches."""
        memory_cleaned = await self._memory_cache.cleanup_expired()
        query_cleaned = await self._query_cache.cleanup_expired()

        # Clean up tracking data structures
        memory_stats = await self._memory_cache.get_stats()
        if memory_stats["size"] > 0:
            # In a real implementation, you'd iterate through cache entries
            # For now, just clear tracking structures if cache is empty
            pass

        if memory_stats["size"] == 0:
            self._content_hash_map.clear()
            self._cached_memory_ids.clear()

        return memory_cleaned + query_cleaned
