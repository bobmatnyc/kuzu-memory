"""
Unit tests for CLI automatic MCP config repair functionality.

Tests that the CLI automatically repairs broken MCP configurations
before running commands, without user interaction.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.cli.commands import _silent_repair_mcp_configs


class TestSilentRepairMcpConfigs:
    """Test the _silent_repair_mcp_configs function."""

    @patch("kuzu_memory.installers.json_utils.save_json_config")
    @patch("kuzu_memory.installers.json_utils.fix_broken_mcp_args")
    @patch("kuzu_memory.installers.json_utils.load_json_config")
    @patch("kuzu_memory.cli.commands.Path.home")
    def test_repairs_broken_config(
        self, mock_home, mock_load, mock_fix, mock_save, tmp_path
    ):
        """Test that broken configs are repaired silently."""
        # Setup
        claude_json = tmp_path / ".claude.json"
        mock_home.return_value = tmp_path

        broken_config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}
            }
        }
        fixed_config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}}
        }
        fixes = ["Fixed kuzu-memory: args ['mcp', 'serve'] -> ['mcp']"]

        mock_load.return_value = broken_config
        mock_fix.return_value = (fixed_config, fixes)

        # Create the file so it exists
        claude_json.write_text("{}")

        # Execute
        _silent_repair_mcp_configs()

        # Verify
        mock_load.assert_called_once_with(claude_json)
        mock_fix.assert_called_once_with(broken_config)
        mock_save.assert_called_once_with(claude_json, fixed_config, indent=2)

    @patch("kuzu_memory.installers.json_utils.save_json_config")
    @patch("kuzu_memory.installers.json_utils.fix_broken_mcp_args")
    @patch("kuzu_memory.installers.json_utils.load_json_config")
    @patch("kuzu_memory.cli.commands.Path.home")
    def test_no_repair_when_no_fixes_needed(
        self, mock_home, mock_load, mock_fix, mock_save, tmp_path
    ):
        """Test that config is not written when no fixes are needed."""
        # Setup
        claude_json = tmp_path / ".claude.json"
        mock_home.return_value = tmp_path

        correct_config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}}
        }

        mock_load.return_value = correct_config
        mock_fix.return_value = (correct_config, [])  # No fixes needed

        # Create the file
        claude_json.write_text("{}")

        # Execute
        _silent_repair_mcp_configs()

        # Verify
        mock_load.assert_called_once()
        mock_fix.assert_called_once()
        # save_json_config should NOT be called when no fixes are needed
        mock_save.assert_not_called()

    @patch("kuzu_memory.cli.commands.Path.home")
    def test_does_nothing_when_config_missing(self, mock_home, tmp_path):
        """Test that function returns early when .claude.json doesn't exist."""
        # Setup
        mock_home.return_value = tmp_path
        # Don't create the file

        # Execute (should not raise)
        _silent_repair_mcp_configs()

        # Verify - should have exited early without errors

    @patch("kuzu_memory.installers.json_utils.load_json_config")
    @patch("kuzu_memory.cli.commands.Path.home")
    def test_silent_failure_on_exception(self, mock_home, mock_load, tmp_path):
        """Test that exceptions are caught silently."""
        # Setup
        claude_json = tmp_path / ".claude.json"
        mock_home.return_value = tmp_path
        claude_json.write_text("{}")

        # Make load_json_config raise an exception
        mock_load.side_effect = Exception("Test error")

        # Execute (should not raise)
        _silent_repair_mcp_configs()

        # Verify - should have caught the exception silently

    @patch("kuzu_memory.installers.json_utils.save_json_config")
    @patch("kuzu_memory.installers.json_utils.fix_broken_mcp_args")
    @patch("kuzu_memory.installers.json_utils.load_json_config")
    @patch("kuzu_memory.cli.commands.Path.home")
    def test_repairs_multiple_projects(
        self, mock_home, mock_load, mock_fix, mock_save, tmp_path
    ):
        """Test repairing multiple project-specific configurations."""
        # Setup
        claude_json = tmp_path / ".claude.json"
        mock_home.return_value = tmp_path

        broken_config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}
            },
            "projects": {
                "/project1": {
                    "mcpServers": {
                        "kuzu-memory": {
                            "command": "kuzu-memory",
                            "args": ["mcp", "serve"],
                        }
                    }
                },
                "/project2": {
                    "mcpServers": {
                        "kuzu-memory": {
                            "command": "kuzu-memory",
                            "args": ["mcp", "serve"],
                        }
                    }
                },
            },
        }

        fixed_config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}},
            "projects": {
                "/project1": {
                    "mcpServers": {
                        "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}
                    }
                },
                "/project2": {
                    "mcpServers": {
                        "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}
                    }
                },
            },
        }

        fixes = [
            "Fixed kuzu-memory: args ['mcp', 'serve'] -> ['mcp']",
            "Fixed kuzu-memory in project /project1: args ['mcp', 'serve'] -> ['mcp']",
            "Fixed kuzu-memory in project /project2: args ['mcp', 'serve'] -> ['mcp']",
        ]

        mock_load.return_value = broken_config
        mock_fix.return_value = (fixed_config, fixes)

        claude_json.write_text("{}")

        # Execute
        _silent_repair_mcp_configs()

        # Verify
        mock_save.assert_called_once_with(claude_json, fixed_config, indent=2)

    @patch("kuzu_memory.installers.json_utils.fix_broken_mcp_args")
    @patch("kuzu_memory.installers.json_utils.load_json_config")
    @patch("kuzu_memory.cli.commands.Path.home")
    def test_only_fixes_kuzu_memory_servers(
        self, mock_home, mock_load, mock_fix, tmp_path
    ):
        """Test that only kuzu-memory servers are fixed."""
        # Setup
        claude_json = tmp_path / ".claude.json"
        mock_home.return_value = tmp_path

        config = {
            "mcpServers": {
                "other-server": {"command": "other", "args": ["mcp", "serve"]},
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]},
            }
        }

        # fix_broken_mcp_args should only fix kuzu-memory
        fixed_config = {
            "mcpServers": {
                "other-server": {
                    "command": "other",
                    "args": ["mcp", "serve"],
                },  # Unchanged
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]},  # Fixed
            }
        }
        fixes = ["Fixed kuzu-memory: args ['mcp', 'serve'] -> ['mcp']"]

        mock_load.return_value = config
        mock_fix.return_value = (fixed_config, fixes)

        claude_json.write_text("{}")

        # Execute
        _silent_repair_mcp_configs()

        # Verify fix_broken_mcp_args was called
        mock_fix.assert_called_once_with(config)


class TestCliAutoRepairIntegration:
    """Integration tests for CLI auto-repair on command invocation."""

    @pytest.mark.integration
    @patch("kuzu_memory.cli.commands._silent_repair_mcp_configs")
    def test_auto_repair_called_on_status_command(self, mock_repair):
        """Test that auto-repair is called when running status command."""
        from click.testing import CliRunner

        from kuzu_memory.cli.commands import cli

        runner = CliRunner()

        # Run status command (should trigger auto-repair)
        # Use isolated_filesystem to avoid affecting real project
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["status"])

            # Verify auto-repair was called
            mock_repair.assert_called_once()

    @pytest.mark.integration
    @patch("kuzu_memory.cli.commands._silent_repair_mcp_configs")
    def test_auto_repair_skipped_on_help(self, mock_repair):
        """Test that auto-repair is skipped for help commands."""
        from click.testing import CliRunner

        from kuzu_memory.cli.commands import cli

        runner = CliRunner()

        # Run help command (should NOT trigger auto-repair)
        result = runner.invoke(cli, ["help"])

        # Verify auto-repair was NOT called
        mock_repair.assert_not_called()

    @pytest.mark.integration
    @patch("kuzu_memory.cli.commands._silent_repair_mcp_configs")
    def test_auto_repair_skipped_when_no_subcommand(self, mock_repair):
        """Test that auto-repair is skipped when no subcommand is provided."""
        from click.testing import CliRunner

        from kuzu_memory.cli.commands import cli

        runner = CliRunner()

        # Run without subcommand (should show help, NOT trigger auto-repair)
        result = runner.invoke(cli, [])

        # Verify auto-repair was NOT called
        mock_repair.assert_not_called()
