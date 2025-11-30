"""
Memory storage and management for KuzuMemory.

Refactored core store interface that coordinates query building and memory enhancement.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, cast

from ..core.config import KuzuMemoryConfig
from ..core.models import Memory
from ..utils.exceptions import DatabaseError, ValidationError
from .cache import MemoryCache
from .memory_enhancer import MemoryEnhancer
from .query_builder import QueryBuilder

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Handles memory storage, extraction, and lifecycle management.

    Coordinates query building and memory enhancement components to provide
    the core implementation for memory operations.
    """

    def __init__(self, db_adapter: Any, config: KuzuMemoryConfig) -> None:
        """
        Initialize memory store.

        Args:
            db_adapter: Database adapter for storage operations
            config: Configuration object
        """
        self.db_adapter = db_adapter
        self.config = config

        # Initialize components
        self.query_builder = QueryBuilder(db_adapter)
        self.memory_enhancer = MemoryEnhancer(config)

        # Initialize cache
        self.cache = (
            MemoryCache(
                maxsize=config.recall.cache_size,
                ttl_seconds=config.recall.cache_ttl_seconds,
            )
            if config.recall.enable_caching
            else None
        )

        # Storage statistics
        self._storage_stats = {
            "memories_stored": 0,
            "memories_skipped": 0,
            "memories_updated": 0,
            "extraction_errors": 0,
            "storage_errors": 0,
        }

    def generate_memories(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str = "conversation",
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
    ) -> list[str]:
        """
        Extract and store memories from content.

        Args:
            content: Text to extract memories from
            metadata: Additional metadata
            source: Source of the content
            user_id: Optional user ID
            session_id: Optional session ID
            agent_id: Agent identifier

        Returns:
            List of memory IDs that were created/updated
        """
        try:
            logger.debug(f"Generating memories from content: {len(content)} characters")

            # Extract memories using pattern matching
            extracted_memories = self.memory_enhancer.extract_memories_from_content(content)

            if not extracted_memories:
                logger.info("No memories extracted from content")
                return []

            # Extract entities from the full content
            entities = self.memory_enhancer.extract_entities_from_content(content)

            # Enhance memories with entity information
            if entities:
                self.memory_enhancer.enhance_memories_with_entities(extracted_memories, entities)

            # Get existing memories for deduplication
            existing_memories = self.query_builder.get_existing_memories_for_deduplication(
                content=content,
                source=source,
                user_id=user_id,
                session_id=session_id,
                days_back=30,
            )

            # Prepare base memory data
            base_memory_data: dict[str, Any] = {
                "source": source,
                "user_id": user_id,
                "session_id": session_id,
                "agent_id": agent_id,
                "metadata": metadata or {},
            }

            # Process and store each extracted memory
            stored_ids = []
            memory_id_to_extracted = {}  # Map to track which memory ID corresponds to which extracted memory

            for extracted_memory in extracted_memories:
                try:
                    memory_id = self.memory_enhancer.process_extracted_memory(
                        extracted_memory, existing_memories, base_memory_data
                    )

                    if memory_id:
                        # Store mapping and create Memory object for database storage
                        memory_id_to_extracted[memory_id] = extracted_memory

                        # Convert ExtractedMemory to Memory
                        memory_to_store = Memory(
                            id=memory_id,
                            content=extracted_memory.content,
                            source_type=base_memory_data["source"],
                            memory_type=extracted_memory.memory_type,
                            user_id=base_memory_data["user_id"],
                            session_id=base_memory_data["session_id"],
                            agent_id=base_memory_data["agent_id"],
                            confidence=extracted_memory.confidence,
                            metadata={
                                **cast(dict[str, Any], base_memory_data["metadata"]),
                                "pattern_used": extracted_memory.pattern_used,
                                "extraction_metadata": extracted_memory.metadata,
                            },
                        )

                        # Add entities if available
                        if hasattr(extracted_memory, "entities") and extracted_memory.entities:
                            memory_to_store.entities = extracted_memory.entities

                        # Store in database
                        self._store_memory_in_database(memory_to_store)
                        stored_ids.append(memory_id)
                        self._storage_stats["memories_stored"] += 1
                    else:
                        self._storage_stats["memories_skipped"] += 1

                except Exception as e:
                    self._storage_stats["storage_errors"] += 1
                    logger.error(f"Error processing and storing extracted memory: {e}")

            logger.info(f"Generated {len(stored_ids)} memories from content")
            return stored_ids

        except Exception as e:
            self._storage_stats["extraction_errors"] += 1
            logger.error(f"Error generating memories: {e}")
            raise DatabaseError(f"Failed to generate memories: {e}")

    def _store_memory_in_database(self, memory: Memory, is_update: bool = False) -> None:
        """
        Store or update a memory in the database using query builder.

        Args:
            memory: Memory object to store
            is_update: Whether this is an update operation
        """
        try:
            # Store the memory
            self.query_builder.store_memory_in_database(memory, is_update)

            # Store associated entities
            if hasattr(memory, "entities") and memory.entities:
                self.query_builder.store_memory_entities(memory)

            # Clear cache if caching is enabled
            if self.cache:
                # Clear entire cache since we don't have clear_related method
                self.cache.clear_all()

            logger.debug(f"Memory {'updated' if is_update else 'stored'}: {memory.id}")

        except Exception as e:
            logger.error(f"Error storing memory in database: {e}")
            raise DatabaseError(f"Failed to store memory: {e}")

    def cleanup_expired_memories(self) -> int:
        """
        Clean up expired memories using query builder.

        Returns:
            Number of memories removed
        """
        try:
            removed_count = self.query_builder.cleanup_expired_memories()

            # Clear cache after cleanup
            if self.cache:
                self.cache.clear_all()

            return removed_count

        except Exception as e:
            logger.error(f"Error cleaning up expired memories: {e}")
            raise DatabaseError(f"Failed to cleanup expired memories: {e}")

    def get_recent_memories(self, limit: int = 10, **filters: Any) -> list[Memory]:
        """
        Get recent memories using query builder.

        Args:
            limit: Maximum number of memories to return
            **filters: Additional filters

        Returns:
            List of recent memories
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = f"recent:{limit}:{hash(str(sorted(filters.items())))}"
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

            # Query database
            memories = self.query_builder.get_recent_memories(limit, **filters)

            # Cache result
            if self.cache and memories:
                cache_key = f"recent:{limit}:{hash(str(sorted(filters.items())))}"
                self.cache.put(cache_key, memories)

            return memories

        except Exception as e:
            logger.error(f"Error getting recent memories: {e}")
            raise DatabaseError(f"Failed to get recent memories: {e}")

    def get_memory_by_id(self, memory_id: str) -> Memory | None:
        """
        Get a specific memory by its ID using query builder.

        Args:
            memory_id: ID of the memory to retrieve

        Returns:
            Memory object or None if not found
        """
        try:
            # Check cache first
            if self.cache:
                cached_result = self.cache.get(f"memory:{memory_id}")
                if cached_result is not None:
                    return cached_result

            # Query database
            memory = self.query_builder.get_memory_by_id(memory_id)

            # Cache result
            if self.cache and memory:
                self.cache.put(f"memory:{memory_id}", memory)

            return memory

        except Exception as e:
            logger.error(f"Error getting memory by ID: {e}")
            raise DatabaseError(f"Failed to get memory by ID: {e}")

    def get_memory_count(self) -> int:
        """
        Get total count of non-expired memories.

        Returns:
            Total memory count
        """
        try:
            # Direct query to avoid the statistics method issues
            query = """
                MATCH (m:Memory)
                WHERE m.valid_to IS NULL OR m.valid_to > $now
                RETURN count(m) as count
            """
            params = {"now": datetime.now()}
            results = self.query_builder.db_adapter.execute_query(query, params)
            return results[0]["count"] if results else 0

        except Exception as e:
            logger.error(f"Error getting memory count: {e}")
            return 0

    def get_memory_type_stats(self) -> dict[str, int]:
        """
        Get statistics by memory type.

        Returns:
            Dictionary mapping memory types to counts
        """
        try:
            stats = self.query_builder.get_memory_statistics()
            return stats.get("memory_by_type", {})

        except Exception as e:
            logger.error(f"Error getting memory type statistics: {e}")
            return {}

    def get_source_stats(self) -> dict[str, int]:
        """
        Get statistics by source.

        Returns:
            Dictionary mapping sources to counts
        """
        try:
            stats = self.query_builder.get_memory_statistics()
            return stats.get("memory_by_source", {})

        except Exception as e:
            logger.error(f"Error getting source statistics: {e}")
            return {}

    def get_daily_activity_stats(self, days: int = 7) -> dict[str, int]:
        """
        Get daily activity statistics.

        Args:
            days: Number of days to include

        Returns:
            Dictionary mapping dates to memory counts
        """
        try:
            # This would require a more complex query - simplified implementation
            recent_count = self.query_builder.get_memory_statistics().get("recent_activity", 0)

            # Return simplified daily stats (could be enhanced with more detailed queries)
            today = datetime.now().date()
            return {
                str(today - timedelta(days=i)): (recent_count // days if recent_count else 0)
                for i in range(days)
            }

        except Exception as e:
            logger.error(f"Error getting daily activity statistics: {e}")
            return {}

    def get_average_memory_length(self) -> float:
        """
        Get average memory content length.

        Returns:
            Average length in characters
        """
        try:
            # This would require a more complex aggregation query
            # Simplified implementation using recent memories
            recent_memories = self.get_recent_memories(limit=100)
            if not recent_memories:
                return 0.0

            total_length = sum(len(memory.content) for memory in recent_memories)
            return total_length / len(recent_memories)

        except Exception as e:
            logger.error(f"Error getting average memory length: {e}")
            return 0.0

    def get_oldest_memory_date(self) -> datetime | None:
        """
        Get the date of the oldest memory.

        Returns:
            Datetime of oldest memory or None
        """
        try:
            # This would require a specific query - simplified implementation
            # Could be enhanced with a dedicated query in QueryBuilder
            return None  # Placeholder

        except Exception as e:
            logger.error(f"Error getting oldest memory date: {e}")
            return None

    def get_newest_memory_date(self) -> datetime | None:
        """
        Get the date of the newest memory.

        Returns:
            Datetime of newest memory or None
        """
        try:
            recent_memories = self.get_recent_memories(limit=1)
            if recent_memories:
                return recent_memories[0].created_at
            return None

        except Exception as e:
            logger.error(f"Error getting newest memory date: {e}")
            return None

    def get_expired_memories(self) -> list[Memory]:
        """
        Get list of expired memories.

        Returns:
            List of expired memories
        """
        try:
            # This would require a specific query in QueryBuilder
            # Simplified implementation
            return []  # Placeholder

        except Exception as e:
            logger.error(f"Error getting expired memories: {e}")
            return []

    def find_duplicate_memories(self) -> list[list[Memory]]:
        """
        Find groups of duplicate memories.

        Returns:
            List of memory groups that are duplicates
        """
        try:
            # This would require sophisticated duplicate detection
            # Could be enhanced with the deduplication engine
            return []  # Placeholder

        except Exception as e:
            logger.error(f"Error finding duplicate memories: {e}")
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by its ID.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deleted successfully
        """
        try:
            # This would require a delete query in QueryBuilder
            # Placeholder implementation
            logger.info(f"Memory deletion requested: {memory_id}")
            return False  # Not implemented yet

        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False

    def get_storage_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        try:
            # Combine statistics from all components
            stats = {
                "storage": self._storage_stats.copy(),
                "query_performance": self.query_builder.get_query_performance_stats(),
                "memory_enhancement": self.memory_enhancer.get_enhancement_statistics(),
                "database": self.query_builder.get_memory_statistics(),
            }

            # Add cache statistics if available
            if self.cache:
                stats["cache"] = self.cache.get_stats()

            return stats

        except Exception as e:
            logger.error(f"Error getting storage statistics: {e}")
            return {"storage": self._storage_stats.copy(), "error": str(e)}

    def clear_cache(self) -> None:
        """Clear the memory cache if enabled."""
        if self.cache:
            self.cache.clear_all()
            logger.info("Memory cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics if caching is enabled."""
        if self.cache:
            return self.cache.get_stats()
        return {"cache_enabled": False}

    def batch_store_memories(self, memories: list[Memory]) -> list[str]:
        """
        Store multiple memories in a single batch operation.

        This method provides efficient batch storage by delegating to the
        QueryBuilder's batch implementation, reducing database round-trips.

        Args:
            memories: List of Memory objects to store

        Returns:
            List of memory IDs that were successfully stored

        Raises:
            DatabaseError: If batch storage fails
            ValidationError: If memories list is invalid
        """
        try:
            if not memories:
                return []

            # Validate memories
            for memory in memories:
                if not isinstance(memory, Memory):
                    raise ValidationError(
                        "memories",
                        type(memory).__name__,
                        "All items must be Memory objects",
                    )

            # Delegate to query builder for batch storage
            stored_ids = self.query_builder.batch_store_memories(memories)

            # Update statistics
            self._storage_stats["memories_stored"] += len(stored_ids)

            # Clear cache if caching is enabled
            if self.cache:
                self.cache.clear_all()

            logger.info(f"Batch stored {len(stored_ids)} memories")
            return stored_ids

        except ValidationError:
            raise
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            logger.error(f"Error batch storing memories: {e}")
            raise DatabaseError(f"Failed to batch store memories: {e}")

    def batch_get_memories_by_ids(self, memory_ids: list[str]) -> list[Memory]:
        """
        Retrieve multiple memories by their IDs in a single batch operation.

        This method provides efficient batch retrieval by checking the cache
        first, then fetching any missing memories from the database in a
        single query.

        Args:
            memory_ids: List of memory IDs to retrieve

        Returns:
            List of Memory objects (may be fewer than requested if some IDs don't exist)

        Raises:
            DatabaseError: If batch retrieval fails
        """
        try:
            if not memory_ids:
                return []

            memories_to_fetch = []
            cached_memories = []

            # Check cache first if enabled
            if self.cache:
                for memory_id in memory_ids:
                    cached = self.cache.get(f"memory:{memory_id}")
                    if cached is not None:
                        cached_memories.append(cached)
                    else:
                        memories_to_fetch.append(memory_id)
            else:
                memories_to_fetch = memory_ids

            # Fetch missing memories from database
            if memories_to_fetch:
                db_memories = self.query_builder.batch_get_memories_by_ids(memories_to_fetch)

                # Cache the fetched memories
                if self.cache:
                    for memory in db_memories:
                        self.cache.put(f"memory:{memory.id}", memory)

                # Combine cached and fetched memories
                all_memories = cached_memories + db_memories
            else:
                all_memories = cached_memories

            logger.debug(
                f"Batch retrieved {len(all_memories)} memories (cached: {len(cached_memories)}, fetched: {len(memories_to_fetch)})"
            )
            return all_memories

        except Exception as e:
            logger.error(f"Error batch retrieving memories: {e}")
            raise DatabaseError(f"Failed to batch get memories: {e}")

    def get_memories_by_user(self, user_id: str, limit: int = 100) -> list[Memory]:
        """
        Get all memories created by a specific user.

        Args:
            user_id: User ID to filter by
            limit: Maximum number of memories to return

        Returns:
            List of memories created by the user
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = f"user_memories:{user_id}:{limit}"
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

            # Query database with user_id filter
            query = """
                MATCH (m:Memory)
                WHERE m.user_id = $user_id
                  AND (m.valid_to IS NULL OR m.valid_to > $now)
                RETURN m
                ORDER BY m.created_at DESC
                LIMIT $limit
            """
            params = {"user_id": user_id, "now": datetime.now(), "limit": limit}
            results = self.query_builder.db_adapter.execute_query(query, params)

            # Convert results to Memory objects
            memories = []
            for row in results:
                if "m" in row:
                    memory = Memory.from_dict(row["m"])
                    memories.append(memory)

            # Cache result
            if self.cache and memories:
                cache_key = f"user_memories:{user_id}:{limit}"
                self.cache.put(cache_key, memories)

            logger.debug(f"Found {len(memories)} memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Error getting memories by user: {e}")
            raise DatabaseError(f"Failed to get memories by user: {e}")

    def get_users(self) -> list[str]:
        """
        Get list of all user IDs that have created memories.

        Returns:
            List of unique user IDs (excluding null values)
        """
        try:
            # Check cache first
            if self.cache:
                cached_result = self.cache.get("all_users")
                if cached_result is not None:
                    return cached_result

            # Query database for unique user IDs
            query = """
                MATCH (m:Memory)
                WHERE m.user_id IS NOT NULL
                  AND (m.valid_to IS NULL OR m.valid_to > $now)
                RETURN DISTINCT m.user_id as user_id
                ORDER BY user_id
            """
            params = {"now": datetime.now()}
            results = self.query_builder.db_adapter.execute_query(query, params)

            # Extract user IDs
            users = [row["user_id"] for row in results if "user_id" in row]

            # Cache result
            if self.cache:
                self.cache.put("all_users", users)

            logger.debug(f"Found {len(users)} unique users")
            return users

        except Exception as e:
            logger.error(f"Error getting users: {e}")
            raise DatabaseError(f"Failed to get users: {e}")
