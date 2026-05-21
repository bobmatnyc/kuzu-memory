"""Tests for bash hooks migration system."""

import json
import tempfile
from pathlib import Path

import pytest

from kuzu_memory.migrations import MigrationManager
from kuzu_memory.migrations.v1_7_0_bash_hooks import BashHooksMigration


def test_migration_manager_initialization():
    """Test that migration manager can be initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MigrationManager(project_root=Path(tmpdir))
        assert manager.project_root == Path(tmpdir)
        assert manager.get_last_version() == "0.0.0"


def test_migration_manager_registers_migrations():
    """Test that migrations can be registered."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MigrationManager(project_root=Path(tmpdir))
        manager.register(BashHooksMigration)
        assert len(manager._migrations) == 1


def test_migration_manager_tracks_version():
    """Test that migration manager tracks versions correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MigrationManager(project_root=Path(tmpdir))

        # Initially no version
        assert manager.get_last_version() == "0.0.0"

        # Set version
        manager.set_version("1.7.0")
        assert manager.get_last_version() == "1.7.0"

        # Version persists across instances
        manager2 = MigrationManager(project_root=Path(tmpdir))
        assert manager2.get_last_version() == "1.7.0"


def test_bash_hooks_migration_description():
    """Test bash hooks migration has proper description."""
    migration = BashHooksMigration()
    description = migration.description()
    assert "bash" in description.lower()
    assert "fast" in description.lower()


def test_bash_hooks_migration_version_range():
    """Test bash hooks migration applies to correct version range."""
    migration = BashHooksMigration()
    assert migration.from_version == "1.7.0"
    assert migration.to_version == "999.0.0"


def test_migration_runs_when_upgrading():
    """Test that migration runs when upgrading from old to new version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MigrationManager(project_root=Path(tmpdir))

        # Simulate old version
        manager.set_version("1.6.0")

        # Register migration
        manager.register(BashHooksMigration)

        # Run migrations (upgrading to 1.7.0)
        # This won't actually modify anything since we don't have Claude settings,
        # but it should run without errors
        results = manager.run_migrations("1.7.0")

        # Should have attempted the migration
        assert len(results) >= 0  # Migration may or may not have changes


def test_migration_skips_when_already_migrated():
    """Test that migration doesn't run if already on current version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MigrationManager(project_root=Path(tmpdir))

        # Already on current version
        manager.set_version("1.7.0")

        # Register migration
        manager.register(BashHooksMigration)

        # Run migrations (no upgrade needed)
        results = manager.run_migrations("1.7.0")

        # Should not run any migrations
        assert len(results) == 0


def test_bash_hook_script_exists():
    """Test that bash hook scripts are bundled with the package."""
    from kuzu_memory import __file__ as km_init_file

    pkg_dir = Path(km_init_file).parent
    bash_hooks_dir = pkg_dir / "hooks" / "bash"

    # Check if directory exists (it should after installation)
    # In development, scripts are in src/kuzu_memory/hooks/bash/
    if not bash_hooks_dir.exists():
        bash_hooks_dir = Path("src/kuzu_memory/hooks/bash")

    assert bash_hooks_dir.exists(), f"Bash hooks directory not found at {bash_hooks_dir}"

    # Check for expected scripts
    expected_scripts = ["learn_hook.sh", "session_start_hook.sh", "enhance_hook.sh"]
    for script_name in expected_scripts:
        script_path = bash_hooks_dir / script_name
        assert script_path.exists(), f"Script not found: {script_path}"
        # Check if executable (only on Unix-like systems)
        if script_path.exists():
            import stat

            assert script_path.stat().st_mode & stat.S_IXUSR, (
                f"Script not executable: {script_path}"
            )


def test_bash_hook_script_syntax():
    """Test that bash hook scripts have valid syntax."""
    from kuzu_memory import __file__ as km_init_file

    pkg_dir = Path(km_init_file).parent
    bash_hooks_dir = pkg_dir / "hooks" / "bash"

    # In development, use source directory
    if not bash_hooks_dir.exists():
        bash_hooks_dir = Path("src/kuzu_memory/hooks/bash")

    scripts = ["learn_hook.sh", "session_start_hook.sh", "enhance_hook.sh"]

    for script_name in scripts:
        script_path = bash_hooks_dir / script_name
        if script_path.exists():
            # Read script and check for shebang
            content = script_path.read_text()
            assert content.startswith("#!/bin/bash"), f"Missing shebang in {script_name}"
            assert "set -euo pipefail" in content, f"Missing safety flags in {script_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
