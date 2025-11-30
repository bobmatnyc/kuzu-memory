"""
Memory storage and management for KuzuMemory.

Handles memory storage, retrieval, expiration, and cleanup with
robust error handling and performance optimization.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

from ..core.config import KuzuMemoryConfig
from ..core.models import ExtractedMemory, Memory
from ..extraction.entities import Entity, EntityExtractor
from ..extraction.patterns import PatternExtractor
from ..extraction.relationships import RelationshipDetector
from ..utils.deduplication import DeduplicationEngine
from ..utils.exceptions import (
    DatabaseError,
    ExtractionError,
    PerformanceError,
    PerformanceThresholdError,
)
from ..utils.validation import validate_text_input
from .cache import MemoryCache

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Handles memory storage, extraction, and lifecycle management.

    Provides the core implementation for generate_memories() with
    pattern extraction, entity detection, deduplication, and storage.
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

        # Initialize extraction components
        self.pattern_extractor = PatternExtractor(
            enable_compilation=config.extraction.enable_pattern_compilation,
            custom_patterns=config.extraction.custom_patterns,
        )

        self.entity_extractor = EntityExtractor(
            enable_compilation=config.extraction.enable_pattern_compilation
        )

        self.relationship_detector = RelationshipDetector()

        # Initialize deduplication engine
        self.deduplication_engine = DeduplicationEngine(
            near_threshold=0.95, semantic_threshold=0.85, enable_update_detection=True
        )

        # Initialize cache
        self.cache = (
            MemoryCache(
                maxsize=config.recall.cache_size,
                ttl_seconds=config.recall.cache_ttl_seconds,
            )
            if config.recall.enable_caching
            else None
        )

        # Statistics
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
            user_id: Associated user ID
            session_id: Associated session ID
            agent_id: Agent that generated the content

        Returns:
            List of created memory IDs

        Raises:
            ExtractionError: If extraction fails
            DatabaseError: If storage fails
            PerformanceError: If operation exceeds time limit
        """
        start_time = datetime.now()

        try:
            # Validate input
            if not content or not content.strip():
                return []

            clean_content = validate_text_input(content, "generate_memories_content")

            # Extract memories using patterns
            extracted_memories = self._extract_memories_from_content(clean_content)

            if not extracted_memories:
                logger.debug("No memories extracted from content")
                return []

            # Extract entities from content
            entities = self._extract_entities_from_content(clean_content)

            # Enhance extracted memories with entities
            self._enhance_memories_with_entities(extracted_memories, entities)

            # Get existing memories for deduplication
            existing_memories = self._get_existing_memories_for_deduplication(
                user_id, session_id, agent_id
            )

            # Process each extracted memory
            stored_memory_ids = []

            for extracted_memory in extracted_memories:
                try:
                    memory_id = self._process_extracted_memory(
                        extracted_memory,
                        existing_memories,
                        metadata or {},
                        source,
                        user_id,
                        session_id,
                        agent_id,
                    )

                    if memory_id:
                        stored_memory_ids.append(memory_id)

                except Exception as e:
                    logger.error(f"Error processing extracted memory: {e}")
                    self._storage_stats["storage_errors"] += 1
                    continue

            # Check performance requirement
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            max_time = self.config.performance.max_generation_time_ms

            if self.config.performance.enable_performance_monitoring and execution_time > max_time:
                raise PerformanceThresholdError(
                    "generate_memories", execution_time / 1000, max_time / 1000
                )

            # Update statistics
            self._storage_stats["memories_stored"] += len(stored_memory_ids)

            logger.info(f"Generated {len(stored_memory_ids)} memories in {execution_time:.1f}ms")

            return stored_memory_ids

        except Exception as e:
            self._storage_stats["extraction_errors"] += 1
            if isinstance(e, ExtractionError | DatabaseError | PerformanceError):
                raise
            raise ExtractionError(
                f"Failed to extract memories from content (length: {len(content)}): {e}",
                context={"content_length": len(content), "error": str(e)},
                cause=e,
            )

    def _extract_memories_from_content(self, content: str) -> list[ExtractedMemory]:
        """Extract memories using pattern matching."""
        try:
            return self.pattern_extractor.extract_memories(content)
        except Exception as e:
            logger.error(f"Pattern extraction failed: {e}")
            return []

    def _extract_entities_from_content(self, content: str) -> list[Entity]:
        """Extract entities from content."""
        try:
            if self.config.extraction.enable_entity_extraction:
                return self.entity_extractor.extract_entities(content)
            return []
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def _enhance_memories_with_entities(
        self, memories: list[ExtractedMemory], entities: list[str]
    ) -> None:
        """Enhance extracted memories with relevant entities."""
        if not entities:
            return

        # Create a map of entity positions
        entity_map = {}
        for entity in entities:
            for pos in range(entity.start_pos, entity.end_pos + 1):
                entity_map[pos] = entity

        # For each memory, find overlapping entities
        for memory in memories:
            memory_entities = set()

            # Check if any entities overlap with the memory's original position
            if "start_pos" in memory.metadata and "end_pos" in memory.metadata:
                start_pos = memory.metadata["start_pos"]
                end_pos = memory.metadata["end_pos"]

                for pos in range(start_pos, end_pos + 1):
                    if pos in entity_map:
                        memory_entities.add(entity_map[pos].text)

            # Also check for entities mentioned in the memory content
            memory_content_lower = memory.content.lower()
            for entity in entities:
                if entity.text.lower() in memory_content_lower:
                    memory_entities.add(entity.text)

            memory.entities = list(memory_entities)

    def _get_existing_memories_for_deduplication(
        self,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
        limit: int = 1000,
    ) -> list[Memory]:
        """Get existing memories for deduplication check."""
        try:
            # Build query to get recent memories for the same user/session
            query = """
                MATCH (m:Memory)
                WHERE m.valid_to IS NULL OR m.valid_to > $current_time
            """

            parameters = {"current_time": datetime.now().isoformat(), "limit": limit}

            # Add filters based on available identifiers
            if user_id:
                query += " AND m.user_id = $user_id"
                parameters["user_id"] = user_id

            if session_id:
                query += " AND m.session_id = $session_id"
                parameters["session_id"] = session_id

            if agent_id:
                query += " AND m.agent_id = $agent_id"
                parameters["agent_id"] = agent_id

            # Order by recency and limit
            query += """
                RETURN m
                ORDER BY m.created_at DESC
                LIMIT $limit
            """

            results = self.db_adapter.execute_query(query, parameters)

            # Convert results to Memory objects
            memories = []
            for result in results:
                try:
                    memory_data = result["m"]
                    memory = Memory.from_dict(memory_data)
                    memories.append(memory)
                except Exception as e:
                    logger.warning(f"Failed to parse memory from database: {e}")
                    continue

            return memories

        except Exception as e:
            logger.error(f"Failed to get existing memories: {e}")
            return []

    def _process_extracted_memory(
        self,
        extracted_memory: ExtractedMemory,
        existing_memories: list[Memory],
        metadata: dict[str, Any],
        source: str,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> str | None:
        """Process a single extracted memory through deduplication and storage."""

        # Check for duplicates
        dedup_action = self.deduplication_engine.get_deduplication_action(
            extracted_memory.content, existing_memories, extracted_memory.memory_type
        )

        action = dedup_action["action"]

        if action == "skip":
            logger.debug(f"Skipping duplicate memory: {dedup_action['reason']}")
            self._storage_stats["memories_skipped"] += 1
            return None

        elif action == "update":
            # Update existing memory
            existing_memory = dedup_action["existing_memory"]
            updated_memory_id = self._update_existing_memory(
                existing_memory, extracted_memory, metadata
            )
            if updated_memory_id:
                self._storage_stats["memories_updated"] += 1
            return updated_memory_id

        else:  # action == 'store'
            # Store new memory
            return self._store_new_memory(
                extracted_memory, metadata, source, user_id, session_id, agent_id
            )

    def _update_existing_memory(
        self,
        existing_memory: Memory,
        extracted_memory: ExtractedMemory,
        metadata: dict[str, Any],
    ) -> str | None:
        """Update an existing memory with new information."""
        try:
            # Create updated memory object
            updated_memory = Memory(
                id=existing_memory.id,  # Keep same ID
                content=extracted_memory.content,  # New content
                memory_type=extracted_memory.memory_type,
                importance=max(existing_memory.importance, extracted_memory.confidence),
                confidence=extracted_memory.confidence,
                source_type=existing_memory.source_type,
                agent_id=existing_memory.agent_id,
                user_id=existing_memory.user_id,
                session_id=existing_memory.session_id,
                entities=list(set(existing_memory.entities + extracted_memory.entities)),
                metadata={
                    **existing_memory.metadata,
                    **metadata,
                    "updated_at": datetime.now().isoformat(),
                    "update_reason": "content_correction",
                    "previous_content": existing_memory.content,
                },
                # Keep original timestamps but update access info
                created_at=existing_memory.created_at,
                valid_from=existing_memory.valid_from,
                valid_to=existing_memory.valid_to,
                accessed_at=datetime.now(),
                access_count=existing_memory.access_count + 1,
            )

            # Update in database
            self._store_memory_in_database(updated_memory, is_update=True)

            # Invalidate cache
            if self.cache:
                self.cache.invalidate_memory(existing_memory.id)

            logger.info(f"Updated memory {existing_memory.id}")
            return existing_memory.id

        except Exception as e:
            logger.error(f"Failed to update memory {existing_memory.id}: {e}")
            return None

    def _store_new_memory(
        self,
        extracted_memory: ExtractedMemory,
        metadata: dict[str, Any],
        source: str,
        user_id: str | None,
        session_id: str | None,
        agent_id: str,
    ) -> str | None:
        """Store a new memory in the database."""
        try:
            # Convert extracted memory to full Memory object
            memory = extracted_memory.to_memory(
                source_type=source,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
            )

            # Add additional metadata
            memory.metadata.update(metadata)

            # Store in database
            self._store_memory_in_database(memory, is_update=False)

            # Cache the memory
            if self.cache:
                self.cache.put_memory(memory)

            logger.debug(f"Stored new memory {memory.id}")
            return memory.id

        except Exception as e:
            logger.error(f"Failed to store new memory: {e}")
            return None

    def _store_memory_in_database(self, memory: Memory, is_update: bool = False) -> None:
        """Store or update memory in the database."""
        try:
            memory_data = memory.to_dict()
            # Remove entities from memory_data as they're stored separately
            memory_data.pop("entities", None)

            if is_update:
                # Update existing memory
                query = """
                    MATCH (m:Memory {id: $id})
                    SET m.content = $content,
                        m.content_hash = $content_hash,
                        m.accessed_at = $accessed_at,
                        m.access_count = $access_count,
                        m.memory_type = $memory_type,
                        m.importance = $importance,
                        m.confidence = $confidence,
                        m.metadata = $metadata
                    RETURN m.id
                """
            else:
                # Create new memory
                query = """
                    CREATE (m:Memory {
                        id: $id,
                        content: $content,
                        content_hash: $content_hash,
                        created_at: $created_at,
                        valid_from: $valid_from,
                        valid_to: $valid_to,
                        accessed_at: $accessed_at,
                        access_count: $access_count,
                        memory_type: $memory_type,
                        importance: $importance,
                        confidence: $confidence,
                        source_type: $source_type,
                        agent_id: $agent_id,
                        user_id: $user_id,
                        session_id: $session_id,
                        metadata: $metadata
                    })
                    RETURN m.id
                """

            # Execute the query
            result = self.db_adapter.execute_query(query, memory_data)

            if not result:
                raise DatabaseError("Failed to store memory - no result returned")

            # Store entities and relationships if this is a new memory
            if not is_update and memory.entities:
                self._store_memory_entities(memory)

        except Exception as e:
            raise DatabaseError(f"Failed to store memory in database: {e}")

    def _store_memory_entities(self, memory: Memory) -> None:
        """Store entities and their relationships to the memory."""
        if not memory.entities:
            return

        try:
            # Store entities and create relationships
            for entity_text in memory.entities:
                # Type narrow: entity can be str | dict[str, Any]
                if isinstance(entity_text, str):
                    normalized_name = entity_text.lower().strip()
                elif isinstance(entity_text, dict):
                    # Extract name from dict entity
                    entity_name = entity_text.get("name") or entity_text.get("text", "")
                    if not isinstance(entity_name, str):
                        continue  # Skip malformed entity
                    normalized_name = entity_name.lower().strip()
                else:
                    continue  # Skip unknown entity type

                # Check if entity exists
                check_query = "MATCH (e:Entity {normalized_name: $normalized_name}) RETURN e.id"
                existing = self.db_adapter.execute_query(
                    check_query, {"normalized_name": normalized_name}
                )

                current_time = datetime.now()
                entity_id = f"entity_{hashlib.md5(normalized_name.encode()).hexdigest()[:8]}"

                if existing:
                    # Update existing entity
                    update_query = """
                        MATCH (e:Entity {normalized_name: $normalized_name})
                        SET e.last_seen = $current_time,
                            e.mention_count = e.mention_count + 1
                        RETURN e.id
                    """
                    entity_params = {
                        "normalized_name": normalized_name,
                        "current_time": current_time,
                    }
                else:
                    # Create new entity
                    create_query = """
                        CREATE (e:Entity {
                            id: $entity_id,
                            name: $name,
                            entity_type: $entity_type,
                            normalized_name: $normalized_name,
                            first_seen: $current_time,
                            last_seen: $current_time,
                            mention_count: 1
                        })
                        RETURN e.id
                    """
                    entity_params = {
                        "entity_id": entity_id,
                        "normalized_name": normalized_name,
                        "name": entity_text,
                        "entity_type": "extracted",
                        "current_time": current_time,
                    }
                    update_query = create_query

                self.db_adapter.execute_query(update_query, entity_params)

                # Create MENTIONS relationship (check if it exists first)
                check_mentions_query = """
                    MATCH (m:Memory {id: $memory_id})-[r:MENTIONS]->(e:Entity {normalized_name: $normalized_name})
                    RETURN r
                """

                existing_mentions = self.db_adapter.execute_query(
                    check_mentions_query,
                    {"memory_id": memory.id, "normalized_name": normalized_name},
                )

                if not existing_mentions:
                    # Create new MENTIONS relationship
                    create_mentions_query = """
                        MATCH (m:Memory {id: $memory_id})
                        MATCH (e:Entity {normalized_name: $normalized_name})
                        CREATE (m)-[r:MENTIONS {confidence: $confidence}]->(e)
                        RETURN r
                    """

                    mentions_params = {
                        "memory_id": memory.id,
                        "normalized_name": normalized_name,
                        "confidence": 0.9,  # Default confidence for extracted entities
                    }

                    self.db_adapter.execute_query(create_mentions_query, mentions_params)

        except Exception as e:
            logger.error(f"Failed to store entities for memory {memory.id}: {e}")

    def cleanup_expired_memories(self) -> int:
        """
        Clean up expired memories based on retention policies.

        Returns:
            Number of memories cleaned up
        """
        if not self.config.retention.enable_auto_cleanup:
            return 0

        try:
            cleaned_count = self.db_adapter.cleanup_expired_memories()

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired memories")

                # Clear cache since memories were deleted
                if self.cache:
                    self.cache.clear_all()

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            return 0

    def get_recent_memories(self, limit: int = 10, **filters: Any) -> list[Memory]:
        """
        Get recent memories, optionally filtered.

        Args:
            limit: Maximum number of memories to return
            **filters: Optional filters (e.g., memory_type, user_id)

        Returns:
            List of recent memories
        """
        try:
            return self.db_adapter.get_recent_memories(limit=limit, **filters)
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []

    def get_memory_by_id(self, memory_id: str) -> Memory | None:
        """
        Get a specific memory by ID.

        Args:
            memory_id: Memory ID to retrieve

        Returns:
            Memory object or None if not found
        """
        try:
            return self.db_adapter.get_memory_by_id(memory_id)
        except Exception as e:
            logger.error(f"Failed to get memory by ID: {e}")
            return None

    def get_storage_statistics(self) -> dict[str, Any]:
        """Get memory storage statistics."""
        try:
            db_stats = self.db_adapter.get_statistics()

            return {
                "storage_stats": self._storage_stats.copy(),
                "database_stats": db_stats,
                "extraction_stats": {
                    "pattern_stats": self.pattern_extractor.get_pattern_statistics(),
                    "entity_stats": self.entity_extractor.get_entity_statistics(),
                    "relationship_stats": self.relationship_detector.get_relationship_statistics(),
                },
                "deduplication_stats": self.deduplication_engine.get_statistics(),
                "cache_stats": self.cache.get_stats() if self.cache else None,
            }

        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {"error": str(e)}
