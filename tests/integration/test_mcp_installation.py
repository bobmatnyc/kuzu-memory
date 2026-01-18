"""
Integration tests for MCP installation system.

Tests end-to-end workflows including detection, installation, and configuration merging.
"""

import json
from pathlib import Path

import pytest

from kuzu_memory.installers.detection import AISystemDetector, detect_ai_systems
from kuzu_memory.installers.registry import get_installer


class TestAISystemDetection:
    """Test AI system auto-detection."""

    def test_detect_no_systems(self, tmp_path, monkeypatch):
        """Test detection in empty project."""
        # Mock home directory to avoid detecting global installations
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        detector = AISystemDetector(tmp_path)

        systems = detector.detect_all()

        # Should detect all possible systems but none installed
        assert len(systems) > 0
        installed = [s for s in systems if s.exists]
        assert len(installed) == 0

    def test_detect_cursor_project(self, tmp_path):
        """Test detection of Cursor project."""
        # Create Cursor directory
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        detector = AISystemDetector(tmp_path)
        systems = detector.detect_all()

        cursor_systems = [s for s in systems if "cursor" in s.installer_name.lower()]
        assert len(cursor_systems) > 0

        # Should be marked as can_install
        cursor = next(s for s in cursor_systems if s.config_type == "project")
        assert cursor.can_install

    def test_detect_vscode_project(self, tmp_path):
        """Test detection of VS Code project."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()

        detector = AISystemDetector(tmp_path)
        systems = detector.detect_available()

        vscode = next((s for s in systems if s.installer_name == "vscode"), None)
        assert vscode is not None
        assert vscode.can_install

    def test_detect_multiple_systems(self, tmp_path):
        """Test detection of multiple systems."""
        # Create multiple system directories
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".vscode").mkdir()

        detector = AISystemDetector(tmp_path)
        available = detector.detect_available()

        # Should detect both
        installer_names = [s.installer_name for s in available]
        assert "cursor" in installer_names
        assert "vscode" in installer_names

    def test_detect_installed_systems(self, tmp_path):
        """Test detection of systems with existing configs."""
        # Create Cursor with config
        cursor_config = tmp_path / ".cursor" / "mcp.json"
        cursor_config.parent.mkdir()
        cursor_config.write_text("{}")

        detector = AISystemDetector(tmp_path)
        installed = detector.detect_installed()

        # Should find Cursor as installed
        cursor = next((s for s in installed if s.installer_name == "cursor"), None)
        assert cursor is not None
        assert cursor.exists

    def test_detect_recommended_systems(self, tmp_path):
        """Test getting recommended systems to install."""
        # Create directory but no config
        (tmp_path / ".cursor").mkdir()

        # Create config for VS Code (already installed)
        vscode_config = tmp_path / ".vscode" / "mcp.json"
        vscode_config.parent.mkdir()
        vscode_config.write_text("{}")

        detector = AISystemDetector(tmp_path)
        recommended = detector.get_recommended_systems()

        # Cursor should be recommended (dir exists, no config)
        cursor = next((s for s in recommended if s.installer_name == "cursor"), None)
        assert cursor is not None

        # VS Code should NOT be recommended (already has config)
        vscode = next((s for s in recommended if s.installer_name == "vscode"), None)
        assert vscode is None

    def test_detect_ai_systems_function(self, tmp_path):
        """Test convenience function for detection."""
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".vscode").mkdir()

        systems = detect_ai_systems(tmp_path)

        assert isinstance(systems, list)
        assert "cursor" in systems
        assert "vscode" in systems


class TestEndToEndInstallation:
    """Test complete installation workflows."""

    def test_install_cursor_in_empty_project(self, tmp_path):
        """Test installing Cursor in empty project."""
        installer = get_installer("cursor", tmp_path)
        assert installer is not None

        result = installer.install()

        assert result.success
        assert result.ai_system == "Cursor IDE"

        # Verify file created
        config_path = tmp_path / ".cursor" / "mcp.json"
        assert config_path.exists()

        # Verify valid JSON
        with open(config_path) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "kuzu-memory" in config["mcpServers"]

    def test_install_multiple_systems(self, tmp_path):
        """Test installing multiple systems in same project."""
        # Install Cursor
        cursor = get_installer("cursor", tmp_path)
        cursor_result = cursor.install()
        assert cursor_result.success

        # Install VS Code
        vscode = get_installer("vscode", tmp_path)
        vscode_result = vscode.install()
        assert vscode_result.success

        # Both configs should exist independently
        assert (tmp_path / ".cursor" / "mcp.json").exists()
        assert (tmp_path / ".vscode" / "mcp.json").exists()

    def test_install_preserves_unrelated_config(self, tmp_path):
        """Test that installation preserves unrelated configuration."""
        # Create Cursor config with extra settings
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir()

        original_config = {
            "mcpServers": {"other-server": {"command": "other"}},
            "otherSettings": {"theme": "dark"},
        }

        with open(config_path, "w") as f:
            json.dump(original_config, f)

        # Install KuzuMemory
        installer = get_installer("cursor", tmp_path)
        result = installer.install()

        assert result.success

        # Verify everything preserved
        with open(config_path) as f:
            config = json.load(f)

        assert "otherSettings" in config
        assert config["otherSettings"]["theme"] == "dark"
        assert "other-server" in config["mcpServers"]
        assert "kuzu-memory" in config["mcpServers"]

    def test_sequential_installations_preserve_order(self, tmp_path):
        """Test that multiple installations preserve each other."""
        config_path = tmp_path / ".cursor" / "mcp.json"

        # First installation
        installer1 = get_installer("cursor", tmp_path)
        result1 = installer1.install()
        assert result1.success

        # Manually add another server
        with open(config_path) as f:
            config = json.load(f)

        config["mcpServers"]["manual-server"] = {"command": "manual"}

        with open(config_path, "w") as f:
            json.dump(config, f)

        # Second installation (force mode)
        installer2 = get_installer("cursor", tmp_path)
        result2 = installer2.install(force=False)
        assert result2.success

        # All servers should still be present
        with open(config_path) as f:
            final_config = json.load(f)

        assert "kuzu-memory" in final_config["mcpServers"]
        assert "manual-server" in final_config["mcpServers"]

    def test_dry_run_workflow(self, tmp_path):
        """Test dry-run workflow."""
        # Create existing config
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir()

        existing = {"mcpServers": {"existing": {"command": "cmd"}}}
        with open(config_path, "w") as f:
            json.dump(existing, f)

        # Dry run
        installer = get_installer("cursor", tmp_path)
        result = installer.install(dry_run=True)

        assert result.success
        assert "[DRY RUN]" in result.message

        # Config should be unchanged
        with open(config_path) as f:
            config = json.load(f)

        assert config == existing
        assert "kuzu-memory" not in config.get("mcpServers", {})

    def test_install_with_verbose_output(self, tmp_path):
        """Test installation with verbose mode."""
        installer = get_installer("cursor", tmp_path)
        result = installer.install(verbose=True)

        assert result.success

        # Should have created files
        assert len(result.files_created) > 0

    def test_backup_restoration(self, tmp_path):
        """Test that backups can be used for restoration."""
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir()

        # Original config
        original = {"mcpServers": {"original": {"command": "original"}}}
        with open(config_path, "w") as f:
            json.dump(original, f)

        # Install (creates backup)
        installer = get_installer("cursor", tmp_path)
        result = installer.install()

        assert result.success
        assert len(result.backup_files) > 0

        # Verify backup exists
        backup_file = result.backup_files[0]
        assert backup_file.exists()

        # Backup should contain original config
        with open(backup_file) as f:
            backup_config = json.load(f)

        assert "original" in backup_config["mcpServers"]
        assert "kuzu-memory" not in backup_config.get("mcpServers", {})


class TestCrossSystemCompatibility:
    """Test compatibility across different AI systems."""

    def test_same_mcp_config_in_different_systems(self, tmp_path):
        """Test that KuzuMemory config is consistent across systems."""
        # Install in both Cursor and VS Code
        cursor = get_installer("cursor", tmp_path)
        vscode = get_installer("vscode", tmp_path)

        cursor.install()
        vscode.install()

        # Load both configs
        with open(tmp_path / ".cursor" / "mcp.json") as f:
            cursor_config = json.load(f)

        with open(tmp_path / ".vscode" / "mcp.json") as f:
            vscode_config = json.load(f)

        # KuzuMemory server config should be identical
        cursor_kuzu = cursor_config["mcpServers"]["kuzu-memory"]
        vscode_kuzu = vscode_config["mcpServers"]["kuzu-memory"]

        assert cursor_kuzu["command"] == vscode_kuzu["command"]
        assert cursor_kuzu.get("args") == vscode_kuzu.get("args")

    def test_project_specific_vs_global_configs(self, tmp_path, monkeypatch):
        """Test difference between project-specific and global configs."""
        # Mock home for Windsurf
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        (fake_home / ".codeium" / "windsurf").mkdir(parents=True)

        # Install project-specific (Cursor)
        cursor = get_installer("cursor", tmp_path)
        cursor_result = cursor.install()

        # Install global (Windsurf)
        windsurf = get_installer("windsurf", tmp_path)
        windsurf_result = windsurf.install()

        assert cursor_result.success
        assert windsurf_result.success

        # Project-specific should be in project
        assert (tmp_path / ".cursor" / "mcp.json").exists()

        # Global should be in home
        assert (fake_home / ".codeium" / "windsurf" / "mcp_config.json").exists()

        # And NOT in project
        assert not (tmp_path / ".codeium" / "windsurf" / "mcp_config.json").exists()
