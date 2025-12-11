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
            "projects": {"/other/project": {"mcpServers": {"other-server": {"command": "other"}}}}
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
        config = {"projects": {project_key: {"mcpServers": {"other-server": {"command": "other"}}}}}
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
            "mcpServers": {
                "kuzu-memory": {"command": "mcp"},
                "other-server": {"command": "other"},
            }
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

    def test_auto_fix_broken_mcp_args(self, tmp_path, monkeypatch, caplog):
        """Test auto-fix of broken MCP args during config update."""
        import logging

        caplog.set_level(logging.INFO)

        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        project_key = str(project_path.resolve())

        # Create global config with broken args
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {
                project_key: {
                    "mcpServers": {
                        "kuzu-memory": {
                            "command": "kuzu-memory",
                            "args": ["mcp", "serve"],  # Broken pattern
                        }
                    }
                }
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        installer._update_global_mcp_config()

        # Check that config was auto-fixed
        with open(global_config_path) as f:
            result = json.load(f)

        # Args should be fixed to just ["mcp"]
        assert result["projects"][project_key]["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

        # Check that appropriate logging occurred
        assert any("Auto-fixed" in record.message for record in caplog.records)

    def test_repair_hooks_config_fixes_command_paths(self, tmp_path, monkeypatch):
        """Test auto-repair fixes incorrect command paths."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create .claude directory and settings with incorrect path
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"

        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "kuzu-memory hooks enhance",  # Relative path
                            }
                        ],
                    }
                ]
            }
        }
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        success, messages = installer._repair_hooks_config()

        # Check repair succeeded
        assert success is True
        assert any("Updated command path" in msg for msg in messages)

        # Check config was updated
        with open(settings_path) as f:
            result = json.load(f)

        command = result["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        # Should now have absolute path
        assert command.startswith("/")
        assert "hooks enhance" in command

    def test_repair_hooks_config_migrates_legacy_events(self, tmp_path):
        """Test auto-repair migrates legacy event names."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create .claude directory and settings with legacy event names
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"

        settings = {
            "hooks": {
                "user_prompt_submit": [  # Legacy snake_case
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "/path/kuzu hooks enhance"}],
                    }
                ],
                "post_tool_use": [  # Legacy snake_case
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "/path/kuzu hooks learn"}],
                    }
                ],
            }
        }
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        success, messages = installer._repair_hooks_config()

        # Check repair succeeded
        assert success is True
        assert any(
            "Migrated event: user_prompt_submit → UserPromptSubmit" in msg for msg in messages
        )
        assert any("Migrated event: post_tool_use → PostToolUse" in msg for msg in messages)

        # Check config was updated
        with open(settings_path) as f:
            result = json.load(f)

        # Should have new event names
        assert "UserPromptSubmit" in result["hooks"]
        assert "PostToolUse" in result["hooks"]
        # Should not have old event names
        assert "user_prompt_submit" not in result["hooks"]
        assert "post_tool_use" not in result["hooks"]

    def test_repair_hooks_config_removes_invalid_events(self, tmp_path):
        """Test auto-repair removes invalid event names."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create .claude directory and settings with invalid event
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"

        settings = {
            "hooks": {
                "InvalidEventName": [
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "/path/cmd"}],
                    }
                ],
                "UserPromptSubmit": [  # Valid event
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "/path/kuzu hooks enhance"}],
                    }
                ],
            }
        }
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        success, messages = installer._repair_hooks_config()

        # Check repair succeeded
        assert success is True
        assert any("Removed invalid event: InvalidEventName" in msg for msg in messages)

        # Check config was updated
        with open(settings_path) as f:
            result = json.load(f)

        # Should keep valid event
        assert "UserPromptSubmit" in result["hooks"]
        # Should remove invalid event
        assert "InvalidEventName" not in result["hooks"]

    def test_repair_hooks_config_fixes_legacy_syntax(self, tmp_path, monkeypatch):
        """Test auto-repair fixes legacy command syntax."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create .claude directory and settings with legacy syntax
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"

        # Mock the command path to a known value
        mock_path = "/usr/local/bin/kuzu-memory"
        monkeypatch.setattr(
            ClaudeHooksInstaller,
            "_get_kuzu_memory_command_path",
            lambda self: mock_path,
        )

        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"{mock_path} enhance",  # Missing 'hooks'
                            }
                        ],
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"{mock_path} learn",  # Missing 'hooks'
                            }
                        ],
                    }
                ],
            }
        }
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        success, messages = installer._repair_hooks_config()

        # Check repair succeeded
        assert success is True
        assert any("Updated syntax" in msg for msg in messages)

        # Check config was updated
        with open(settings_path) as f:
            result = json.load(f)

        # Should have 'hooks' subcommand added
        enhance_cmd = result["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        learn_cmd = result["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        assert "hooks enhance" in enhance_cmd
        assert "hooks learn" in learn_cmd

    def test_repair_hooks_config_creates_backup(self, tmp_path):
        """Test auto-repair creates backup before modifying."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create .claude directory and settings
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"

        original_settings = {
            "hooks": {
                "user_prompt_submit": [  # Will be migrated
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "/path/cmd"}],
                    }
                ]
            }
        }
        with open(settings_path, "w") as f:
            json.dump(original_settings, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        success, messages = installer._repair_hooks_config()

        # Check repair succeeded
        assert success is True
        assert any("Created backup" in msg for msg in messages)

        # Check backup file exists
        backup_path = settings_path.with_suffix(".json.backup")
        assert backup_path.exists()

        # Check backup contains original content
        with open(backup_path) as f:
            backup = json.load(f)
        assert backup == original_settings

    def test_repair_hooks_config_handles_nonexistent_file(self, tmp_path):
        """Test auto-repair handles missing settings file."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        installer = ClaudeHooksInstaller(project_path)
        success, messages = installer._repair_hooks_config()

        # Should succeed (nothing to repair)
        assert success is True
        assert any("doesn't exist yet" in msg for msg in messages)

    def test_repair_hooks_config_handles_errors_gracefully(self, tmp_path):
        """Test auto-repair handles errors without crashing."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create .claude directory with invalid JSON
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"
        settings_path.write_text("{invalid json")

        installer = ClaudeHooksInstaller(project_path)
        success, messages = installer._repair_hooks_config()

        # Should fail gracefully
        assert success is False
        assert any("Failed to repair" in msg for msg in messages)

    def test_test_installation_with_auto_repair(self, tmp_path, monkeypatch):
        """Test that _test_installation runs auto-repair when needed."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create .claude directory with issues
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.local.json"

        settings = {
            "hooks": {
                "user_prompt_submit": [  # Legacy event name
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "kuzu-memory enhance"}],
                    }
                ]
            }
        }
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        # Mock subprocess to avoid actual command execution
        import subprocess
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

        installer = ClaudeHooksInstaller(project_path)
        warnings = installer._test_installation()

        # Should have auto-repaired the config
        with open(settings_path) as f:
            result = json.load(f)

        # Event should be migrated
        assert "UserPromptSubmit" in result["hooks"]
        assert "user_prompt_submit" not in result["hooks"]

        # Should have minimal warnings after repair
        # (might have warnings about command not found, but not about event names)
        invalid_event_warnings = [w for w in warnings if "Invalid hook event" in w]
        assert len(invalid_event_warnings) == 0

    def test_detect_broken_mcp_installations_empty(self, tmp_path, monkeypatch):
        """Test detection when no broken installations exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        installer = ClaudeHooksInstaller(project_path)

        broken = installer._detect_broken_mcp_installations()
        assert broken == []

    def test_detect_broken_mcp_installations_finds_broken(self, tmp_path, monkeypatch):
        """Test detection finds broken installations."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create projects
        project1 = tmp_path / "project1"
        project1.mkdir()
        project2 = tmp_path / "project2"
        project2.mkdir()

        # Create global config with broken MCP configs
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {
                str(project1): {
                    "mcpServers": {
                        "kuzu-memory": {
                            "type": "stdio",
                            "command": "kuzu-memory",
                            "args": ["mcp"],
                        }
                    }
                },
                str(project2): {
                    "mcpServers": {
                        "kuzu-memory": {
                            "type": "stdio",
                            "command": "kuzu-memory",
                            "args": ["mcp"],
                        }
                    }
                },
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f)

        installer = ClaudeHooksInstaller(project1)
        broken = installer._detect_broken_mcp_installations()

        assert len(broken) == 2
        assert broken[0]["project_path"] == str(project1)
        assert broken[0]["project_exists"] is True
        assert broken[0]["config"]["command"] == "kuzu-memory"

    def test_detect_broken_mcp_installations_handles_missing_dirs(self, tmp_path, monkeypatch):
        """Test detection handles missing project directories."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create global config with non-existent project
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {
                "/nonexistent/project": {
                    "mcpServers": {
                        "kuzu-memory": {
                            "type": "stdio",
                            "command": "kuzu-memory",
                            "args": ["mcp"],
                        }
                    }
                }
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f)

        project_path = tmp_path / "project"
        project_path.mkdir()
        installer = ClaudeHooksInstaller(project_path)
        broken = installer._detect_broken_mcp_installations()

        assert len(broken) == 1
        assert broken[0]["project_exists"] is False

    def test_migrate_to_local_mcp_json_creates_new(self, tmp_path):
        """Test migration creates new .mcp.json."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        kuzu_config = {
            "type": "stdio",
            "command": "kuzu-memory",
            "args": ["mcp"],
            "env": {"KUZU_MEMORY_DB": str(project_path / "kuzu-memories")},
        }

        installer = ClaudeHooksInstaller(project_path)
        success, message = installer._migrate_to_local_mcp_json(project_path, kuzu_config)

        assert success is True
        assert "Migrated to" in message

        # Verify .mcp.json was created
        mcp_json = project_path / ".mcp.json"
        assert mcp_json.exists()

        with open(mcp_json) as f:
            result = json.load(f)

        assert "mcpServers" in result
        assert "kuzu-memory" in result["mcpServers"]
        assert result["mcpServers"]["kuzu-memory"] == kuzu_config

    def test_migrate_to_local_mcp_json_preserves_existing_servers(self, tmp_path):
        """Test migration preserves other MCP servers."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create existing .mcp.json with another server
        mcp_json = project_path / ".mcp.json"
        existing_config = {
            "mcpServers": {
                "other-server": {
                    "type": "stdio",
                    "command": "other-server",
                }
            }
        }
        with open(mcp_json, "w") as f:
            json.dump(existing_config, f)

        kuzu_config = {
            "type": "stdio",
            "command": "kuzu-memory",
            "args": ["mcp"],
        }

        installer = ClaudeHooksInstaller(project_path)
        success, _message = installer._migrate_to_local_mcp_json(project_path, kuzu_config)

        assert success is True

        # Verify both servers exist
        with open(mcp_json) as f:
            result = json.load(f)

        assert "other-server" in result["mcpServers"]
        assert "kuzu-memory" in result["mcpServers"]

    def test_migrate_to_local_mcp_json_skips_existing_without_force(self, tmp_path):
        """Test migration skips if kuzu-memory already exists."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create existing .mcp.json with kuzu-memory
        mcp_json = project_path / ".mcp.json"
        existing_config = {
            "mcpServers": {
                "kuzu-memory": {
                    "type": "stdio",
                    "command": "old-command",
                }
            }
        }
        with open(mcp_json, "w") as f:
            json.dump(existing_config, f)

        kuzu_config = {
            "type": "stdio",
            "command": "new-command",
        }

        installer = ClaudeHooksInstaller(project_path)
        success, message = installer._migrate_to_local_mcp_json(
            project_path, kuzu_config, force=False
        )

        assert success is False
        assert "already in .mcp.json" in message

        # Verify original config preserved
        with open(mcp_json) as f:
            result = json.load(f)

        assert result["mcpServers"]["kuzu-memory"]["command"] == "old-command"

    def test_migrate_to_local_mcp_json_overwrites_with_force(self, tmp_path):
        """Test migration overwrites with force=True."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create existing .mcp.json with kuzu-memory
        mcp_json = project_path / ".mcp.json"
        existing_config = {
            "mcpServers": {
                "kuzu-memory": {
                    "type": "stdio",
                    "command": "old-command",
                }
            }
        }
        with open(mcp_json, "w") as f:
            json.dump(existing_config, f)

        kuzu_config = {
            "type": "stdio",
            "command": "new-command",
        }

        installer = ClaudeHooksInstaller(project_path)
        success, _message = installer._migrate_to_local_mcp_json(
            project_path, kuzu_config, force=True
        )

        assert success is True

        # Verify config was updated
        with open(mcp_json) as f:
            result = json.load(f)

        assert result["mcpServers"]["kuzu-memory"]["command"] == "new-command"

    def test_cleanup_broken_configs_removes_entries(self, tmp_path, monkeypatch):
        """Test cleanup removes broken entries from ~/.claude.json."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create projects
        project1 = tmp_path / "project1"
        project1.mkdir()
        project2 = tmp_path / "project2"
        project2.mkdir()

        # Create global config
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {
                str(project1): {
                    "mcpServers": {
                        "kuzu-memory": {"command": "kuzu"},
                        "other-server": {"command": "other"},
                    }
                },
                str(project2): {
                    "mcpServers": {
                        "kuzu-memory": {"command": "kuzu"},
                    }
                },
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f)

        installer = ClaudeHooksInstaller(project1)
        success, message = installer._cleanup_broken_configs([str(project1), str(project2)])

        assert success is True
        assert "Cleaned up" in message

        # Verify backup was created
        backups = list(tmp_path.glob(".claude.json.backup.*"))
        assert len(backups) == 1

        # Verify kuzu-memory was removed
        with open(global_config_path) as f:
            result = json.load(f)

        # project1 should still exist (has other-server)
        assert str(project1) in result["projects"]
        assert "kuzu-memory" not in result["projects"][str(project1)]["mcpServers"]
        assert "other-server" in result["projects"][str(project1)]["mcpServers"]

        # project2 should be removed (only had kuzu-memory)
        assert str(project2) not in result["projects"]

    def test_cleanup_broken_configs_creates_backup(self, tmp_path, monkeypatch):
        """Test cleanup creates timestamped backup."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        project = tmp_path / "project"
        project.mkdir()

        # Create global config
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {
                str(project): {
                    "mcpServers": {
                        "kuzu-memory": {"command": "kuzu"},
                    }
                }
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f)

        installer = ClaudeHooksInstaller(project)
        success, _message = installer._cleanup_broken_configs([str(project)])

        assert success is True

        # Verify backup exists and has correct format
        backups = list(tmp_path.glob(".claude.json.backup.*"))
        assert len(backups) == 1
        assert backups[0].name.startswith(".claude.json.backup.202")

        # Verify backup contains original content
        with open(backups[0]) as f:
            backup = json.load(f)
        assert backup == config

    def test_migrate_broken_mcp_configs_full_workflow(self, tmp_path, monkeypatch, capsys):
        """Test full migration workflow."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create projects
        project1 = tmp_path / "project1"
        project1.mkdir()
        project2 = tmp_path / "project2"
        project2.mkdir()

        # Create global config with broken installations
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {
                str(project1): {
                    "mcpServers": {
                        "kuzu-memory": {
                            "type": "stdio",
                            "command": "kuzu-memory",
                            "args": ["mcp"],
                        }
                    }
                },
                str(project2): {
                    "mcpServers": {
                        "kuzu-memory": {
                            "type": "stdio",
                            "command": "kuzu-memory",
                            "args": ["mcp"],
                        }
                    }
                },
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f)

        installer = ClaudeHooksInstaller(project1)
        results = installer._migrate_broken_mcp_configs()

        # Check results
        assert results["detected"] == 2
        assert results["migrated"] == 2
        assert results["failed"] == 0
        assert results["skipped"] == 0

        # Check output
        captured = capsys.readouterr()
        assert "Migrating MCP configurations" in captured.out
        assert "Migration complete: 2 project(s) migrated" in captured.out

        # Verify .mcp.json files were created
        assert (project1 / ".mcp.json").exists()
        assert (project2 / ".mcp.json").exists()

        # Verify configs are correct
        with open(project1 / ".mcp.json") as f:
            mcp1 = json.load(f)
        assert "kuzu-memory" in mcp1["mcpServers"]

        # Verify cleanup happened
        with open(global_config_path) as f:
            cleaned = json.load(f)
        assert "projects" not in cleaned or not cleaned.get("projects")

    def test_migrate_broken_mcp_configs_skips_missing_dirs(self, tmp_path, monkeypatch, capsys):
        """Test migration skips non-existent directories."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create global config with non-existent project
        global_config_path = tmp_path / ".claude.json"
        config = {
            "projects": {
                "/nonexistent/project": {
                    "mcpServers": {
                        "kuzu-memory": {"command": "kuzu"},
                    }
                }
            }
        }
        with open(global_config_path, "w") as f:
            json.dump(config, f)

        project = tmp_path / "project"
        project.mkdir()
        installer = ClaudeHooksInstaller(project)
        results = installer._migrate_broken_mcp_configs()

        assert results["detected"] == 1
        assert results["migrated"] == 0
        assert results["skipped"] == 1

        # Check output
        captured = capsys.readouterr()
        assert "Skipped 1 project(s)" in captured.out

    def test_update_mcp_local_config_creates_new_file(self, tmp_path):
        """Test mcp.local.json creation when file doesn't exist."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()

        installer = ClaudeHooksInstaller(project_path)
        mcp_local_path = claude_dir / "mcp.local.json"

        # Should create new config
        installer._update_mcp_local_config(mcp_local_path)

        assert mcp_local_path.exists()

        with open(mcp_local_path) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "kuzu-memory" in config["mcpServers"]
        assert config["mcpServers"]["kuzu-memory"]["type"] == "stdio"
        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        assert "KUZU_MEMORY_PROJECT" in config["mcpServers"]["kuzu-memory"]["env"]

    def test_update_mcp_local_config_preserves_other_servers(self, tmp_path):
        """Test mcp.local.json preserves other MCP servers."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        mcp_local_path = claude_dir / "mcp.local.json"

        # Create existing config with other server
        existing_config = {
            "mcpServers": {
                "mcp-ticketer": {
                    "type": "stdio",
                    "command": "/path/to/mcp-ticketer",
                    "args": ["mcp", "/path/to/project"],
                    "env": {"GITHUB_TOKEN": "token123"},
                }
            }
        }
        with open(mcp_local_path, "w") as f:
            json.dump(existing_config, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        installer._update_mcp_local_config(mcp_local_path)

        with open(mcp_local_path) as f:
            result = json.load(f)

        # Check other server preserved
        assert "mcp-ticketer" in result["mcpServers"]
        assert result["mcpServers"]["mcp-ticketer"]["env"]["GITHUB_TOKEN"] == "token123"

        # Check kuzu-memory added
        assert "kuzu-memory" in result["mcpServers"]
        assert result["mcpServers"]["kuzu-memory"]["type"] == "stdio"

    def test_update_mcp_local_config_creates_backup(self, tmp_path):
        """Test mcp.local.json creates backup before modification."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        mcp_local_path = claude_dir / "mcp.local.json"

        # Create existing config
        existing_config = {"mcpServers": {"other-server": {"command": "other"}}}
        with open(mcp_local_path, "w") as f:
            json.dump(existing_config, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        installer._update_mcp_local_config(mcp_local_path)

        # Check backup was created
        backup_path = claude_dir / "mcp.local.json.backup"
        assert backup_path.exists()

        # Check backup contains original content
        with open(backup_path) as f:
            backup = json.load(f)
        assert "kuzu-memory" not in backup["mcpServers"]
        assert "other-server" in backup["mcpServers"]

    def test_update_mcp_local_config_merges_not_overwrites(self, tmp_path):
        """Test mcp.local.json merges configs instead of overwriting."""
        project_path = tmp_path / "project"
        project_path.mkdir()
        claude_dir = project_path / ".claude"
        claude_dir.mkdir()
        mcp_local_path = claude_dir / "mcp.local.json"

        # Create complex existing config
        existing_config = {
            "mcpServers": {
                "mcp-ticketer": {
                    "type": "stdio",
                    "command": "/venv/bin/mcp-ticketer",
                    "args": ["mcp", "/project"],
                    "env": {"MCP_TICKETER_ADAPTER": "github", "GITHUB_TOKEN": "token"},
                },
                "mcp-browser": {"type": "stdio", "command": "mcp-browser", "args": []},
                "mcp-vector-search": {
                    "type": "stdio",
                    "command": "mcp-vector-search",
                    "args": ["search"],
                },
            }
        }
        with open(mcp_local_path, "w") as f:
            json.dump(existing_config, f, indent=2)

        installer = ClaudeHooksInstaller(project_path)
        installer._update_mcp_local_config(mcp_local_path)

        with open(mcp_local_path) as f:
            result = json.load(f)

        # Check all servers preserved
        assert len(result["mcpServers"]) == 4  # 3 existing + 1 new
        assert "mcp-ticketer" in result["mcpServers"]
        assert "mcp-browser" in result["mcpServers"]
        assert "mcp-vector-search" in result["mcpServers"]
        assert "kuzu-memory" in result["mcpServers"]

        # Check kuzu-memory config is correct
        kuzu_config = result["mcpServers"]["kuzu-memory"]
        assert kuzu_config["type"] == "stdio"
        assert kuzu_config["args"] == ["mcp"]
        assert "KUZU_MEMORY_PROJECT" in kuzu_config["env"]
