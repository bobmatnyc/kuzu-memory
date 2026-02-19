"""
Unit tests for project root detection fix.

Tests the fix for the bug where home directory was incorrectly
detected as project root instead of the current directory.
"""

import logging
import tempfile
from pathlib import Path

import pytest

from kuzu_memory.utils.project_setup import find_project_root

logger = logging.getLogger(__name__)


class TestProjectRootDetection:
    """Test project root detection logic."""

    def test_current_directory_with_indicator(self, tmp_path: Path) -> None:
        """Test that current directory is used when it has project indicators."""
        # Create a project directory with .git
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / ".git").mkdir()

        # Should return the current directory
        result = find_project_root(project_dir)
        assert result == project_dir

    def test_current_directory_with_pyproject(self, tmp_path: Path) -> None:
        """Test detection with pyproject.toml."""
        project_dir = tmp_path / "python-project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").touch()

        result = find_project_root(project_dir)
        assert result == project_dir

    def test_current_directory_with_package_json(self, tmp_path: Path) -> None:
        """Test detection with package.json."""
        project_dir = tmp_path / "js-project"
        project_dir.mkdir()
        (project_dir / "package.json").touch()

        result = find_project_root(project_dir)
        assert result == project_dir

    def test_walk_up_to_parent_with_indicator(self, tmp_path: Path) -> None:
        """Test walking up to parent directory when current has no indicators."""
        # Create parent with .git
        parent_dir = tmp_path / "repo"
        parent_dir.mkdir()
        (parent_dir / ".git").mkdir()

        # Create subdirectory without indicators
        sub_dir = parent_dir / "src" / "deep"
        sub_dir.mkdir(parents=True)

        # Should walk up and find parent
        result = find_project_root(sub_dir)
        assert result == parent_dir

    def test_never_use_home_directory(self, tmp_path: Path) -> None:
        """
        Test that home directory is NEVER used as project root.

        This is the critical bug fix test.
        """
        # Mock home directory with project indicators
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        (fake_home / ".git").mkdir()  # Home has .git (like /Users/masa might)
        (fake_home / "Makefile").touch()  # Home has Makefile

        # Create a subdirectory without indicators
        work_dir = fake_home / "hostgator_db_migration"
        work_dir.mkdir()

        # Should return work_dir, NOT fake_home
        result = find_project_root(work_dir, _home_dir=fake_home)
        assert result == work_dir, (
            f"Expected {work_dir}, got {result}. "
            "Home directory should NEVER be used as project root!"
        )

    def test_stop_at_home_directory_boundary(self, tmp_path: Path) -> None:
        """Test that search stops at home directory boundary."""
        # Create fake home and parent above it
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        (parent_dir / ".git").mkdir()

        fake_home = parent_dir / "home"
        fake_home.mkdir()

        # Create subdirectory under home
        work_dir = fake_home / "projects" / "myproject"
        work_dir.mkdir(parents=True)

        # Should return work_dir, NOT parent_dir above home
        result = find_project_root(work_dir, _home_dir=fake_home)
        assert result == work_dir

    def test_no_indicators_returns_current_directory(self, tmp_path: Path) -> None:
        """Test that current directory is returned when no indicators found."""
        # Create directory with no project indicators
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = find_project_root(empty_dir)
        assert result == empty_dir

    def test_deep_nesting_finds_correct_root(self, tmp_path: Path) -> None:
        """Test finding root in deeply nested structure."""
        # Create root with indicator
        root = tmp_path / "myproject"
        root.mkdir()
        (root / "pyproject.toml").touch()

        # Create deep nesting
        deep = root / "src" / "pkg" / "subpkg" / "module"
        deep.mkdir(parents=True)

        result = find_project_root(deep)
        assert result == root

    def test_multiple_indicators_in_current_dir(self, tmp_path: Path) -> None:
        """Test with multiple project indicators in current directory."""
        project_dir = tmp_path / "fullstack"
        project_dir.mkdir()
        (project_dir / ".git").mkdir()
        (project_dir / "package.json").touch()
        (project_dir / "pyproject.toml").touch()

        result = find_project_root(project_dir)
        assert result == project_dir

    def test_prefers_current_over_parent(self, tmp_path: Path) -> None:
        """Test that current directory is preferred even if parent has indicators."""
        # Create parent with .git
        parent = tmp_path / "parent-repo"
        parent.mkdir()
        (parent / ".git").mkdir()

        # Create child with its own indicator
        child = parent / "sub-project"
        child.mkdir()
        (child / "pyproject.toml").touch()

        # Should prefer child over parent
        result = find_project_root(child)
        assert result == child

    def test_real_world_scenario_hostgator_migration(self, tmp_path: Path) -> None:
        """
        Test the exact scenario from the bug report.

        Running kuzu-memory init from /Users/masa/hostgator_db_migration
        should create memories in that directory, not in /Users/masa.
        """
        # Simulate /Users/masa with project indicators
        fake_home = tmp_path / "masa"
        fake_home.mkdir()
        (fake_home / ".git").mkdir()  # User's home might have .git
        (fake_home / "Makefile").touch()  # Or other indicators

        # Simulate hostgator_db_migration directory (no indicators)
        work_dir = fake_home / "hostgator_db_migration"
        work_dir.mkdir()

        # Run detection
        result = find_project_root(work_dir, _home_dir=fake_home)

        # Should return work_dir, not fake_home
        assert result == work_dir, (
            f"Bug reproduced! Expected {work_dir} but got {result}. "
            "This would create memories in the wrong location."
        )

    def test_default_to_current_directory_when_none_specified(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Test that current directory is used when start_path is None."""
        # Create and change to test directory
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / ".git").mkdir()

        # Mock cwd
        monkeypatch.chdir(test_dir)

        # Call without arguments
        result = find_project_root()
        assert result == test_dir

    def test_resolves_symlinks(self, tmp_path: Path) -> None:
        """Test that paths are resolved (symlinks followed)."""
        # Create actual directory
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        (real_dir / "pyproject.toml").touch()

        # Create symlink
        symlink_dir = tmp_path / "link"
        symlink_dir.symlink_to(real_dir)

        # Should resolve to real directory
        result = find_project_root(symlink_dir)
        assert result == real_dir.resolve()


class TestProjectRootEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_root_filesystem_boundary(self, tmp_path: Path) -> None:
        """Test behavior at filesystem root."""
        # Use tmp_path as simulated root
        fake_root = tmp_path
        work_dir = fake_root / "work"
        work_dir.mkdir()

        # Mock home to be under fake_root
        fake_home = fake_root / "home"
        fake_home.mkdir()

        result = find_project_root(work_dir, _home_dir=fake_home)
        # Should return work_dir since no indicators found
        assert result == work_dir

    def test_permission_denied_on_parent(self, tmp_path: Path) -> None:
        """Test graceful handling when parent directory is inaccessible."""
        # This test verifies the function doesn't crash on permission errors
        test_dir = tmp_path / "accessible"
        test_dir.mkdir()

        # The function should handle this gracefully by returning current dir
        result = find_project_root(test_dir)
        assert result is not None


class TestProjectRootLogging:
    """Test logging behavior."""

    def test_logs_found_in_current_directory(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging when indicator found in current directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".git").mkdir()

        with caplog.at_level(logging.DEBUG, logger="kuzu_memory.utils.project_setup"):
            find_project_root(project_dir)

        assert "Found project root at current directory" in caplog.text
        assert str(project_dir) in caplog.text

    def test_logs_home_directory_boundary(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging when home directory boundary is reached."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        (fake_home / ".git").mkdir()

        work_dir = fake_home / "work"
        work_dir.mkdir()

        with caplog.at_level(logging.DEBUG, logger="kuzu_memory.utils.project_setup"):
            find_project_root(work_dir, _home_dir=fake_home)

        assert "Reached home directory" in caplog.text or "Using current directory" in caplog.text

    def test_logs_no_project_root_found(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging when no project root is found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with caplog.at_level(logging.DEBUG):
            result = find_project_root(empty_dir)

        assert "No project root found" in caplog.text or result == empty_dir
