"""
Unit tests for Claude hooks installer.
"""

import json
import tempfile
from pathlib import Path

import pytest

from kuzu_memory.installers.claude_hooks import ClaudeHooksInstaller


class TestClaudeHooksInstaller:
    """Test Claude Code hooks installer."""

    def test_update_global_mcp_config_creates_new_file(self, tmp_path, monkeypatch):
        """Test MCP config creation when global config doesn't exist."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        installer = ClaudeHooksInstaller(project_path)

        # Should create new config
        installer._update_global_mcp_config()

        global_config_path = tmp_path / ".claude.json"
        assert global_config_path.exists()

        with open(global_config_path) as f:
            config = json.load(f)

        project_key = str(project_path.resolve())
        assert "projects" in config
        assert project_key in config["projects"]
        assert "mcpServers" in config["projects"][project_key]
        assert "kuzu-memory" in config["projects"][project_key]["mcpServers"]

    def test_update_global_mcp_config_preserves_existing_projects(self, tmp_path, monkeypatch):
        """Test MCP config preserves other projects."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create global config with existing project
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {
                "/other/project": {"mcpServers": {"other-server": {"command": "other"}}}
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f, indent=2)

        project_path = tmp_path / "project"
        project_path.mkdir()
        installer = ClaudeHooksInstaller(project_path)
        installer._update_global_mcp_config()

        with open(global_config_path) as f:
            result = json.load(f)

        # Check other project preserved
        assert "/other/project" in result["projects"]
        assert "other-server" in result["projects"]["/other/project"]["mcpServers"]

        # Check new project added
        project_key = str(project_path.resolve())
        assert project_key in result["projects"]
        assert "kuzu-memory" in result["projects"][project_key]["mcpServers"]

    def test_update_global_mcp_config_preserves_other_mcp_servers(self, tmp_path, monkeypatch):
        """Test MCP config preserves other servers in same project."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        project_key = str(project_path.resolve())

        # Create global config with existing server in same project
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {project_key: {"mcpServers": {"other-server": {"command": "other"}}}}
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        installer._update_global_mcp_config()

        with open(global_config_path) as f:
            result = json.load(f)

        # Check other server preserved
        assert "other-server" in result["projects"][project_key]["mcpServers"]
        # Check kuzu-memory added
        assert "kuzu-memory" in result["projects"][project_key]["mcpServers"]

    def test_clean_legacy_mcp_locations_removes_top_level(self, tmp_path, monkeypatch):
        """Test cleanup removes MCP from top-level ~/.claude.json."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create global config with top-level kuzu-memory
        global_config_path = tmp_path / ".claude.json"
        config = {
            "mcpServers": {
                "kuzu-memory": {"command": "mcp", "args": []},
                "other-server": {"command": "other"},
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f, indent=2)

        project_path = tmp_path / "project"
        project_path.mkdir()
        installer = ClaudeHooksInstaller(project_path)

        warnings = installer._clean_legacy_mcp_locations()

        # Check warning was returned
        assert len(warnings) > 0
        assert "top-level" in warnings[0].lower()

        # Check kuzu-memory was removed from top-level
        with open(global_config_path) as f:
            result = json.load(f)

        assert "kuzu-memory" not in result["mcpServers"]
        assert "other-server" in result["mcpServers"]

    def test_clean_legacy_mcp_locations_removes_from_settings(self, tmp_path, monkeypatch):
        """Test cleanup removes MCP from settings.local.json."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create settings.local.json with kuzu-memory MCP server
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"
        settings = {
            "mcpServers": {"kuzu-memory": {"command": "mcp"}, "other-server": {"command": "other"}}
        }
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        warnings = installer._clean_legacy_mcp_locations()

        # Check warning was returned
        assert len(warnings) > 0
        assert "settings.local.json" in warnings[0]

        # Check kuzu-memory was removed
        with open(settings_path) as f:
            result = json.load(f)

        assert "kuzu-memory" not in result.get("mcpServers", {})
        assert "other-server" in result.get("mcpServers", {})

    def test_clean_legacy_mcp_locations_handles_empty_mcpservers(self, tmp_path, monkeypatch):
        """Test cleanup removes empty mcpServers dict."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create settings.local.json with only kuzu-memory
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"
        settings = {"mcpServers": {"kuzu-memory": {"command": "mcp"}}}
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        warnings = installer._clean_legacy_mcp_locations()

        # Check warning was returned
        assert len(warnings) > 0

        # Check mcpServers was removed entirely
        with open(settings_path) as f:
            result = json.load(f)

        assert "mcpServers" not in result

    def test_installer_properties(self, tmp_path):
        """Test installer basic properties."""
        installer = ClaudeHooksInstaller(tmp_path)

        assert installer.ai_system_name == "claude"
        assert "CLAUDE.md" in installer.required_files
        assert "hooks" in installer.description.lower()
