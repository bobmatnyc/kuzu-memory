"""
Database query construction and optimization for KuzuMemory.

Handles complex query building, filtering, and database interaction logic.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Protocol, runtime_checkable

from ..core.constants import (
    DEFAULT_DEDUPLICATION_DAYS,
    DEFAULT_ENTITY_CONFIDENCE,
    DEFAULT_ENTITY_TYPE,
    DEFAULT_EXTRACTION_METHOD,
    DEFAULT_SEARCH_WORD_COUNT,
    MAX_SLOW_QUERIES_TO_TRACK,
    SLOW_QUERY_THRESHOLD_MS,
    VERY_SLOW_QUERY_THRESHOLD_MS,
)
from ..core.models import Memory, MemoryType
from ..utils.exceptions import DatabaseError
from ..utils.validation import sanitize_for_database

logger = logging.getLogger(__name__)


@runtime_checkable
class DatabaseAdapter(Protocol):
    """Protocol for database adapter interface."""

    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        timeout_ms: float | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a database query with parameters."""
        ...


class QueryBuilder:
    """Handles database query construction and execution."""

    def __init__(self, db_adapter: DatabaseAdapter) -> None:
        """Initialize query builder with database adapter."""
        self.db_adapter: DatabaseAdapter = db_adapter
        self.query_stats: dict[str, Any] = {
            "queries_executed": 0,
            "queries_failed": 0,
            "avg_query_time": 0.0,
            "slow_queries": [],
        }

    def get_existing_memories_for_deduplication(
        self,
        content: str,
        source: str,
        user_id: str | None = None,
        session_id: str | None = None,
        days_back: int = DEFAULT_DEDUPLICATION_DAYS,
    ) -> list[Memory]:
        """
        Get existing memories for deduplication analysis.

        Args:
            content: Content to check for duplicates
            source: Source of the content
            user_id: Optional user ID filter
            session_id: Optional session ID filter
            days_back: Number of days to look back for duplicates

        Returns:
            List of potentially duplicate memories
        """
        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()

            # Build query conditions
            conditions = []
            params = {}

            # Time-based filtering (most important for performance)
            cutoff_date = datetime.now() - timedelta(days=days_back)
            conditions.append("m.created_at >= $cutoff_date")
            params["cutoff_date"] = cutoff_date.isoformat()

            # Source filtering
            if source:
                conditions.append("m.source_type = $source_type")
                params["source_type"] = source

            # User filtering
            if user_id:
                conditions.append("m.user_id = $user_id")
                params["user_id"] = user_id

            # Session filtering
            if session_id:
                conditions.append("m.session_id = $session_id")
                params["session_id"] = session_id

            # Content similarity filtering (optimized)
            content_words = content.lower().split()
            if len(content_words) > 0:
                # Use a single parameter array instead of multiple parameters
                # This reduces query complexity and improves performance
                first_words = content_words[
                    :DEFAULT_SEARCH_WORD_COUNT
                ]  # Use first N words for initial filtering
                params["search_words"] = first_words  # type: ignore[assignment]  # Kuzu accepts list[str] in params dict

                # Use a more efficient query structure with list_contains
                # This avoids dynamic query building in loops
                conditions.append("ANY(word IN $search_words WHERE LOWER(m.content) CONTAINS word)")

            # Construct final query
            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
            MATCH (m:Memory)
            WHERE {where_clause}
            RETURN m
            ORDER BY m.created_at DESC
            LIMIT 100
            """

            # Execute query
            results = self.db_adapter.execute_query(query, params)

            # Convert results to Memory objects
            memories = []
            for result in results:
                try:
                    memory_data = result["m"]
                    memory = self._convert_db_result_to_memory(memory_data)
                    if memory:
                        memories.append(memory)
                except Exception as e:
                    logger.warning(f"Error converting memory result: {e}")

            # Update query performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, len(memories))

            return memories

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error querying existing memories: {e}")
            raise DatabaseError(f"Failed to query existing memories: {e}")

    def store_memory_in_database(self, memory: Memory, is_update: bool = False) -> None:
        """
        Store or update a memory in the database.

        Args:
            memory: Memory object to store
            is_update: Whether this is an update operation
        """
        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()

            # Prepare memory data for storage
            # For timestamps, Kuzu accepts ISO format strings
            memory_data = {
                "id": memory.id,
                "content": sanitize_for_database(memory.content),
                "source": memory.source_type,
                "memory_type": memory.memory_type.value,
                "created_at": (
                    memory.created_at.isoformat()
                    if isinstance(memory.created_at, datetime)
                    else memory.created_at
                ),
                "expires_at": (
                    memory.valid_to.isoformat()
                    if memory.valid_to and isinstance(memory.valid_to, datetime)
                    else memory.valid_to
                ),
                "user_id": memory.user_id,
                "session_id": memory.session_id,
                "agent_id": memory.agent_id,
                "metadata": (json.dumps(memory.metadata or {}, default=str)),
            }

            if is_update:
                # Update existing memory
                query = """
                MATCH (m:Memory {id: $id})
                SET m.content = $content,
                    m.source_type = $source,
                    m.memory_type = $memory_type,
                    m.valid_to = $expires_at,
                    m.user_id = $user_id,
                    m.session_id = $session_id,
                    m.agent_id = $agent_id,
                    m.metadata = $metadata,
                    m.updated_at = $updated_at
                RETURN m
                """
                memory_data["updated_at"] = datetime.now().isoformat()
            else:
                # Create new memory
                query = """
                CREATE (m:Memory {
                    id: $id,
                    content: $content,
                    source_type: $source,
                    memory_type: $memory_type,
                    created_at: TIMESTAMP($created_at),
                    valid_to: CASE WHEN $expires_at IS NOT NULL THEN TIMESTAMP($expires_at) ELSE NULL END,
                    user_id: $user_id,
                    session_id: $session_id,
                    agent_id: $agent_id,
                    metadata: $metadata
                })
                RETURN m
                """

            # Execute storage query
            result = self.db_adapter.execute_query(query, memory_data)

            if not result:
                raise DatabaseError(f"Failed to {'update' if is_update else 'create'} memory")

            # Update performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, 1)

            logger.debug(f"Memory {'updated' if is_update else 'stored'}: {memory.id}")

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error storing memory in database: {e}")
            raise DatabaseError(f"Failed to store memory: {e}")

    def store_memory_entities(self, memory: Memory) -> None:
        """
        Store entities extracted from a memory.

        Args:
            memory: Memory object with entities to store
        """
        if not hasattr(memory, "entities") or not memory.entities:
            return

        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()

            # Store each entity and create relationships
            for entity in memory.entities:
                # Handle both string and dictionary entity formats
                if isinstance(entity, str):
                    # Convert string entity to dictionary format
                    entity_name = entity.strip()
                    entity_type = DEFAULT_ENTITY_TYPE
                    entity_confidence = DEFAULT_ENTITY_CONFIDENCE
                    extraction_method = DEFAULT_EXTRACTION_METHOD
                elif isinstance(entity, dict):
                    entity_name = entity.get("name", "").strip()
                    entity_type = entity.get("type", DEFAULT_ENTITY_TYPE)
                    entity_confidence = entity.get("confidence", DEFAULT_ENTITY_CONFIDENCE)
                    extraction_method = entity.get("extraction_method", DEFAULT_EXTRACTION_METHOD)
                else:
                    logger.warning(f"Skipping invalid entity format: {type(entity)}")
                    continue

                if not entity_name:
                    logger.warning("Skipping entity with empty name")
                    continue

                # Generate entity ID
                entity_id = f"{entity_name}:{entity_type}"

                # Normalize entity name for case-insensitive matching
                normalized_name = entity_name.lower().strip()

                entity_query = """
                MERGE (e:Entity {id: $id})
                ON CREATE SET e.name = $name,
                             e.entity_type = $entity_type,
                             e.normalized_name = $normalized_name,
                             e.first_seen = TIMESTAMP($created_at),
                             e.last_seen = TIMESTAMP($created_at),
                             e.mention_count = 1
                ON MATCH SET e.mention_count = COALESCE(e.mention_count, 0) + 1,
                            e.last_seen = TIMESTAMP($created_at)
                RETURN e
                """

                entity_params = {
                    "id": entity_id,
                    "name": entity_name,
                    "entity_type": entity_type,
                    "normalized_name": normalized_name,
                    "created_at": datetime.now().isoformat(),
                }

                self.db_adapter.execute_query(entity_query, entity_params)

                # Create relationship between memory and entity
                relationship_query = """
                MATCH (m:Memory {id: $memory_id})
                MATCH (e:Entity {id: $entity_id})
                MERGE (m)-[r:MENTIONS]->(e)
                ON CREATE SET r.confidence = $confidence,
                             r.extraction_method = $extraction_method
                RETURN r
                """

                relationship_params = {
                    "memory_id": memory.id,
                    "entity_id": entity_id,
                    "confidence": entity_confidence,
                    "extraction_method": extraction_method,
                }

                self.db_adapter.execute_query(relationship_query, relationship_params)

            # Update performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, len(memory.entities))

            logger.debug(f"Stored {len(memory.entities)} entities for memory {memory.id}")

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error storing memory entities: {e}")
            raise DatabaseError(f"Failed to store memory entities: {e}")

    def get_recent_memories(self, limit: int = 10, **filters: Any) -> list[Memory]:
        """
        Get recent memories with optional filtering.

        Args:
            limit: Maximum number of memories to return
            **filters: Additional filters (memory_type, source, user_id, etc.)

        Returns:
            List of recent memories
        """
        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()

            # Build query conditions
            conditions = []
            params: dict[str, Any] = {"limit": limit}

            # Apply filters
            for filter_key, filter_value in filters.items():
                if filter_value is not None:
                    if filter_key == "memory_type" and isinstance(filter_value, MemoryType):
                        conditions.append(f"m.memory_type = ${filter_key}")
                        params[filter_key] = filter_value.value
                    else:
                        conditions.append(f"m.{filter_key} = ${filter_key}")
                        params[filter_key] = filter_value

            # Add expiration filter
            conditions.append("(m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now))")
            params["now"] = datetime.now().isoformat()  # type: ignore[assignment]  # Kuzu accepts ISO string for timestamps

            # Construct query
            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
            MATCH (m:Memory)
            WHERE {where_clause}
            RETURN m
            ORDER BY m.created_at DESC
            LIMIT $limit
            """

            # Execute query
            results = self.db_adapter.execute_query(query, params)

            # Convert results to Memory objects
            memories = []
            for result in results:
                try:
                    memory_data = result["m"]
                    memory = self._convert_db_result_to_memory(memory_data)
                    if memory:
                        memories.append(memory)
                except Exception as e:
                    logger.warning(f"Error converting memory result: {e}")

            # Update performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, len(memories))

            return memories

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error getting recent memories: {e}")
            raise DatabaseError(f"Failed to get recent memories: {e}")

    def get_memory_by_id(self, memory_id: str) -> Memory | None:
        """
        Get a specific memory by its ID.

        Args:
            memory_id: ID of the memory to retrieve

        Returns:
            Memory object or None if not found
        """
        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()

            query = """
            MATCH (m:Memory {id: $memory_id})
            WHERE m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now)
            RETURN m
            """

            params = {"memory_id": memory_id, "now": datetime.now().isoformat()}

            # Execute query
            results = self.db_adapter.execute_query(query, params)

            if not results:
                return None

            # Convert result to Memory object
            memory_data = results[0]["m"]
            memory = self._convert_db_result_to_memory(memory_data)

            # Update performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, 1 if memory else 0)

            return memory

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error getting memory by ID: {e}")
            raise DatabaseError(f"Failed to get memory by ID: {e}")

    def cleanup_expired_memories(self) -> int:
        """
        Remove expired memories from the database.

        Returns:
            Number of memories removed
        """
        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()

            # Query to find and delete expired memories
            query = """
            MATCH (m:Memory)
            WHERE m.valid_to IS NOT NULL AND m.valid_to <= TIMESTAMP($now)
            WITH m
            OPTIONAL MATCH (m)-[r]-()
            DELETE r, m
            RETURN count(m) as deleted_count
            """

            params = {"now": datetime.now().isoformat()}

            # Execute cleanup query
            results = self.db_adapter.execute_query(query, params)
            deleted_count = results[0]["deleted_count"] if results else 0

            # Update performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, deleted_count)

            logger.info(f"Cleaned up {deleted_count} expired memories")
            return deleted_count

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error cleaning up expired memories: {e}")
            raise DatabaseError(f"Failed to cleanup expired memories: {e}")

    def get_memory_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive memory statistics from the database.

        Returns:
            Dictionary with various statistics
        """
        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()

            # Multiple queries for different statistics
            stats_queries = {
                "total_memories": {
                    "query": """
                        MATCH (m:Memory)
                        WHERE m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now)
                        RETURN count(m) as count
                    """,
                    "params": ["now"],
                },
                "memory_by_type": {
                    "query": """
                        MATCH (m:Memory)
                        WHERE m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now)
                        RETURN m.memory_type as type, count(m) as count
                        ORDER BY count DESC
                    """,
                    "params": ["now"],
                },
                "memory_by_source": {
                    "query": """
                        MATCH (m:Memory)
                        WHERE m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now)
                        RETURN m.source_type as source, count(m) as count
                        ORDER BY count DESC
                        LIMIT 10
                    """,
                    "params": ["now"],
                },
                "recent_activity": {
                    "query": """
                        MATCH (m:Memory)
                        WHERE m.created_at >= TIMESTAMP($week_ago) AND (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now))
                        RETURN count(m) as recent_count
                    """,
                    "params": ["now", "week_ago"],
                },
            }

            all_params = {
                "now": datetime.now().isoformat(),
                "week_ago": (datetime.now() - timedelta(days=7)).isoformat(),
            }

            stats = {}

            # Execute each statistics query
            for stat_name, query_info in stats_queries.items():
                try:
                    query: str = str(query_info["query"])
                    # Only include parameters that this query needs
                    params_list = list(query_info["params"])
                    query_params = {k: v for k, v in all_params.items() if k in params_list}

                    results = self.db_adapter.execute_query(query, query_params)

                    if stat_name == "total_memories":
                        stats[stat_name] = results[0]["count"] if results else 0
                    elif stat_name == "recent_activity":
                        stats[stat_name] = results[0]["recent_count"] if results else 0
                    else:
                        stats[stat_name] = {
                            result[next(iter(result.keys()))]: result["count"] for result in results
                        }

                except Exception as e:
                    logger.warning(f"Error getting {stat_name} statistics: {e}")
                    stats[stat_name] = {}

            # Add query performance statistics
            stats["query_performance"] = self.query_stats.copy()

            # Update performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, len(stats))

            return stats

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error getting memory statistics: {e}")
            return {}

    def _convert_db_result_to_memory(self, memory_data: dict[str, Any]) -> Memory | None:
        """
        Convert database result to Memory object.

        Args:
            memory_data: Raw memory data from database

        Returns:
            Memory object or None if conversion fails
        """
        try:
            # Parse metadata
            metadata = {}
            if memory_data.get("metadata"):
                try:
                    metadata = json.loads(memory_data["metadata"])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse metadata for memory {memory_data.get('id')}")

            # Handle legacy memory types
            memory_type_str = memory_data["memory_type"]
            memory_type = self._convert_legacy_memory_type(memory_type_str)

            # Create Memory object
            memory = Memory(
                id=memory_data["id"],
                content=memory_data["content"],
                content_hash=memory_data.get("content_hash", ""),
                created_at=memory_data["created_at"],
                valid_from=memory_data.get("valid_from"),
                valid_to=memory_data.get("valid_to"),
                accessed_at=memory_data.get("accessed_at"),
                access_count=memory_data.get("access_count", 0),
                memory_type=memory_type,
                importance=memory_data.get("importance", 0.5),
                confidence=memory_data.get("confidence", 1.0),
                source_type=memory_data.get("source_type", "conversation"),
                agent_id=memory_data.get("agent_id", "default"),
                user_id=memory_data.get("user_id"),
                session_id=memory_data.get("session_id"),
                metadata=metadata,
            )

            return memory

        except Exception as e:
            logger.error(f"Error converting database result to Memory: {e}")
            return None

    def _update_query_stats(self, execution_time: float, result_count: int) -> None:
        """
        Update query performance statistics.

        Args:
            execution_time: Time taken to execute query in seconds
            result_count: Number of results returned
        """
        try:
            # Update average query time
            total_queries = self.query_stats["queries_executed"]
            if total_queries > 1:
                current_avg = self.query_stats["avg_query_time"]
                self.query_stats["avg_query_time"] = (
                    current_avg * (total_queries - 1) + execution_time
                ) / total_queries
            else:
                self.query_stats["avg_query_time"] = execution_time

            # Track slow queries
            if execution_time > SLOW_QUERY_THRESHOLD_MS / 1000.0:
                slow_query_info = {
                    "execution_time": execution_time,
                    "result_count": result_count,
                    "timestamp": datetime.now().isoformat(),
                }
                self.query_stats["slow_queries"].append(slow_query_info)

                # Keep only last N slow queries
                if len(self.query_stats["slow_queries"]) > MAX_SLOW_QUERIES_TO_TRACK:
                    self.query_stats["slow_queries"] = self.query_stats["slow_queries"][
                        -MAX_SLOW_QUERIES_TO_TRACK:
                    ]

            # Log performance warnings
            if execution_time > VERY_SLOW_QUERY_THRESHOLD_MS / 1000.0:
                logger.warning(
                    f"Very slow query detected: {execution_time:.2f}s for {result_count} results"
                )

        except Exception as e:
            logger.warning(f"Error updating query statistics: {e}")

    def _convert_legacy_memory_type(self, type_str: str) -> MemoryType:
        """
        Convert legacy memory type strings to new cognitive types.

        Args:
            type_str: Memory type string from database

        Returns:
            Corresponding MemoryType enum
        """
        # Legacy type migration mapping
        legacy_mapping = {
            "identity": MemoryType.SEMANTIC,  # Facts about identity
            "decision": MemoryType.EPISODIC,  # Decisions are events
            "pattern": MemoryType.PROCEDURAL,  # Patterns are procedures
            "solution": MemoryType.PROCEDURAL,  # Solutions are instructions
            "status": MemoryType.WORKING,  # Status is current work
            "context": MemoryType.EPISODIC,  # Context is experiential
        }

        # Standardized cognitive types
        cognitive_types = {
            "SEMANTIC": MemoryType.SEMANTIC,
            "EPISODIC": MemoryType.EPISODIC,
            "PROCEDURAL": MemoryType.PROCEDURAL,
            "WORKING": MemoryType.WORKING,
            "SENSORY": MemoryType.SENSORY,
            "PREFERENCE": MemoryType.PREFERENCE,
        }

        # First check if it's a legacy type
        if type_str.lower() in legacy_mapping:
            converted_type = legacy_mapping[type_str.lower()]
            logger.debug(f"Converted legacy memory type '{type_str}' to '{converted_type.value}'")
            return converted_type

        # Then check if it's a standard cognitive type
        if type_str.upper() in cognitive_types:
            return cognitive_types[type_str.upper()]

        # Try direct MemoryType conversion
        try:
            return MemoryType(type_str)
        except ValueError:
            logger.warning(f"Unknown memory type '{type_str}', defaulting to EPISODIC")
            return MemoryType.EPISODIC

    def get_query_performance_stats(self) -> dict[str, Any]:
        """Get query performance statistics."""
        return {
            "total_queries": self.query_stats["queries_executed"],
            "failed_queries": self.query_stats["queries_failed"],
            "success_rate": (
                (self.query_stats["queries_executed"] - self.query_stats["queries_failed"])
                / max(self.query_stats["queries_executed"], 1)
            )
            * 100,
            "average_query_time": self.query_stats["avg_query_time"],
            "slow_query_count": len(self.query_stats["slow_queries"]),
            "recent_slow_queries": self.query_stats["slow_queries"][-5:],  # Last 5 slow queries
        }

    def batch_store_memories(self, memories: list[Memory]) -> list[str]:
        """
        Store multiple memories in a single batch operation.

        Args:
            memories: List of Memory objects to store

        Returns:
            List of memory IDs that were successfully stored
        """
        if not memories:
            return []

        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()
            stored_ids = []

            # Build batch upsert query using MERGE for efficiency
            # This executes as a single database transaction and handles duplicates
            batch_query = """
            UNWIND $memories AS mem
            MERGE (m:Memory {id: mem.id})
            ON CREATE SET
                m.content = mem.content,
                m.source_type = mem.source,
                m.memory_type = mem.memory_type,
                m.created_at = TIMESTAMP(mem.created_at),
                m.valid_to = CASE WHEN mem.expires_at IS NOT NULL THEN TIMESTAMP(mem.expires_at) ELSE NULL END,
                m.user_id = mem.user_id,
                m.session_id = mem.session_id,
                m.agent_id = mem.agent_id,
                m.metadata = mem.metadata
            ON MATCH SET
                m.content = mem.content,
                m.source_type = mem.source,
                m.memory_type = mem.memory_type,
                m.valid_to = CASE WHEN mem.expires_at IS NOT NULL THEN TIMESTAMP(mem.expires_at) ELSE NULL END,
                m.user_id = mem.user_id,
                m.session_id = mem.session_id,
                m.agent_id = mem.agent_id,
                m.metadata = mem.metadata
            RETURN m.id as memory_id
            """

            # Prepare batch data
            batch_data = []
            for memory in memories:
                memory_data = {
                    "id": memory.id,
                    "content": sanitize_for_database(memory.content),
                    "source": memory.source_type,
                    "memory_type": memory.memory_type.value,
                    "created_at": (
                        memory.created_at.isoformat()
                        if isinstance(memory.created_at, datetime)
                        else memory.created_at
                    ),
                    "expires_at": (
                        memory.valid_to.isoformat()
                        if memory.valid_to and isinstance(memory.valid_to, datetime)
                        else memory.valid_to
                    ),
                    "user_id": memory.user_id,
                    "session_id": memory.session_id,
                    "agent_id": memory.agent_id,
                    "metadata": (json.dumps(memory.metadata or {}, default=str)),
                }
                batch_data.append(memory_data)

            # Execute batch insert
            results = self.db_adapter.execute_query(batch_query, {"memories": batch_data})

            # Collect stored IDs
            for result in results:
                stored_ids.append(result["memory_id"])

            # Update performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, len(stored_ids))

            logger.info(f"Batch stored {len(stored_ids)} memories in {execution_time:.2f}s")
            return stored_ids

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error batch storing memories: {e}")
            raise DatabaseError(f"Failed to batch store memories: {e}")

    def batch_get_memories_by_ids(self, memory_ids: list[str]) -> list[Memory]:
        """
        Get multiple memories by their IDs in a single query.

        Args:
            memory_ids: List of memory IDs to retrieve

        Returns:
            List of Memory objects
        """
        if not memory_ids:
            return []

        try:
            self.query_stats["queries_executed"] += 1
            start_time = datetime.now()

            # Use UNWIND for efficient batch retrieval
            query = """
            UNWIND $memory_ids AS mid
            MATCH (m:Memory {id: mid})
            WHERE m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now)
            RETURN m
            ORDER BY m.created_at DESC
            """

            params = {"memory_ids": memory_ids, "now": datetime.now().isoformat()}

            # Execute batch query
            results = self.db_adapter.execute_query(query, params)

            # Convert results to Memory objects
            memories = []
            for result in results:
                try:
                    memory_data = result["m"]
                    memory = self._convert_db_result_to_memory(memory_data)
                    if memory:
                        memories.append(memory)
                except Exception as e:
                    logger.warning(f"Error converting memory result: {e}")

            # Update performance stats
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_query_stats(execution_time, len(memories))

            logger.debug(f"Batch retrieved {len(memories)} memories in {execution_time:.2f}s")
            return memories

        except Exception as e:
            self.query_stats["queries_failed"] += 1
            logger.error(f"Error batch getting memories: {e}")
            raise DatabaseError(f"Failed to batch get memories: {e}")
