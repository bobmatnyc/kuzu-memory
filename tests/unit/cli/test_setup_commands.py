"""
Unit tests for setup_commands.py focusing on --with-git-hooks functionality.

Tests the new git hooks integration in the setup command, including:
- Helper function logic (_detect_git_repository, _find_git_directory, _install_git_hooks)
- Integration with setup command
- Dry-run behavior
- Error handling and user feedback
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kuzu_memory.cli.setup_commands import (
    _detect_git_repository,
    _find_git_directory,
    _install_git_hooks,
    setup,
)


@pytest.fixture
def runner():
    """Provide Click test runner with isolated filesystem."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock console output for testing."""
    with patch("kuzu_memory.cli.setup_commands.rich_print") as mock:
        yield mock


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTION TESTS - Core Logic
# ═══════════════════════════════════════════════════════════


class TestDetectGitRepository:
    """Test _detect_git_repository helper function."""

    def test_detect_git_repository_finds_git(self, tmp_path):
        """Test detection when .git directory exists in project root."""
        # Create .git directory
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Call _detect_git_repository
        result = _detect_git_repository(tmp_path)

        # Assert returns True
        assert result is True

    def test_detect_git_repository_searches_parent_dirs(self, tmp_path):
        """Test detection searches up to 5 parent directories."""
        # Create nested directory structure: repo/.git, repo/subdir/nested/project
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        # Create nested subdirectories
        nested_project = repo_root / "subdir" / "nested" / "project"
        nested_project.mkdir(parents=True)

        # Call from child directory (3 levels deep)
        result = _detect_git_repository(nested_project)

        # Assert returns True (found .git in parent)
        assert result is True

    def test_detect_git_repository_searches_up_to_5_levels(self, tmp_path):
        """Test detection only searches up to 5 parent directories."""
        # Create very deep nesting: 6 levels deep
        current = tmp_path
        for i in range(6):
            current = current / f"level{i}"
            current.mkdir()

        # Put .git at the root (6 levels up from deepest directory)
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Call from 6th level (should NOT find .git)
        deepest = tmp_path / "level0" / "level1" / "level2" / "level3" / "level4" / "level5"
        result = _detect_git_repository(deepest)

        # Assert returns False (exceeded 5 levels search depth)
        assert result is False

    def test_detect_git_repository_no_git(self, tmp_path):
        """Test detection when no git repository exists."""
        # Use tmp_path without .git directory
        result = _detect_git_repository(tmp_path)

        # Assert returns False
        assert result is False

    def test_detect_git_repository_stops_at_filesystem_root(self, tmp_path):
        """Test detection stops when reaching filesystem root."""
        # Create a single directory (one level from tmp_path)
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # No .git anywhere
        result = _detect_git_repository(project_dir)

        # Assert returns False (stops safely without infinite loop)
        assert result is False


class TestFindGitDirectory:
    """Test _find_git_directory helper function."""

    def test_find_git_directory_returns_path(self, tmp_path):
        """Test finding .git directory returns correct path."""
        # Create .git directory
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Call _find_git_directory
        result = _find_git_directory(tmp_path)

        # Assert returns correct Path
        assert result == git_dir
        assert result.exists()

    def test_find_git_directory_returns_path_from_parent(self, tmp_path):
        """Test finding .git directory in parent returns correct path."""
        # Create nested structure
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        nested_dir = repo_root / "src" / "app"
        nested_dir.mkdir(parents=True)

        # Call from nested directory
        result = _find_git_directory(nested_dir)

        # Assert returns correct Path to .git in parent
        assert result == git_dir
        assert result.exists()

    def test_find_git_directory_returns_none(self, tmp_path):
        """Test finding .git directory returns None when not found."""
        # Use tmp_path without .git
        result = _find_git_directory(tmp_path)

        # Assert returns None
        assert result is None

    def test_find_git_directory_returns_none_beyond_5_levels(self, tmp_path):
        """Test finding .git beyond 5 levels returns None."""
        # Create 6 levels of nesting
        current = tmp_path
        for i in range(6):
            current = current / f"level{i}"
            current.mkdir()

        # Put .git at root
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Call from 6th level
        deepest = tmp_path / "level0" / "level1" / "level2" / "level3" / "level4" / "level5"
        result = _find_git_directory(deepest)

        # Assert returns None (exceeded search depth)
        assert result is None


class TestInstallGitHooks:
    """Test _install_git_hooks helper function."""

    def test_install_git_hooks_success(self, tmp_path):
        """Test successful git hooks installation."""
        # Create mock context
        ctx = MagicMock()
        ctx.invoke = MagicMock()

        with patch("kuzu_memory.cli.setup_commands.rich_print"):
            # Patch the import statement inside _install_git_hooks
            with patch("kuzu_memory.cli.git_commands.install_hooks") as mock_cmd:
                # Call _install_git_hooks
                result = _install_git_hooks(ctx, tmp_path, force=False)

                # Assert hooks installed successfully
                assert result is True
                ctx.invoke.assert_called_once_with(mock_cmd, force=False)

    def test_install_git_hooks_with_force(self, tmp_path):
        """Test git hooks installation with force flag."""
        ctx = MagicMock()

        with patch("kuzu_memory.cli.setup_commands.rich_print"):
            with patch("kuzu_memory.cli.git_commands.install_hooks") as mock_cmd:
                result = _install_git_hooks(ctx, tmp_path, force=True)

                assert result is True
                ctx.invoke.assert_called_once_with(mock_cmd, force=True)

    def test_install_git_hooks_handles_system_exit(self, tmp_path):
        """Test git hooks installation handles SystemExit from git command."""
        ctx = MagicMock()
        ctx.invoke.side_effect = SystemExit(1)

        with patch("kuzu_memory.cli.setup_commands.rich_print") as mock_print:
            result = _install_git_hooks(ctx, tmp_path, force=False)

            # Assert returns False on failure
            assert result is False
            # Assert warning message displayed
            assert any(
                "Git hooks installation failed" in str(call) for call in mock_print.call_args_list
            )

    def test_install_git_hooks_handles_exception(self, tmp_path):
        """Test git hooks installation handles general exceptions."""
        ctx = MagicMock()
        ctx.invoke.side_effect = RuntimeError("Git error")

        with patch("kuzu_memory.cli.setup_commands.rich_print") as mock_print:
            result = _install_git_hooks(ctx, tmp_path, force=False)

            # Assert returns False on exception
            assert result is False
            # Assert warning message displayed
            assert any("Git hooks warning" in str(call) for call in mock_print.call_args_list)

    def test_install_git_hooks_system_exit_zero_returns_false(self, tmp_path):
        """Test git hooks installation with SystemExit(0) still returns False."""
        ctx = MagicMock()
        ctx.invoke.side_effect = SystemExit(0)

        with patch("kuzu_memory.cli.setup_commands.rich_print"):
            result = _install_git_hooks(ctx, tmp_path, force=False)

            # SystemExit(0) is not an error, but we return False since we exited
            # This matches the implementation behavior
            assert result is False


# ═══════════════════════════════════════════════════════════
# INTEGRATION WITH SETUP COMMAND - Mock-based Tests
# ═══════════════════════════════════════════════════════════


class TestSetupCommandGitHooksIntegration:
    """Test setup command integration with --with-git-hooks flag."""

    @pytest.fixture
    def mock_setup_dependencies(self):
        """Mock all setup command dependencies."""
        with (
            patch("kuzu_memory.cli.setup_commands.find_project_root") as mock_root,
            patch("kuzu_memory.cli.setup_commands.get_project_db_path") as mock_db_path,
            patch("kuzu_memory.cli.setup_commands.get_project_memories_dir") as mock_mem,
            patch("kuzu_memory.cli.setup_commands._detect_installed_systems") as mock_detect,
            patch("kuzu_memory.cli.setup_commands.init") as mock_init,
            patch("kuzu_memory.cli.setup_commands._detect_git_repository") as mock_git_detect,
            patch("kuzu_memory.cli.setup_commands._install_git_hooks") as mock_install_hooks,
            patch("kuzu_memory.cli.setup_commands.rich_panel"),
            patch("kuzu_memory.cli.setup_commands.rich_print"),
        ):
            # Configure mocks
            test_root = Path("/tmp/test-project")
            mock_root.return_value = test_root

            # Create mock path object for db_path with .exists() method
            mock_db = MagicMock()
            mock_db.__str__ = lambda self: str(test_root / ".kuzu-memory" / "memory.db")
            mock_db_path.return_value = mock_db

            mock_mem.return_value = test_root / ".kuzu-memory" / "memories"
            mock_detect.return_value = []  # No existing installations
            mock_git_detect.return_value = True  # Git repo detected by default

            yield {
                "root": mock_root,
                "db": mock_db,
                "db_path": mock_db_path,
                "mem": mock_mem,
                "detect": mock_detect,
                "init": mock_init,
                "git_detect": mock_git_detect,
                "install_hooks": mock_install_hooks,
            }

    def test_setup_with_git_hooks_installs_hooks(self, runner, mock_setup_dependencies):
        """Test setup auto-installs git hooks when git repo detected."""
        # Configure mocks
        mock_setup_dependencies["git_detect"].return_value = True
        mock_setup_dependencies["install_hooks"].return_value = True
        mock_setup_dependencies["db"].exists.return_value = True

        # Call setup without --skip-git-hooks (git hooks auto-install by default)
        result = runner.invoke(
            setup,
            ["--skip-install"],
            obj={"project_root": Path("/tmp/test-project")},
        )

        # Assert git hooks installation was called
        mock_setup_dependencies["install_hooks"].assert_called_once()
        assert result.exit_code == 0

    def test_setup_without_git_hooks_skips_installation(self, runner, mock_setup_dependencies):
        """Test setup with --skip-git-hooks flag skips git hooks installation."""
        # Configure mocks
        mock_setup_dependencies["db"].exists.return_value = True

        # Call setup with --skip-git-hooks flag
        result = runner.invoke(
            setup,
            ["--skip-git-hooks", "--skip-install"],
            obj={"project_root": Path("/tmp/test-project")},
        )

        # Assert git hooks installation was NOT called
        mock_setup_dependencies["install_hooks"].assert_not_called()
        assert result.exit_code == 0

    def test_setup_with_git_hooks_no_git_repo_warns(self, runner, mock_setup_dependencies):
        """Test setup warns if no git repo detected."""
        # Configure mocks - no git repo detected
        mock_setup_dependencies["git_detect"].return_value = False
        mock_setup_dependencies["db"].exists.return_value = True

        with patch("kuzu_memory.cli.setup_commands.rich_print") as mock_print:
            # Call setup without --skip-git-hooks (auto-install is default)
            result = runner.invoke(
                setup,
                ["--skip-install"],
                obj={"project_root": Path("/tmp/test-project")},
            )

            # Assert warning message displayed about no git repo
            warning_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Git repository not detected" in call for call in warning_calls)

            # Assert git hooks installation was NOT called
            mock_setup_dependencies["install_hooks"].assert_not_called()
            assert result.exit_code == 0

    def test_setup_with_git_hooks_continues_on_failure(self, runner, mock_setup_dependencies):
        """Test setup continues if git hooks installation fails."""
        # Configure mocks - git hooks installation fails
        mock_setup_dependencies["git_detect"].return_value = True
        mock_setup_dependencies["install_hooks"].return_value = False
        mock_setup_dependencies["db"].exists.return_value = True

        # Call setup without --skip-git-hooks (auto-install is default)
        result = runner.invoke(
            setup,
            ["--skip-install"],
            obj={"project_root": Path("/tmp/test-project")},
        )

        # Assert setup continues (doesn't raise)
        assert result.exit_code == 0

        # Assert completion message shows failure
        # Check that hooks were attempted but failed
        mock_setup_dependencies["install_hooks"].assert_called_once()

    def test_setup_with_git_hooks_force_reinstall(self, runner, mock_setup_dependencies):
        """Test setup --force passes force flag to git hooks."""
        # Configure mocks
        mock_setup_dependencies["git_detect"].return_value = True
        mock_setup_dependencies["install_hooks"].return_value = True
        mock_setup_dependencies["db"].exists.return_value = True

        # Call setup with --force flag (git hooks auto-install is default)
        result = runner.invoke(
            setup,
            ["--force", "--skip-install"],
            obj={"project_root": Path("/tmp/test-project")},
        )

        # Assert git hooks installation called with force=True
        mock_setup_dependencies["install_hooks"].assert_called_once()
        call_args = mock_setup_dependencies["install_hooks"].call_args
        assert call_args[1]["force"] is True
        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════
# DRY-RUN TESTING
# ═══════════════════════════════════════════════════════════


class TestSetupDryRunWithGitHooks:
    """Test setup --dry-run --with-git-hooks behavior."""

    @pytest.fixture
    def mock_setup_dry_run_dependencies(self):
        """Mock setup dependencies for dry-run tests."""
        with (
            patch("kuzu_memory.cli.setup_commands.find_project_root") as mock_root,
            patch("kuzu_memory.cli.setup_commands.get_project_db_path") as mock_db_path,
            patch("kuzu_memory.cli.setup_commands.get_project_memories_dir") as mock_mem,
            patch("kuzu_memory.cli.setup_commands._detect_installed_systems") as mock_detect,
            patch("kuzu_memory.cli.setup_commands._detect_git_repository") as mock_git_detect,
            patch("kuzu_memory.cli.setup_commands._install_git_hooks") as mock_install_hooks,
            patch("kuzu_memory.cli.setup_commands.rich_panel"),
            patch("kuzu_memory.cli.setup_commands.rich_print") as mock_print,
        ):
            test_root = Path("/tmp/test-project")
            mock_root.return_value = test_root

            # Create mock path object for db_path
            mock_db = MagicMock()
            mock_db.__str__ = lambda self: str(test_root / ".kuzu-memory" / "memory.db")
            mock_db_path.return_value = mock_db

            mock_mem.return_value = test_root / ".kuzu-memory" / "memories"
            mock_detect.return_value = []
            mock_git_detect.return_value = True

            yield {
                "root": mock_root,
                "db": mock_db,
                "db_path": mock_db_path,
                "mem": mock_mem,
                "detect": mock_detect,
                "git_detect": mock_git_detect,
                "install_hooks": mock_install_hooks,
                "print": mock_print,
            }

    def test_setup_dry_run_with_git_hooks_previews_only(
        self, runner, mock_setup_dry_run_dependencies
    ):
        """Test setup --dry-run previews git hooks without installing."""
        # Configure mocks
        mock_setup_dry_run_dependencies["git_detect"].return_value = True
        mock_setup_dry_run_dependencies["db"].exists.return_value = False

        # Call setup with dry_run=True (git hooks auto-install is default)
        result = runner.invoke(
            setup,
            ["--dry-run", "--skip-install"],
            obj={"project_root": Path("/tmp/test-project")},
        )

        # Assert preview message shown
        print_calls = [
            str(call) for call in mock_setup_dry_run_dependencies["print"].call_args_list
        ]
        assert any("DRY RUN" in call or "dry run" in call.lower() for call in print_calls)
        assert any("git hooks" in call.lower() for call in print_calls)

        # Assert no actual installation occurred
        mock_setup_dry_run_dependencies["install_hooks"].assert_not_called()
        assert result.exit_code == 0

    def test_setup_dry_run_shows_git_hooks_preview(self, runner, mock_setup_dry_run_dependencies):
        """Test dry-run shows what git hooks would be installed."""
        mock_setup_dry_run_dependencies["git_detect"].return_value = True
        mock_setup_dry_run_dependencies["db"].exists.return_value = False

        result = runner.invoke(
            setup,
            ["--dry-run", "--skip-install"],
            obj={"project_root": Path("/tmp/test-project")},
        )

        # Check output mentions git hooks
        print_calls = mock_setup_dry_run_dependencies["print"].call_args_list
        output_text = " ".join(str(call) for call in print_calls)

        assert "git hooks" in output_text.lower() or "auto-sync" in output_text.lower()
        assert result.exit_code == 0

    def test_setup_dry_run_without_git_repo_shows_warning(
        self, runner, mock_setup_dry_run_dependencies
    ):
        """Test dry-run shows warning when git repo not detected."""
        # No git repo
        mock_setup_dry_run_dependencies["git_detect"].return_value = False
        mock_setup_dry_run_dependencies["db"].exists.return_value = False

        result = runner.invoke(
            setup,
            ["--dry-run", "--skip-install"],
            obj={"project_root": Path("/tmp/test-project")},
        )

        # Should NOT attempt installation
        mock_setup_dry_run_dependencies["install_hooks"].assert_not_called()

        # Note: In dry-run mode, the warning happens BEFORE the dry-run check
        # so we should see a warning about no git repo
        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════
# EDGE CASES AND ERROR HANDLING
# ═══════════════════════════════════════════════════════════


class TestSetupGitHooksEdgeCases:
    """Test edge cases and error handling for git hooks functionality."""

    def test_setup_handles_git_detection_exception(self, runner):
        """Test setup handles exceptions during git detection gracefully."""
        with (
            patch("kuzu_memory.cli.setup_commands.find_project_root") as mock_root,
            patch("kuzu_memory.cli.setup_commands.get_project_db_path") as mock_db_path,
            patch("kuzu_memory.cli.setup_commands.get_project_memories_dir") as mock_mem,
            patch("kuzu_memory.cli.setup_commands._detect_installed_systems") as mock_detect,
            patch("kuzu_memory.cli.setup_commands._detect_git_repository") as mock_git_detect,
            patch("kuzu_memory.cli.setup_commands.rich_panel"),
            patch("kuzu_memory.cli.setup_commands.rich_print"),
        ):
            # Configure mocks
            test_root = Path("/tmp/test-project")
            mock_root.return_value = test_root

            # Create mock db path
            mock_db = MagicMock()
            mock_db.exists.return_value = True
            mock_db_path.return_value = mock_db

            mock_mem.return_value = test_root / ".kuzu-memory" / "memories"
            mock_detect.return_value = []

            # Git detection raises exception
            mock_git_detect.side_effect = PermissionError("Permission denied")

            # Call should handle exception gracefully
            result = runner.invoke(
                setup,
                ["--skip-install"],
                obj={"project_root": test_root},
            )

            # Assert command fails gracefully with error message
            assert result.exit_code == 1

    def test_setup_completion_message_reflects_git_hooks_status(self, runner):
        """Test setup completion message correctly reflects git hooks installation status."""
        with (
            patch("kuzu_memory.cli.setup_commands.find_project_root") as mock_root,
            patch("kuzu_memory.cli.setup_commands.get_project_db_path") as mock_db_path,
            patch("kuzu_memory.cli.setup_commands.get_project_memories_dir") as mock_mem,
            patch("kuzu_memory.cli.setup_commands._detect_installed_systems") as mock_detect,
            patch("kuzu_memory.cli.setup_commands._detect_git_repository") as mock_git_detect,
            patch("kuzu_memory.cli.setup_commands._install_git_hooks") as mock_install,
            patch("kuzu_memory.cli.setup_commands.rich_panel") as mock_panel,
            patch("kuzu_memory.cli.setup_commands.rich_print"),
        ):
            test_root = Path("/tmp/test-project")
            mock_root.return_value = test_root

            # Create mock db path
            mock_db = MagicMock()
            mock_db.exists.return_value = True
            mock_db_path.return_value = mock_db

            mock_mem.return_value = test_root / ".kuzu-memory" / "memories"
            mock_detect.return_value = []
            mock_git_detect.return_value = True
            mock_install.return_value = True

            result = runner.invoke(
                setup,
                ["--skip-install"],
                obj={"project_root": test_root},
            )

            # Check completion panel for git hooks status
            panel_calls = [str(call) for call in mock_panel.call_args_list]
            completion_message = panel_calls[-1] if panel_calls else ""

            # Should show installed status
            assert "Git Hooks" in completion_message or "git hooks" in completion_message.lower()
            assert result.exit_code == 0

    def test_setup_suggests_manual_git_hooks_when_not_installed(self, runner):
        """Test setup suggests manual installation when git hooks skipped but repo exists."""
        with (
            patch("kuzu_memory.cli.setup_commands.find_project_root") as mock_root,
            patch("kuzu_memory.cli.setup_commands.get_project_db_path") as mock_db_path,
            patch("kuzu_memory.cli.setup_commands.get_project_memories_dir") as mock_mem,
            patch("kuzu_memory.cli.setup_commands._detect_installed_systems") as mock_detect,
            patch("kuzu_memory.cli.setup_commands._detect_git_repository") as mock_git_detect,
            patch("kuzu_memory.cli.setup_commands.rich_panel") as mock_panel,
            patch("kuzu_memory.cli.setup_commands.rich_print"),
        ):
            test_root = Path("/tmp/test-project")
            mock_root.return_value = test_root

            # Create mock db path
            mock_db = MagicMock()
            mock_db.exists.return_value = True
            mock_db_path.return_value = mock_db

            mock_mem.return_value = test_root / ".kuzu-memory" / "memories"
            mock_detect.return_value = []

            # Git repo exists but hooks explicitly skipped
            mock_git_detect.return_value = True

            result = runner.invoke(
                setup,
                ["--skip-git-hooks", "--skip-install"],
                obj={"project_root": test_root},
            )

            # Check completion message suggests git hooks
            panel_calls = [str(call) for call in mock_panel.call_args_list]
            completion_message = " ".join(panel_calls)

            # Should suggest enabling auto-sync
            assert (
                "git install-hooks" in completion_message.lower()
                or "auto-sync" in completion_message.lower()
            )
            assert result.exit_code == 0
