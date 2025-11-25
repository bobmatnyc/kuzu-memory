"""
Comprehensive tests for MCP args auto-fix functionality across all installers.

Tests the fix_broken_mcp_args() implementation in:
- cursor_installer.py
- vscode_installer.py
- windsurf_installer.py
- auggie_mcp_installer.py
"""

import json
from pathlib import Path

import pytest

from kuzu_memory.installers.auggie_mcp_installer import AuggieMCPInstaller
from kuzu_memory.installers.cursor_installer import CursorInstaller
from kuzu_memory.installers.json_utils import fix_broken_mcp_args
from kuzu_memory.installers.vscode_installer import VSCodeInstaller
from kuzu_memory.installers.windsurf_installer import WindsurfInstaller


class TestMCPArgsAutoFixFunction:
    """Test the fix_broken_mcp_args() function directly."""

    def test_fixes_broken_mcp_serve_args(self):
        """Test fixing broken ['mcp', 'serve'] args."""
        config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}}
        }

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 1
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        assert "Fixed kuzu-memory" in fixes[0]

    def test_preserves_additional_args(self):
        """Test that additional args after 'serve' are preserved."""
        config = {
            "mcpServers": {
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": ["mcp", "serve", "--verbose", "--debug"],
                }
            }
        }

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 1
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == [
            "mcp",
            "--verbose",
            "--debug",
        ]

    def test_preserves_correct_args(self):
        """Test that correct ['mcp'] args are not modified."""
        config = {"mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}}}

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

    def test_only_fixes_kuzu_memory_servers(self):
        """Test that only kuzu-memory servers are fixed."""
        config = {
            "mcpServers": {
                "other-server": {"command": "other", "args": ["mcp", "serve"]},
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]},
            }
        }

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 1
        # kuzu-memory should be fixed
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        # other-server should NOT be fixed
        assert fixed["mcpServers"]["other-server"]["args"] == ["mcp", "serve"]

    def test_handles_multiple_kuzu_servers(self):
        """Test fixing multiple kuzu-memory configurations."""
        config = {
            "mcpServers": {
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]},
                "kuzu-memory-dev": {
                    "command": "kuzu-memory",
                    "args": ["mcp", "serve", "--debug"],
                },
            }
        }

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 2
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        assert fixed["mcpServers"]["kuzu-memory-dev"]["args"] == ["mcp", "--debug"]

    def test_handles_project_configs_claude_hooks(self):
        """Test fixing project-specific configs (Claude Hooks pattern)."""
        config = {
            "projects": {
                "/path/to/project": {
                    "mcpServers": {
                        "kuzu-memory": {
                            "command": "kuzu-memory",
                            "args": ["mcp", "serve"],
                        }
                    }
                }
            }
        }

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 1
        assert fixed["projects"]["/path/to/project"]["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

    def test_handles_empty_config(self):
        """Test handling empty configuration."""
        config = {}
        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert fixed == {}

    def test_handles_no_mcpservers(self):
        """Test handling config without mcpServers."""
        config = {"other": "data"}
        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert fixed == {"other": "data"}

    def test_handles_non_dict_config(self):
        """Test handling non-dictionary input."""
        config = "not a dict"
        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert fixed == "not a dict"


class TestCursorAutoFix:
    """Test auto-fix in CursorInstaller."""

    def test_cursor_fixes_broken_config_on_install(self, tmp_path):
        """Test Cursor installer auto-fixes broken config during installation."""
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        # Create broken config
        broken_config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}}
        }

        with open(config_path, "w") as f:
            json.dump(broken_config, f)

        # Install should auto-fix
        installer = CursorInstaller(tmp_path)
        result = installer.install(force=True)

        assert result.success

        # Verify config was fixed
        with open(config_path) as f:
            config = json.load(f)

        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

    def test_cursor_preserves_correct_config(self, tmp_path):
        """Test Cursor installer doesn't modify correct config."""
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        # Create correct config
        correct_config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}}
        }

        with open(config_path, "w") as f:
            json.dump(correct_config, f)

        # Install should not modify
        installer = CursorInstaller(tmp_path)
        result = installer.install(force=True)

        assert result.success

        # Verify config unchanged
        with open(config_path) as f:
            config = json.load(f)

        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

    def test_cursor_preserves_other_servers(self, tmp_path):
        """Test Cursor installer only fixes kuzu-memory, not other servers."""
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        # Create config with multiple servers
        mixed_config = {
            "mcpServers": {
                "other-server": {"command": "other", "args": ["mcp", "serve"]},
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]},
            }
        }

        with open(config_path, "w") as f:
            json.dump(mixed_config, f)

        # Install WITHOUT force to preserve existing servers
        installer = CursorInstaller(tmp_path)
        result = installer.install(force=False)

        assert result.success

        # Verify only kuzu-memory was fixed, other-server preserved
        with open(config_path) as f:
            config = json.load(f)

        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        assert config["mcpServers"]["other-server"]["args"] == ["mcp", "serve"]


class TestVSCodeAutoFix:
    """Test auto-fix in VSCodeInstaller."""

    def test_vscode_fixes_broken_config_on_install(self, tmp_path):
        """Test VS Code installer auto-fixes broken config during installation."""
        config_path = tmp_path / ".vscode" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        # Create broken config
        broken_config = {
            "mcpServers": {
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": ["mcp", "serve", "--verbose"],
                }
            }
        }

        with open(config_path, "w") as f:
            json.dump(broken_config, f)

        # Install should auto-fix (without force to test merging)
        installer = VSCodeInstaller(tmp_path)
        result = installer.install(force=False)

        assert result.success

        # Verify config was fixed and --verbose preserved
        with open(config_path) as f:
            config = json.load(f)

        # Note: Since we're not using force, the existing config is merged
        # The auto-fix happens BEFORE merging, so the args should be fixed
        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp", "--verbose"]

    def test_vscode_handles_servers_format(self, tmp_path):
        """Test VS Code installer handles 'servers' format with auto-fix."""
        config_path = tmp_path / ".vscode" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        # Create VS Code format with broken args
        broken_config = {
            "servers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}}
        }

        with open(config_path, "w") as f:
            json.dump(broken_config, f)

        # Install should normalize and auto-fix
        installer = VSCodeInstaller(tmp_path)
        result = installer.install(force=True)

        assert result.success

        # Verify format normalized and args fixed
        with open(config_path) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]


class TestWindsurfAutoFix:
    """Test auto-fix in WindsurfInstaller."""

    def test_windsurf_fixes_broken_config_on_install(self, tmp_path, monkeypatch):
        """Test Windsurf installer auto-fixes broken config during installation."""
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        windsurf_dir = fake_home / ".codeium" / "windsurf"
        windsurf_dir.mkdir(parents=True)

        config_path = windsurf_dir / "mcp_config.json"

        # Create broken config
        broken_config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}}
        }

        with open(config_path, "w") as f:
            json.dump(broken_config, f)

        # Install should auto-fix
        installer = WindsurfInstaller(tmp_path)
        result = installer.install(force=True)

        assert result.success

        # Verify config was fixed
        with open(config_path) as f:
            config = json.load(f)

        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]


class TestAuggieAutoFix:
    """Test auto-fix in AuggieMCPInstaller."""

    def test_auggie_fixes_broken_config_on_install(self, tmp_path, monkeypatch):
        """Test Auggie installer auto-fixes broken config during installation."""
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        auggie_dir = fake_home / ".augment"
        auggie_dir.mkdir(parents=True)

        config_path = auggie_dir / "settings.json"

        # Create broken config
        broken_config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}}
        }

        with open(config_path, "w") as f:
            json.dump(broken_config, f)

        # Install should auto-fix
        installer = AuggieMCPInstaller(tmp_path)
        result = installer.install(force=True)

        assert result.success

        # Verify config was fixed
        with open(config_path) as f:
            config = json.load(f)

        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]


class TestEdgeCases:
    """Test edge cases for auto-fix functionality."""

    def test_empty_args_list(self):
        """Test handling empty args list."""
        config = {"mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": []}}}

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == []

    def test_single_arg_list(self):
        """Test handling single-element args list."""
        config = {"mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}}}

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

    def test_no_args_field(self):
        """Test handling server config without args field."""
        config = {"mcpServers": {"kuzu-memory": {"command": "kuzu-memory"}}}

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert "args" not in fixed["mcpServers"]["kuzu-memory"]

    def test_non_list_args(self):
        """Test handling non-list args value."""
        config = {"mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": "not a list"}}}

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == "not a list"

    def test_malformed_mcpservers(self):
        """Test handling malformed mcpServers value."""
        config = {"mcpServers": "not a dict"}

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 0
        assert fixed["mcpServers"] == "not a dict"

    def test_nested_projects_with_mixed_configs(self):
        """Test fixing nested project configs with mix of broken and correct."""
        config = {
            "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]}},
            "projects": {
                "/project1": {
                    "mcpServers": {"kuzu-memory": {"command": "kuzu-memory", "args": ["mcp"]}}
                },
                "/project2": {
                    "mcpServers": {
                        "kuzu-memory": {
                            "command": "kuzu-memory",
                            "args": ["mcp", "serve", "--debug"],
                        }
                    }
                },
            },
        }

        fixed, fixes = fix_broken_mcp_args(config)

        assert len(fixes) == 2  # Root and project2
        assert fixed["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        assert fixed["projects"]["/project1"]["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        assert fixed["projects"]["/project2"]["mcpServers"]["kuzu-memory"]["args"] == [
            "mcp",
            "--debug",
        ]


class TestRegressionScenarios:
    """Test that auto-fix doesn't break existing functionality."""

    def test_fresh_install_no_autofix_trigger(self, tmp_path):
        """Test fresh install doesn't incorrectly trigger auto-fix."""
        installer = CursorInstaller(tmp_path)
        result = installer.install()

        assert result.success

        # Fresh install should have correct args from the start
        config_path = tmp_path / ".cursor" / "mcp.json"
        with open(config_path) as f:
            config = json.load(f)

        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

    def test_config_merging_with_autofix(self, tmp_path):
        """Test that config merging works correctly with auto-fix."""
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        # Create existing config with broken kuzu-memory and correct other server
        existing_config = {
            "mcpServers": {
                "github-mcp": {"command": "github-mcp", "args": ["start"]},
                "kuzu-memory": {"command": "kuzu-memory", "args": ["mcp", "serve"]},
            }
        }

        with open(config_path, "w") as f:
            json.dump(existing_config, f)

        # Install without force (should merge)
        installer = CursorInstaller(tmp_path)
        result = installer.install(force=False)

        assert result.success

        # Verify merging preserved github-mcp and fixed kuzu-memory
        with open(config_path) as f:
            config = json.load(f)

        assert "github-mcp" in config["mcpServers"]
        assert config["mcpServers"]["github-mcp"]["args"] == ["start"]
        assert config["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]

    def test_backup_creation_still_works(self, tmp_path):
        """Test that backup creation still works with auto-fix."""
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)

        # Create existing config
        with open(config_path, "w") as f:
            json.dump({"mcpServers": {"test": {"command": "test"}}}, f)

        # Install should create backup
        installer = CursorInstaller(tmp_path)
        result = installer.install(force=True)

        assert result.success
        assert len(result.backup_files) > 0

        # Verify backup exists
        backup_dir = tmp_path / ".kuzu-memory-backups"
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob("mcp.json.backup_*"))
        assert len(backup_files) > 0
