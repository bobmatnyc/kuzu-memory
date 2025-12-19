"""
Unit tests for git sync functionality.

Tests git commit filtering, branch pattern matching, and memory conversion.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from kuzu_memory.core.config import GitSyncConfig
from kuzu_memory.core.models import MemoryType
from kuzu_memory.integrations.git_sync import GitSyncError, GitSyncManager


class TestGitSyncConfig:
    """Test GitSyncConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GitSyncConfig()

        assert config.enabled is True
        assert config.last_sync_timestamp is None
        assert config.last_commit_sha is None
        assert "main" in config.branch_include_patterns
        assert "master" in config.branch_include_patterns  # Bug fix: master added
        assert "develop" in config.branch_include_patterns
        assert "tmp/*" in config.branch_exclude_patterns
        assert "feat:" in config.significant_prefixes
        assert "fix:" in config.significant_prefixes
        assert "wip" in config.skip_patterns
        assert config.min_message_length == 5  # Bug fix: reduced from 20 to 5
        assert config.include_merge_commits is True
        assert config.auto_sync_on_push is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = GitSyncConfig(
            enabled=False,
            last_sync_timestamp="2024-01-01T00:00:00",
            last_commit_sha="abc123",
            branch_include_patterns=["custom/*"],
            significant_prefixes=["custom:"],
            min_message_length=10,
        )

        assert config.enabled is False
        assert config.last_sync_timestamp == "2024-01-01T00:00:00"
        assert config.last_commit_sha == "abc123"
        assert config.branch_include_patterns == ["custom/*"]
        assert config.significant_prefixes == ["custom:"]
        assert config.min_message_length == 10


class TestGitSyncManager:
    """Test GitSyncManager class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GitSyncConfig(enabled=True)

    @pytest.fixture
    def mock_repo(self):
        """Create mock git repository."""
        repo = MagicMock()
        repo.active_branch.name = "main"
        return repo

    @pytest.fixture
    def manager_no_git(self, config, tmp_path):
        """Create manager without git repository."""
        with patch("kuzu_memory.integrations.git_sync.git", create=True) as mock_git:
            mock_git.Repo.side_effect = Exception("Not a git repo")
            manager = GitSyncManager(
                repo_path=tmp_path,
                config=config,
            )
            yield manager

    def test_init_without_git(self, config, tmp_path):
        """Test initialization without git repository."""
        with patch("kuzu_memory.integrations.git_sync.git", create=True) as mock_git:
            mock_git.Repo.side_effect = Exception("Not a git repo")

            manager = GitSyncManager(
                repo_path=tmp_path,
                config=config,
            )

            assert manager.is_available() is False

    def test_init_git_not_installed(self, config, tmp_path):
        """Test initialization when gitpython not installed."""
        # Mock the import to raise ImportError
        with patch.dict("sys.modules", {"git": None}):
            with patch(
                "builtins.__import__", side_effect=ImportError("No module named 'git'")
            ):
                manager = GitSyncManager(
                    repo_path=tmp_path,
                    config=config,
                )

                assert manager.is_available() is False

    def test_matches_pattern(self, config, tmp_path):
        """Test pattern matching."""
        manager = GitSyncManager(
            repo_path=tmp_path,
            config=config,
        )

        # Test exact match
        assert manager._matches_pattern("main", ["main"]) is True
        assert manager._matches_pattern("develop", ["main"]) is False

        # Test glob patterns
        assert manager._matches_pattern("feature/test", ["feature/*"]) is True
        assert manager._matches_pattern("bugfix/123", ["feature/*"]) is False
        assert manager._matches_pattern("tmp/test", ["tmp/*"]) is True

        # Test multiple patterns
        assert manager._matches_pattern("feature/test", ["main", "feature/*"]) is True
        assert manager._matches_pattern("other", ["main", "feature/*"]) is False

    def test_filter_branches(self, config, tmp_path):
        """Test branch filtering."""
        manager = GitSyncManager(
            repo_path=tmp_path,
            config=config,
        )

        # Create mock branches
        main_branch = Mock()
        main_branch.name = "main"

        feature_branch = Mock()
        feature_branch.name = "feature/test"

        tmp_branch = Mock()
        tmp_branch.name = "tmp/test"

        test_branch = Mock()
        test_branch.name = "test/something"

        branches = [main_branch, feature_branch, tmp_branch, test_branch]

        filtered = manager._filter_branches(branches)

        # Should include main and feature/*, exclude tmp/* and test/*
        assert main_branch in filtered
        assert feature_branch in filtered
        assert tmp_branch not in filtered
        assert test_branch not in filtered

    def test_is_significant_commit_prefixes(self, config, tmp_path):
        """Test significant commit detection based on prefixes."""
        manager = GitSyncManager(
            repo_path=tmp_path,
            config=config,
        )

        # Significant commits (must be >= 20 chars)
        feat_commit = Mock()
        feat_commit.message = "feat: add new feature implementation"
        feat_commit.parents = []
        assert manager._is_significant_commit(feat_commit) is True

        fix_commit = Mock()
        fix_commit.message = "fix: resolve critical bug in auth system"
        fix_commit.parents = []
        assert manager._is_significant_commit(fix_commit) is True

        refactor_commit = Mock()
        refactor_commit.message = "refactor: improve code structure and performance"
        refactor_commit.parents = []
        assert manager._is_significant_commit(refactor_commit) is True

        # Non-significant commits
        chore_commit = Mock()
        chore_commit.message = "chore: update dependencies"
        chore_commit.parents = []
        assert manager._is_significant_commit(chore_commit) is False

        style_commit = Mock()
        style_commit.message = "style: fix formatting"
        style_commit.parents = []
        assert manager._is_significant_commit(style_commit) is False

    def test_is_significant_commit_skip_patterns(self, config, tmp_path):
        """Test commit skipping based on patterns."""
        manager = GitSyncManager(
            repo_path=tmp_path,
            config=config,
        )

        # WIP commit (should be skipped)
        wip_commit = Mock()
        wip_commit.message = "wip: work in progress"
        wip_commit.parents = []
        assert manager._is_significant_commit(wip_commit) is False

        # TMP commit (should be skipped)
        tmp_commit = Mock()
        tmp_commit.message = "tmp: temporary change"
        tmp_commit.parents = []
        assert manager._is_significant_commit(tmp_commit) is False

    def test_is_significant_commit_length(self, config, tmp_path):
        """Test commit message length filtering."""
        config.min_message_length = 20

        manager = GitSyncManager(
            repo_path=tmp_path,
            config=config,
        )

        # Too short
        short_commit = Mock()
        short_commit.message = "feat: short"
        short_commit.parents = []
        assert manager._is_significant_commit(short_commit) is False

        # Long enough
        long_commit = Mock()
        long_commit.message = "feat: this is a longer commit message"
        long_commit.parents = []
        assert manager._is_significant_commit(long_commit) is True

    def test_is_significant_commit_merge(self, config, tmp_path):
        """Test merge commit detection."""
        config.include_merge_commits = True

        manager = GitSyncManager(
            repo_path=tmp_path,
            config=config,
        )

        # Merge commit (2 parents)
        merge_commit = Mock()
        merge_commit.message = "Merge branch 'feature' into main"
        merge_commit.parents = [Mock(), Mock()]  # 2 parents
        assert manager._is_significant_commit(merge_commit) is True

        # Regular commit (1 parent)
        regular_commit = Mock()
        regular_commit.message = "regular commit message"
        regular_commit.parents = [Mock()]  # 1 parent
        assert manager._is_significant_commit(regular_commit) is False

    def test_get_changed_files(self, config, tmp_path, mock_repo):
        """Test getting changed files from commit."""
        with patch("kuzu_memory.integrations.git_sync.git", create=True):
            manager = GitSyncManager(
                repo_path=tmp_path,
                config=config,
            )
            manager._repo = mock_repo
            manager._git_available = True

            # Test with parent (regular commit)
            parent = Mock()
            commit = Mock()
            commit.parents = [parent]

            diff1 = Mock()
            diff1.b_path = "file1.py"
            diff1.a_path = None

            diff2 = Mock()
            diff2.b_path = "file2.py"
            diff2.a_path = None

            parent.diff.return_value = [diff1, diff2]

            files = manager._get_changed_files(commit)
            assert "file1.py" in files
            assert "file2.py" in files
            assert len(files) == 2

    def test_commit_to_memory(self, config, tmp_path, mock_repo):
        """Test converting commit to memory."""
        with patch("kuzu_memory.integrations.git_sync.git", create=True):
            manager = GitSyncManager(
                repo_path=tmp_path,
                config=config,
            )
            manager._repo = mock_repo
            manager._git_available = True

            # Create mock commit with properly configured author/committer
            commit = Mock()
            commit.message = "feat: add new feature"
            commit.hexsha = "abc123def456"
            commit.author = Mock()
            commit.author.name = "Test User"
            commit.author.email = "test@example.com"
            commit.committer = Mock()
            commit.committer.name = "Test User"
            commit.committer.email = "test@example.com"
            commit.committed_datetime = datetime(2024, 1, 1, 12, 0, 0)
            commit.parents = [Mock()]

            # Mock diff for file stats
            parent = commit.parents[0]
            diff = Mock()
            diff.b_path = "test.py"
            diff.a_path = None
            diff.diff = b""  # Empty diff for binary/new file
            parent.diff.return_value = [diff]

            memory = manager._commit_to_memory(commit)

            assert "feat: add new feature" in memory.content
            assert "test.py" in memory.content
            assert memory.memory_type == MemoryType.EPISODIC
            assert memory.source_type == "git_sync"
            assert memory.metadata["commit_sha"] == "abc123def456"
            assert "Test User" in memory.metadata["commit_author"]
            assert memory.metadata["commit_timestamp"] == "2024-01-01T12:00:00"
            assert memory.created_at == datetime(2024, 1, 1, 12, 0, 0)
            # Verify new fields
            assert "file_stats" in memory.metadata
            assert "file_categories" in memory.metadata

    def test_get_sync_status_not_available(self, manager_no_git):
        """Test sync status when git not available."""
        status = manager_no_git.get_sync_status()

        assert status["available"] is False
        assert "reason" in status

    def test_sync_not_available(self, manager_no_git):
        """Test sync when git not available."""
        result = manager_no_git.sync()

        assert result["success"] is False
        assert "error" in result
        assert result["commits_synced"] == 0


class TestGitSyncIntegration:
    """Integration tests for git sync with mocked git."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GitSyncConfig(enabled=True)

    @pytest.fixture
    def mock_memory_store(self):
        """Create mock memory store."""
        store = Mock()
        store.store_memory = Mock(side_effect=lambda m: m)
        # batch_store_memories returns list of memory IDs
        store.batch_store_memories = Mock(return_value=["mem_id_123"])
        # get_recent_memories returns empty list (no duplicates)
        store.get_recent_memories = Mock(return_value=[])
        return store

    def test_sync_dry_run(self, config, tmp_path, mock_memory_store):
        """Test dry run sync."""
        with patch("kuzu_memory.integrations.git_sync.git", create=True) as mock_git:
            # Setup mock repo
            mock_repo = MagicMock()
            mock_git.Repo.return_value = mock_repo

            # Create mock commits
            commit1 = Mock()
            commit1.hexsha = "abc123"
            commit1.message = "feat: first feature with enough length"
            commit1.committed_datetime = datetime(2024, 1, 1, 12, 0, 0)
            commit1.parents = []

            commit2 = Mock()
            commit2.hexsha = "def456"
            commit2.message = "fix: bug fix with sufficient length"
            commit2.committed_datetime = datetime(2024, 1, 2, 12, 0, 0)
            commit2.parents = []

            # Setup branch
            branch = Mock()
            branch.name = "main"
            mock_repo.branches = [branch]
            mock_repo.iter_commits.return_value = [commit1, commit2]

            manager = GitSyncManager(
                repo_path=tmp_path,
                config=config,
                memory_store=mock_memory_store,
            )
            # Manually enable git since we mocked it after init
            manager._repo = mock_repo
            manager._git_available = True

            result = manager.sync(dry_run=True)

            assert result["success"] is True
            assert result["dry_run"] is True
            assert result["commits_found"] == 2
            assert result["commits_synced"] == 0
            # Memory store should not be called in dry run
            mock_memory_store.store_memory.assert_not_called()

    def test_sync_incremental(self, config, tmp_path, mock_memory_store):
        """Test incremental sync."""
        # Set last sync timestamp
        config.last_sync_timestamp = "2024-01-01T12:00:00"

        with patch("kuzu_memory.integrations.git_sync.git", create=True) as mock_git:
            # Setup mock repo
            mock_repo = MagicMock()
            mock_git.Repo.return_value = mock_repo

            # Old commit (before last sync)
            old_commit = Mock()
            old_commit.hexsha = "old123"
            old_commit.message = "feat: old commit with enough length"
            old_commit.committed_datetime = datetime(2024, 1, 1, 10, 0, 0)
            old_commit.parents = []
            old_commit.tree.traverse.return_value = []

            # New commit (after last sync)
            new_commit = Mock()
            new_commit.hexsha = "new123"
            new_commit.message = "feat: new commit with enough length"
            new_commit.committed_datetime = datetime(2024, 1, 2, 12, 0, 0)
            new_commit.parents = []
            new_commit.tree.traverse.return_value = [Mock(path="test.py")]
            # Properly configure author and committer
            new_commit.author = Mock()
            new_commit.author.name = "Test"
            new_commit.author.email = "test@example.com"
            new_commit.committer = Mock()
            new_commit.committer.name = "Test"
            new_commit.committer.email = "test@example.com"

            # Setup branch
            branch = Mock()
            branch.name = "main"
            mock_repo.branches = [branch]
            mock_repo.iter_commits.return_value = [new_commit, old_commit]
            mock_repo.active_branch.name = "main"

            manager = GitSyncManager(
                repo_path=tmp_path,
                config=config,
                memory_store=mock_memory_store,
            )
            # Manually enable git since we mocked it after init
            manager._repo = mock_repo
            manager._git_available = True

            result = manager.sync(mode="incremental")

            assert result["success"] is True
            assert result["commits_synced"] == 1  # Only new commit
            # Memory store should be called once via batch_store_memories
            assert mock_memory_store.batch_store_memories.call_count == 1

    def test_sync_all_duplicates_updates_state(
        self, config, tmp_path, mock_memory_store
    ):
        """Test that state updates even when all commits are duplicates (bug fix for 1M-XXX)."""
        # Set last sync timestamp
        config.last_sync_timestamp = "2024-01-01T12:00:00"
        config.last_commit_sha = None  # Simulate state where SHA was never set

        with patch("kuzu_memory.integrations.git_sync.git", create=True) as mock_git:
            # Setup mock repo
            mock_repo = MagicMock()
            mock_git.Repo.return_value = mock_repo

            # Create a commit that will be marked as duplicate
            duplicate_commit = Mock()
            duplicate_commit.hexsha = "duplicate123"
            duplicate_commit.message = "feat: commit that already exists"
            duplicate_commit.committed_datetime = datetime(2024, 1, 2, 12, 0, 0)
            duplicate_commit.parents = []
            duplicate_commit.tree.traverse.return_value = [Mock(path="test.py")]
            duplicate_commit.author = Mock()
            duplicate_commit.author.name = "Test"
            duplicate_commit.author.email = "test@example.com"
            duplicate_commit.committer = Mock()
            duplicate_commit.committer.name = "Test"
            duplicate_commit.committer.email = "test@example.com"

            # Setup branch
            branch = Mock()
            branch.name = "main"
            mock_repo.branches = [branch]
            mock_repo.iter_commits.return_value = [duplicate_commit]
            mock_repo.active_branch.name = "main"

            # Mock memory store to return duplicate (empty batch result)
            mock_memory_store.batch_store_memories = Mock(
                return_value=[]
            )  # Duplicate detection
            # Mock get_recent_memories to simulate duplicate check
            duplicate_memory = Mock()
            duplicate_memory.metadata = {"commit_sha": "duplicate123"}
            mock_memory_store.get_recent_memories = Mock(
                return_value=[duplicate_memory]
            )

            manager = GitSyncManager(
                repo_path=tmp_path,
                config=config,
                memory_store=mock_memory_store,
            )
            manager._repo = mock_repo
            manager._git_available = True

            result = manager.sync(mode="incremental")

            # Assertions
            assert result["success"] is True
            assert result["commits_synced"] == 0  # All duplicates
            assert result["commits_skipped"] == 1  # One duplicate
            # CRITICAL: State should be updated even though all commits were duplicates
            assert config.last_commit_sha == "duplicate123"
            assert config.last_sync_timestamp == "2024-01-02T12:00:00"
