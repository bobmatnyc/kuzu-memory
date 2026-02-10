"""
Smart pruning with multi-factor retention scoring.

Provides intelligent memory pruning based on multiple factors:
- Age (older memories score lower)
- Size (larger memories score lower)
- Access patterns (frequently accessed score higher)
- Importance (user-set importance score)

Includes protection rules to prevent accidental deletion of critical memories
and archive/restore functionality for recovery.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetentionScore:
    """Multi-factor retention score for a memory."""

    memory_id: str
    age_score: float  # 0-1, lower = older
    size_score: float  # 0-1, lower = larger
    access_score: float  # 0-1, higher = more accessed
    importance_score: float  # 0-1, from memory.importance field
    total_score: float  # weighted combination
    is_protected: bool
    protection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "memory_id": self.memory_id,
            "age_score": self.age_score,
            "size_score": self.size_score,
            "access_score": self.access_score,
            "importance_score": self.importance_score,
            "total_score": self.total_score,
            "is_protected": self.is_protected,
            "protection_reason": self.protection_reason,
        }


@dataclass
class SmartPruneResult:
    """Result of smart pruning operation."""

    success: bool
    strategy: str
    candidates: int
    pruned: int
    archived: int
    protected: int
    execution_time_ms: float
    dry_run: bool
    backup_path: Path | None = None
    error: str | None = None
    score_breakdown: dict[str, Any] | None = None


class SmartPruningStrategy:
    """
    Multi-factor pruning strategy with protection rules.

    Scoring weights (must sum to 1.0):
    - age: 0.35 (older = lower score)
    - size: 0.20 (larger = lower score)
    - access: 0.30 (more frequent = higher score)
    - importance: 0.15 (user importance field)

    Protection rules (any true = protected):
    - importance >= 0.8
    - access_count >= 10
    - age < 30 days
    - source_type in PROTECTED_SOURCES
    - memory_type == "PREFERENCE"
    """

    # Scoring weights (must sum to 1.0)
    WEIGHT_AGE = 0.35
    WEIGHT_SIZE = 0.20
    WEIGHT_ACCESS = 0.30
    WEIGHT_IMPORTANCE = 0.15

    # Protection thresholds
    MIN_AGE_DAYS = 30  # Never prune memories younger than this
    MIN_ACCESS_COUNT = 10  # Never prune frequently accessed memories
    MIN_IMPORTANCE = 0.8  # Never prune high-importance memories
    PROTECTED_SOURCES = {"claude-code-hook", "cli", "project-initialization"}

    # Normalization constants
    MAX_AGE_DAYS = 365  # Age beyond this normalized to 0
    MAX_CONTENT_SIZE = 10000  # Size beyond this normalized to 0
    MAX_ACCESS_COUNT = 20  # Access count capped at this value
    RECENCY_WINDOW_DAYS = 90  # Recent access window for score calculation

    def __init__(
        self,
        db_adapter: Any,  # KuzuDBAdapter instance
        threshold: float = 0.3,
        archive_enabled: bool = True,
    ):
        """
        Initialize smart pruning strategy.

        Args:
            db_adapter: KuzuDBAdapter instance for database operations
            threshold: Total score threshold (memories below this are candidates)
            archive_enabled: Enable archiving before deletion
        """
        self.db_adapter = db_adapter
        self.threshold = threshold
        self.archive_enabled = archive_enabled

    def _calculate_age_score(self, created_at: datetime) -> float:
        """
        Calculate age score (older = lower score).

        Args:
            created_at: Memory creation timestamp

        Returns:
            Score from 0-1 (0 = very old, 1 = very recent)
        """
        now = datetime.now(UTC)
        # Handle timezone-naive datetimes
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        age_days = (now - created_at).days

        # Normalize: 0 days = 1.0, 365+ days = 0.0
        return max(0.0, 1.0 - (age_days / self.MAX_AGE_DAYS))

    def _calculate_size_score(self, content_length: int) -> float:
        """
        Calculate size score (larger = lower score).

        Args:
            content_length: Length of memory content in characters

        Returns:
            Score from 0-1 (0 = very large, 1 = very small)
        """
        # Normalize: 0 chars = 1.0, 10000+ chars = 0.0
        return max(0.0, 1.0 - (content_length / self.MAX_CONTENT_SIZE))

    def _calculate_access_score(
        self, access_count: int, accessed_at: datetime | None
    ) -> float:
        """
        Calculate access score (more access = higher score).

        Combines access frequency and recency.

        Args:
            access_count: Number of times memory was accessed
            accessed_at: Last access timestamp (None if never accessed)

        Returns:
            Score from 0-1 (0 = never accessed, 1 = frequently accessed recently)
        """
        # Frequency score: normalized by MAX_ACCESS_COUNT
        freq_score = min(1.0, access_count / self.MAX_ACCESS_COUNT)

        # Recency score: based on last access within 90-day window
        recency_score = 0.0
        if accessed_at:
            now = datetime.now(UTC)
            # Handle timezone-naive datetimes
            if accessed_at.tzinfo is None:
                accessed_at = accessed_at.replace(tzinfo=UTC)

            days_since_access = (now - accessed_at).days
            # Normalize: 0 days = 1.0, 90+ days = 0.0
            recency_score = max(
                0.0, 1.0 - (days_since_access / self.RECENCY_WINDOW_DAYS)
            )

        # Weighted combination: favor frequency slightly over recency
        return (freq_score * 0.6) + (recency_score * 0.4)

    def _is_protected(self, memory: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Check if memory is protected from pruning.

        Args:
            memory: Memory data dictionary

        Returns:
            Tuple of (is_protected: bool, reason: str | None)
        """
        # Check importance threshold
        importance = memory.get("importance")
        if importance is None:
            importance = 0.5
        if importance >= self.MIN_IMPORTANCE:
            return True, f"high importance ({importance:.2f})"

        # Check access count
        access_count = memory.get("access_count")
        if access_count is None:
            access_count = 0
        if access_count >= self.MIN_ACCESS_COUNT:
            return True, f"frequently accessed ({access_count} times)"

        # Check age
        created_at = memory.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)

            age_days = (datetime.now(UTC) - created_at).days
            if age_days < self.MIN_AGE_DAYS:
                return True, f"too recent ({age_days} days)"

        # Check protected source types
        source_type = memory.get("source_type", "")
        if source_type in self.PROTECTED_SOURCES:
            return True, f"protected source ({source_type})"

        # Check memory type (preferences should never be auto-pruned)
        memory_type = memory.get("memory_type", "")
        if memory_type == "PREFERENCE":
            return True, "user preference"

        return False, None

    def calculate_scores(self) -> list[RetentionScore]:
        """
        Calculate retention scores for all memories.

        Returns:
            List of RetentionScore objects sorted by total_score (lowest first)
        """
        # Query all memories with their metrics
        query = """
        MATCH (m:Memory)
        RETURN
            m.id AS id,
            m.content AS content,
            m.created_at AS created_at,
            m.accessed_at AS accessed_at,
            m.access_count AS access_count,
            m.importance AS importance,
            m.source_type AS source_type,
            m.memory_type AS memory_type
        """

        try:
            results = self.db_adapter.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to query memories for scoring: {e}")
            return []

        scores: list[RetentionScore] = []

        for row in results:
            memory_id = row.get("id", "")
            if not memory_id:
                continue

            # Parse timestamp fields
            created_at = row.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            elif created_at is None:
                created_at = datetime.now(UTC)

            accessed_at = row.get("accessed_at")
            if isinstance(accessed_at, str) and accessed_at:
                accessed_at = datetime.fromisoformat(accessed_at.replace("Z", "+00:00"))

            # Calculate individual factor scores
            content = row.get("content") or ""  # Handle None content
            age_score = self._calculate_age_score(created_at)
            size_score = self._calculate_size_score(len(content))
            access_count = row.get("access_count")
            if access_count is None:
                access_count = 0
            access_score = self._calculate_access_score(access_count, accessed_at)
            importance_score = row.get("importance")
            if importance_score is None:
                importance_score = 0.5

            # Calculate weighted total score
            total_score = (
                (age_score * self.WEIGHT_AGE)
                + (size_score * self.WEIGHT_SIZE)
                + (access_score * self.WEIGHT_ACCESS)
                + (importance_score * self.WEIGHT_IMPORTANCE)
            )

            # Check protection rules
            is_protected, protection_reason = self._is_protected(row)

            score = RetentionScore(
                memory_id=memory_id,
                age_score=age_score,
                size_score=size_score,
                access_score=access_score,
                importance_score=importance_score,
                total_score=total_score,
                is_protected=is_protected,
                protection_reason=protection_reason,
            )
            scores.append(score)

        # Sort by total score (lowest first = most likely to prune)
        scores.sort(key=lambda s: s.total_score)

        logger.info(f"Calculated retention scores for {len(scores)} memories")
        return scores

    def get_prune_candidates(self) -> list[RetentionScore]:
        """
        Get memories below threshold that aren't protected.

        Returns:
            List of RetentionScore objects eligible for pruning
        """
        scores = self.calculate_scores()

        candidates = [
            s for s in scores if s.total_score < self.threshold and not s.is_protected
        ]

        logger.info(
            f"Found {len(candidates)} prune candidates "
            f"(threshold={self.threshold}, total={len(scores)})"
        )
        return candidates

    def execute(
        self,
        dry_run: bool = True,
        create_backup: bool = True,
    ) -> SmartPruneResult:
        """
        Execute smart pruning operation.

        Args:
            dry_run: If True, only analyze without deleting
            create_backup: If True, create database backup before pruning

        Returns:
            SmartPruneResult with execution details
        """
        start_time = time.time()

        try:
            # Calculate scores and get candidates
            all_scores = self.calculate_scores()
            candidates = [
                s
                for s in all_scores
                if s.total_score < self.threshold and not s.is_protected
            ]
            protected_count = sum(1 for s in all_scores if s.is_protected)

            # Calculate score breakdown statistics
            score_breakdown = {
                "total_memories": len(all_scores),
                "avg_age_score": (
                    sum(s.age_score for s in all_scores) / len(all_scores)
                    if all_scores
                    else 0
                ),
                "avg_size_score": (
                    sum(s.size_score for s in all_scores) / len(all_scores)
                    if all_scores
                    else 0
                ),
                "avg_access_score": (
                    sum(s.access_score for s in all_scores) / len(all_scores)
                    if all_scores
                    else 0
                ),
                "avg_importance_score": (
                    sum(s.importance_score for s in all_scores) / len(all_scores)
                    if all_scores
                    else 0
                ),
                "below_threshold": len(candidates),
                "protected": protected_count,
            }

            if dry_run:
                execution_time_ms = (time.time() - start_time) * 1000
                return SmartPruneResult(
                    success=True,
                    strategy="smart",
                    candidates=len(candidates),
                    pruned=0,
                    archived=0,
                    protected=protected_count,
                    execution_time_ms=execution_time_ms,
                    dry_run=True,
                    score_breakdown=score_breakdown,
                )

            # Create backup if requested
            backup_path = None
            if create_backup:
                backup_path = self._create_backup()

            # Archive candidates if enabled
            archived_count = 0
            if self.archive_enabled and candidates:
                archived_count = self._archive_memories(candidates)

            # Delete candidates
            deleted_count = 0
            if candidates:
                deleted_count = self._delete_memories([c.memory_id for c in candidates])

            execution_time_ms = (time.time() - start_time) * 1000

            return SmartPruneResult(
                success=True,
                strategy="smart",
                candidates=len(candidates),
                pruned=deleted_count,
                archived=archived_count,
                protected=protected_count,
                execution_time_ms=execution_time_ms,
                dry_run=False,
                backup_path=backup_path,
                score_breakdown=score_breakdown,
            )

        except Exception as e:
            logger.error(f"Smart pruning failed: {e}", exc_info=True)
            execution_time_ms = (time.time() - start_time) * 1000
            return SmartPruneResult(
                success=False,
                strategy="smart",
                candidates=0,
                pruned=0,
                archived=0,
                protected=0,
                execution_time_ms=execution_time_ms,
                dry_run=dry_run,
                error=str(e),
            )

    def _create_backup(self) -> Path:
        """Create database backup before pruning."""
        import shutil

        db_path = Path(self.db_adapter.db_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{db_path.name}_backup_smart_{timestamp}"
        backup_path = db_path.parent / backup_filename

        logger.info(f"Creating backup: {backup_path}")

        # Copy the database directory
        if db_path.is_dir():
            shutil.copytree(db_path, backup_path)
        else:
            shutil.copy2(db_path, backup_path)

        logger.info(f"Backup created: {backup_path}")
        return backup_path

    def _archive_memories(self, candidates: list[RetentionScore]) -> int:
        """
        Archive memories to ArchivedMemory table.

        Args:
            candidates: List of RetentionScore objects to archive

        Returns:
            Number of memories archived
        """
        if not candidates:
            return 0

        try:
            # Get full memory data for candidates
            memory_ids = [c.memory_id for c in candidates]

            # Query memories to archive
            query = """
            MATCH (m:Memory)
            WHERE m.id IN $ids
            RETURN m
            """

            results = self.db_adapter.execute_query(query, {"ids": memory_ids})

            # Build score lookup
            score_map = {c.memory_id: c for c in candidates}

            # Insert into ArchivedMemory table
            archived_count = 0
            for row in results:
                memory = row.get("m", {})
                memory_id = memory.get("id")
                if not memory_id:
                    continue

                score = score_map.get(memory_id)
                if not score:
                    continue

                # Create archive entry
                archive_query = """
                CREATE (a:ArchivedMemory {
                    id: $id,
                    original_id: $original_id,
                    content: $content,
                    memory_type: $memory_type,
                    source_type: $source_type,
                    importance: $importance,
                    created_at: $created_at,
                    archived_at: $archived_at,
                    prune_score: $prune_score,
                    prune_reason: $prune_reason,
                    expires_at: $expires_at
                })
                """

                archive_id = f"archive-{memory_id}-{int(time.time())}"
                archived_at = datetime.now(UTC)
                expires_at = archived_at + timedelta(days=30)  # 30-day recovery window

                archive_params = {
                    "id": archive_id,
                    "original_id": memory_id,
                    "content": memory.get("content", ""),
                    "memory_type": memory.get("memory_type", ""),
                    "source_type": memory.get("source_type", ""),
                    "importance": memory.get("importance", 0.5),
                    "created_at": memory.get("created_at"),
                    "archived_at": archived_at.isoformat(),
                    "prune_score": score.total_score,
                    "prune_reason": f"Smart prune (score={score.total_score:.3f})",
                    "expires_at": expires_at.isoformat(),
                }

                try:
                    self.db_adapter.execute_query(archive_query, archive_params)
                    archived_count += 1
                except Exception as e:
                    logger.error(f"Failed to archive memory {memory_id}: {e}")

            logger.info(f"Archived {archived_count} memories")
            return archived_count

        except Exception as e:
            logger.error(f"Failed to archive memories: {e}", exc_info=True)
            return 0

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

        try:
            # Delete in batches for performance
            batch_size = 100
            total_deleted = 0

            for i in range(0, len(memory_ids), batch_size):
                batch = memory_ids[i : i + batch_size]

                query = """
                MATCH (m:Memory)
                WHERE m.id IN $ids
                DELETE m
                """

                try:
                    self.db_adapter.execute_query(query, {"ids": batch})
                    total_deleted += len(batch)
                    logger.debug(f"Deleted batch of {len(batch)} memories")
                except Exception as e:
                    logger.error(f"Failed to delete batch: {e}")

            logger.info(f"Deleted {total_deleted} memories")
            return total_deleted

        except Exception as e:
            logger.error(f"Failed to delete memories: {e}", exc_info=True)
            return 0


class ArchiveManager:
    """Manages archived memories with recovery window."""

    RECOVERY_DAYS = 30

    def __init__(self, db_adapter: Any):
        """
        Initialize archive manager.

        Args:
            db_adapter: KuzuDBAdapter instance
        """
        self.db_adapter = db_adapter

    def restore(self, archive_id: str) -> bool:
        """
        Restore archived memory to active Memory table.

        Args:
            archive_id: ID of archived memory to restore

        Returns:
            True if restored successfully
        """
        try:
            # Get archived memory
            query = """
            MATCH (a:ArchivedMemory)
            WHERE a.id = $archive_id
            RETURN a
            """

            results = self.db_adapter.execute_query(query, {"archive_id": archive_id})
            if not results:
                logger.warning(f"Archive not found: {archive_id}")
                return False

            archive = results[0].get("a", {})

            # Restore to Memory table with new ID
            restore_query = """
            CREATE (m:Memory {
                id: $id,
                content: $content,
                memory_type: $memory_type,
                source_type: $source_type,
                importance: $importance,
                created_at: $created_at,
                accessed_at: $accessed_at,
                access_count: 0,
                confidence: 1.0,
                agent_id: 'archive-restore',
                metadata: $metadata
            })
            """

            new_id = f"restored-{archive.get('original_id', '')}-{int(time.time())}"
            metadata = json.dumps(
                {
                    "restored_from": archive_id,
                    "original_id": archive.get("original_id"),
                    "restored_at": datetime.now(UTC).isoformat(),
                    "prune_score": archive.get("prune_score"),
                }
            )

            restore_params = {
                "id": new_id,
                "content": archive.get("content", ""),
                "memory_type": archive.get("memory_type", ""),
                "source_type": archive.get("source_type", ""),
                "importance": archive.get("importance", 0.5),
                "created_at": archive.get("created_at"),
                "accessed_at": datetime.now(UTC).isoformat(),
                "metadata": metadata,
            }

            self.db_adapter.execute_query(restore_query, restore_params)

            # Delete archive entry
            delete_query = """
            MATCH (a:ArchivedMemory {id: $archive_id})
            DELETE a
            """
            self.db_adapter.execute_query(delete_query, {"archive_id": archive_id})

            logger.info(f"Restored memory from archive: {archive_id} -> {new_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore archive {archive_id}: {e}", exc_info=True)
            return False

    def purge_expired(self) -> int:
        """
        Permanently delete archives past recovery window.

        Returns:
            Number of archives purged
        """
        try:
            current_time = datetime.now(UTC).isoformat()

            # Query expired archives
            query = """
            MATCH (a:ArchivedMemory)
            WHERE a.expires_at < $current_time
            RETURN COUNT(a) AS count
            """

            result = self.db_adapter.execute_query(
                query, {"current_time": current_time}
            )
            count = result[0].get("count", 0) if result else 0

            if count > 0:
                # Delete expired archives
                delete_query = """
                MATCH (a:ArchivedMemory)
                WHERE a.expires_at < $current_time
                DELETE a
                """

                self.db_adapter.execute_query(
                    delete_query, {"current_time": current_time}
                )
                logger.info(f"Purged {count} expired archives")

            return count

        except Exception as e:
            logger.error(f"Failed to purge expired archives: {e}", exc_info=True)
            return 0

    def list_archives(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        List archived memories.

        Args:
            limit: Maximum number of archives to return

        Returns:
            List of archive dictionaries
        """
        try:
            query = """
            MATCH (a:ArchivedMemory)
            RETURN a
            ORDER BY a.archived_at DESC
            LIMIT $limit
            """

            results = self.db_adapter.execute_query(query, {"limit": limit})

            archives = []
            for row in results:
                archive = row.get("a", {})
                archives.append(
                    {
                        "id": archive.get("id"),
                        "original_id": archive.get("original_id"),
                        "content_preview": archive.get("content", "")[:100],
                        "memory_type": archive.get("memory_type"),
                        "source_type": archive.get("source_type"),
                        "archived_at": archive.get("archived_at"),
                        "expires_at": archive.get("expires_at"),
                        "prune_score": archive.get("prune_score"),
                    }
                )

            return archives

        except Exception as e:
            logger.error(f"Failed to list archives: {e}", exc_info=True)
            return []
