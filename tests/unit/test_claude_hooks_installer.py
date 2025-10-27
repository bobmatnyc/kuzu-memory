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

    def test_clean_global_config_no_file(self, tmp_path, monkeypatch):
        """Test cleanup when global config doesn't exist."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        installer = ClaudeHooksInstaller(tmp_path / "project")

        # Should not raise any errors
        installer._clean_global_config()

    def test_clean_global_config_no_kuzu_entries(self, tmp_path, monkeypatch):
        """Test cleanup when no kuzu-memory entries exist."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create global config without kuzu-memory
        global_config_path = tmp_path / ".claude.json"
        config = {
            "project1": {"mcpServers": {"other-server": {"command": "other-command", "args": []}}}
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f, indent=2)

        installer = ClaudeHooksInstaller(tmp_path / "project")
        installer._clean_global_config()

        # Config should remain unchanged
        with open(global_config_path) as f:
            result = json.load(f)

        assert result == config
        assert not (tmp_path / ".claude.json.backup").exists()

    def test_clean_global_config_with_kuzu_in_project(self, tmp_path, monkeypatch):
        """Test cleanup removes kuzu-memory from project entries."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create global config with kuzu-memory in project
        global_config_path = tmp_path / ".claude.json"
        config = {
            "project1": {
                "mcpServers": {
                    "kuzu-memory": {"command": "mcp", "args": ["serve", "kuzu-memory"]},
                    "other-server": {"command": "other-command", "args": []},
                }
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f, indent=2)

        installer = ClaudeHooksInstaller(tmp_path / "project")
        installer._clean_global_config()

        # Check backup was created
        backup_path = tmp_path / ".claude.json.backup"
        assert backup_path.exists()

        # Check kuzu-memory was removed
        with open(global_config_path) as f:
            result = json.load(f)

        assert "kuzu-memory" not in result["project1"]["mcpServers"]
        assert "other-server" in result["project1"]["mcpServers"]

    def test_clean_global_config_with_top_level_kuzu(self, tmp_path, monkeypatch):
        """Test cleanup removes kuzu-memory from top-level entries."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create global config with top-level kuzu-memory
        global_config_path = tmp_path / ".claude.json"
        config = {
            "mcpServers": {
                "kuzu-memory": {"command": "mcp", "args": ["serve", "kuzu-memory"]},
                "other-server": {"command": "other-command", "args": []},
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f, indent=2)

        installer = ClaudeHooksInstaller(tmp_path / "project")
        installer._clean_global_config()

        # Check backup was created
        backup_path = tmp_path / ".claude.json.backup"
        assert backup_path.exists()

        # Check kuzu-memory was removed
        with open(global_config_path) as f:
            result = json.load(f)

        assert "kuzu-memory" not in result["mcpServers"]
        assert "other-server" in result["mcpServers"]

    def test_clean_global_config_multiple_projects(self, tmp_path, monkeypatch):
        """Test cleanup removes kuzu-memory from multiple projects."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create global config with kuzu-memory in multiple places
        global_config_path = tmp_path / ".claude.json"
        config = {
            "project1": {
                "mcpServers": {"kuzu-memory": {"command": "mcp", "args": ["serve", "kuzu-memory"]}}
            },
            "project2": {
                "mcpServers": {"kuzu-memory": {"command": "mcp", "args": ["serve", "kuzu-memory"]}}
            },
            "mcpServers": {"kuzu-memory": {"command": "mcp", "args": ["serve", "kuzu-memory"]}},
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f, indent=2)

        installer = ClaudeHooksInstaller(tmp_path / "project")
        installer._clean_global_config()

        # Check backup was created
        backup_path = tmp_path / ".claude.json.backup"
        assert backup_path.exists()

        # Check all kuzu-memory entries were removed
        with open(global_config_path) as f:
            result = json.load(f)

        assert "kuzu-memory" not in result.get("mcpServers", {})
        assert "kuzu-memory" not in result.get("project1", {}).get("mcpServers", {})
        assert "kuzu-memory" not in result.get("project2", {}).get("mcpServers", {})

    def test_clean_global_config_handles_corrupt_json(self, tmp_path, monkeypatch):
        """Test cleanup gracefully handles corrupt JSON."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create corrupt global config
        global_config_path = tmp_path / ".claude.json"
        global_config_path.write_text("{invalid json")

        installer = ClaudeHooksInstaller(tmp_path / "project")

        # Should not raise error, just log warning
        installer._clean_global_config()

    def test_installer_properties(self, tmp_path):
        """Test installer basic properties."""
        installer = ClaudeHooksInstaller(tmp_path)

        assert installer.ai_system_name == "claude"
        assert "CLAUDE.md" in installer.required_files
        assert "hooks" in installer.description.lower()
