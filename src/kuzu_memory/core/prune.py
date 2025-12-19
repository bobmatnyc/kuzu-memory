"""
Memory pruning functionality for KuzuMemory.

Provides intelligent memory pruning strategies to optimize database size
while preserving important memories. Supports multiple pruning strategies
with safety checks and backup capabilities.
"""

import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .memory import KuzuMemory

logger = logging.getLogger(__name__)


@dataclass
class PruneStats:
    """Statistics about pruning operation."""

    total_memories: int
    memories_to_prune: int
    memories_to_keep: int
    protected_count: int
    by_age: dict[str, int]
    by_size: dict[str, int]
    by_source: dict[str, int]
    estimated_content_savings_bytes: int
    estimated_db_savings_bytes: int


@dataclass
class PruneResult:
    """Result of pruning operation."""

    success: bool
    memories_pruned: int
    backup_path: Path | None
    execution_time_ms: float
    error: str | None = None


class PruningStrategy:
    """Base class for pruning strategies."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    def should_prune(self, memory: dict[str, Any]) -> tuple[bool, str]:
        """
        Determine if a memory should be pruned.

        Args:
            memory: Memory data dict with fields: id, source_type, created_at, content, etc.

        Returns:
            Tuple of (should_prune: bool, reason: str)
        """
        raise NotImplementedError


class SafePruningStrategy(PruningStrategy):
    """
    Safe pruning strategy - only prune old, minimal-impact git_sync commits.

    Rules:
    - Only git_sync source type
    - Older than 90 days
    - Either < 2 changed files OR < 200 bytes content
    - Expected: ~7% reduction, very low risk
    """

    def __init__(self) -> None:
        super().__init__(
            "safe",
            "Prune old, minimal-impact git commits (>90 days, <2 files or <200 bytes)",
        )
        self.min_age_days = 90
        self.max_changed_files = 2
        self.max_content_size = 200

    def should_prune(self, memory: dict[str, Any]) -> tuple[bool, str]:
        """Check if memory meets safe pruning criteria."""
        # Only prune git_sync memories
        if memory.get("source_type") != "git_sync":
            return False, "not git_sync"

        # Check age
        created_at = memory.get("created_at")
        if not created_at:
            return False, "no created_at"

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        age_days = (datetime.now() - created_at).days
        if age_days < self.min_age_days:
            return False, f"too recent ({age_days} days)"

        # Check changed files or content size
        metadata = memory.get("metadata", {})
        changed_files = metadata.get("changed_files", 0)
        # Handle case where changed_files is a list (of filenames) instead of a count
        if isinstance(changed_files, list):
            changed_files = len(changed_files)
        content_size = len(memory.get("content", ""))

        if changed_files < self.max_changed_files:
            return True, f"old + minimal files ({age_days}d, {changed_files} files)"

        if content_size < self.max_content_size:
            return True, f"old + small content ({age_days}d, {content_size}B)"

        return False, "does not meet criteria"


class IntelligentPruningStrategy(PruningStrategy):
    """
    Intelligent pruning strategy - value-based pruning considering commit importance.

    Rules:
    - Only git_sync source type
    - Older than 90 days
    - NOT important commit types (feat, fix, perf, BREAKING)
    - Changed files < 3
    - Expected: ~15-20% reduction, low risk
    """

    def __init__(self) -> None:
        super().__init__(
            "intelligent",
            "Value-based pruning excluding important commits (>90 days, not feat/fix/perf/BREAKING, <3 files)",
        )
        self.min_age_days = 90
        self.max_changed_files = 3
        self.important_prefixes = ["feat:", "fix:", "perf:", "breaking"]

    def should_prune(self, memory: dict[str, Any]) -> tuple[bool, str]:
        """Check if memory meets intelligent pruning criteria."""
        # Only prune git_sync memories
        if memory.get("source_type") != "git_sync":
            return False, "not git_sync"

        # Check age
        created_at = memory.get("created_at")
        if not created_at:
            return False, "no created_at"

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        age_days = (datetime.now() - created_at).days
        if age_days < self.min_age_days:
            return False, f"too recent ({age_days} days)"

        # Check if it's an important commit type
        content = memory.get("content", "").lower()
        for prefix in self.important_prefixes:
            if prefix in content:
                return False, f"important commit type ({prefix})"

        # Check changed files
        metadata = memory.get("metadata", {})
        changed_files = metadata.get("changed_files", 0)
        # Handle case where changed_files is a list (of filenames) instead of a count
        if isinstance(changed_files, list):
            changed_files = len(changed_files)
        if changed_files >= self.max_changed_files:
            return False, f"too many files ({changed_files} files)"

        return (
            True,
            f"old + unimportant + small scope ({age_days}d, {changed_files} files)",
        )


class AggressivePruningStrategy(PruningStrategy):
    """
    Aggressive pruning strategy - drastic pruning for critically large databases.

    Rules:
    - Works on ALL source types except protected ones
    - Any of:
      - Older than 180 days
      - Older than 60 days AND < 2 changed files
      - Content size < 300 bytes
    - Expected: ~30-50% reduction, moderate risk
    """

    def __init__(self) -> None:
        super().__init__(
            "aggressive",
            "Aggressive pruning for critically large databases (>180d OR >60d+<2files OR <300B)",
        )
        self.max_age_days = 180
        self.moderate_age_days = 60
        self.max_changed_files = 2
        self.max_content_size = 300

    def should_prune(self, memory: dict[str, Any]) -> tuple[bool, str]:
        """Check if memory meets aggressive pruning criteria."""
        # Check age
        created_at = memory.get("created_at")
        if not created_at:
            return False, "no created_at"

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        age_days = (datetime.now() - created_at).days

        # Very old memories
        if age_days > self.max_age_days:
            return True, f"very old ({age_days} days)"

        # Moderately old + minimal files
        metadata = memory.get("metadata", {})
        changed_files = metadata.get("changed_files", 0)
        # Handle case where changed_files is a list (of filenames) instead of a count
        if isinstance(changed_files, list):
            changed_files = len(changed_files)
        if age_days > self.moderate_age_days and changed_files < self.max_changed_files:
            return (
                True,
                f"moderately old + minimal files ({age_days}d, {changed_files} files)",
            )

        # Small content
        content_size = len(memory.get("content", ""))
        if content_size < self.max_content_size:
            return True, f"small content ({content_size}B)"

        return False, "does not meet criteria"


class PercentagePruningStrategy(PruningStrategy):
    """
    Percentage-based pruning strategy - prune oldest X% of memories.

    Rules:
    - Works on ALL source types except protected ones
    - Prunes the oldest X% of memories by creation date
    - No other criteria - just age-based
    - Expected: Configurable reduction (default 30%)
    """

    def __init__(self, percentage: float = 30.0) -> None:
        """
        Initialize percentage pruning strategy.

        Args:
            percentage: Percentage of oldest memories to prune (0-100)
        """
        if not 0 < percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")

        super().__init__(
            "percentage",
            f"Prune oldest {percentage}% of memories by creation date",
        )
        self.percentage = percentage
        self._cutoff_timestamp: datetime | None = None

    def set_cutoff_from_memories(self, memories: list[dict[str, Any]]) -> None:
        """
        Calculate cutoff timestamp from memory list.

        This must be called before should_prune() is used, with the full list
        of non-protected memories.

        Args:
            memories: List of all non-protected memories
        """
        if not memories:
            self._cutoff_timestamp = None
            return

        # Extract timestamps
        timestamps = []
        for memory in memories:
            created_at = memory.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                timestamps.append(created_at)

        if not timestamps:
            self._cutoff_timestamp = None
            return

        # Sort and find cutoff
        timestamps.sort()
        cutoff_index = int(len(timestamps) * (self.percentage / 100.0))
        self._cutoff_timestamp = timestamps[cutoff_index] if cutoff_index < len(timestamps) else None

        logger.debug(
            f"Percentage pruning: {len(timestamps)} memories, "
            f"cutoff at {self._cutoff_timestamp} ({self.percentage}%)"
        )

    def should_prune(self, memory: dict[str, Any]) -> tuple[bool, str]:
        """Check if memory is in oldest X%."""
        if self._cutoff_timestamp is None:
            return False, "cutoff not calculated"

        created_at = memory.get("created_at")
        if not created_at:
            return False, "no created_at"

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        if created_at <= self._cutoff_timestamp:
            age_days = (datetime.now() - created_at).days
            return True, f"in oldest {self.percentage}% ({age_days} days old)"

        return False, f"newer than cutoff"


# Protected memory sources that should never be pruned
PROTECTED_SOURCES = ["claude-code-hook", "cli", "project-initialization"]


class MemoryPruner:
    """
    Intelligent memory pruning with safety checks.

    Provides multiple pruning strategies with backup capabilities
    and detailed reporting.
    """

    def __init__(self, memory: "KuzuMemory") -> None:
        """
        Initialize memory pruner.

        Args:
            memory: KuzuMemory instance to prune
        """
        self.memory = memory
        self.strategies = {
            "safe": SafePruningStrategy(),
            "intelligent": IntelligentPruningStrategy(),
            "aggressive": AggressivePruningStrategy(),
            "percentage": PercentagePruningStrategy(percentage=30.0),
        }

    def _is_protected(self, memory: dict[str, Any]) -> bool:
        """Check if a memory is protected from pruning."""
        source_type = memory.get("source_type", "")
        return source_type in PROTECTED_SOURCES

    def analyze(self, strategy_name: str = "safe") -> PruneStats:
        """
        Analyze which memories would be pruned without actually pruning.

        Args:
            strategy_name: Name of pruning strategy to use

        Returns:
            PruneStats with analysis results
        """
        if strategy_name not in self.strategies:
            raise ValueError(
                f"Unknown strategy: {strategy_name}. Available: {list(self.strategies.keys())}"
            )

        strategy = self.strategies[strategy_name]
        logger.info(f"Analyzing memories with '{strategy_name}' strategy: {strategy.description}")

        # Get all memories with metadata
        memories = self._get_all_memories_with_metadata()
        total_count = len(memories)

        # Separate protected from non-protected memories
        non_protected_memories = [m for m in memories if not self._is_protected(m)]

        # For percentage strategy, calculate cutoff from non-protected memories
        if isinstance(strategy, PercentagePruningStrategy):
            strategy.set_cutoff_from_memories(non_protected_memories)

        # Categorize memories
        to_prune = []
        to_keep = []
        protected = []

        by_age: dict[str, int] = {"90-120d": 0, "120-180d": 0, "180+d": 0}
        by_size: dict[str, int] = {"<200B": 0, "200-500B": 0, "500B+": 0}
        by_source: dict[str, int] = {}

        for memory in memories:
            # Check if protected
            if self._is_protected(memory):
                protected.append(memory)
                to_keep.append(memory)
                continue

            # Check if should prune
            should_prune, _reason = strategy.should_prune(memory)

            if should_prune:
                to_prune.append(memory)

                # Categorize by age
                created_at = memory.get("created_at")
                if created_at:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)
                    age_days = (datetime.now() - created_at).days

                    if 90 <= age_days < 120:
                        by_age["90-120d"] += 1
                    elif 120 <= age_days < 180:
                        by_age["120-180d"] += 1
                    elif age_days >= 180:
                        by_age["180+d"] += 1

                # Categorize by size
                content_size = len(memory.get("content", ""))
                if content_size < 200:
                    by_size["<200B"] += 1
                elif content_size < 500:
                    by_size["200-500B"] += 1
                else:
                    by_size["500B+"] += 1

                # Categorize by source
                source = memory.get("source_type", "unknown")
                by_source[source] = by_source.get(source, 0) + 1
            else:
                to_keep.append(memory)

        # Calculate savings
        content_savings = sum(len(m.get("content", "")) for m in to_prune)
        # Estimate database savings (rough approximation: 10x content size for indexes, metadata, etc.)
        db_savings = content_savings * 10

        return PruneStats(
            total_memories=total_count,
            memories_to_prune=len(to_prune),
            memories_to_keep=len(to_keep),
            protected_count=len(protected),
            by_age=by_age,
            by_size=by_size,
            by_source=by_source,
            estimated_content_savings_bytes=content_savings,
            estimated_db_savings_bytes=db_savings,
        )

    def backup(self) -> Path:
        """
        Create backup of database before pruning.

        Returns:
            Path to backup file
        """

        db_path = Path(self.memory.db_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{db_path.name}_backup_{timestamp}"
        backup_path = db_path.parent / backup_filename

        logger.info(f"Creating backup: {backup_path}")

        # Copy the database directory
        if db_path.is_dir():
            shutil.copytree(db_path, backup_path)
        else:
            shutil.copy2(db_path, backup_path)

        logger.info(f"Backup created successfully: {backup_path}")
        return backup_path

    def prune(
        self,
        strategy_name: str = "safe",
        execute: bool = False,
        create_backup: bool = True,
    ) -> PruneResult:
        """
        Execute pruning operation.

        Args:
            strategy_name: Name of pruning strategy to use
            execute: If True, actually prune. If False, dry-run only.
            create_backup: If True, create backup before pruning

        Returns:
            PruneResult with operation results
        """
        import time

        start_time = time.time()

        try:
            # Validate strategy
            if strategy_name not in self.strategies:
                return PruneResult(
                    success=False,
                    memories_pruned=0,
                    backup_path=None,
                    execution_time_ms=0,
                    error=f"Unknown strategy: {strategy_name}",
                )

            strategy = self.strategies[strategy_name]
            logger.info(f"Starting prune with '{strategy_name}' strategy (execute={execute})")

            # Create backup if requested and executing
            backup_path = None
            if execute and create_backup:
                backup_path = self.backup()

            # Get memories to prune
            memories = self._get_all_memories_with_metadata()

            # Separate protected from non-protected memories
            non_protected_memories = [m for m in memories if not self._is_protected(m)]

            # For percentage strategy, calculate cutoff from non-protected memories
            if isinstance(strategy, PercentagePruningStrategy):
                strategy.set_cutoff_from_memories(non_protected_memories)

            to_prune = []

            for memory in memories:
                if self._is_protected(memory):
                    continue

                should_prune, reason = strategy.should_prune(memory)
                if should_prune:
                    to_prune.append(memory["id"])
                    logger.debug(f"Will prune memory {memory['id'][:8]}: {reason}")

            # Execute pruning if requested
            memories_pruned = 0
            if execute and to_prune:
                logger.info(f"Pruning {len(to_prune)} memories...")
                memories_pruned = self._delete_memories(to_prune)
                logger.info(f"Successfully pruned {memories_pruned} memories")
            else:
                logger.info(f"Dry-run: would prune {len(to_prune)} memories")

            execution_time_ms = (time.time() - start_time) * 1000

            return PruneResult(
                success=True,
                memories_pruned=memories_pruned if execute else len(to_prune),
                backup_path=backup_path,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f"Pruning failed: {e}", exc_info=True)
            execution_time_ms = (time.time() - start_time) * 1000
            return PruneResult(
                success=False,
                memories_pruned=0,
                backup_path=None,
                execution_time_ms=execution_time_ms,
                error=str(e),
            )

    def _get_all_memories_with_metadata(self) -> list[dict[str, Any]]:
        """
        Get all memories with metadata from database.

        Returns:
            List of memory dicts with all fields
        """
        import json

        # Use the memory store to query all memories
        query = """
        MATCH (m:Memory)
        RETURN
            m.id AS id,
            m.content AS content,
            m.source_type AS source_type,
            m.created_at AS created_at,
            m.metadata AS metadata
        """

        results = self.memory.memory_store.db_adapter.execute_query(query)
        memories = []

        for row in results:
            # Parse metadata if it's a string
            metadata = row.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata) if metadata else {}
                except (json.JSONDecodeError, TypeError):
                    metadata = {}

            memory = {
                "id": row.get("id", ""),
                "content": row.get("content", ""),
                "source_type": row.get("source_type", ""),
                "created_at": row.get("created_at"),
                "metadata": metadata,
            }
            memories.append(memory)

        logger.debug(f"Retrieved {len(memories)} memories from database")
        return memories

    def _delete_memories(self, memory_ids: list[str]) -> int:
        """
        Delete memories from database.

        Args:
            memory_ids: List of memory IDs to delete

        Returns:
            Number of memories deleted
        """
        if not memory_ids:
            return 0

        # Delete in batches for performance
        batch_size = 100
        total_deleted = 0

        for i in range(0, len(memory_ids), batch_size):
            batch = memory_ids[i : i + batch_size]

            # Build delete query
            query = """
            MATCH (m:Memory)
            WHERE m.id IN $ids
            DELETE m
            """

            try:
                self.memory.memory_store.db_adapter.execute_query(query, {"ids": batch})
                total_deleted += len(batch)
                logger.debug(f"Deleted batch of {len(batch)} memories ({total_deleted} total)")
            except Exception as e:
                logger.error(f"Failed to delete batch: {e}")
                # Continue with next batch

        # Clear cache after deletion
        if hasattr(self.memory.memory_store, "cache") and self.memory.memory_store.cache:
            self.memory.memory_store.cache.clear()

        return total_deleted
