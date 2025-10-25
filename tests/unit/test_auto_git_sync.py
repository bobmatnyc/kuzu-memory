"""
Unit tests for automatic git sync functionality.

Tests automatic git commit indexing with interval-based and trigger-based syncing.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from kuzu_memory.core.config import GitSyncConfig
from kuzu_memory.integrations.auto_git_sync import AutoGitSyncManager


class TestAutoGitSyncManager:
    """Test AutoGitSyncManager class."""

    @pytest.fixture
    def config(self):
        """Create test configuration with auto-sync enabled."""
        return GitSyncConfig(
            enabled=True,
            auto_sync_enabled=True,
            auto_sync_on_enhance=True,
            auto_sync_on_learn=False,
            auto_sync_interval_hours=24,
            auto_sync_max_commits=50,
        )

    @pytest.fixture
    def mock_git_sync(self):
        """Create mock GitSyncManager."""
        git_sync = MagicMock()
        git_sync.is_available.return_value = True
        git_sync.sync.return_value = {
            "success": True,
            "commits_synced": 5,
            "last_commit_sha": "abc123",
        }
        return git_sync

    @pytest.fixture
    def state_path(self, tmp_path):
        """Create temporary state file path."""
        return tmp_path / "git_sync_state.json"

    @pytest.fixture
    def manager(self, mock_git_sync, config, state_path):
        """Create AutoGitSyncManager instance."""
        return AutoGitSyncManager(
            git_sync_manager=mock_git_sync,
            config=config,
            state_path=state_path,
        )

    def test_init_creates_empty_state(self, manager, state_path):
        """Test initialization creates empty state if file doesn't exist."""
        assert not state_path.exists()
        assert manager._state["last_sync"] is None
        assert manager._state["last_commit_sha"] is None
        assert manager._state["commits_synced"] == 0

    def test_init_loads_existing_state(self, mock_git_sync, config, tmp_path):
        """Test initialization loads existing state file."""
        state_path = tmp_path / "git_sync_state.json"
        existing_state = {
            "last_sync": "2024-01-01T12:00:00",
            "last_commit_sha": "xyz789",
            "commits_synced": 42,
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(existing_state, f)

        manager = AutoGitSyncManager(
            git_sync_manager=mock_git_sync,
            config=config,
            state_path=state_path,
        )

        assert manager._state["last_sync"] == "2024-01-01T12:00:00"
        assert manager._state["last_commit_sha"] == "xyz789"
        assert manager._state["commits_synced"] == 42

    def test_should_auto_sync_disabled(self, manager):
        """Test should_auto_sync returns False when disabled."""
        manager.config.auto_sync_enabled = False
        assert manager.should_auto_sync("enhance") is False

    def test_should_auto_sync_git_unavailable(self, manager):
        """Test should_auto_sync returns False when git unavailable."""
        manager.git_sync.is_available.return_value = False
        assert manager.should_auto_sync("enhance") is False

    def test_should_auto_sync_trigger_disabled(self, manager):
        """Test should_auto_sync respects trigger-specific config."""
        # learn is disabled by default
        assert manager.should_auto_sync("learn") is False

        # enhance is enabled
        assert manager.should_auto_sync("enhance") is True

    def test_should_auto_sync_init_always_syncs(self, manager):
        """Test init trigger always syncs when enabled."""
        # Even with interval, init should sync
        manager._state["last_sync"] = datetime.now().isoformat()
        assert manager.should_auto_sync("init") is True

    def test_should_auto_sync_interval_elapsed(self, manager):
        """Test interval-based syncing when interval has elapsed."""
        # Set last sync to 25 hours ago (interval is 24 hours)
        last_sync = datetime.now() - timedelta(hours=25)
        manager._state["last_sync"] = last_sync.isoformat()

        assert manager.should_auto_sync("enhance") is True

    def test_should_auto_sync_interval_not_elapsed(self, manager):
        """Test interval-based syncing when interval has not elapsed."""
        # Set last sync to 1 hour ago (interval is 24 hours)
        last_sync = datetime.now() - timedelta(hours=1)
        manager._state["last_sync"] = last_sync.isoformat()

        assert manager.should_auto_sync("enhance") is False

    def test_should_auto_sync_no_previous_sync(self, manager):
        """Test should_auto_sync when there's no previous sync."""
        assert manager._state["last_sync"] is None
        assert manager.should_auto_sync("enhance") is True

    def test_should_auto_sync_interval_zero(self, manager):
        """Test interval=0 disables periodic syncing."""
        manager.config.auto_sync_interval_hours = 0

        # Even with no previous sync, should not sync if interval is 0
        assert manager._should_sync_by_interval() is False

        # But init/periodic triggers should still work
        assert manager.should_auto_sync("init") is True

    def test_auto_sync_if_needed_skips_when_conditions_not_met(self, manager):
        """Test auto_sync_if_needed skips when conditions not met."""
        # Set last sync to 1 hour ago (within 24-hour interval)
        last_sync = datetime.now() - timedelta(hours=1)
        manager._state["last_sync"] = last_sync.isoformat()

        result = manager.auto_sync_if_needed("enhance")

        assert result["success"] is True
        assert result["skipped"] is True
        assert "conditions not met" in result["reason"].lower()
        manager.git_sync.sync.assert_not_called()

    def test_auto_sync_if_needed_performs_sync(self, manager, state_path):
        """Test auto_sync_if_needed performs sync when conditions are met."""
        result = manager.auto_sync_if_needed("enhance")

        assert result["success"] is True
        assert result.get("skipped") is not True
        assert result["trigger"] == "enhance"
        manager.git_sync.sync.assert_called_once_with(mode="initial", dry_run=False)

        # Check state was updated
        assert manager._state["last_sync"] is not None
        assert manager._state["last_commit_sha"] == "abc123"
        assert manager._state["commits_synced"] == 5

        # Check state was persisted
        assert state_path.exists()
        with open(state_path) as f:
            saved_state = json.load(f)
        assert saved_state["last_commit_sha"] == "abc123"

    def test_auto_sync_if_needed_incremental_mode(self, manager):
        """Test auto_sync_if_needed uses incremental mode after first sync."""
        # Simulate previous sync
        manager._state["last_sync"] = (datetime.now() - timedelta(hours=25)).isoformat()

        result = manager.auto_sync_if_needed("enhance")

        assert result["success"] is True
        manager.git_sync.sync.assert_called_once_with(mode="incremental", dry_run=False)

    def test_auto_sync_if_needed_handles_sync_failure(self, manager):
        """Test auto_sync_if_needed handles sync failures gracefully."""
        manager.git_sync.sync.side_effect = Exception("Git sync failed")

        result = manager.auto_sync_if_needed("enhance")

        assert result["success"] is False
        assert "error" in result
        assert "Git sync failed" in result["error"]

    def test_get_sync_state(self, manager):
        """Test get_sync_state returns state copy."""
        manager._state["last_sync"] = "2024-01-01T00:00:00"
        manager._state["last_commit_sha"] = "abc123"
        manager._state["commits_synced"] = 10

        state = manager.get_sync_state()

        assert state["last_sync"] == "2024-01-01T00:00:00"
        assert state["last_commit_sha"] == "abc123"
        assert state["commits_synced"] == 10

        # Verify it's a copy
        state["commits_synced"] = 999
        assert manager._state["commits_synced"] == 10

    def test_force_sync_ignores_interval(self, manager):
        """Test force_sync ignores interval checks."""
        # Set last sync to 1 hour ago (within interval)
        manager._state["last_sync"] = (datetime.now() - timedelta(hours=1)).isoformat()

        result = manager.force_sync()

        assert result["success"] is True
        manager.git_sync.sync.assert_called_once_with(mode="auto", dry_run=False)

    def test_force_sync_updates_state(self, manager, state_path):
        """Test force_sync updates state after successful sync."""
        result = manager.force_sync()

        assert result["success"] is True
        assert manager._state["last_sync"] is not None
        assert manager._state["last_commit_sha"] == "abc123"
        assert manager._state["commits_synced"] == 5

        # Verify state was saved
        assert state_path.exists()

    def test_force_sync_handles_failure(self, manager):
        """Test force_sync handles sync failures."""
        manager.git_sync.sync.side_effect = Exception("Sync failed")

        result = manager.force_sync()

        assert result["success"] is False
        assert "Sync failed" in result["error"]

    def test_state_persistence(self, manager, state_path):
        """Test state is properly persisted and loaded."""
        # Perform sync
        manager.auto_sync_if_needed("init")

        # Create new manager with same state path
        new_manager = AutoGitSyncManager(
            git_sync_manager=manager.git_sync,
            config=manager.config,
            state_path=state_path,
        )

        # Verify state was loaded
        assert new_manager._state["last_sync"] is not None
        assert new_manager._state["last_commit_sha"] == "abc123"
        assert new_manager._state["commits_synced"] == 5

    def test_corrupted_state_file_recovery(self, mock_git_sync, config, tmp_path):
        """Test manager handles corrupted state file gracefully."""
        state_path = tmp_path / "git_sync_state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        state_path.write_text("{ invalid json }")

        # Should not crash, should create fresh state
        manager = AutoGitSyncManager(
            git_sync_manager=mock_git_sync,
            config=config,
            state_path=state_path,
        )

        assert manager._state["last_sync"] is None
        assert manager._state["commits_synced"] == 0


class TestAutoGitSyncIntegration:
    """Integration tests for auto git sync with KuzuMemory."""

    def test_auto_sync_respects_max_commits_config(self):
        """Test auto_sync_max_commits configuration is respected."""
        # This would require integration test with actual GitSyncManager
        # Placeholder for future implementation
        pass

    def test_auto_sync_does_not_block_operations(self):
        """Test auto-sync runs without blocking main operations."""
        # This would require performance testing
        # Placeholder for future implementation
        pass
