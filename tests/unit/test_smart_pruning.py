"""
Unit tests for smart pruning strategy.

Tests multi-factor scoring, protection rules, archiving, and pruning execution.
"""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from kuzu_memory.core.smart_pruning import (
    ArchiveManager,
    RetentionScore,
    SmartPruneResult,
    SmartPruningStrategy,
)


@pytest.fixture
def mock_db_adapter():
    """Create mock database adapter."""
    adapter = Mock()
    adapter.db_path = Path("/tmp/test.db")
    adapter.execute_query = Mock(return_value=[])
    return adapter


@pytest.fixture
def smart_strategy(mock_db_adapter):
    """Create SmartPruningStrategy instance."""
    return SmartPruningStrategy(
        db_adapter=mock_db_adapter,
        threshold=0.3,
        archive_enabled=True,
    )


class TestScoreCalculation:
    """Test individual factor score calculations."""

    def test_age_score_recent(self, smart_strategy):
        """Test age score for recent memory (should be high)."""
        created_at = datetime.now(UTC) - timedelta(days=10)
        score = smart_strategy._calculate_age_score(created_at)

        # Recent memory should have high age score (close to 1.0)
        assert 0.9 < score <= 1.0

    def test_age_score_old(self, smart_strategy):
        """Test age score for old memory (should be low)."""
        created_at = datetime.now(UTC) - timedelta(days=365)
        score = smart_strategy._calculate_age_score(created_at)

        # Very old memory should have low age score (close to 0.0)
        assert 0.0 <= score < 0.1

    def test_age_score_mid(self, smart_strategy):
        """Test age score for middle-aged memory."""
        created_at = datetime.now(UTC) - timedelta(days=180)
        score = smart_strategy._calculate_age_score(created_at)

        # Mid-age should be around 0.5
        assert 0.4 < score < 0.6

    def test_size_score_small(self, smart_strategy):
        """Test size score for small content (should be high)."""
        score = smart_strategy._calculate_size_score(100)

        # Small content should have high size score
        assert score > 0.9

    def test_size_score_large(self, smart_strategy):
        """Test size score for large content (should be low)."""
        score = smart_strategy._calculate_size_score(15000)

        # Large content should have low size score
        assert score <= 0.0

    def test_size_score_mid(self, smart_strategy):
        """Test size score for medium content."""
        score = smart_strategy._calculate_size_score(5000)

        # Mid-size should be around 0.5
        assert 0.4 < score < 0.6

    def test_access_score_never_accessed(self, smart_strategy):
        """Test access score for never-accessed memory."""
        score = smart_strategy._calculate_access_score(0, None)

        # Never accessed should have score of 0
        assert score == 0.0

    def test_access_score_frequently_accessed(self, smart_strategy):
        """Test access score for frequently accessed memory."""
        accessed_at = datetime.now(UTC) - timedelta(days=5)
        score = smart_strategy._calculate_access_score(25, accessed_at)

        # Frequently accessed recently should have high score
        assert score > 0.8

    def test_access_score_old_access(self, smart_strategy):
        """Test access score for memory accessed long ago."""
        accessed_at = datetime.now(UTC) - timedelta(days=120)
        score = smart_strategy._calculate_access_score(5, accessed_at)

        # Old access should have lower score
        assert score < 0.5

    def test_access_score_combines_frequency_and_recency(self, smart_strategy):
        """Test that access score combines frequency and recency."""
        # High frequency, old access
        accessed_at_old = datetime.now(UTC) - timedelta(days=100)
        score_old = smart_strategy._calculate_access_score(20, accessed_at_old)

        # Low frequency, recent access
        accessed_at_recent = datetime.now(UTC) - timedelta(days=5)
        score_recent = smart_strategy._calculate_access_score(5, accessed_at_recent)

        # Both should have reasonable scores but different
        assert 0.3 < score_old < 0.8
        assert 0.3 < score_recent < 0.8
        assert score_old != score_recent


class TestProtectionRules:
    """Test memory protection rules."""

    def test_protection_high_importance(self, smart_strategy):
        """Test protection for high-importance memory."""
        memory = {
            "id": "test-1",
            "importance": 0.9,
            "access_count": 0,
            "created_at": datetime.now(UTC) - timedelta(days=100),
            "source_type": "manual",
            "memory_type": "FACT",
        }

        is_protected, reason = smart_strategy._is_protected(memory)

        assert is_protected is True
        assert "importance" in reason

    def test_protection_high_access_count(self, smart_strategy):
        """Test protection for frequently accessed memory."""
        memory = {
            "id": "test-2",
            "importance": 0.5,
            "access_count": 15,
            "created_at": datetime.now(UTC) - timedelta(days=100),
            "source_type": "manual",
            "memory_type": "FACT",
        }

        is_protected, reason = smart_strategy._is_protected(memory)

        assert is_protected is True
        assert "accessed" in reason

    def test_protection_recent_age(self, smart_strategy):
        """Test protection for recent memory."""
        memory = {
            "id": "test-3",
            "importance": 0.5,
            "access_count": 0,
            "created_at": datetime.now(UTC) - timedelta(days=20),
            "source_type": "manual",
            "memory_type": "FACT",
        }

        is_protected, reason = smart_strategy._is_protected(memory)

        assert is_protected is True
        assert "recent" in reason

    def test_protection_protected_source(self, smart_strategy):
        """Test protection for protected source type."""
        memory = {
            "id": "test-4",
            "importance": 0.5,
            "access_count": 0,
            "created_at": datetime.now(UTC) - timedelta(days=100),
            "source_type": "claude-code-hook",
            "memory_type": "FACT",
        }

        is_protected, reason = smart_strategy._is_protected(memory)

        assert is_protected is True
        assert "protected source" in reason

    def test_protection_preference_type(self, smart_strategy):
        """Test protection for PREFERENCE memory type."""
        memory = {
            "id": "test-5",
            "importance": 0.5,
            "access_count": 0,
            "created_at": datetime.now(UTC) - timedelta(days=100),
            "source_type": "manual",
            "memory_type": "PREFERENCE",
        }

        is_protected, reason = smart_strategy._is_protected(memory)

        assert is_protected is True
        assert "preference" in reason

    def test_not_protected(self, smart_strategy):
        """Test memory that should not be protected."""
        memory = {
            "id": "test-6",
            "importance": 0.3,
            "access_count": 2,
            "created_at": datetime.now(UTC) - timedelta(days=100),
            "source_type": "git_sync",
            "memory_type": "FACT",
        }

        is_protected, reason = smart_strategy._is_protected(memory)

        assert is_protected is False
        assert reason is None


class TestCandidateSelection:
    """Test candidate selection for pruning."""

    def test_get_prune_candidates_filters_by_threshold(self, smart_strategy, mock_db_adapter):
        """Test that candidates are filtered by score threshold."""
        # Mock query results with varying scores
        mock_db_adapter.execute_query.return_value = [
            {
                "id": "low-score",
                "content": "a" * 8000,  # Large content
                "created_at": (datetime.now(UTC) - timedelta(days=300)).isoformat(),
                "accessed_at": None,
                "access_count": 0,
                "importance": 0.2,
                "source_type": "git_sync",
                "memory_type": "FACT",
            },
            {
                "id": "high-score",
                "content": "Small",
                "created_at": datetime.now(UTC).isoformat(),
                "accessed_at": datetime.now(UTC).isoformat(),
                "access_count": 20,
                "importance": 0.9,
                "source_type": "manual",
                "memory_type": "FACT",
            },
        ]

        candidates = smart_strategy.get_prune_candidates()

        # Only low-score memory should be candidate
        assert len(candidates) == 1
        assert candidates[0].memory_id == "low-score"
        assert candidates[0].total_score < smart_strategy.threshold

    def test_get_prune_candidates_excludes_protected(self, smart_strategy, mock_db_adapter):
        """Test that protected memories are excluded from candidates."""
        mock_db_adapter.execute_query.return_value = [
            {
                "id": "protected-high-importance",
                "content": "a" * 8000,
                "created_at": (datetime.now(UTC) - timedelta(days=300)).isoformat(),
                "accessed_at": None,
                "access_count": 0,
                "importance": 0.9,  # High importance = protected
                "source_type": "git_sync",
                "memory_type": "FACT",
            },
        ]

        candidates = smart_strategy.get_prune_candidates()

        # Protected memory should not be candidate even with low age/access scores
        assert len(candidates) == 0


class TestPruningExecution:
    """Test pruning execution."""

    def test_execute_dry_run(self, smart_strategy, mock_db_adapter):
        """Test dry-run execution."""
        # Create memory with very low score (old + large + never accessed + low importance)
        mock_db_adapter.execute_query.return_value = [
            {
                "id": "candidate-1",
                "content": "a" * 9000,  # Large content = low size score
                "created_at": (
                    datetime.now(UTC) - timedelta(days=350)
                ).isoformat(),  # Very old = low age score
                "accessed_at": None,  # Never accessed = 0 access score
                "access_count": 0,
                "importance": 0.1,  # Low importance
                "source_type": "git_sync",
                "memory_type": "FACT",
            },
        ]

        result = smart_strategy.execute(dry_run=True, create_backup=False)

        assert result.success is True
        assert result.dry_run is True
        assert result.candidates > 0
        assert result.pruned == 0
        assert result.archived == 0
        assert result.score_breakdown is not None

    @patch("kuzu_memory.core.smart_pruning.SmartPruningStrategy._create_backup")
    @patch("kuzu_memory.core.smart_pruning.SmartPruningStrategy._archive_memories")
    @patch("kuzu_memory.core.smart_pruning.SmartPruningStrategy._delete_memories")
    def test_execute_with_backup_and_archive(
        self,
        mock_delete,
        mock_archive,
        mock_backup,
        smart_strategy,
        mock_db_adapter,
    ):
        """Test execution with backup and archive enabled."""
        # Create memory with very low score
        mock_db_adapter.execute_query.return_value = [
            {
                "id": "candidate-1",
                "content": "a" * 9000,  # Large content
                "created_at": (
                    datetime.now(UTC) - timedelta(days=350)
                ).isoformat(),  # Very old
                "accessed_at": None,  # Never accessed
                "access_count": 0,
                "importance": 0.1,  # Low importance
                "source_type": "git_sync",
                "memory_type": "FACT",
            },
        ]

        mock_backup.return_value = Path("/tmp/backup")
        mock_archive.return_value = 1
        mock_delete.return_value = 1

        result = smart_strategy.execute(dry_run=False, create_backup=True)

        assert result.success is True
        assert result.dry_run is False
        assert result.candidates == 1
        assert result.archived == 1
        assert result.pruned == 1
        assert result.backup_path == Path("/tmp/backup")

        mock_backup.assert_called_once()
        mock_archive.assert_called_once()
        mock_delete.assert_called_once()


class TestArchiveManager:
    """Test archive management functionality."""

    def test_restore_archive(self, mock_db_adapter):
        """Test restoring archived memory."""
        manager = ArchiveManager(mock_db_adapter)

        # Mock archive query
        mock_db_adapter.execute_query.side_effect = [
            # First call: get archive
            [
                {
                    "a": {
                        "id": "archive-123",
                        "original_id": "mem-123",
                        "content": "Test content",
                        "memory_type": "FACT",
                        "source_type": "manual",
                        "importance": 0.5,
                        "created_at": datetime.now(UTC).isoformat(),
                        "prune_score": 0.2,
                    }
                }
            ],
            # Second call: restore to Memory
            [],
            # Third call: delete archive
            [],
        ]

        success = manager.restore("archive-123")

        assert success is True
        assert mock_db_adapter.execute_query.call_count == 3

    def test_restore_nonexistent_archive(self, mock_db_adapter):
        """Test restoring non-existent archive."""
        manager = ArchiveManager(mock_db_adapter)

        mock_db_adapter.execute_query.return_value = []

        success = manager.restore("nonexistent")

        assert success is False

    def test_purge_expired_archives(self, mock_db_adapter):
        """Test purging expired archives."""
        manager = ArchiveManager(mock_db_adapter)

        # Mock queries: count query, then delete
        mock_db_adapter.execute_query.side_effect = [
            [{"count": 5}],
            [],
        ]

        count = manager.purge_expired()

        assert count == 5
        assert mock_db_adapter.execute_query.call_count == 2

    def test_list_archives(self, mock_db_adapter):
        """Test listing archives."""
        manager = ArchiveManager(mock_db_adapter)

        mock_db_adapter.execute_query.return_value = [
            {
                "a": {
                    "id": "archive-1",
                    "original_id": "mem-1",
                    "content": "Content 1" * 50,
                    "memory_type": "FACT",
                    "source_type": "manual",
                    "archived_at": datetime.now(UTC).isoformat(),
                    "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                    "prune_score": 0.25,
                }
            },
        ]

        archives = manager.list_archives(limit=10)

        assert len(archives) == 1
        assert archives[0]["id"] == "archive-1"
        assert len(archives[0]["content_preview"]) == 100  # Truncated to 100 chars


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_database(self, smart_strategy, mock_db_adapter):
        """Test with empty database."""
        mock_db_adapter.execute_query.return_value = []

        candidates = smart_strategy.get_prune_candidates()

        assert len(candidates) == 0

    def test_null_values_handling(self, smart_strategy, mock_db_adapter):
        """Test handling of null/missing values."""
        mock_db_adapter.execute_query.return_value = [
            {
                "id": "incomplete",
                "content": None,  # Null content
                "created_at": None,  # Null timestamp
                "accessed_at": None,
                "access_count": None,  # Null count
                "importance": None,  # Null importance
                "source_type": "manual",
                "memory_type": "FACT",
            },
        ]

        # Should not raise exception
        scores = smart_strategy.calculate_scores()

        assert len(scores) == 1
        # Should use defaults for null values

    def test_timezone_aware_datetimes(self, smart_strategy):
        """Test handling of timezone-aware datetimes."""
        # Timezone-aware datetime
        created_at = datetime.now(UTC) - timedelta(days=50)
        score = smart_strategy._calculate_age_score(created_at)

        assert 0.0 <= score <= 1.0

    def test_timezone_naive_datetimes(self, smart_strategy):
        """Test handling of timezone-naive datetimes."""
        # Timezone-naive datetime (should be handled)
        created_at = datetime.now() - timedelta(days=50)
        score = smart_strategy._calculate_age_score(created_at)

        assert 0.0 <= score <= 1.0
