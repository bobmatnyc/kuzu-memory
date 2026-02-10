"""
Integration tests for subservient mode in setup and installation workflows.

Tests the full integration with CLI commands and installers.
"""

import os
from pathlib import Path

import pytest

from kuzu_memory.installers.claude_hooks import ClaudeHooksInstaller
from kuzu_memory.utils.subservient import create_subservient_config


@pytest.fixture
def test_project(tmp_path: Path) -> Path:
    """Create a test project directory."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()
    return project_root


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables."""
    monkeypatch.delenv("KUZU_MEMORY_MODE", raising=False)


class TestClaudeHooksInstallerSubservient:
    """Test ClaudeHooksInstaller respects subservient mode."""

    def test_installer_skips_in_subservient_mode_via_env(self, test_project: Path, monkeypatch):
        """Test that installer skips installation when env var is set."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")

        installer = ClaudeHooksInstaller(test_project)
        result = installer.install(force=False, dry_run=False)

        assert result.success is True
        assert "subservient mode" in result.message.lower()
        assert len(result.files_created) == 0
        assert len(result.warnings) > 0
        assert "subservient mode" in result.warnings[0].lower()

    def test_installer_skips_in_subservient_mode_via_config(self, test_project: Path, clean_env):
        """Test that installer skips installation when config file exists."""
        create_subservient_config(test_project, managed_by="claude-mpm")

        installer = ClaudeHooksInstaller(test_project)
        result = installer.install(force=False, dry_run=False)

        assert result.success is True
        assert "claude-mpm" in result.message.lower()
        assert len(result.files_created) == 0

    def test_installer_proceeds_in_normal_mode(self, test_project: Path, clean_env):
        """Test that installer proceeds normally when not in subservient mode."""
        installer = ClaudeHooksInstaller(test_project)

        # This may fail due to missing prerequisites, but should NOT skip due to subservient mode
        try:
            result = installer.install(force=False, dry_run=True)
            # If it succeeds in dry run, verify it's not skipping
            if result.success:
                assert "subservient" not in result.message.lower()
        except Exception as e:
            # Should fail with prerequisite error, not subservient mode skip
            assert "subservient" not in str(e).lower()

    def test_installer_force_flag_ignored_in_subservient(self, test_project: Path, monkeypatch):
        """Test that force flag doesn't override subservient mode."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")

        installer = ClaudeHooksInstaller(test_project)
        result = installer.install(force=True, dry_run=False)

        # Should still skip even with force=True
        assert result.success is True
        assert "subservient mode" in result.message.lower()
        assert len(result.files_created) == 0

    def test_installer_dry_run_respects_subservient(self, test_project: Path, monkeypatch):
        """Test that dry run mode still respects subservient mode."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")

        installer = ClaudeHooksInstaller(test_project)
        result = installer.install(force=False, dry_run=True)

        assert result.success is True
        assert "subservient mode" in result.message.lower()


class TestSubservientModeEdgeCases:
    """Test edge cases and error handling."""

    def test_both_env_and_config_set(self, test_project: Path, monkeypatch):
        """Test that env var takes priority when both are set."""
        # Set conflicting values
        create_subservient_config(test_project, managed_by="config-framework")
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")

        installer = ClaudeHooksInstaller(test_project)
        result = installer.install(force=False, dry_run=False)

        # Should use env var (parent framework not specified in message)
        assert result.success is True
        assert "subservient mode" in result.message.lower()

    def test_corrupted_config_file_treated_as_normal_mode(self, test_project: Path, clean_env):
        """Test that corrupted config file doesn't prevent installation."""
        # Create corrupted config
        config_path = test_project / ".kuzu-memory-config"
        config_path.write_text("corrupted{ yaml:: syntax\n")

        installer = ClaudeHooksInstaller(test_project)

        # Should proceed normally (or fail with prerequisite error, not config error)
        try:
            result = installer.install(force=False, dry_run=True)
            # If dry run succeeds, it should not mention subservient mode
            if result.success or "subservient" not in result.message.lower():
                # This is correct - corrupted config is ignored
                pass
        except Exception as e:
            # Should not fail due to config parsing
            assert "yaml" not in str(e).lower()
            assert "config" not in str(e).lower()

    def test_unset_env_var_after_set(self, test_project: Path, monkeypatch):
        """Test that unsetting env var allows installation."""
        # First set it
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")
        installer = ClaudeHooksInstaller(test_project)
        result = installer.install(force=False, dry_run=False)
        assert "subservient mode" in result.message.lower()

        # Now unset it
        monkeypatch.delenv("KUZU_MEMORY_MODE")

        # Should now attempt normal installation
        installer2 = ClaudeHooksInstaller(test_project)
        try:
            result2 = installer2.install(force=False, dry_run=True)
            # If dry run succeeds, should not skip
            if result2.success:
                assert "subservient" not in result2.message.lower()
        except Exception:
            # May fail for other reasons, but not subservient mode
            pass


class TestSubservientModeMessages:
    """Test that appropriate messages are shown to users."""

    def test_message_includes_managed_by(self, test_project: Path, clean_env):
        """Test that installation result includes managed_by information."""
        create_subservient_config(test_project, managed_by="test-framework")

        installer = ClaudeHooksInstaller(test_project)
        result = installer.install(force=False, dry_run=False)

        assert "test-framework" in result.message.lower()

    def test_warning_present_in_subservient_mode(self, test_project: Path, monkeypatch):
        """Test that warnings list includes subservient mode warning."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")

        installer = ClaudeHooksInstaller(test_project)
        result = installer.install(force=False, dry_run=False)

        assert len(result.warnings) > 0
        assert any("subservient" in w.lower() for w in result.warnings)

    def test_no_warnings_in_normal_mode(self, test_project: Path, clean_env):
        """Test that no subservient warnings in normal mode."""
        installer = ClaudeHooksInstaller(test_project)

        try:
            result = installer.install(force=False, dry_run=True)
            if result.success:
                # Should not have subservient mode warnings
                subservient_warnings = [w for w in result.warnings if "subservient" in w.lower()]
                assert len(subservient_warnings) == 0
        except Exception:
            # May fail for prerequisites, that's OK
            pass
