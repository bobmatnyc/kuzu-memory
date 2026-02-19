"""Tests for the enhanced migration system."""

from __future__ import annotations

from pathlib import Path

import pytest

from kuzu_memory.migrations import (
    CleanupMigration,
    ConfigMigration,
    HooksMigration,
    Migration,
    MigrationResult,
    MigrationType,
    SchemaMigration,
    discover_migrations,
    get_migration_manager,
)


def test_migration_types_enum():
    """Test MigrationType enum has all expected values."""
    assert MigrationType.CONFIG == MigrationType("config")
    assert MigrationType.SCHEMA == MigrationType("schema")
    assert MigrationType.HOOKS == MigrationType("hooks")
    assert MigrationType.SETTINGS == MigrationType("settings")
    assert MigrationType.STRUCTURE == MigrationType("structure")
    assert MigrationType.DATA == MigrationType("data")
    assert MigrationType.CLEANUP == MigrationType("cleanup")


def test_migration_result_dataclass():
    """Test MigrationResult dataclass."""
    result = MigrationResult(
        success=True,
        message="Test migration succeeded",
        changes=["change1", "change2"],
        warnings=["warning1"],
    )

    assert result.success is True
    assert result.message == "Test migration succeeded"
    assert len(result.changes) == 2
    assert len(result.warnings) == 1


def test_discover_migrations():
    """Test auto-discovery of migration classes."""
    migrations = discover_migrations()

    # Should find at least our example migrations
    migration_names = [m.__name__ for m in migrations]
    assert "BashHooksMigration" in migration_names
    assert "ConfigDefaultsMigration" in migration_names
    assert "CleanupOldLogsMigration" in migration_names

    # Should not include base classes
    assert "Migration" not in migration_names
    assert "ConfigMigration" not in migration_names
    assert "HooksMigration" not in migration_names


def test_migration_manager_initialization():
    """Test MigrationManager initialization."""
    manager = get_migration_manager()

    # Should have migrations registered
    assert len(manager._migrations) > 0

    # Should have state (may have been migrated before)
    assert manager.state is not None
    assert isinstance(manager.state.last_version, str)


def test_migration_manager_chaining():
    """Test MigrationManager method chaining."""
    from kuzu_memory.migrations.manager import MigrationManager

    class DummyMigration(Migration):
        name = "dummy"
        from_version = "1.0.0"
        to_version = "2.0.0"

        def description(self) -> str:
            return "Dummy migration"

        def check_applicable(self) -> bool:
            return False

        def migrate(self) -> MigrationResult:
            return MigrationResult(success=True, message="Done")

    manager = MigrationManager()
    result = manager.register(DummyMigration).register(DummyMigration)

    assert result is manager  # Should return self for chaining
    assert len(manager._migrations) == 2


def test_migration_priority_ordering():
    """Test migrations are ordered by priority."""
    manager = get_migration_manager()
    pending = manager.get_pending_migrations("999.0.0")

    # If we have multiple migrations, they should be sorted by priority
    if len(pending) > 1:
        priorities = [m.priority for m in pending]
        assert priorities == sorted(priorities), "Migrations should be sorted by priority"


def test_config_migration_base_class(tmp_path: Path):
    """Test ConfigMigration base class functionality."""

    class TestConfigMigration(ConfigMigration):
        name = "test_config"
        from_version = "1.0.0"
        to_version = "2.0.0"
        config_file = ".test/config.json"

        def description(self) -> str:
            return "Test config migration"

        def migrate(self) -> MigrationResult:
            config_path = self.get_config_path()
            config = self.read_json(config_path)
            config["new_key"] = "new_value"
            self.write_json(config_path, config)

            return MigrationResult(
                success=True,
                message="Config updated",
                changes=["Added new_key"],
            )

    # Create test config
    config_path = tmp_path / ".test" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('{"old_key": "old_value"}')

    migration = TestConfigMigration(project_root=tmp_path)
    assert migration.check_applicable() is True

    result = migration.migrate()
    assert result.success is True
    assert "new_key" in migration.read_json(config_path)

    # Check backup was created
    backup_path = config_path.with_suffix(".json.bak")
    assert backup_path.exists()


def test_cleanup_migration_base_class(tmp_path: Path):
    """Test CleanupMigration base class functionality."""

    class TestCleanupMigration(CleanupMigration):
        name = "test_cleanup"
        from_version = "1.0.0"
        to_version = "2.0.0"

        def description(self) -> str:
            return "Test cleanup migration"

        def check_applicable(self) -> bool:
            return (tmp_path / "old_file.txt").exists()

        def migrate(self) -> MigrationResult:
            old_file = tmp_path / "old_file.txt"
            if old_file.exists():
                old_file.unlink()
                return MigrationResult(
                    success=True,
                    message="Cleaned up old file",
                    changes=["Removed old_file.txt"],
                )
            return MigrationResult(success=True, message="Nothing to clean")

    # Create old file
    old_file = tmp_path / "old_file.txt"
    old_file.write_text("old content")

    migration = TestCleanupMigration(project_root=tmp_path)
    assert migration.check_applicable() is True
    assert migration.priority == 900  # Cleanup has high priority

    result = migration.migrate()
    assert result.success is True
    assert not old_file.exists()


def test_migration_dry_run():
    """Test dry-run mode doesn't make changes."""
    manager = get_migration_manager()

    # Dry run should return results without executing
    results = manager.run_migrations("999.0.0", dry_run=True)

    # All results should indicate dry-run
    for result in results:
        assert "[DRY RUN]" in result.message


def test_migration_type_filtering():
    """Test filtering migrations by type."""
    manager = get_migration_manager()

    # Get only cleanup migrations
    pending_all = manager.get_pending_migrations("999.0.0")
    results = manager.run_migrations(
        "999.0.0",
        dry_run=True,
        migration_types=[MigrationType.CLEANUP],
    )

    # If we have cleanup migrations, they should be in results
    cleanup_count = sum(1 for m in pending_all if m.migration_type == MigrationType.CLEANUP)

    if cleanup_count > 0:
        assert len(results) <= cleanup_count


def test_migration_history_tracking(tmp_path: Path):
    """Test migration history is tracked correctly."""
    from kuzu_memory.migrations.manager import MigrationManager

    class TestMigration(Migration):
        name = "test_history"
        from_version = "0.0.0"
        to_version = "1.0.0"
        migration_type = MigrationType.CONFIG

        def description(self) -> str:
            return "Test history tracking"

        def check_applicable(self) -> bool:
            return True

        def migrate(self) -> MigrationResult:
            return MigrationResult(
                success=True,
                message="Migration successful",
                changes=["Change 1", "Change 2"],
            )

    manager = MigrationManager(project_root=tmp_path)
    manager.register(TestMigration)

    # Run migration
    manager.run_migrations("1.0.0")

    # Check history
    history = manager.get_history(1)
    assert len(history) == 1
    assert history[0].name == "test_history"
    assert history[0].success is True
    assert len(history[0].changes) == 2

    # Check state file was created
    state_file = tmp_path / ".kuzu-memory" / "migration_state.json"
    assert state_file.exists()


def test_migration_rollback(tmp_path: Path):
    """Test migration rollback functionality."""

    class TestRollbackMigration(ConfigMigration):
        name = "test_rollback"
        from_version = "0.0.0"
        to_version = "1.0.0"
        config_file = ".test/config.json"

        def description(self) -> str:
            return "Test rollback"

        def migrate(self) -> MigrationResult:
            config_path = self.get_config_path()
            config = self.read_json(config_path)

            # Backup is created automatically by write_json
            config["modified"] = True
            self.write_json(config_path, config)

            # Simulate failure
            return MigrationResult(success=False, message="Migration failed")

    # Create test config
    config_path = tmp_path / ".test" / "config.json"
    config_path.parent.mkdir(parents=True)
    original_content = '{"original": true}'
    config_path.write_text(original_content)

    migration = TestRollbackMigration(project_root=tmp_path)
    result = migration.migrate()
    assert result.success is False

    # Backup should exist before rollback
    backup_path = config_path.with_suffix(".json.bak")
    assert backup_path.exists(), "Backup should be created by write_json"

    # Rollback should restore original
    success = migration.rollback()
    assert success is True

    # After rollback, backup should be removed (restored to original)
    # The rollback removes the .bak file after restoring


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
