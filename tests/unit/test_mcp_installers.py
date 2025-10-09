"""
Unit tests for MCP installers (Cursor, VSCode, Windsurf).
"""

import json
from pathlib import Path

import pytest

from kuzu_memory.installers.cursor_installer import CursorInstaller
from kuzu_memory.installers.vscode_installer import VSCodeInstaller
from kuzu_memory.installers.windsurf_installer import WindsurfInstaller


class TestCursorInstaller:
    """Test Cursor IDE MCP installer."""

    def test_installer_properties(self, tmp_path):
        """Test installer basic properties."""
        installer = CursorInstaller(tmp_path)

        assert installer.ai_system_name == "Cursor IDE"
        assert ".cursor/mcp.json" in installer.required_files
        assert "project-specific" in installer.description.lower()

    def test_install_creates_config(self, tmp_path):
        """Test installation creates MCP configuration."""
        installer = CursorInstaller(tmp_path)

        result = installer.install(force=False, dry_run=False)

        assert result.success
        assert len(result.files_created) > 0

        # Check config file exists
        config_path = tmp_path / ".cursor" / "mcp.json"
        assert config_path.exists()

        # Check config content
        with open(config_path) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "kuzu-memory" in config["mcpServers"]
        assert config["mcpServers"]["kuzu-memory"]["command"] == "kuzu-memory"

    def test_install_preserves_existing_servers(self, tmp_path):
        """Test that existing MCP servers are preserved."""
        # Create existing configuration
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        existing_config = {
            "mcpServers": {"existing-server": {"command": "existing-cmd"}}
        }

        with open(config_path, "w") as f:
            json.dump(existing_config, f)

        # Install
        installer = CursorInstaller(tmp_path)
        result = installer.install(force=False)

        assert result.success

        # Check both servers exist
        with open(config_path) as f:
            config = json.load(f)

        assert "existing-server" in config["mcpServers"]
        assert "kuzu-memory" in config["mcpServers"]
        assert config["mcpServers"]["existing-server"]["command"] == "existing-cmd"

    def test_install_dry_run(self, tmp_path):
        """Test dry-run mode doesn't create files."""
        installer = CursorInstaller(tmp_path)

        result = installer.install(dry_run=True)

        assert result.success
        assert "[DRY RUN]" in result.message

        # No files should be created
        config_path = tmp_path / ".cursor" / "mcp.json"
        assert not config_path.exists()

    def test_install_force_mode(self, tmp_path):
        """Test force mode overwrites existing configuration."""
        # Create existing configuration
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        existing_config = {"mcpServers": {"old-server": {"command": "old"}}}

        with open(config_path, "w") as f:
            json.dump(existing_config, f)

        # Install with force
        installer = CursorInstaller(tmp_path)
        result = installer.install(force=True)

        assert result.success
        assert len(result.backup_files) > 0  # Backup should be created

    def test_install_creates_backup(self, tmp_path):
        """Test that backups are created for existing files."""
        # Create existing configuration
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        with open(config_path, "w") as f:
            json.dump({"test": "data"}, f)

        # Install (will modify existing)
        installer = CursorInstaller(tmp_path)
        result = installer.install()

        # Check backup was created
        backup_dir = tmp_path / ".kuzu-memory-backups"
        assert backup_dir.exists()

        backup_files = list(backup_dir.glob("mcp.json.backup_*"))
        assert len(backup_files) > 0


class TestVSCodeInstaller:
    """Test VS Code MCP installer."""

    def test_installer_properties(self, tmp_path):
        """Test installer basic properties."""
        installer = VSCodeInstaller(tmp_path)

        assert installer.ai_system_name == "VS Code (Claude Extension)"
        assert ".vscode/mcp.json" in installer.required_files
        assert "project-specific" in installer.description.lower()

    def test_install_creates_config(self, tmp_path):
        """Test installation creates MCP configuration."""
        installer = VSCodeInstaller(tmp_path)

        result = installer.install()

        assert result.success

        # Check config file exists
        config_path = tmp_path / ".vscode" / "mcp.json"
        assert config_path.exists()

        # Check config content
        with open(config_path) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "kuzu-memory" in config["mcpServers"]

    def test_normalize_vscode_format(self, tmp_path):
        """Test VS Code 'servers' format is normalized."""
        # Create VS Code format config
        config_path = tmp_path / ".vscode" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        vscode_config = {"servers": {"existing": {"command": "cmd"}}}

        with open(config_path, "w") as f:
            json.dump(vscode_config, f)

        # Install
        installer = VSCodeInstaller(tmp_path)
        result = installer.install()

        assert result.success

        # Check format was normalized
        with open(config_path) as f:
            config = json.load(f)

        # Should use mcpServers now
        assert "mcpServers" in config
        assert "existing" in config["mcpServers"]
        assert "kuzu-memory" in config["mcpServers"]

    def test_install_preserves_existing_servers(self, tmp_path):
        """Test that existing MCP servers are preserved."""
        config_path = tmp_path / ".vscode" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        existing_config = {
            "mcpServers": {"github-mcp": {"command": "github-mcp-server"}}
        }

        with open(config_path, "w") as f:
            json.dump(existing_config, f)

        # Install
        installer = VSCodeInstaller(tmp_path)
        result = installer.install()

        assert result.success

        # Both servers should exist
        with open(config_path) as f:
            config = json.load(f)

        assert "github-mcp" in config["mcpServers"]
        assert "kuzu-memory" in config["mcpServers"]


class TestWindsurfInstaller:
    """Test Windsurf IDE MCP installer."""

    def test_installer_properties(self, tmp_path):
        """Test installer basic properties."""
        installer = WindsurfInstaller(tmp_path)

        assert installer.ai_system_name == "Windsurf IDE"
        assert ".codeium/windsurf/mcp_config.json" in installer.required_files
        assert "global" in installer.description.lower()

    def test_install_uses_home_directory(self, tmp_path, monkeypatch):
        """Test that Windsurf installs to home directory."""
        # Mock home directory
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Create Windsurf directory
        windsurf_dir = fake_home / ".codeium" / "windsurf"
        windsurf_dir.mkdir(parents=True)

        # Install (use tmp_path as project root, but config goes to home)
        installer = WindsurfInstaller(tmp_path)
        result = installer.install()

        assert result.success

        # Config should be in home directory, not project
        config_path = fake_home / ".codeium" / "windsurf" / "mcp_config.json"
        assert config_path.exists()

        # Project directory should NOT have config
        project_config = tmp_path / ".codeium" / "windsurf" / "mcp_config.json"
        assert not project_config.exists()

    def test_install_with_custom_project(self, tmp_path, monkeypatch):
        """Test installation with custom project path."""
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        windsurf_dir = fake_home / ".codeium" / "windsurf"
        windsurf_dir.mkdir(parents=True)

        custom_project = tmp_path / "my_project"
        custom_project.mkdir()

        # Install with custom project
        installer = WindsurfInstaller(tmp_path)
        result = installer.install(project_path=str(custom_project))

        assert result.success

        # Check env includes project path
        config_path = fake_home / ".codeium" / "windsurf" / "mcp_config.json"
        with open(config_path) as f:
            config = json.load(f)

        env = config["mcpServers"]["kuzu-memory"].get("env", {})
        assert "KUZU_MEMORY_PROJECT" in env
        assert str(custom_project.resolve()) in env["KUZU_MEMORY_PROJECT"]

    def test_install_without_windsurf_fails(self, tmp_path, monkeypatch):
        """Test installation fails if Windsurf not installed."""
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Don't create Windsurf directory

        installer = WindsurfInstaller(tmp_path)
        result = installer.install()

        assert not result.success
        assert "not found" in result.message.lower()

    def test_install_dry_run(self, tmp_path, monkeypatch):
        """Test dry-run mode for global installation."""
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        windsurf_dir = fake_home / ".codeium" / "windsurf"
        windsurf_dir.mkdir(parents=True)

        installer = WindsurfInstaller(tmp_path)
        result = installer.install(dry_run=True)

        assert result.success
        assert "[DRY RUN]" in result.message
        assert "GLOBAL" in result.message

        # No files should be created
        config_path = fake_home / ".codeium" / "windsurf" / "mcp_config.json"
        assert not config_path.exists()


class TestInstallerRegistry:
    """Test that MCP installers are properly registered."""

    def test_cursor_installer_registered(self):
        """Test Cursor installer is registered."""
        from kuzu_memory.installers.registry import has_installer

        assert has_installer("cursor")

    def test_vscode_installer_registered(self):
        """Test VS Code installer is registered."""
        from kuzu_memory.installers.registry import has_installer

        assert has_installer("vscode")

    def test_windsurf_installer_registered(self):
        """Test Windsurf installer is registered."""
        from kuzu_memory.installers.registry import has_installer

        assert has_installer("windsurf")

    def test_get_installer_returns_correct_type(self, tmp_path):
        """Test registry returns correct installer types."""
        from kuzu_memory.installers.registry import get_installer

        cursor = get_installer("cursor", tmp_path)
        vscode = get_installer("vscode", tmp_path)
        windsurf = get_installer("windsurf", tmp_path)

        assert isinstance(cursor, CursorInstaller)
        assert isinstance(vscode, VSCodeInstaller)
        assert isinstance(windsurf, WindsurfInstaller)
