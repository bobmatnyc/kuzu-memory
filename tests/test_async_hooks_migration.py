"""Tests for async hooks migration system."""

import json
import tempfile
from pathlib import Path

import pytest
from kuzu_memory.migrations import MigrationManager
from kuzu_memory.migrations.v1_6_33_async_hooks import AsyncHooksMigration


def test_async_hooks_migration_description():
    """Test async hooks migration has proper description."""
    migration = AsyncHooksMigration()
    description = migration.description()
    assert "async" in description.lower()
    assert "sessionstart" in description.lower() or "posttooluse" in description.lower()


def test_async_hooks_migration_version_range():
    """Test async hooks migration applies to correct version range."""
    migration = AsyncHooksMigration()
    assert migration.from_version == "1.6.33"
    assert migration.to_version == "999.0.0"


def test_async_hooks_migration_priority():
    """Test async hooks migration has correct priority (after bash hooks)."""
    migration = AsyncHooksMigration()
    assert migration.priority == 150  # After bash hooks (100), before cleanup (900)


def test_migration_adds_async_to_session_start():
    """Test that migration adds async flag to SessionStart hooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        settings_path = project_root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Create settings with SessionStart hook without async flag
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/kuzu-memory hooks session-start",
                            }
                        ],
                    }
                ]
            }
        }
        settings_path.write_text(json.dumps(settings, indent=2))

        # Run migration
        migration = AsyncHooksMigration(project_root=project_root)
        assert migration.check_applicable()

        result = migration.migrate()
        assert result.success
        assert len(result.changes) > 0
        assert "SessionStart" in result.changes[0]

        # Verify async flag was added
        updated_settings = json.loads(settings_path.read_text())
        session_start_hook = updated_settings["hooks"]["SessionStart"][0]["hooks"][0]
        assert session_start_hook.get("async") is True


def test_migration_adds_async_to_post_tool_use():
    """Test that migration adds async flag to PostToolUse hooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        settings_path = project_root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Create settings with PostToolUse hook without async flag
        settings = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/kuzu-memory hooks learn",
                            }
                        ],
                    }
                ]
            }
        }
        settings_path.write_text(json.dumps(settings, indent=2))

        # Run migration
        migration = AsyncHooksMigration(project_root=project_root)
        assert migration.check_applicable()

        result = migration.migrate()
        assert result.success
        assert len(result.changes) > 0
        assert "PostToolUse" in result.changes[0]

        # Verify async flag was added
        updated_settings = json.loads(settings_path.read_text())
        post_tool_use_hook = updated_settings["hooks"]["PostToolUse"][0]["hooks"][0]
        assert post_tool_use_hook.get("async") is True


def test_migration_keeps_user_prompt_submit_synchronous():
    """Test that migration ensures UserPromptSubmit hooks remain synchronous."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        settings_path = project_root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Create settings with UserPromptSubmit hook with async flag (incorrect)
        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/kuzu-memory hooks enhance",
                                "async": True,  # This should be removed
                            }
                        ],
                    }
                ],
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/kuzu-memory hooks session-start",
                            }
                        ],
                    }
                ],
            }
        }
        settings_path.write_text(json.dumps(settings, indent=2))

        # Run migration
        migration = AsyncHooksMigration(project_root=project_root)
        result = migration.migrate()
        assert result.success

        # Verify async flag was removed from UserPromptSubmit
        updated_settings = json.loads(settings_path.read_text())
        user_prompt_submit_hook = updated_settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]
        assert "async" not in user_prompt_submit_hook

        # Verify async flag was added to SessionStart
        session_start_hook = updated_settings["hooks"]["SessionStart"][0]["hooks"][0]
        assert session_start_hook.get("async") is True


def test_migration_skips_already_migrated_hooks():
    """Test that migration doesn't modify hooks that already have async flags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        settings_path = project_root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Create settings with hooks already having async flags
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/kuzu-memory hooks session-start",
                                "async": True,
                            }
                        ],
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/kuzu-memory hooks learn",
                                "async": True,
                            }
                        ],
                    }
                ],
            }
        }
        settings_path.write_text(json.dumps(settings, indent=2))

        # Migration should not be applicable
        migration = AsyncHooksMigration(project_root=project_root)
        assert not migration.check_applicable()

        result = migration.migrate()
        assert result.success
        assert len(result.changes) == 0


def test_migration_creates_backup():
    """Test that migration creates backup before modifying settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        settings_path = project_root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Create settings with hook to migrate
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/kuzu-memory hooks session-start",
                            }
                        ],
                    }
                ]
            }
        }
        settings_path.write_text(json.dumps(settings, indent=2))

        # Run migration
        migration = AsyncHooksMigration(project_root=project_root)
        migration.migrate()

        # Verify backup was created
        backup_path = settings_path.with_suffix(".json.bak")
        assert backup_path.exists()

        # Verify backup contains original content
        backup_settings = json.loads(backup_path.read_text())
        session_start_hook = backup_settings["hooks"]["SessionStart"][0]["hooks"][0]
        assert "async" not in session_start_hook


def test_migration_manager_runs_async_hooks_migration():
    """Test that migration manager can run async hooks migration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        manager = MigrationManager(project_root=project_root)

        # Simulate old version
        manager.set_version("1.6.32")

        # Create settings with hook to migrate
        settings_path = project_root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/kuzu-memory hooks session-start",
                            }
                        ],
                    }
                ]
            }
        }
        settings_path.write_text(json.dumps(settings, indent=2))

        # Register migration
        manager.register(AsyncHooksMigration)

        # Run migrations (upgrading to 1.6.33)
        results = manager.run_migrations("1.6.33")

        # Should have run the migration
        assert len(results) > 0


def test_migration_handles_non_kuzu_hooks():
    """Test that migration doesn't modify non-kuzu hooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        settings_path = project_root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Create settings with non-kuzu hooks
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/usr/local/bin/some-other-tool start",
                            }
                        ],
                    }
                ]
            }
        }
        settings_path.write_text(json.dumps(settings, indent=2))

        # Migration should not be applicable
        migration = AsyncHooksMigration(project_root=project_root)
        assert not migration.check_applicable()

        result = migration.migrate()
        assert result.success
        assert len(result.changes) == 0

        # Verify settings unchanged
        updated_settings = json.loads(settings_path.read_text())
        assert updated_settings == settings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
