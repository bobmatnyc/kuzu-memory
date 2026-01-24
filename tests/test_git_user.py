"""
Tests for git user detection and memory tagging.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig, MemoryConfig
from kuzu_memory.core.memory import KuzuMemory
from kuzu_memory.core.models import Memory, MemoryType
from kuzu_memory.utils.git_user import GitUserInfo, GitUserProvider


class TestGitUserProvider:
    """Test GitUserProvider utility."""

    def setup_method(self):
        """Clear cache before each test."""
        GitUserProvider.clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        GitUserProvider.clear_cache()

    def test_get_git_user_info_with_email(self):
        """Test git user detection with email configured."""
        with patch.object(
            GitUserProvider,
            "_run_git_command",
            side_effect=lambda args, cwd=None: (
                "john@example.com" if "user.email" in args else "John Doe"
            ),
        ):
            user_info = GitUserProvider.get_git_user_info()

            assert user_info.user_id == "john@example.com"
            assert user_info.email == "john@example.com"
            assert user_info.name == "John Doe"
            assert user_info.source == "git_email"

    def test_get_git_user_info_with_name_only(self):
        """Test git user detection with only name configured (no email)."""
        with patch.object(
            GitUserProvider,
            "_run_git_command",
            side_effect=lambda args, cwd=None: (None if "user.email" in args else "John Doe"),
        ):
            user_info = GitUserProvider.get_git_user_info()

            assert user_info.user_id == "John Doe"
            assert user_info.email is None
            assert user_info.name == "John Doe"
            assert user_info.source == "git_name"

    def test_get_git_user_info_fallback_to_system_user(self):
        """Test fallback to system username when git is not configured."""
        with (
            patch.object(GitUserProvider, "_run_git_command", return_value=None),
            patch("kuzu_memory.utils.git_user.getpass.getuser", return_value="testuser"),
        ):
            user_info = GitUserProvider.get_git_user_info()

            assert user_info.user_id == "testuser"
            assert user_info.email is None
            assert user_info.name is None
            assert user_info.source == "system_user"

    def test_get_git_user_id_returns_user_id_only(self):
        """Test get_git_user_id returns just the user_id string."""
        with patch.object(
            GitUserProvider,
            "_run_git_command",
            side_effect=lambda args, cwd=None: (
                "jane@example.com" if "user.email" in args else None
            ),
        ):
            user_id = GitUserProvider.get_git_user_id()

            assert user_id == "jane@example.com"
            assert isinstance(user_id, str)

    def test_get_git_user_info_caching(self):
        """Test that git user info is cached."""
        call_count = 0

        def mock_run_git_command(args, cwd=None):
            nonlocal call_count
            call_count += 1
            if "user.email" in args:
                return "cached@example.com"
            return "Cached User"

        with patch.object(GitUserProvider, "_run_git_command", side_effect=mock_run_git_command):
            # First call
            user_info1 = GitUserProvider.get_git_user_info()
            first_call_count = call_count

            # Second call should use cache
            user_info2 = GitUserProvider.get_git_user_info()
            second_call_count = call_count

            assert user_info1.user_id == user_info2.user_id
            assert first_call_count == 2  # email + name
            assert second_call_count == 2  # No new calls, cache used (call_count unchanged)

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        with patch.object(
            GitUserProvider,
            "_run_git_command",
            return_value="test@example.com",
        ):
            # Populate cache
            GitUserProvider.get_git_user_info()
            assert len(GitUserProvider._cache) > 0

            # Clear cache
            GitUserProvider.clear_cache()
            assert len(GitUserProvider._cache) == 0

    def test_is_git_available_true(self):
        """Test is_git_available when git is configured."""
        with patch.object(
            GitUserProvider,
            "_run_git_command",
            return_value="user@example.com",
        ):
            assert GitUserProvider.is_git_available() is True

    def test_is_git_available_false(self):
        """Test is_git_available when git is not configured."""
        with patch.object(GitUserProvider, "_run_git_command", return_value=None):
            assert GitUserProvider.is_git_available() is False

    def test_git_user_info_to_dict(self):
        """Test GitUserInfo.to_dict conversion."""
        user_info = GitUserInfo(
            user_id="test@example.com",
            email="test@example.com",
            name="Test User",
            source="git_email",
        )

        data = user_info.to_dict()
        assert data["user_id"] == "test@example.com"
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert data["source"] == "git_email"


class TestKuzuMemoryUserTagging:
    """Test KuzuMemory user tagging integration."""

    def test_kuzu_memory_auto_detects_git_user(self, tmp_path):
        """Test that KuzuMemory auto-detects git user on initialization."""
        db_path = tmp_path / ".kuzu-memory" / "test.db"

        with patch.object(
            GitUserProvider,
            "get_git_user_info",
            return_value=GitUserInfo(
                user_id="auto@example.com",
                email="auto@example.com",
                name="Auto User",
                source="git_email",
            ),
        ):
            km = KuzuMemory(db_path=db_path)

            assert km._user_id == "auto@example.com"
            assert km.get_current_user_id() == "auto@example.com"

            km.close()

    def test_kuzu_memory_respects_user_id_override(self, tmp_path):
        """Test that manual user_id override takes precedence."""
        db_path = tmp_path / ".kuzu-memory" / "test.db"

        config = KuzuMemoryConfig.default()
        config.memory.user_id_override = "override@example.com"

        km = KuzuMemory(db_path=db_path, config=config)

        assert km._user_id == "override@example.com"
        km.close()

    def test_kuzu_memory_disables_auto_tagging(self, tmp_path):
        """Test that auto-tagging can be disabled."""
        db_path = tmp_path / ".kuzu-memory" / "test.db"

        config = KuzuMemoryConfig.default()
        config.memory.auto_tag_git_user = False

        km = KuzuMemory(db_path=db_path, config=config)

        assert km._user_id is None
        km.close()

    def test_generate_memories_uses_auto_detected_user(self, tmp_path):
        """Test that generated memories use auto-detected user_id."""
        db_path = tmp_path / ".kuzu-memory" / "test.db"

        with patch.object(
            GitUserProvider,
            "get_git_user_info",
            return_value=GitUserInfo(
                user_id="generator@example.com",
                email="generator@example.com",
                name="Generator User",
                source="git_email",
            ),
        ):
            km = KuzuMemory(db_path=db_path)

            # Mock memory store to capture the user_id
            captured_user_id = None

            def mock_generate(
                content, metadata=None, source="conversation", user_id=None, **kwargs
            ):
                nonlocal captured_user_id
                captured_user_id = user_id
                return []

            km.memory_store.generate_memories = mock_generate

            # Generate memories
            km.generate_memories("Test preference: Python")

            # Verify user_id was passed
            assert captured_user_id == "generator@example.com"

            km.close()

    def test_remember_uses_auto_detected_user(self, tmp_path):
        """Test that remember() uses auto-detected user_id."""
        db_path = tmp_path / ".kuzu-memory" / "test.db"

        with patch.object(
            GitUserProvider,
            "get_git_user_info",
            return_value=GitUserInfo(
                user_id="remember@example.com",
                email="remember@example.com",
                name="Remember User",
                source="git_email",
            ),
        ):
            km = KuzuMemory(db_path=db_path)

            # Mock _store_memory_in_database to capture the memory
            captured_memory = None

            def mock_store(memory, is_update=False):
                nonlocal captured_memory
                captured_memory = memory

            km.memory_store._store_memory_in_database = mock_store

            # Remember something
            km.remember("User prefers dark mode")

            # Verify memory was tagged with user_id
            assert captured_memory is not None
            assert captured_memory.user_id == "remember@example.com"

            km.close()

    def test_get_users_returns_unique_user_ids(self, tmp_path):
        """Test get_users() returns list of unique user IDs."""
        db_path = tmp_path / ".kuzu-memory" / "test.db"

        km = KuzuMemory(db_path=db_path)

        # Mock memory store
        km.memory_store.get_users = MagicMock(
            return_value=["user1@example.com", "user2@example.com"]
        )

        users = km.get_users()

        assert len(users) == 2
        assert "user1@example.com" in users
        assert "user2@example.com" in users

        km.close()

    def test_get_memories_by_user_filters_correctly(self, tmp_path):
        """Test get_memories_by_user() filters by user_id."""
        db_path = tmp_path / ".kuzu-memory" / "test.db"

        km = KuzuMemory(db_path=db_path)

        # Create mock memories
        mock_memory = Memory(
            content="User-specific memory",
            memory_type=MemoryType.PREFERENCE,
            user_id="specific@example.com",
        )

        km.memory_store.get_memories_by_user = MagicMock(return_value=[mock_memory])

        memories = km.get_memories_by_user("specific@example.com")

        assert len(memories) == 1
        assert memories[0].user_id == "specific@example.com"

        km.close()

    def test_statistics_includes_user_info(self, tmp_path):
        """Test that statistics include current user and user stats."""
        db_path = tmp_path / ".kuzu-memory" / "test.db"

        with patch.object(
            GitUserProvider,
            "get_git_user_info",
            return_value=GitUserInfo(
                user_id="stats@example.com",
                email="stats@example.com",
                name="Stats User",
                source="git_email",
            ),
        ):
            km = KuzuMemory(db_path=db_path)

            # Mock get_users
            km.memory_store.get_users = MagicMock(
                return_value=["stats@example.com", "other@example.com"]
            )

            stats = km.get_statistics()

            assert stats["system_info"]["current_user_id"] == "stats@example.com"
            assert "user_stats" in stats
            assert stats["user_stats"]["total_users"] == 2
            assert stats["user_stats"]["current_user"] == "stats@example.com"

            km.close()


class TestGitSyncUserTagging:
    """Test git sync user tagging."""

    def test_git_commit_tagged_with_author_email(self):
        """Test that git commits are tagged with author/committer email."""
        from kuzu_memory.core.config import GitSyncConfig
        from kuzu_memory.integrations.git_sync import GitSyncManager

        # Create mock commit
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_commit.message = "feat: add new feature"
        mock_commit.parents = []
        mock_commit.author.name = "John Doe"
        mock_commit.author.email = "john@example.com"
        mock_commit.committer.name = "Jane Smith"
        mock_commit.committer.email = "jane@example.com"
        mock_commit.committed_datetime = MagicMock()
        mock_commit.committed_datetime.replace = MagicMock(
            return_value=MagicMock(isoformat=MagicMock(return_value="2025-01-01T00:00:00"))
        )
        mock_commit.tree.traverse = MagicMock(return_value=[])

        config = GitSyncConfig()
        git_sync = GitSyncManager(repo_path=Path.cwd(), config=config, memory_store=None)

        # Mock _get_changed_files to avoid actual git operations
        git_sync._get_changed_files = MagicMock(return_value=["file1.py", "file2.py"])

        # Convert to memory
        memory = git_sync._commit_to_memory(mock_commit)

        # Verify user_id is set to committer email (priority over author)
        assert memory.user_id == "jane@example.com"
        assert memory.metadata["commit_author"] == "John Doe <john@example.com>"
        assert memory.metadata["commit_committer"] == "Jane Smith <jane@example.com>"


class TestMemoryStoreUserFiltering:
    """Test MemoryStore user filtering methods."""

    def test_get_memories_by_user_query(self, tmp_path):
        """Test get_memories_by_user generates correct query."""
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.memory_store import MemoryStore

        config = KuzuMemoryConfig.default()

        # Create mock db_adapter
        mock_adapter = MagicMock()
        mock_adapter.execute_query = MagicMock(return_value=[])

        store = MemoryStore(mock_adapter, config)

        # Call get_memories_by_user
        store.get_memories_by_user("test@example.com", limit=50)

        # Verify query was called with correct parameters
        assert mock_adapter.execute_query.called
        call_args = mock_adapter.execute_query.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "m.user_id = $user_id" in query
        assert params["user_id"] == "test@example.com"
        assert params["limit"] == 50

    def test_get_users_query(self, tmp_path):
        """Test get_users generates correct query."""
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.memory_store import MemoryStore

        config = KuzuMemoryConfig.default()

        # Create mock db_adapter
        mock_adapter = MagicMock()
        mock_adapter.execute_query = MagicMock(
            return_value=[
                {"user_id": "user1@example.com"},
                {"user_id": "user2@example.com"},
            ]
        )

        store = MemoryStore(mock_adapter, config)

        # Call get_users
        users = store.get_users()

        # Verify query was called
        assert mock_adapter.execute_query.called
        call_args = mock_adapter.execute_query.call_args
        query = call_args[0][0]

        assert "DISTINCT m.user_id" in query
        assert "m.user_id IS NOT NULL" in query

        # Verify results
        assert len(users) == 2
        assert "user1@example.com" in users
        assert "user2@example.com" in users


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
