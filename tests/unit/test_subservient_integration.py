"""
Tests for subservient mode integration utilities.

Tests the convenience functions for parent frameworks to enable and manage
subservient mode programmatically.
"""

import os
from pathlib import Path

import pytest
from kuzu_memory.utils.subservient import (
    create_subservient_config,
    enable_subservient_mode,
    is_subservient_mode,
    remove_subservient_config,
)


class TestEnableSubservientMode:
    """Test enable_subservient_mode convenience function."""

    def test_enable_subservient_mode_creates_config(self, tmp_path: Path) -> None:
        """Test that enable_subservient_mode creates config file."""
        result = enable_subservient_mode(
            project_root=tmp_path, managed_by="test-framework"
        )

        assert result["success"] is True
        assert "config_path" in result
        assert result["env_var_set"] is False

        # Verify config file exists
        config_path = Path(result["config_path"])
        assert config_path.exists()
        assert config_path.name == ".kuzu-memory-config"

        # Verify subservient mode is detected
        assert is_subservient_mode(tmp_path) is True

    def test_enable_subservient_mode_with_string_path(self, tmp_path: Path) -> None:
        """Test enable_subservient_mode accepts string path."""
        result = enable_subservient_mode(
            project_root=str(tmp_path),
            managed_by="test-framework",  # String instead of Path
        )

        assert result["success"] is True
        assert is_subservient_mode(tmp_path) is True

    def test_enable_subservient_mode_with_env_var(self, tmp_path: Path) -> None:
        """Test enable_subservient_mode can set environment variable."""
        # Clear any existing env var
        os.environ.pop("KUZU_MEMORY_MODE", None)

        result = enable_subservient_mode(
            project_root=tmp_path, managed_by="test-framework", set_env_var=True
        )

        assert result["success"] is True
        assert result["env_var_set"] is True

        # Verify environment variable is set
        assert os.getenv("KUZU_MEMORY_MODE") == "subservient"

        # Verify detection via env var
        assert is_subservient_mode() is True

        # Cleanup
        os.environ.pop("KUZU_MEMORY_MODE", None)

    def test_enable_subservient_mode_custom_managed_by(self, tmp_path: Path) -> None:
        """Test enable_subservient_mode with custom managed_by value."""
        result = enable_subservient_mode(project_root=tmp_path, managed_by="claude-mpm")

        assert result["success"] is True

        # Verify managed_by is stored in config
        import yaml

        config_path = Path(result["config_path"])
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["managed_by"] == "claude-mpm"
        assert config["mode"] == "subservient"

    def test_enable_subservient_mode_nonexistent_path(self) -> None:
        """Test enable_subservient_mode raises error for nonexistent path."""
        with pytest.raises(ValueError, match="does not exist"):
            enable_subservient_mode(project_root="/nonexistent/path", managed_by="test")

    def test_enable_subservient_mode_file_not_directory(self, tmp_path: Path) -> None:
        """Test enable_subservient_mode raises error when path is a file."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="not a directory"):
            enable_subservient_mode(project_root=file_path, managed_by="test")

    def test_enable_subservient_mode_invalid_type(self) -> None:
        """Test enable_subservient_mode raises error for invalid path type."""
        with pytest.raises(ValueError, match="must be Path or str"):
            enable_subservient_mode(project_root=123, managed_by="test")  # type: ignore

    def test_enable_subservient_mode_default_managed_by(self, tmp_path: Path) -> None:
        """Test enable_subservient_mode uses default managed_by."""
        result = enable_subservient_mode(project_root=tmp_path)

        assert result["success"] is True

        # Verify default managed_by is "unknown"
        import yaml

        config_path = Path(result["config_path"])
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["managed_by"] == "unknown"


class TestSubservientModeIntegration:
    """Test complete subservient mode integration workflows."""

    def test_enable_and_detect_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow: enable -> detect -> verify."""
        # Initially not in subservient mode
        assert is_subservient_mode(tmp_path) is False

        # Enable subservient mode
        result = enable_subservient_mode(
            project_root=tmp_path, managed_by="integration-test"
        )
        assert result["success"] is True

        # Verify detection works
        assert is_subservient_mode(tmp_path) is True

        # Verify config file exists
        config_path = tmp_path / ".kuzu-memory-config"
        assert config_path.exists()

    def test_enable_disable_workflow(self, tmp_path: Path) -> None:
        """Test enable -> disable workflow."""
        # Enable
        enable_subservient_mode(tmp_path, managed_by="test")
        assert is_subservient_mode(tmp_path) is True

        # Disable
        removed = remove_subservient_config(tmp_path)
        assert removed is True

        # Verify disabled
        assert is_subservient_mode(tmp_path) is False

    def test_multiple_enable_calls_idempotent(self, tmp_path: Path) -> None:
        """Test multiple enable_subservient_mode calls are safe."""
        # First enable
        result1 = enable_subservient_mode(tmp_path, managed_by="framework-1")
        assert result1["success"] is True

        # Second enable (overwrites)
        result2 = enable_subservient_mode(tmp_path, managed_by="framework-2")
        assert result2["success"] is True

        # Verify latest managed_by value
        import yaml

        config_path = Path(result2["config_path"])
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["managed_by"] == "framework-2"

    def test_env_var_takes_precedence_over_config(self, tmp_path: Path) -> None:
        """Test environment variable takes precedence over config file."""
        # No config file, no env var
        assert is_subservient_mode(tmp_path) is False

        # Create config file
        create_subservient_config(tmp_path, managed_by="config")
        assert is_subservient_mode(tmp_path) is True

        # Set env var (should override config)
        os.environ["KUZU_MEMORY_MODE"] = "subservient"
        try:
            # Detection should work even without project_root
            assert is_subservient_mode() is True

            # Still works with project_root
            assert is_subservient_mode(tmp_path) is True
        finally:
            os.environ.pop("KUZU_MEMORY_MODE", None)


class TestParentFrameworkScenarios:
    """Test scenarios for parent frameworks (like Claude MPM)."""

    def test_mpm_setup_workflow(self, tmp_path: Path) -> None:
        """Test workflow for Claude MPM setup phase."""
        # Simulate MPM setup command
        project_root = tmp_path

        # 1. Enable subservient mode
        result = enable_subservient_mode(
            project_root=project_root, managed_by="claude-mpm"
        )
        assert result["success"] is True

        # 2. Verify subservient mode is active
        assert is_subservient_mode(project_root) is True

        # 3. MPM would now install its own centralized hooks
        # (not tested here, but this is where MPM would do it)

        # 4. Verify config file contains correct metadata
        import yaml

        config_path = Path(result["config_path"])
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["mode"] == "subservient"
        assert config["managed_by"] == "claude-mpm"
        assert "version" in config

    def test_custom_framework_with_env_var(self, tmp_path: Path) -> None:
        """Test custom framework using environment variable strategy."""
        # Framework sets env var globally
        os.environ["KUZU_MEMORY_MODE"] = "subservient"

        try:
            # Detection works without config file
            assert is_subservient_mode(tmp_path) is True

            # Framework can still create config for documentation
            enable_subservient_mode(
                project_root=tmp_path,
                managed_by="custom-framework",
                set_env_var=False,  # Already set
            )

            # Both methods detect subservient mode
            assert is_subservient_mode(tmp_path) is True
        finally:
            os.environ.pop("KUZU_MEMORY_MODE", None)

    def test_framework_cleanup_on_uninstall(self, tmp_path: Path) -> None:
        """Test framework cleanup workflow when uninstalling."""
        # Setup
        enable_subservient_mode(tmp_path, managed_by="framework")
        assert is_subservient_mode(tmp_path) is True

        # Framework uninstalls
        removed = remove_subservient_config(tmp_path)
        assert removed is True

        # Verify cleanup
        assert is_subservient_mode(tmp_path) is False
        config_path = tmp_path / ".kuzu-memory-config"
        assert not config_path.exists()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_enable_with_permission_error(self, tmp_path: Path) -> None:
        """Test enable_subservient_mode handles permission errors."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        # Make directory read-only (may not work on all systems)
        try:
            readonly_dir.chmod(0o444)

            with pytest.raises(OSError):
                enable_subservient_mode(project_root=readonly_dir, managed_by="test")
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_is_subservient_mode_with_malformed_config(self, tmp_path: Path) -> None:
        """Test is_subservient_mode handles malformed config gracefully."""
        # Create malformed config file
        config_path = tmp_path / ".kuzu-memory-config"
        config_path.write_text("invalid: yaml: content: [")

        # Should return False and not crash
        assert is_subservient_mode(tmp_path) is False

    def test_is_subservient_mode_with_non_dict_config(self, tmp_path: Path) -> None:
        """Test is_subservient_mode handles non-dict YAML."""
        # Create config with non-dict content
        config_path = tmp_path / ".kuzu-memory-config"
        config_path.write_text("just a string")

        # Should return False
        assert is_subservient_mode(tmp_path) is False

    def test_env_var_with_alternative_values(self) -> None:
        """Test that alternative env var values are recognized."""
        # Test "managed" alias
        os.environ["KUZU_MEMORY_MODE"] = "managed"
        try:
            assert is_subservient_mode() is True
        finally:
            os.environ.pop("KUZU_MEMORY_MODE", None)

        # Test "delegated" alias
        os.environ["KUZU_MEMORY_MODE"] = "delegated"
        try:
            assert is_subservient_mode() is True
        finally:
            os.environ.pop("KUZU_MEMORY_MODE", None)

        # Test case insensitivity
        os.environ["KUZU_MEMORY_MODE"] = "SUBSERVIENT"
        try:
            assert is_subservient_mode() is True
        finally:
            os.environ.pop("KUZU_MEMORY_MODE", None)
