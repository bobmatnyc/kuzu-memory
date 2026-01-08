"""
Unit tests for git sync file enhancement features.

Tests the enhanced file reference capabilities including:
- Enhanced content format with searchable file list
- File statistics (insertions/deletions)
- File categorization by type
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from kuzu_memory.core.config import GitSyncConfig
from kuzu_memory.core.models import MemoryType
from kuzu_memory.integrations.git_sync import GitSyncManager


@pytest.fixture
def git_config() -> GitSyncConfig:
    """Create test git sync configuration."""
    return GitSyncConfig(
        enabled=True,
        branch_include_patterns=["main", "master", "develop"],
        branch_exclude_patterns=["feature/*", "bugfix/*"],
        skip_patterns=["WIP", "tmp", "temp"],
        significant_prefixes=["feat:", "fix:", "docs:", "refactor:"],
        min_message_length=10,
        include_merge_commits=True,
    )


@pytest.fixture
def mock_repo(tmp_path: Path) -> Mock:
    """Create a mock git repository."""
    repo = Mock()
    repo.working_dir = str(tmp_path)
    return repo


@pytest.fixture
def git_sync_manager(tmp_path: Path, git_config: GitSyncConfig) -> GitSyncManager:
    """Create GitSyncManager instance with mocked repo."""
    manager = GitSyncManager(repo_path=tmp_path, config=git_config, memory_store=None)
    manager._git_available = True
    # Mock repo with proper active_branch handling
    manager._repo = None  # Set to None to trigger "unknown" branch
    return manager


class TestEnhancedContentFormat:
    """Test enhanced content format with searchable file list."""

    def test_content_with_few_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test content format with ≤10 files."""
        # Create mock commit
        commit = Mock()
        commit.message = "feat: add new feature"
        commit.hexsha = "abc123def456"
        commit.parents = [Mock()]
        commit.committed_datetime = datetime(2025, 10, 25, 12, 0, 0)
        commit.author = Mock()
        commit.author.name = "Test Author"
        commit.author.email = "test@example.com"
        commit.committer = Mock()
        commit.committer.name = "Test Committer"
        commit.committer.email = "test@example.com"

        # Mock changed files (5 files)
        changed_files = [
            "src/feature.py",
            "src/utils.py",
            "tests/test_feature.py",
            "docs/README.md",
            "config.yaml",
        ]

        with patch.object(git_sync_manager, "_get_changed_files", return_value=changed_files):
            with patch.object(git_sync_manager, "_get_file_stats", return_value={}):
                with patch.object(git_sync_manager, "_categorize_files", return_value={}):
                    memory = git_sync_manager._commit_to_memory(commit)

        # Verify content format
        assert memory.content.startswith("feat: add new feature")
        assert "\nChanged files:\n" in memory.content
        assert "- src/feature.py" in memory.content
        assert "- src/utils.py" in memory.content
        assert "- tests/test_feature.py" in memory.content
        assert "- docs/README.md" in memory.content
        assert "- config.yaml" in memory.content
        assert "... and" not in memory.content  # No truncation

    def test_content_with_many_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test content format with >10 files (truncation)."""
        commit = Mock()
        commit.message = "feat: major refactoring"
        commit.hexsha = "abc123def456"
        commit.parents = [Mock()]
        commit.committed_datetime = datetime(2025, 10, 25, 12, 0, 0)
        commit.author = Mock()
        commit.author.name = "Test Author"
        commit.author.email = "test@example.com"
        commit.committer = Mock()
        commit.committer.name = "Test Committer"
        commit.committer.email = "test@example.com"

        # Mock changed files (15 files)
        changed_files = [f"src/file{i}.py" for i in range(15)]

        with patch.object(git_sync_manager, "_get_changed_files", return_value=changed_files):
            with patch.object(git_sync_manager, "_get_file_stats", return_value={}):
                with patch.object(git_sync_manager, "_categorize_files", return_value={}):
                    memory = git_sync_manager._commit_to_memory(commit)

        # Verify truncation
        assert memory.content.startswith("feat: major refactoring")
        assert "\nChanged files:\n" in memory.content
        assert "- src/file0.py" in memory.content
        assert "- src/file9.py" in memory.content
        assert "... and 5 more files" in memory.content
        # Files 10-14 should not appear
        assert "- src/file10.py" not in memory.content
        assert "- src/file14.py" not in memory.content

    def test_content_with_no_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test content format with empty file list."""
        commit = Mock()
        commit.message = "docs: update documentation"
        commit.hexsha = "abc123def456"
        commit.parents = [Mock()]
        commit.committed_datetime = datetime(2025, 10, 25, 12, 0, 0)
        commit.author = Mock()
        commit.author.name = "Test Author"
        commit.author.email = "test@example.com"
        commit.committer = Mock()
        commit.committer.name = "Test Committer"
        commit.committer.email = "test@example.com"

        with patch.object(git_sync_manager, "_get_changed_files", return_value=[]):
            with patch.object(git_sync_manager, "_get_file_stats", return_value={}):
                with patch.object(git_sync_manager, "_categorize_files", return_value={}):
                    memory = git_sync_manager._commit_to_memory(commit)

        # Content should be just the message
        assert memory.content == "docs: update documentation"
        assert "Changed files:" not in memory.content


class TestFileStats:
    """Test file statistics calculation."""

    def test_file_stats_normal_commit(self, git_sync_manager: GitSyncManager) -> None:
        """Test file stats for normal commit with parent."""
        commit = Mock()
        commit.parents = [Mock()]

        # Mock diff with patch data
        diff1 = Mock()
        diff1.b_path = "src/feature.py"
        diff1.a_path = "src/feature.py"
        # Note: Each line starting with '+' (but not '+++') counts as insertion
        diff1.diff = b"""@@ -1,3 +1,5 @@
+# New header
 def existing_function():
     pass
+
+def new_function():
+    pass
"""

        diff2 = Mock()
        diff2.b_path = "src/utils.py"
        diff2.a_path = "src/utils.py"
        diff2.diff = b"""@@ -10,5 +10,3 @@
 def helper():
-    old_code = True
-    return old_code
+    return True
"""

        commit.parents[0].diff.return_value = [diff1, diff2]

        stats = git_sync_manager._get_file_stats(commit)

        # Verify stats
        assert "src/feature.py" in stats
        # 4 lines with '+': "# New header", empty line, "def new_function():", "pass"
        assert stats["src/feature.py"]["insertions"] == 4
        assert stats["src/feature.py"]["deletions"] == 0

        assert "src/utils.py" in stats
        assert stats["src/utils.py"]["insertions"] == 1
        assert stats["src/utils.py"]["deletions"] == 2

    def test_file_stats_initial_commit(self, git_sync_manager: GitSyncManager) -> None:
        """Test file stats for initial commit (no parent)."""
        commit = Mock()
        commit.parents = []

        stats = git_sync_manager._get_file_stats(commit)

        # Should return empty dict for initial commit
        assert stats == {}

    def test_file_stats_merge_commit(self, git_sync_manager: GitSyncManager) -> None:
        """Test file stats for merge commit (multiple parents)."""
        commit = Mock()
        commit.parents = [Mock(), Mock()]  # Merge commit has 2+ parents

        # Mock diff from first parent
        diff = Mock()
        diff.b_path = "src/merged.py"
        diff.a_path = "src/merged.py"
        diff.diff = b"""@@ -1,1 +1,2 @@
 existing_line
+new_line
"""

        commit.parents[0].diff.return_value = [diff]

        stats = git_sync_manager._get_file_stats(commit)

        # Should still work with first parent
        assert "src/merged.py" in stats
        assert stats["src/merged.py"]["insertions"] == 1
        assert stats["src/merged.py"]["deletions"] == 0

    def test_file_stats_error_handling(self, git_sync_manager: GitSyncManager) -> None:
        """Test graceful error handling when diff fails."""
        commit = Mock()
        commit.parents = [Mock()]
        commit.parents[0].diff.side_effect = Exception("Git error")

        stats = git_sync_manager._get_file_stats(commit)

        # Should return empty dict on error
        assert stats == {}

    def test_file_stats_binary_file(self, git_sync_manager: GitSyncManager) -> None:
        """Test file stats with binary file (no diff text)."""
        commit = Mock()
        commit.parents = [Mock()]

        diff = Mock()
        diff.b_path = "image.png"
        diff.a_path = "image.png"
        diff.diff = None  # Binary files have no diff

        commit.parents[0].diff.return_value = [diff]

        stats = git_sync_manager._get_file_stats(commit)

        # Should handle binary files gracefully
        assert "image.png" in stats
        assert stats["image.png"]["insertions"] == 0
        assert stats["image.png"]["deletions"] == 0


class TestFileCategorization:
    """Test file categorization by type."""

    def test_categorize_source_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test categorization of source code files."""
        files = [
            "src/main.py",
            "src/utils.js",
            "src/component.ts",
            "src/app.jsx",
            "src/view.tsx",
            "src/Server.java",
            "src/handler.go",
            "src/lib.rs",
            "src/controller.php",
            "src/model.rb",
            "src/core.c",
            "src/helper.cpp",
            "src/header.h",
            "src/template.hpp",
        ]

        categories = git_sync_manager._categorize_files(files)

        assert "source" in categories
        assert len(categories["source"]) == 14
        assert "src/main.py" in categories["source"]
        assert "src/utils.js" in categories["source"]
        assert "src/component.ts" in categories["source"]

    def test_categorize_test_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test categorization of test files."""
        files = [
            "test_main.py",
            "tests/test_utils.py",
            "src/feature_test.js",
            "spec/component.spec.ts",
            "__tests__/app.test.js",
        ]

        categories = git_sync_manager._categorize_files(files)

        assert "tests" in categories
        assert len(categories["tests"]) == 5
        assert "test_main.py" in categories["tests"]
        assert "tests/test_utils.py" in categories["tests"]
        assert "__tests__/app.test.js" in categories["tests"]

    def test_categorize_docs_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test categorization of documentation files."""
        files = [
            "README.md",
            "CHANGELOG.md",
            "docs/guide.md",
            "documentation/api.md",
        ]

        categories = git_sync_manager._categorize_files(files)

        assert "docs" in categories
        assert len(categories["docs"]) == 4
        assert "README.md" in categories["docs"]
        assert "CHANGELOG.md" in categories["docs"]
        assert "docs/guide.md" in categories["docs"]

    def test_categorize_config_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test categorization of configuration files."""
        files = [
            "package.json",
            "config.yaml",
            "settings.yml",
            "pyproject.toml",
            "setup.ini",
            "app.cfg",
            "database.config",
            ".env",
            "Dockerfile",
            "Makefile",
        ]

        categories = git_sync_manager._categorize_files(files)

        assert "config" in categories
        assert len(categories["config"]) == 10
        assert "package.json" in categories["config"]
        assert "config.yaml" in categories["config"]
        assert "Dockerfile" in categories["config"]

    def test_categorize_other_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test categorization of unrecognized file types."""
        files = [
            "image.png",
            "data.csv",
            "archive.zip",
            "LICENSE",
        ]

        categories = git_sync_manager._categorize_files(files)

        assert "other" in categories
        assert len(categories["other"]) == 4
        assert "image.png" in categories["other"]
        assert "LICENSE" in categories["other"]

    def test_categorize_mixed_files(self, git_sync_manager: GitSyncManager) -> None:
        """Test categorization of mixed file types."""
        files = [
            "src/main.py",
            "tests/test_main.py",
            "README.md",
            "config.yaml",
            "image.png",
        ]

        categories = git_sync_manager._categorize_files(files)

        # All categories should be present
        assert "source" in categories
        assert "tests" in categories
        assert "docs" in categories
        assert "config" in categories
        assert "other" in categories

        assert categories["source"] == ["src/main.py"]
        assert categories["tests"] == ["tests/test_main.py"]
        assert categories["docs"] == ["README.md"]
        assert categories["config"] == ["config.yaml"]
        assert categories["other"] == ["image.png"]

    def test_categorize_empty_list(self, git_sync_manager: GitSyncManager) -> None:
        """Test categorization of empty file list."""
        categories = git_sync_manager._categorize_files([])

        # Should return empty dict (empty categories removed)
        assert categories == {}

    def test_categorize_removes_empty_categories(self, git_sync_manager: GitSyncManager) -> None:
        """Test that empty categories are removed from result."""
        files = ["src/main.py"]  # Only source file

        categories = git_sync_manager._categorize_files(files)

        # Only source category should be present
        assert "source" in categories
        assert "tests" not in categories
        assert "docs" not in categories
        assert "config" not in categories
        assert "other" not in categories


class TestMetadataIntegration:
    """Test integration of file stats and categories in metadata."""

    def test_metadata_includes_file_stats(self, git_sync_manager: GitSyncManager) -> None:
        """Test that metadata includes file_stats field."""
        commit = Mock()
        commit.message = "feat: add feature"
        commit.hexsha = "abc123def456"
        commit.parents = [Mock()]
        commit.committed_datetime = datetime(2025, 10, 25, 12, 0, 0)
        commit.author = Mock()
        commit.author.name = "Test Author"
        commit.author.email = "test@example.com"
        commit.committer = Mock()
        commit.committer.name = "Test Committer"
        commit.committer.email = "test@example.com"

        # Mock file stats
        file_stats = {
            "src/feature.py": {"insertions": 10, "deletions": 5},
            "tests/test_feature.py": {"insertions": 20, "deletions": 0},
        }

        with patch.object(git_sync_manager, "_get_changed_files", return_value=[]):
            with patch.object(git_sync_manager, "_get_file_stats", return_value=file_stats):
                with patch.object(git_sync_manager, "_categorize_files", return_value={}):
                    memory = git_sync_manager._commit_to_memory(commit)

        assert "file_stats" in memory.metadata
        assert memory.metadata["file_stats"] == file_stats

    def test_metadata_includes_file_categories(self, git_sync_manager: GitSyncManager) -> None:
        """Test that metadata includes file_categories field."""
        commit = Mock()
        commit.message = "feat: add feature"
        commit.hexsha = "abc123def456"
        commit.parents = [Mock()]
        commit.committed_datetime = datetime(2025, 10, 25, 12, 0, 0)
        commit.author = Mock()
        commit.author.name = "Test Author"
        commit.author.email = "test@example.com"
        commit.committer = Mock()
        commit.committer.name = "Test Committer"
        commit.committer.email = "test@example.com"

        # Mock file categories
        file_categories = {
            "source": ["src/feature.py"],
            "tests": ["tests/test_feature.py"],
            "docs": ["README.md"],
        }

        with patch.object(git_sync_manager, "_get_changed_files", return_value=[]):
            with patch.object(git_sync_manager, "_get_file_stats", return_value={}):
                with patch.object(
                    git_sync_manager,
                    "_categorize_files",
                    return_value=file_categories,
                ):
                    memory = git_sync_manager._commit_to_memory(commit)

        assert "file_categories" in memory.metadata
        assert memory.metadata["file_categories"] == file_categories

    def test_metadata_preserves_existing_fields(self, git_sync_manager: GitSyncManager) -> None:
        """Test that new metadata fields don't break existing ones."""
        commit = Mock()
        commit.message = "feat: add feature"
        commit.hexsha = "abc123def456"
        commit.parents = [Mock()]
        commit.committed_datetime = datetime(2025, 10, 25, 12, 0, 0)
        # Configure Mock objects with spec to properly handle attribute access
        commit.author = Mock()
        commit.author.name = "Test Author"
        commit.author.email = "test@example.com"
        commit.committer = Mock()
        commit.committer.name = "Test Committer"
        commit.committer.email = "test@example.com"

        with patch.object(git_sync_manager, "_get_changed_files", return_value=[]):
            with patch.object(git_sync_manager, "_get_file_stats", return_value={}):
                with patch.object(git_sync_manager, "_categorize_files", return_value={}):
                    memory = git_sync_manager._commit_to_memory(commit)

        # Verify all existing metadata fields are still present
        assert memory.metadata["commit_sha"] == "abc123def456"
        assert memory.metadata["commit_author"] == "Test Author <test@example.com>"
        assert memory.metadata["commit_committer"] == "Test Committer <test@example.com>"
        assert "commit_timestamp" in memory.metadata
        assert memory.metadata["branch"] == "unknown"
        assert "changed_files" in memory.metadata
        assert "parent_count" in memory.metadata
        # New fields
        assert "file_stats" in memory.metadata
        assert "file_categories" in memory.metadata

    def test_full_integration_example(self, git_sync_manager: GitSyncManager) -> None:
        """Test full integration with real-world example."""
        commit = Mock()
        commit.message = "feat: implement user authentication"
        commit.hexsha = "abc123def456"
        commit.parents = [Mock()]
        commit.committed_datetime = datetime(2025, 10, 25, 12, 0, 0)
        commit.author = Mock()
        commit.author.name = "John Doe"
        commit.author.email = "john@example.com"
        commit.committer = Mock()
        commit.committer.name = "John Doe"
        commit.committer.email = "john@example.com"

        changed_files = [
            "src/auth/login.py",
            "src/auth/register.py",
            "src/auth/utils.py",
            "tests/test_auth.py",
            "docs/auth.md",
            "config/auth.yaml",
        ]

        file_stats = {
            "src/auth/login.py": {"insertions": 50, "deletions": 0},
            "src/auth/register.py": {"insertions": 40, "deletions": 0},
            "src/auth/utils.py": {"insertions": 20, "deletions": 5},
            "tests/test_auth.py": {"insertions": 100, "deletions": 0},
            "docs/auth.md": {"insertions": 30, "deletions": 0},
            "config/auth.yaml": {"insertions": 10, "deletions": 0},
        }

        file_categories = {
            "source": [
                "src/auth/login.py",
                "src/auth/register.py",
                "src/auth/utils.py",
            ],
            "tests": ["tests/test_auth.py"],
            "docs": ["docs/auth.md"],
            "config": ["config/auth.yaml"],
        }

        with patch.object(git_sync_manager, "_get_changed_files", return_value=changed_files):
            with patch.object(git_sync_manager, "_get_file_stats", return_value=file_stats):
                with patch.object(
                    git_sync_manager,
                    "_categorize_files",
                    return_value=file_categories,
                ):
                    memory = git_sync_manager._commit_to_memory(commit)

        # Verify enhanced content
        assert memory.content.startswith("feat: implement user authentication")
        assert "- src/auth/login.py" in memory.content
        assert "- tests/test_auth.py" in memory.content
        assert "- config/auth.yaml" in memory.content

        # Verify metadata
        assert memory.metadata["file_stats"] == file_stats
        assert memory.metadata["file_categories"] == file_categories
        assert memory.metadata["changed_files"] == changed_files

        # Verify memory properties
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.source_type == "git_sync"
        assert memory.user_id == "john@example.com"
