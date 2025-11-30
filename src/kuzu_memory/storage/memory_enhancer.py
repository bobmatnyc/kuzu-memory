"""
Memory enhancement and processing for KuzuMemory.

Handles entity extraction, memory enhancement, and processing logic.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..core.config import KuzuMemoryConfig
from ..core.models import ExtractedMemory, Memory, MemoryType
from ..extraction.entities import EntityExtractor
from ..extraction.patterns import PatternExtractor
from ..extraction.relationships import RelationshipDetector
from ..utils.deduplication import DeduplicationEngine
from ..utils.exceptions import ExtractionError
from ..utils.validation import validate_text_input

# Import NLP classifier if available
try:
    from ..nlp.classifier import MemoryClassifier

    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False

logger = logging.getLogger(__name__)


class MemoryEnhancer:
    """Handles memory extraction, enhancement, and processing."""

    def __init__(self, config: KuzuMemoryConfig) -> None:
        """
        Initialize memory enhancer.

        Args:
            config: Configuration object
        """
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

        # Initialize NLP classifier if available
        self.nlp_classifier = None
        if NLP_AVAILABLE and config.extraction.enable_nlp_classification:
            try:
                self.nlp_classifier = MemoryClassifier(auto_download=False)
                logger.info("NLP classifier initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize NLP classifier: {e}")

        # Enhancement statistics
        self.enhancement_stats: dict[str, Any] = {
            "memories_processed": 0,
            "memories_enhanced": 0,
            "entities_extracted": 0,
            "relationships_found": 0,
            "extraction_errors": 0,
        }

    def extract_memories_from_content(self, content: str) -> list[ExtractedMemory]:
        """
        Extract discrete memories from content using pattern matching.

        Args:
            content: Text content to extract memories from

        Returns:
            List of extracted memories
        """
        try:
            # Validate input
            validate_text_input(content, min_length=10, max_length=100000)

            # Use pattern extractor to identify discrete memories
            extracted_memories = self.pattern_extractor.extract_memories(content)

            # extracted_memories is already a list of ExtractedMemory objects
            memories = []
            for extraction in extracted_memories:
                try:
                    # Update metadata to include original content context
                    updated_metadata = extraction.metadata.copy() if extraction.metadata else {}
                    updated_metadata.update(
                        {
                            "original_content": content,
                            "extraction_method": "pattern_matching",
                            "extracted_at": datetime.now(),
                        }
                    )

                    # Create a new ExtractedMemory with updated metadata
                    memory = ExtractedMemory(
                        content=extraction.content,
                        memory_type=extraction.memory_type,
                        confidence=extraction.confidence,
                        pattern_used=extraction.pattern_used,
                        entities=extraction.entities,
                        metadata=updated_metadata,
                    )

                    # Enhance with NLP classification if available
                    if self.nlp_classifier:
                        memory = self.enhance_extracted_memory_with_nlp(memory)

                    memories.append(memory)
                except Exception as e:
                    logger.warning(f"Error creating ExtractedMemory: {e}")
                    self.enhancement_stats["extraction_errors"] += 1

            self.enhancement_stats["memories_processed"] += 1
            self.enhancement_stats["memories_enhanced"] += len(memories)

            logger.debug(f"Extracted {len(memories)} memories from content")
            return memories

        except Exception as e:
            self.enhancement_stats["extraction_errors"] += 1
            logger.error(f"Error extracting memories from content: {e}")
            raise ExtractionError(f"Memory extraction failed: {e}")

    def extract_entities_from_content(self, content: str) -> list[dict[str, Any]]:
        """
        Extract entities from content.

        Args:
            content: Text content to extract entities from

        Returns:
            List of entity dictionaries
        """
        try:
            # Use entity extractor to find entities
            entities = self.entity_extractor.extract_entities(content)

            # Enhance entities with additional information
            enhanced_entities = []
            for entity in entities:
                enhanced_entity = {
                    "name": entity.text,
                    "type": entity.entity_type,
                    "confidence": entity.confidence,
                    "context": "",  # Entity doesn't have context
                    "positions": [entity.start_pos, entity.end_pos],
                    "metadata": {
                        "extraction_method": "pattern_matching",
                        "extracted_at": datetime.now(),
                        "normalized_text": entity.normalized_text,
                    },
                }
                enhanced_entities.append(enhanced_entity)

            self.enhancement_stats["entities_extracted"] += len(enhanced_entities)

            logger.debug(f"Extracted {len(enhanced_entities)} entities from content")
            return enhanced_entities

        except Exception as e:
            self.enhancement_stats["extraction_errors"] += 1
            logger.error(f"Error extracting entities from content: {e}")
            return []

    def enhance_memories_with_entities(
        self, memories: list[ExtractedMemory], entities: list[dict[str, Any]]
    ) -> None:
        """
        Enhance extracted memories with entity information.

        Args:
            memories: List of extracted memories to enhance
            entities: List of entities to associate with memories
        """
        try:
            if not entities:
                return

            # For each memory, find relevant entities
            for memory in memories:
                memory_entities = []

                # Find entities that appear in this memory's content
                for entity in entities:
                    if self._entity_appears_in_content(entity, memory.content):
                        # Calculate relevance score based on entity context and memory content
                        relevance_score = self._calculate_entity_relevance(entity, memory)

                        if relevance_score > 0.3:  # Threshold for entity relevance
                            memory_entity = {
                                "name": entity["name"],
                                "type": entity["type"],
                                "confidence": entity["confidence"],
                                "relevance": relevance_score,
                                "context": entity["context"],
                                "extraction_metadata": entity["metadata"],
                            }
                            memory_entities.append(memory_entity)

                # Attach entities to memory
                if memory_entities:
                    if not hasattr(memory, "entities"):
                        memory.entities = []
                    memory.entities.extend(memory_entities)

                    # Update memory metadata
                    if not memory.metadata:
                        memory.metadata = {}
                    memory.metadata["entity_count"] = len(memory_entities)
                    memory.metadata["entities_enhanced"] = True

            logger.debug(f"Enhanced {len(memories)} memories with entity information")

        except Exception as e:
            self.enhancement_stats["extraction_errors"] += 1
            logger.error(f"Error enhancing memories with entities: {e}")

    def process_extracted_memory(
        self,
        extracted_memory: ExtractedMemory,
        existing_memories: list[Memory],
        base_memory_data: dict[str, Any],
    ) -> str | None:
        """
        Process an extracted memory, handling deduplication and storage.

        Args:
            extracted_memory: The memory to process
            existing_memories: List of existing memories for deduplication
            base_memory_data: Base metadata for the memory

        Returns:
            Memory ID if stored, None if skipped
        """
        try:
            # Check for deduplication
            dedup_result = self.deduplication_engine.get_deduplication_action(
                extracted_memory.content, existing_memories
            )

            action = dedup_result.get("action", "store")

            if action == "skip":
                logger.debug(f"Skipping duplicate memory: {extracted_memory.content[:50]}...")
                return None
            elif action == "update":
                # Update existing memory
                existing_memory = dedup_result.get("existing_memory")
                if existing_memory:
                    return self._update_existing_memory(
                        existing_memory, extracted_memory, base_memory_data
                    )

            # Store new memory
            return self._create_new_memory(extracted_memory, base_memory_data)

        except Exception as e:
            self.enhancement_stats["extraction_errors"] += 1
            logger.error(f"Error processing extracted memory: {e}")
            return None

    def _entity_appears_in_content(self, entity: dict[str, Any], content: str) -> bool:
        """
        Check if an entity appears in the given content.

        Args:
            entity: Entity dictionary with name and metadata
            content: Content to check

        Returns:
            True if entity appears in content
        """
        try:
            entity_name = entity["name"].lower()
            content_lower = content.lower()

            # Direct name match
            if entity_name in content_lower:
                return True

            # Check for partial matches for multi-word entities
            if len(entity_name.split()) > 1:
                entity_words = entity_name.split()
                content_words = content_lower.split()

                # Check if all entity words appear in content
                matches = sum(1 for word in entity_words if word in content_words)
                return matches >= len(entity_words) * 0.8  # 80% word match threshold

            return False

        except Exception as e:
            logger.warning(f"Error checking entity appearance: {e}")
            return False

    def _calculate_entity_relevance(self, entity: dict[str, Any], memory: ExtractedMemory) -> float:
        """
        Calculate relevance score between an entity and a memory.

        Args:
            entity: Entity dictionary
            memory: ExtractedMemory object

        Returns:
            Relevance score between 0.0 and 1.0
        """
        try:
            relevance = 0.0

            # Base relevance from entity confidence
            relevance += entity.get("confidence", 0.5) * 0.4

            # Relevance from memory confidence
            relevance += memory.confidence * 0.3

            # Relevance from entity context overlap with memory content
            entity_context = entity.get("context", "").lower()
            memory_content = memory.content.lower()

            if entity_context and memory_content:
                context_words = set(entity_context.split())
                memory_words = set(memory_content.split())
                overlap = len(context_words.intersection(memory_words))
                max_words = max(len(context_words), len(memory_words), 1)
                context_relevance = overlap / max_words
                relevance += context_relevance * 0.3

            return min(1.0, relevance)

        except Exception as e:
            logger.warning(f"Error calculating entity relevance: {e}")
            return 0.5

    def classify_memory(self, content: str) -> dict[str, Any]:
        """
        Classify memory content using NLP if available.

        Args:
            content: Memory content to classify

        Returns:
            Classification result with type, confidence, entities, etc.
        """
        result = {
            "memory_type": MemoryType.EPISODIC,
            "confidence": 0.5,
            "entities": [],
            "keywords": [],
            "intent": None,
            "metadata": {},
        }

        if not self.nlp_classifier:
            return result

        try:
            # Use NLP classifier for automatic classification
            classification = self.nlp_classifier.classify(content)

            result.update(
                {
                    "memory_type": classification.memory_type,
                    "confidence": classification.confidence,
                    "entities": classification.entities,
                    "keywords": classification.keywords,
                    "intent": classification.intent,
                    "metadata": classification.metadata or {},
                }
            )

            # Calculate importance score
            importance = self.nlp_classifier.calculate_importance(
                content, classification.memory_type
            )
            result["importance"] = importance

            logger.debug(
                f"NLP classified memory as {classification.memory_type} "
                f"with confidence {classification.confidence:.2f}"
            )

        except Exception as e:
            logger.warning(f"NLP classification failed: {e}")

        return result

    def enhance_extracted_memory_with_nlp(
        self, extracted_memory: ExtractedMemory
    ) -> ExtractedMemory:
        """
        Enhance an extracted memory with NLP classification.

        Args:
            extracted_memory: Memory to enhance

        Returns:
            Enhanced memory with NLP metadata
        """
        if not self.nlp_classifier:
            return extracted_memory

        try:
            # Get NLP classification
            classification_result = self.classify_memory(extracted_memory.content)

            # Update memory type if NLP has higher confidence
            nlp_confidence = classification_result.get("confidence", 0)
            if nlp_confidence > extracted_memory.confidence:
                extracted_memory.memory_type = classification_result["memory_type"]
                extracted_memory.confidence = nlp_confidence

            # Add entities from NLP
            nlp_entities = classification_result.get("entities", [])
            if nlp_entities:
                # Convert NLP entities (strings) to proper entity dictionaries
                # Ensure extracted_memory.entities is a list of dicts
                if not hasattr(extracted_memory, "entities"):
                    extracted_memory.entities = []

                # Create a set of existing entity names for deduplication
                existing_entity_names = set()
                for entity in extracted_memory.entities:
                    if isinstance(entity, dict) and "name" in entity:
                        existing_entity_names.add(entity["name"].lower())
                    elif isinstance(entity, str):
                        # Handle legacy string entities
                        existing_entity_names.add(entity.lower())

                # Add NLP entities as properly formatted dictionaries
                for nlp_entity in nlp_entities:
                    if isinstance(nlp_entity, str):
                        # Convert string entity to dictionary format
                        entity_name = nlp_entity.strip()
                        if entity_name.lower() not in existing_entity_names:
                            entity_dict = {
                                "name": entity_name,
                                "type": "nlp_extracted",  # Default type for NLP entities
                                "confidence": nlp_confidence,
                                "extraction_method": "nlp",
                            }
                            extracted_memory.entities.append(entity_dict)
                            existing_entity_names.add(entity_name.lower())
                    elif isinstance(nlp_entity, dict):
                        # NLP entity is already a dict, ensure it has required fields
                        entity_name = nlp_entity.get("name", str(nlp_entity))
                        if entity_name.lower() not in existing_entity_names:
                            nlp_entity.setdefault("type", "nlp_extracted")
                            nlp_entity.setdefault("confidence", nlp_confidence)
                            nlp_entity.setdefault("extraction_method", "nlp")
                            extracted_memory.entities.append(nlp_entity)
                            existing_entity_names.add(entity_name.lower())

            # Update metadata with NLP results
            if not extracted_memory.metadata:
                extracted_memory.metadata = {}

            extracted_memory.metadata.update(
                {
                    "nlp_classification": {
                        "type": classification_result["memory_type"].value,
                        "confidence": nlp_confidence,
                        "keywords": classification_result.get("keywords", []),
                        "intent": classification_result.get("intent"),
                        "importance": classification_result.get("importance", 0.5),
                    }
                }
            )

            self.enhancement_stats["memories_enhanced"] += 1

        except Exception as e:
            logger.warning(f"NLP enhancement failed: {e}")

        return extracted_memory  # Default relevance

    def _update_existing_memory(
        self,
        existing_memory: Memory,
        extracted_memory: ExtractedMemory,
        base_memory_data: dict[str, Any],
    ) -> str:
        """
        Update an existing memory with new information.

        Args:
            existing_memory: Existing memory to update
            extracted_memory: New memory data
            base_memory_data: Base metadata

        Returns:
            Updated memory ID
        """
        try:
            # Update memory content if the new content is more comprehensive
            if len(extracted_memory.content) > len(existing_memory.content):
                existing_memory.content = extracted_memory.content

            # Merge metadata
            if existing_memory.metadata is None:
                existing_memory.metadata = {}

            existing_memory.metadata.update(
                {
                    "updated_at": datetime.now(),
                    "update_source": base_memory_data.get("source", "unknown"),
                    "update_reason": "deduplication_merge",
                    "original_confidence": existing_memory.metadata.get("confidence", 1.0),
                    "new_confidence": extracted_memory.confidence,
                }
            )

            # Update entities if new memory has more entities
            if hasattr(extracted_memory, "entities") and extracted_memory.entities:
                if not hasattr(existing_memory, "entities"):
                    existing_memory.entities = []

                # Merge entities (avoid duplicates) - handle both dict and string formats
                existing_entity_names = set()
                # First collect existing entity names
                for entity in existing_memory.entities:
                    if isinstance(entity, dict) and "name" in entity:
                        existing_entity_names.add(entity["name"].lower())
                    elif isinstance(entity, str):
                        existing_entity_names.add(entity.lower())

                # Add new entities that aren't duplicates
                for new_entity in extracted_memory.entities:
                    if isinstance(new_entity, dict):
                        entity_name = new_entity.get("name", "")
                        if entity_name and entity_name.lower() not in existing_entity_names:
                            existing_memory.entities.append(new_entity)
                            existing_entity_names.add(entity_name.lower())
                    elif isinstance(new_entity, str) and new_entity:
                        if new_entity.lower() not in existing_entity_names:
                            # Convert string to dict format
                            entity_dict = {
                                "name": new_entity,
                                "type": "extracted",
                                "confidence": 0.8,
                                "extraction_method": "pattern",
                            }
                            existing_memory.entities.append(entity_dict)
                            existing_entity_names.add(new_entity.lower())

            logger.debug(f"Updated existing memory: {existing_memory.id}")
            return existing_memory.id

        except Exception as e:
            logger.error(f"Error updating existing memory: {e}")
            raise

    def _create_new_memory(
        self, extracted_memory: ExtractedMemory, base_memory_data: dict[str, Any]
    ) -> str:
        """
        Create a new memory from extracted data.

        Args:
            extracted_memory: Extracted memory data
            base_memory_data: Base metadata

        Returns:
            New memory ID
        """
        try:
            # Create Memory object
            memory = Memory(
                content=extracted_memory.content,
                source=base_memory_data.get("source", "conversation"),
                memory_type=extracted_memory.memory_type,
                user_id=base_memory_data.get("user_id"),
                session_id=base_memory_data.get("session_id"),
                agent_id=base_memory_data.get("agent_id", "default"),
                metadata={
                    **base_memory_data.get("metadata", {}),
                    "extraction_confidence": extracted_memory.confidence,
                    "pattern_used": extracted_memory.pattern_used,
                    "extraction_metadata": extracted_memory.metadata,
                },
            )

            # Add entities if available
            if hasattr(extracted_memory, "entities") and extracted_memory.entities:
                memory.entities = extracted_memory.entities

            logger.debug(f"Created new memory: {memory.id}")
            return memory.id

        except Exception as e:
            logger.error(f"Error creating new memory: {e}")
            raise

    def detect_relationships(self, memories: list[ExtractedMemory]) -> list[dict[str, Any]]:
        """
        Detect relationships between extracted memories.

        Args:
            memories: List of extracted memories

        Returns:
            List of relationship dictionaries
        """
        try:
            if len(memories) < 2:
                return []

            relationships = self.relationship_detector.detect_memory_relationships(memories)
            self.enhancement_stats["relationships_found"] += len(relationships)

            logger.debug(f"Detected {len(relationships)} relationships between memories")
            return relationships

        except Exception as e:
            self.enhancement_stats["extraction_errors"] += 1
            logger.error(f"Error detecting relationships: {e}")
            return []

    def get_enhancement_statistics(self) -> dict[str, Any]:
        """Get memory enhancement statistics."""
        stats = self.enhancement_stats.copy()

        # Calculate derived metrics
        if stats["memories_processed"] > 0:
            stats["enhancement_rate"] = (
                stats["memories_enhanced"] / stats["memories_processed"]
            ) * 100
            stats["avg_entities_per_memory"] = (
                stats["entities_extracted"] / stats["memories_processed"]
            )
        else:
            stats["enhancement_rate"] = 0.0
            stats["avg_entities_per_memory"] = 0.0

        if stats["entities_extracted"] > 0:
            stats["avg_relationships_per_entity"] = (
                stats["relationships_found"] / stats["entities_extracted"]
            )
        else:
            stats["avg_relationships_per_entity"] = 0.0

        # Error rate
        total_operations = (
            stats["memories_processed"] + stats["entities_extracted"] + stats["relationships_found"]
        )
        if total_operations > 0:
            stats["error_rate"] = (stats["extraction_errors"] / total_operations) * 100
        else:
            stats["error_rate"] = 0.0

        return stats

    def reset_statistics(self) -> None:
        """Reset enhancement statistics."""
        self.enhancement_stats = {
            "memories_processed": 0,
            "memories_enhanced": 0,
            "entities_extracted": 0,
            "relationships_found": 0,
            "extraction_errors": 0,
        }
        logger.info("Enhancement statistics reset")
