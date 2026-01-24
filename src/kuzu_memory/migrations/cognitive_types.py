"""
Migration utility for converting memory types to cognitive model.

This module handles the migration of existing memories from the domain-specific
type system to the cognitive memory type system.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..core.models import Memory, MemoryType
from ..storage.memory_store import MemoryStore

logger = logging.getLogger(__name__)


class CognitiveTypesMigration:
    """Handles migration of memory types to cognitive model."""

    # Legacy to cognitive type mapping
    MIGRATION_MAP = {
        "identity": MemoryType.SEMANTIC,  # Facts about identity
        "preference": MemoryType.PREFERENCE,  # Unchanged
        "decision": MemoryType.EPISODIC,  # Decisions are events
        "pattern": MemoryType.PROCEDURAL,  # Patterns are procedures
        "solution": MemoryType.PROCEDURAL,  # Solutions are instructions
        "status": MemoryType.WORKING,  # Status is current work
        "context": MemoryType.EPISODIC,  # Context is experiential
    }

    def __init__(self, memory_store: MemoryStore | None = None) -> None:
        """
        Initialize the migration utility.

        Args:
            memory_store: Memory store instance to migrate
        """
        self.memory_store = memory_store
        self.migration_stats: dict[str, Any] = {
            "total_memories": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "type_counts": {},
        }

    def migrate_memory_type(self, legacy_type: str) -> MemoryType:
        """
        Convert a legacy memory type to cognitive type.

        Args:
            legacy_type: Legacy memory type string

        Returns:
            Cognitive MemoryType enum
        """
        # Handle if it's already a MemoryType enum
        if isinstance(legacy_type, MemoryType):
            # Check if it's an old type that needs migration
            if legacy_type.value in self.MIGRATION_MAP:
                return self.MIGRATION_MAP[legacy_type.value]
            return legacy_type

        # Convert string to cognitive type
        legacy_type_lower = legacy_type.lower()

        # First check if it's already a cognitive type
        try:
            # Try to create MemoryType directly
            cognitive_types = [
                "episodic",
                "semantic",
                "procedural",
                "working",
                "sensory",
                "preference",
            ]
            if legacy_type_lower in cognitive_types:
                return MemoryType(legacy_type_lower)
        except ValueError:
            pass

        # Use migration map for legacy types
        if legacy_type_lower in self.MIGRATION_MAP:
            return self.MIGRATION_MAP[legacy_type_lower]

        # Default to episodic for unknown types
        logger.warning(f"Unknown memory type '{legacy_type}', defaulting to EPISODIC")
        return MemoryType.EPISODIC

    def migrate_memory(self, memory: Memory) -> Memory:
        """
        Migrate a single memory to use cognitive types.

        Args:
            memory: Memory to migrate

        Returns:
            Updated memory with cognitive type
        """
        try:
            original_type = memory.memory_type
            new_type = self.migrate_memory_type(original_type)

            # Only update if type changed
            if new_type != original_type:
                memory.memory_type = new_type

                # Update importance based on new type
                memory.importance = MemoryType.get_default_importance(new_type)

                # Update retention based on new type
                retention = MemoryType.get_default_retention(new_type)
                if retention and memory.valid_from:
                    memory.valid_to = memory.valid_from + retention
                else:
                    memory.valid_to = None

                # Add migration metadata
                if not memory.metadata:
                    memory.metadata = {}
                memory.metadata["migrated_from"] = (
                    original_type.value if hasattr(original_type, "value") else str(original_type)
                )
                memory.metadata["migrated_to"] = new_type.value
                memory.metadata["migration_date"] = datetime.now().isoformat()

                logger.debug(f"Migrated memory {memory.id} from {original_type} to {new_type}")
                return memory

            # No migration needed
            return memory

        except Exception as e:
            logger.error(f"Error migrating memory {memory.id}: {e}")
            self.migration_stats["errors"] += 1
            return memory

    def migrate_all_memories(self) -> dict[str, Any]:
        """
        Migrate all memories in the memory store.

        Returns:
            Migration statistics
        """
        if not self.memory_store:
            raise ValueError("No memory store configured for migration")

        try:
            # Get all memories
            all_memories = self.memory_store.list_memories()
            self.migration_stats["total_memories"] = len(all_memories)

            logger.info(f"Starting migration of {len(all_memories)} memories")

            for memory in all_memories:
                original_type = memory.memory_type
                migrated_memory = self.migrate_memory(memory)

                # Track statistics
                if migrated_memory.memory_type != original_type:
                    self.migration_stats["migrated"] += 1

                    # Track type counts
                    type_name = migrated_memory.memory_type.value
                    if type_name not in self.migration_stats["type_counts"]:
                        self.migration_stats["type_counts"][type_name] = 0
                    self.migration_stats["type_counts"][type_name] += 1

                    # Update in store
                    self.memory_store.update_memory(migrated_memory.id, migrated_memory)
                else:
                    self.migration_stats["skipped"] += 1

            logger.info(f"Migration completed: {self.migration_stats}")
            return self.migration_stats

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    def validate_migration(self) -> bool:
        """
        Validate that migration was successful.

        Returns:
            True if all memories have valid cognitive types
        """
        if not self.memory_store:
            return False

        try:
            all_memories = self.memory_store.list_memories()
            cognitive_types = {
                MemoryType.EPISODIC,
                MemoryType.SEMANTIC,
                MemoryType.PROCEDURAL,
                MemoryType.WORKING,
                MemoryType.SENSORY,
                MemoryType.PREFERENCE,
            }

            invalid_memories = []
            for memory in all_memories:
                if memory.memory_type not in cognitive_types:
                    invalid_memories.append(
                        {
                            "id": memory.id,
                            "type": memory.memory_type,
                            "content": memory.content[:50],
                        }
                    )

            if invalid_memories:
                logger.warning(f"Found {len(invalid_memories)} memories with invalid types")
                for mem in invalid_memories[:5]:  # Show first 5
                    logger.warning(f"  - Memory {mem['id']}: type={mem['type']}")
                return False

            logger.info("All memories have valid cognitive types")
            return True

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

    def rollback_migration(self) -> bool:
        """
        Rollback migration using metadata.

        Returns:
            True if rollback successful
        """
        if not self.memory_store:
            return False

        try:
            all_memories = self.memory_store.list_memories()
            rollback_count = 0

            for memory in all_memories:
                if memory.metadata and "migrated_from" in memory.metadata:
                    # Restore original type
                    memory.metadata["migrated_from"]

                    # Convert back to MemoryType enum
                    # Note: This would need the old enum definitions to work properly
                    logger.warning(
                        f"Cannot fully rollback memory {memory.id} - old types no longer defined"
                    )

                    # At minimum, remove migration metadata
                    del memory.metadata["migrated_from"]
                    del memory.metadata["migrated_to"]
                    del memory.metadata["migration_date"]

                    self.memory_store.update_memory(memory.id, memory)
                    rollback_count += 1

            logger.info(f"Rolled back {rollback_count} memories")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


def create_migration_script() -> str:
    """
    Generate a standalone migration script.

    Returns:
        Python script as string
    """
    script = '''#!/usr/bin/env python3
"""
Standalone script to migrate KuzuMemory to cognitive memory types.
Run this script to update all existing memories to the new type system.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.storage.memory_store import MemoryStore
from kuzu_memory.migrations.cognitive_types import CognitiveTypesMigration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the migration."""
    try:
        # Load configuration
        config = KuzuMemoryConfig.from_file()

        # Initialize memory store
        memory_store = MemoryStore(config)

        # Create migration instance
        migration = CognitiveTypesMigration(memory_store)

        # Run validation first
        logger.info("Validating current state...")
        if migration.validate_migration():
            logger.info("Memories already migrated, nothing to do")
            return 0

        # Run migration
        logger.info("Starting migration to cognitive memory types...")
        stats = migration.migrate_all_memories()

        # Validate results
        if migration.validate_migration():
            logger.info("Migration completed successfully!")
            logger.info(f"Statistics: {stats}")
            return 0
        else:
            logger.error("Migration validation failed")
            return 1

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''
    return script


# Export migration function for use in other modules
def migrate_memory_type(legacy_type: str) -> MemoryType:
    """
    Convenience function to migrate a single memory type.

    Args:
        legacy_type: Legacy memory type string

    Returns:
        Cognitive MemoryType enum
    """
    migration = CognitiveTypesMigration()
    return migration.migrate_memory_type(legacy_type)
