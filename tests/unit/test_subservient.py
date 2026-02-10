"""
Unit tests for subservient mode detection utilities.

Tests environment variable detection, config file parsing,
and edge cases for subservient mode functionality.
"""

import os
from pathlib import Path

import pytest
import yaml
from kuzu_memory.utils.subservient import (
    create_subservient_config,
    get_subservient_config,
    is_subservient_mode,
    remove_subservient_config,
)


@pytest.fixture
def mock_project_root(tmp_path: Path) -> Path:
    """Create a temporary project root directory."""
    return tmp_path


@pytest.fixture
def clean_env(monkeypatch):
    """Clean up environment variables before each test."""
    # Remove any existing KUZU_MEMORY_MODE
    monkeypatch.delenv("KUZU_MEMORY_MODE", raising=False)


class TestIsSubservientMode:
    """Tests for is_subservient_mode() function."""

    def test_not_subservient_by_default(self, mock_project_root: Path, clean_env):
        """Test that default mode is not subservient."""
        assert is_subservient_mode(mock_project_root) is False

    def test_env_var_subservient(self, mock_project_root: Path, monkeypatch):
        """Test detection via KUZU_MEMORY_MODE=subservient."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")
        assert is_subservient_mode(mock_project_root) is True

    def test_env_var_managed(self, mock_project_root: Path, monkeypatch):
        """Test detection via KUZU_MEMORY_MODE=managed."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "managed")
        assert is_subservient_mode(mock_project_root) is True

    def test_env_var_delegated(self, mock_project_root: Path, monkeypatch):
        """Test detection via KUZU_MEMORY_MODE=delegated."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "delegated")
        assert is_subservient_mode(mock_project_root) is True

    def test_env_var_case_insensitive(self, mock_project_root: Path, monkeypatch):
        """Test that environment variable detection is case-insensitive."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "SUBSERVIENT")
        assert is_subservient_mode(mock_project_root) is True

        monkeypatch.setenv("KUZU_MEMORY_MODE", "Managed")
        assert is_subservient_mode(mock_project_root) is True

    def test_env_var_invalid_value(self, mock_project_root: Path, monkeypatch):
        """Test that invalid env var values are ignored."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "invalid")
        assert is_subservient_mode(mock_project_root) is False

    def test_config_file_subservient(self, mock_project_root: Path, clean_env):
        """Test detection via .kuzu-memory-config file."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("mode: subservient\nmanaged_by: test\n")

        assert is_subservient_mode(mock_project_root) is True

    def test_config_file_managed(self, mock_project_root: Path, clean_env):
        """Test detection via .kuzu-memory-config with mode=managed."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("mode: managed\nmanaged_by: test\n")

        assert is_subservient_mode(mock_project_root) is True

    def test_config_file_invalid_mode(self, mock_project_root: Path, clean_env):
        """Test that invalid mode in config file is ignored."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("mode: invalid\n")

        assert is_subservient_mode(mock_project_root) is False

    def test_env_var_priority_over_config(self, mock_project_root: Path, monkeypatch):
        """Test that environment variable takes priority over config file."""
        # Create config file with mode=normal
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("mode: normal\n")

        # Set env var to subservient
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")

        # Env var should take priority
        assert is_subservient_mode(mock_project_root) is True

    def test_no_project_root_provided(self, clean_env):
        """Test that function returns False when no project root provided."""
        assert is_subservient_mode(None) is False

    def test_env_var_without_project_root(self, monkeypatch):
        """Test that env var works without project root."""
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")
        assert is_subservient_mode(None) is True


class TestGetSubservientConfig:
    """Tests for get_subservient_config() function."""

    def test_no_config_file(self, mock_project_root: Path):
        """Test that None is returned when config file doesn't exist."""
        result = get_subservient_config(mock_project_root)
        assert result is None

    def test_valid_config_subservient(self, mock_project_root: Path):
        """Test parsing valid subservient config."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text(
            "mode: subservient\nmanaged_by: claude-mpm\nversion: '1.0'\n"
        )

        result = get_subservient_config(mock_project_root)
        assert result is not None
        assert result["mode"] == "subservient"
        assert result["managed_by"] == "claude-mpm"
        assert result["version"] == "1.0"

    def test_valid_config_managed(self, mock_project_root: Path):
        """Test parsing valid managed config."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("mode: managed\nmanaged_by: test-framework\n")

        result = get_subservient_config(mock_project_root)
        assert result is not None
        assert result["mode"] == "managed"
        assert result["managed_by"] == "test-framework"

    def test_config_missing_managed_by(self, mock_project_root: Path):
        """Test that default managed_by is used when not specified."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("mode: subservient\n")

        result = get_subservient_config(mock_project_root)
        assert result is not None
        assert result["managed_by"] == "unknown"

    def test_config_invalid_yaml(self, mock_project_root: Path):
        """Test that invalid YAML returns None."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("invalid: yaml: syntax::\n")

        result = get_subservient_config(mock_project_root)
        assert result is None

    def test_config_not_dict(self, mock_project_root: Path):
        """Test that non-dict YAML returns None."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("- list\n- of\n- items\n")

        result = get_subservient_config(mock_project_root)
        assert result is None

    def test_config_wrong_mode(self, mock_project_root: Path):
        """Test that wrong mode value returns None."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("mode: normal\n")

        result = get_subservient_config(mock_project_root)
        assert result is None

    def test_config_case_insensitive_mode(self, mock_project_root: Path):
        """Test that mode value is case-insensitive."""
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("mode: SUBSERVIENT\nmanaged_by: test\n")

        result = get_subservient_config(mock_project_root)
        assert result is not None
        assert result["mode"] == "subservient"


class TestCreateSubservientConfig:
    """Tests for create_subservient_config() function."""

    def test_create_config_default_managed_by(self, mock_project_root: Path):
        """Test creating config with default managed_by."""
        config_path = create_subservient_config(mock_project_root)

        assert config_path.exists()
        assert config_path == mock_project_root / ".kuzu-memory-config"

        # Verify contents
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["mode"] == "subservient"
        assert config["managed_by"] == "unknown"
        assert config["version"] == "1.0"

    def test_create_config_custom_managed_by(self, mock_project_root: Path):
        """Test creating config with custom managed_by."""
        config_path = create_subservient_config(
            mock_project_root, managed_by="claude-mpm"
        )

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["managed_by"] == "claude-mpm"

    def test_create_config_overwrite_existing(self, mock_project_root: Path):
        """Test that creating config overwrites existing file."""
        # Create initial config
        create_subservient_config(mock_project_root, managed_by="old-framework")

        # Overwrite with new config
        config_path = create_subservient_config(
            mock_project_root, managed_by="new-framework"
        )

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["managed_by"] == "new-framework"

    def test_create_config_yaml_format(self, mock_project_root: Path):
        """Test that created config is valid YAML."""
        config_path = create_subservient_config(mock_project_root, managed_by="test")

        # Verify it's valid YAML by parsing
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert isinstance(config, dict)
        assert "mode" in config
        assert "managed_by" in config
        assert "version" in config


class TestRemoveSubservientConfig:
    """Tests for remove_subservient_config() function."""

    def test_remove_existing_config(self, mock_project_root: Path):
        """Test removing existing config file."""
        # Create config
        create_subservient_config(mock_project_root)

        # Remove it
        result = remove_subservient_config(mock_project_root)

        assert result is True
        assert not (mock_project_root / ".kuzu-memory-config").exists()

    def test_remove_nonexistent_config(self, mock_project_root: Path):
        """Test removing config when it doesn't exist."""
        result = remove_subservient_config(mock_project_root)

        assert result is False


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def test_mpm_installation_scenario(self, mock_project_root: Path, monkeypatch):
        """Test typical MPM installation scenario."""
        # MPM sets environment variable during installation
        monkeypatch.setenv("KUZU_MEMORY_MODE", "subservient")

        # Creates config file
        create_subservient_config(mock_project_root, managed_by="claude-mpm")

        # Both detection methods should work
        assert is_subservient_mode(mock_project_root) is True

        config = get_subservient_config(mock_project_root)
        assert config is not None
        assert config["managed_by"] == "claude-mpm"

    def test_manual_installation_after_mpm(self, mock_project_root: Path):
        """Test manual installation after removing MPM."""
        # Initial MPM installation
        create_subservient_config(mock_project_root, managed_by="claude-mpm")
        assert is_subservient_mode(mock_project_root) is True

        # User removes config to switch to manual mode
        remove_subservient_config(mock_project_root)
        assert is_subservient_mode(mock_project_root) is False

    def test_config_file_corruption_handling(self, mock_project_root: Path):
        """Test that corrupted config files are handled gracefully."""
        # Create corrupted config
        config_path = mock_project_root / ".kuzu-memory-config"
        config_path.write_text("corrupted{ yaml:: syntax\n")

        # Should return False (fail-safe to normal mode)
        assert is_subservient_mode(mock_project_root) is False
        assert get_subservient_config(mock_project_root) is None
