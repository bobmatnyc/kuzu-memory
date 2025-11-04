"""
Integration tests for git sync functionality.

Tests end-to-end git sync with real git repository operations.
"""

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from kuzu_memory.core.config import GitSyncConfig
from kuzu_memory.core.models import MemoryType
from kuzu_memory.integrations.git_sync import GitSyncManager


class TestGitSyncIntegration:
    """Integration tests with real git operations."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a test git repository."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        return repo_path

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GitSyncConfig(enabled=True)

    def test_sync_with_real_commits(self, git_repo, config):
        """Test sync with real git commits."""
        # Create and commit files
        test_file = git_repo / "test.py"
        test_file.write_text("print('hello')")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: add test file with sufficient length"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create another commit
        test_file.write_text("print('hello world')")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "fix: update test file with more content"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create manager
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        # Get commits
        commits = manager.get_significant_commits()

        assert len(commits) == 2
        assert "feat:" in commits[0].message
        assert "fix:" in commits[1].message

    def test_sync_with_branches(self, git_repo, config):
        """Test sync with multiple branches."""
        # Create initial commit
        test_file = git_repo / "test.py"
        test_file.write_text("initial")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: initial commit with enough text"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature/test"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        test_file.write_text("feature work")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: feature work with sufficient length"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create manager
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        # Get commits from all branches
        commits = manager.get_significant_commits()

        # Should get commits from both main and feature branches
        assert len(commits) >= 2

    def test_sync_excludes_non_significant(self, git_repo, config):
        """Test that non-significant commits are excluded."""
        # Create significant commit
        test_file = git_repo / "test.py"
        test_file.write_text("content")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: significant commit with enough text"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create non-significant commit
        test_file.write_text("more content")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "chore: non-significant commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create manager
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        # Get commits
        commits = manager.get_significant_commits()

        # Should only get significant commit
        assert len(commits) == 1
        assert "feat:" in commits[0].message

    def test_incremental_sync(self, git_repo, config):
        """Test incremental sync with timestamp filtering."""
        # Create first commit
        test_file = git_repo / "test.py"
        test_file.write_text("first")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: first commit with sufficient text"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create manager and do initial sync
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        first_commits = manager.get_significant_commits()
        assert len(first_commits) == 1

        # Set sync timestamp to now
        sync_time = datetime.now()

        # Wait to ensure distinct git timestamps (git uses 1-second resolution)
        import time

        time.sleep(1.1)

        # Create second commit
        test_file.write_text("second")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: second commit with sufficient text"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Get only new commits
        new_commits = manager.get_significant_commits(since=sync_time)

        assert len(new_commits) == 1
        assert "second" in new_commits[0].message

    def test_commit_to_memory_conversion(self, git_repo, config):
        """Test converting commits to memories."""
        # Create commit
        test_file = git_repo / "test.py"
        test_file.write_text("content")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: test commit with enough characters"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create manager
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        # Get commit and convert to memory
        commits = manager.get_significant_commits()
        assert len(commits) == 1

        memory = manager._commit_to_memory(commits[0])

        # Verify memory properties
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.source_type == "git_sync"
        assert "feat: test commit" in memory.content
        assert "test.py" in memory.content
        assert "commit_sha" in memory.metadata
        assert "commit_author" in memory.metadata
        assert "commit_timestamp" in memory.metadata
        assert "Test User" in memory.metadata["commit_author"]

    def test_sync_status(self, git_repo, config):
        """Test getting sync status."""
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        status = manager.get_sync_status()

        assert status["available"] is True
        assert status["enabled"] is True
        assert status["repo_path"] == str(git_repo)
        assert "branch_include_patterns" in status
        assert "branch_exclude_patterns" in status

    def test_sync_dry_run_real_repo(self, git_repo, config):
        """Test dry run sync with real repository."""
        # Create commits
        test_file = git_repo / "test.py"
        test_file.write_text("content")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: test commit with sufficient length"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create manager
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        # Perform dry run
        result = manager.sync(dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["commits_found"] > 0
        assert result["commits_synced"] == 0
        assert "commits" in result

    def test_branch_pattern_filtering(self, git_repo, config):
        """Test branch pattern filtering."""
        # Create main branch commit
        test_file = git_repo / "test.py"
        test_file.write_text("main")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: main commit with enough content"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create tmp branch (should be excluded)
        subprocess.run(
            ["git", "checkout", "-b", "tmp/test"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        test_file.write_text("tmp work")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: tmp commit with enough content"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create manager
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        # Get commits
        commits = manager.get_significant_commits()

        # Should only get main branch commit, tmp excluded
        assert len(commits) == 1
        assert "main" in commits[0].message

    def test_merge_commit_detection(self, git_repo, config):
        """Test merge commit inclusion."""
        config.include_merge_commits = True

        # Create initial commit
        test_file = git_repo / "test.py"
        test_file.write_text("initial")

        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: initial commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Get the current branch name (could be main or master)
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        main_branch = result.stdout.strip()

        # Create feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature/test"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        test_file.write_text("feature")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: feature commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Merge back to main branch
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "merge", "--no-ff", "feature/test", "-m", "Merge feature/test"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create manager
        manager = GitSyncManager(
            repo_path=git_repo,
            config=config,
        )

        # Get commits
        commits = manager.get_significant_commits()

        # Should include merge commit
        merge_commits = [c for c in commits if len(c.parents) > 1]
        assert len(merge_commits) >= 1
