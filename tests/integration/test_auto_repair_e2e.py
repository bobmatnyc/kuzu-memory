"""
End-to-end integration tests for CLI automatic MCP config repair.

Tests the complete flow:
1. Create broken MCP config in ~/.claude.json
2. Run kuzu-memory CLI command
3. Verify config is auto-repaired silently
4. Confirm no user interaction or warnings

This validates the user's requirement: "auto-detect and fix installations
with no confirmation or options"
"""

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from kuzu_memory.cli.commands import cli


@pytest.fixture
def backup_claude_config():
    """Backup and restore real ~/.claude.json during tests."""
    claude_json = Path.home() / ".claude.json"
    backup_path = Path.home() / ".claude.json.test-backup"

    # Backup existing config if present
    if claude_json.exists():
        shutil.copy(claude_json, backup_path)

    yield claude_json

    # Restore backup
    if backup_path.exists():
        shutil.move(backup_path, claude_json)
    elif claude_json.exists():
        # No backup existed, remove test file
        claude_json.unlink()


class TestAutoRepairEndToEnd:
    """End-to-end tests for automatic MCP config repair."""

    @pytest.mark.integration
    def test_auto_repair_broken_config_on_status(self, backup_claude_config, tmp_path):
        """
        Test that broken MCP config is auto-repaired when running 'kuzu-memory status'.

        This is the critical test validating the user's requirement.
        """
        claude_json = backup_claude_config

        # Create broken config with ["mcp", "serve"] pattern
        broken_config = {
            "mcpServers": {
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": ["mcp", "serve"],
                    "env": {"PROJECT_ROOT": str(tmp_path)},
                }
            }
        }

        # Write broken config
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(broken_config, f, indent=2)

        # Verify broken config exists
        with open(claude_json, encoding="utf-8") as f:
            before_config = json.load(f)
        assert before_config["mcpServers"]["kuzu-memory"]["args"] == ["mcp", "serve"]

        # Run ANY kuzu-memory command (using status as example)
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        # Verify command ran (may fail due to no DB, but should not error on config)
        # The key is that auto-repair ran silently before the command
        assert "Error" not in result.output or "database" in result.output.lower()

        # Read config after command
        with open(claude_json, encoding="utf-8") as f:
            after_config = json.load(f)

        # CRITICAL VERIFICATION: Args should be auto-fixed to ["mcp"]
        assert after_config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

        # Verify other fields preserved
        assert after_config["mcpServers"]["kuzu-memory"]["command"] == "kuzu-memory"
        assert after_config["mcpServers"]["kuzu-memory"]["env"]["PROJECT_ROOT"] == str(
            tmp_path
        )

        # Verify NO user prompts or confirmation messages in output
        assert "confirm" not in result.output.lower()
        assert "fix" not in result.output.lower()  # No visible "fixing" messages
        assert "repair" not in result.output.lower()

    @pytest.mark.integration
    def test_auto_repair_multiple_projects(self, backup_claude_config, tmp_path):
        """Test auto-repair works across multiple project-specific configs."""
        claude_json = backup_claude_config

        # Create broken config with multiple projects
        broken_config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}
            },
            "projects": {
                "/Users/test/project1": {
                    "mcpServers": {
                        "kuzu-memory": {
                            "command": "kuzu-memory",
                            "args": ["mcp", "serve"],
                        }
                    }
                },
                "/Users/test/project2": {
                    "mcpServers": {
                        "kuzu-memory": {
                            "command": "kuzu-memory",
                            "args": ["mcp", "serve"],
                        }
                    }
                },
            },
        }

        # Write broken config
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(broken_config, f, indent=2)

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        # Read fixed config
        with open(claude_json, encoding="utf-8") as f:
            after_config = json.load(f)

        # Verify all broken configs were fixed
        assert after_config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        assert after_config["projects"]["/Users/test/project1"]["mcpServers"][
            "kuzu-memory"
        ]["args"] == ["mcp"]
        assert after_config["projects"]["/Users/test/project2"]["mcpServers"][
            "kuzu-memory"
        ]["args"] == ["mcp"]

    @pytest.mark.integration
    def test_no_change_when_config_already_correct(self, backup_claude_config):
        """Test that correct configs are not modified."""
        claude_json = backup_claude_config

        # Create correct config
        correct_config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}}
        }

        # Write correct config
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(correct_config, f, indent=2)

        # Get file modification time
        mtime_before = claude_json.stat().st_mtime

        # Run command
        runner = CliRunner()
        runner.invoke(cli, ["status"])

        # Read config after
        with open(claude_json, encoding="utf-8") as f:
            after_config = json.load(f)

        # Config should be unchanged
        assert after_config == correct_config

        # File should not have been rewritten (mtime unchanged)
        mtime_after = claude_json.stat().st_mtime
        assert mtime_before == mtime_after

    @pytest.mark.integration
    def test_auto_repair_preserves_other_servers(self, backup_claude_config):
        """Test that other MCP servers are not affected by auto-repair."""
        claude_json = backup_claude_config

        # Create config with multiple servers
        config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]},
                "other-server": {
                    "command": "other-command",
                    "args": ["some", "args"],  # Should not be touched
                },
                "another-mcp-server": {
                    "command": "another",
                    "args": ["mcp", "serve"],  # Should not be touched (not kuzu-memory)
                },
            }
        }

        # Write config
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Run command
        runner = CliRunner()
        runner.invoke(cli, ["status"])

        # Read fixed config
        with open(claude_json, encoding="utf-8") as f:
            after_config = json.load(f)

        # Verify only kuzu-memory was fixed
        assert after_config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

        # Verify other servers unchanged
        assert after_config["mcpServers"]["other-server"]["args"] == ["some", "args"]
        assert after_config["mcpServers"]["another-mcp-server"]["args"] == [
            "mcp",
            "serve",
        ]

    @pytest.mark.integration
    def test_auto_repair_with_extra_args(self, backup_claude_config, tmp_path):
        """Test auto-repair preserves extra arguments after 'serve'."""
        claude_json = backup_claude_config

        # Create config with extra args after "serve"
        config = {
            "mcpServers": {
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": [
                        "mcp",
                        "serve",
                        "--debug",
                    ],  # Extra arg should be preserved
                }
            }
        }

        # Write config
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Run command
        runner = CliRunner()
        runner.invoke(cli, ["status"])

        # Read fixed config
        with open(claude_json, encoding="utf-8") as f:
            after_config = json.load(f)

        # Verify "serve" was removed but "--debug" was preserved
        assert after_config["mcpServers"]["kuzu-memory"]["args"] == ["mcp", "--debug"]

    @pytest.mark.integration
    def test_auto_repair_persists_across_commands(self, backup_claude_config):
        """Test that auto-repair fix persists and doesn't re-trigger."""
        claude_json = backup_claude_config

        # Create broken config
        broken_config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}
            }
        }

        # Write broken config
        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(broken_config, f, indent=2)

        runner = CliRunner()

        # Run first command - should trigger repair
        runner.invoke(cli, ["status"])

        # Get mtime after first repair
        mtime_after_first = claude_json.stat().st_mtime

        # Run second command - should NOT trigger repair (already fixed)
        runner.invoke(cli, ["status"])

        # Get mtime after second command
        mtime_after_second = claude_json.stat().st_mtime

        # File should not have been rewritten on second command
        assert mtime_after_first == mtime_after_second

    @pytest.mark.integration
    def test_auto_repair_silent_on_missing_config(self, backup_claude_config):
        """Test that missing ~/.claude.json doesn't cause errors."""
        claude_json = backup_claude_config

        # Ensure config doesn't exist
        if claude_json.exists():
            claude_json.unlink()

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        # Should not error about missing config (may error about DB though)
        # The key is that auto-repair doesn't break the command
        assert "claude.json" not in result.output.lower()

    @pytest.mark.integration
    def test_auto_repair_silent_on_invalid_json(self, backup_claude_config):
        """Test that invalid JSON doesn't crash the command."""
        claude_json = backup_claude_config

        # Write invalid JSON
        with open(claude_json, "w", encoding="utf-8") as f:
            f.write("{invalid json}")

        # Run command
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        # Command should run (may fail for other reasons, but not JSON parsing)
        # Auto-repair should silently skip broken JSON
        # The command itself may fail due to missing DB, but that's expected


class TestAutoRepairSkipsHelpCommands:
    """Test that auto-repair is skipped for help/version commands."""

    @pytest.mark.integration
    def test_help_command_skips_repair(self, backup_claude_config):
        """Test that 'kuzu-memory help' doesn't trigger auto-repair."""
        claude_json = backup_claude_config

        # Create broken config
        broken_config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}
            }
        }

        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(broken_config, f, indent=2)

        # Get mtime before
        mtime_before = claude_json.stat().st_mtime

        # Run help command
        runner = CliRunner()
        runner.invoke(cli, ["help"])

        # Config should NOT have been modified
        mtime_after = claude_json.stat().st_mtime
        assert mtime_before == mtime_after

        # Config should still be broken
        with open(claude_json, encoding="utf-8") as f:
            config = json.load(f)
        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp", "serve"]

    @pytest.mark.integration
    def test_version_command_skips_repair(self, backup_claude_config):
        """Test that 'kuzu-memory --version' doesn't trigger auto-repair."""
        claude_json = backup_claude_config

        # Create broken config
        broken_config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}
            }
        }

        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(broken_config, f, indent=2)

        mtime_before = claude_json.stat().st_mtime

        # Run version command
        runner = CliRunner()
        runner.invoke(cli, ["--version"])

        # Config should NOT have been modified
        mtime_after = claude_json.stat().st_mtime
        assert mtime_before == mtime_after


class TestAutoRepairWithDifferentCommands:
    """Test auto-repair works across various CLI commands."""

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "command",
        [
            ["status"],
            ["memory", "recall", "test query"],
            ["doctor"],
            ["init", "--help"],  # Even subcommand help should trigger repair
        ],
    )
    def test_auto_repair_on_various_commands(self, backup_claude_config, command):
        """Test auto-repair triggers on different commands."""
        claude_json = backup_claude_config

        # Create broken config
        broken_config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}
            }
        }

        with open(claude_json, "w", encoding="utf-8") as f:
            json.dump(broken_config, f, indent=2)

        # Run command
        runner = CliRunner()
        runner.invoke(cli, command)

        # Verify config was fixed
        with open(claude_json, encoding="utf-8") as f:
            after_config = json.load(f)

        assert after_config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
