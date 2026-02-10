"""
Unit tests for smart incremental git sync functionality.

Tests bounded iteration, async execution, and sync state tracking.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from kuzu_memory.core.config import GitSyncConfig
from kuzu_memory.integrations.git_sync import GitSyncManager


class TestIncrementalGitSync:
    """Test incremental git sync with bounded iteration."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GitSyncConfig(
            enabled=True,
            auto_sync_enabled=True,
            auto_sync_on_enhance=True,
            auto_sync_interval_hours=24,
            auto_sync_max_commits=50,
        )

    @pytest.fixture
    def mock_repo(self):
        """Create mock git repository."""
        repo = MagicMock()
        repo.branches = []
        return repo

    @pytest.fixture
    def mock_git_sync(self, config, mock_repo, tmp_path):
        """Create mock GitSyncManager."""
        git_sync = GitSyncManager(
            repo_path=tmp_path,
            config=config,
            memory_store=None,
        )
        git_sync._repo = mock_repo
        git_sync._git_available = True
        return git_sync

    def test_sync_incremental_with_max_commits(self, mock_git_sync, mock_repo):
        """Test sync_incremental limits commits with max_commits parameter."""
        # Create mock commits
        mock_commits = []
        for i in range(150):  # More than max_commits
            commit = Mock()
            commit.hexsha = f"sha{i:03d}"
            commit.message = f"feat: commit {i}"
            commit.committed_datetime = datetime.now() - timedelta(days=i)
            commit.parents = []
            commit.author = Mock(name="Author", email="author@example.com")
            commit.committer = Mock(name="Committer", email="committer@example.com")
            mock_commits.append(commit)

        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.branches = [mock_branch]

        # Mock iter_commits to return commits
        mock_repo.iter_commits.return_value = iter(mock_commits)

        # Call sync_incremental with max_commits=100
        result = mock_git_sync.sync_incremental(
            max_age_days=30,
            max_commits=100,
            dry_run=True,  # Don't actually store
        )

        # Verify bounded iteration
        assert result["success"] is True
        assert result["commits_found"] <= 100  # Should be limited
        assert "since" in result
        # sync_incremental only syncs last 30 days, so commits_found should be <= 30
        # (since we created 150 commits, 1 per day going back)

    def test_sync_incremental_uses_last_sync_timestamp(
        self, mock_git_sync, mock_repo, config
    ):
        """Test sync_incremental uses last_sync_timestamp if available."""
        # Set last sync timestamp to 5 days ago
        last_sync = datetime.now() - timedelta(days=5)
        config.last_sync_timestamp = last_sync.isoformat()
        mock_git_sync.config = config

        # Create mock commits (10 days worth)
        mock_commits = []
        for i in range(10):
            commit = Mock()
            commit.hexsha = f"sha{i:03d}"
            commit.message = f"feat: commit {i}"
            commit.committed_datetime = datetime.now() - timedelta(days=i)
            commit.parents = []
            commit.author = Mock(name="Author", email="author@example.com")
            commit.committer = Mock(name="Committer", email="committer@example.com")
            mock_commits.append(commit)

        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.branches = [mock_branch]
        mock_repo.iter_commits.return_value = iter(mock_commits)

        # Call sync_incremental with max_age_days=7
        result = mock_git_sync.sync_incremental(
            max_age_days=7,
            max_commits=100,
            dry_run=True,
        )

        # Since last_sync (5 days ago) is more recent than max_age_days (7 days ago),
        # it should use last_sync as the since parameter
        assert result["success"] is True
        since = datetime.fromisoformat(result["since"])
        # Since should be max(last_sync, 7 days ago) = last_sync (5 days ago)
        assert since >= last_sync - timedelta(seconds=1)  # Allow 1s tolerance

    def test_sync_incremental_uses_max_age_when_no_last_sync(
        self, mock_git_sync, mock_repo, config
    ):
        """Test sync_incremental uses max_age_days when no last sync."""
        # No last sync timestamp
        config.last_sync_timestamp = None
        mock_git_sync.config = config

        # Create mock commits
        mock_commits = []
        for i in range(10):
            commit = Mock()
            commit.hexsha = f"sha{i:03d}"
            commit.message = f"feat: commit {i}"
            commit.committed_datetime = datetime.now() - timedelta(days=i)
            commit.parents = []
            commit.author = Mock(name="Author", email="author@example.com")
            commit.committer = Mock(name="Committer", email="committer@example.com")
            mock_commits.append(commit)

        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.branches = [mock_branch]
        mock_repo.iter_commits.return_value = iter(mock_commits)

        # Call sync_incremental with max_age_days=7
        result = mock_git_sync.sync_incremental(
            max_age_days=7,
            max_commits=100,
            dry_run=True,
        )

        # Should use 7 days ago as since
        assert result["success"] is True
        since = datetime.fromisoformat(result["since"])
        expected_since = datetime.now() - timedelta(days=7)
        assert since >= expected_since - timedelta(minutes=1)  # Allow 1min tolerance

    def test_get_significant_commits_bounded_iteration(self, mock_git_sync, mock_repo):
        """Test get_significant_commits uses bounded iteration with max_commits."""
        # Create 200 mock commits
        mock_commits = []
        for i in range(200):
            commit = Mock()
            commit.hexsha = f"sha{i:03d}"
            commit.message = f"feat: commit {i}"
            commit.committed_datetime = datetime.now() - timedelta(days=i)
            commit.parents = []
            commit.author = Mock(name="Author", email="author@example.com")
            mock_commits.append(commit)

        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.branches = [mock_branch]
        mock_repo.iter_commits.return_value = iter(mock_commits)

        # Call get_significant_commits with max_commits=50
        commits = mock_git_sync.get_significant_commits(max_commits=50)

        # Should return at most 50 commits
        assert len(commits) <= 50

    def test_sync_incremental_updates_sync_state(
        self, mock_git_sync, mock_repo, config
    ):
        """Test sync_incremental updates last_sync_timestamp and last_commit_sha."""
        # Create mock commits
        mock_commits = []
        for i in range(5):
            commit = Mock()
            commit.hexsha = f"sha{i:03d}"
            commit.message = f"feat: commit {i}"
            commit.committed_datetime = datetime.now() - timedelta(days=i)
            commit.parents = []
            commit.author = Mock(name="Author", email="author@example.com")
            commit.committer = Mock(name="Committer", email="committer@example.com")
            mock_commits.append(commit)

        # Mock branch
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.branches = [mock_branch]
        mock_repo.iter_commits.return_value = iter(mock_commits)

        # Mock memory store
        mock_memory_store = Mock()
        mock_memory_store.get_recent_memories.return_value = []
        mock_memory_store.batch_store_memories.return_value = ["mem001"]
        mock_git_sync.memory_store = mock_memory_store

        # Initial state
        assert config.last_sync_timestamp is None
        assert config.last_commit_sha is None

        # Call sync_incremental (not dry_run)
        result = mock_git_sync.sync_incremental(
            max_age_days=7,
            max_commits=100,
            dry_run=False,
        )

        # Verify state was updated
        assert result["success"] is True
        assert config.last_sync_timestamp is not None
        assert config.last_commit_sha is not None
        assert len(config.last_commit_sha) == 6  # SHA is 6 chars (sha000)


class TestAsyncGitSync:
    """Test async git sync execution in hooks."""

    def test_git_sync_async_spawns_subprocess(self, tmp_path):
        """Test _git_sync_async spawns detached subprocess."""
        from kuzu_memory.cli.hooks_commands import _git_sync_async

        logger = Mock()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            _git_sync_async(tmp_path, logger)

            # Verify subprocess was spawned
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args

            # Verify command includes incremental sync
            cmd = call_args[0][0]
            assert "git" in cmd
            assert "sync" in cmd
            assert "--incremental" in cmd
            assert "--max-commits" in cmd
            assert "100" in cmd

            # Verify detached execution
            kwargs = call_args[1]
            assert kwargs["start_new_session"] is True
            assert kwargs["cwd"] == str(tmp_path)

    def test_git_sync_async_handles_errors_gracefully(self, tmp_path):
        """Test _git_sync_async logs errors but doesn't raise."""
        from kuzu_memory.cli.hooks_commands import _git_sync_async

        logger = Mock()

        with patch("subprocess.Popen", side_effect=Exception("Spawn failed")):
            # Should not raise, only log
            _git_sync_async(tmp_path, logger)

            # Verify error was logged
            logger.warning.assert_called_once()
            assert "Failed to launch" in logger.warning.call_args[0][0]
