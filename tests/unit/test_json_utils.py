"""
Unit tests for JSON utility functions used in MCP installers.
"""

import json
from pathlib import Path

import pytest

from kuzu_memory.installers.json_utils import (
    JSONConfigError,
    create_mcp_server_config,
    expand_variables,
    get_standard_variables,
    load_json_config,
    merge_json_configs,
    save_json_config,
    validate_mcp_config,
)


class TestExpandVariables:
    """Test variable expansion in JSON configs."""

    def test_expand_simple_variable(self):
        """Test expanding a simple variable."""
        config = {"path": "${HOME}/documents"}
        variables = {"HOME": "/Users/test"}

        result = expand_variables(config, variables)

        assert result["path"] == "/Users/test/documents"

    def test_expand_multiple_variables(self):
        """Test expanding multiple variables in same string."""
        config = {"path": "${HOME}/${USER}/documents"}
        variables = {"HOME": "/Users/test", "USER": "testuser"}

        result = expand_variables(config, variables)

        assert result["path"] == "/Users/test/testuser/documents"

    def test_expand_nested_dict(self):
        """Test expanding variables in nested dictionaries."""
        config = {"server": {"path": "${HOME}/bin", "user": "${USER}"}}
        variables = {"HOME": "/Users/test", "USER": "testuser"}

        result = expand_variables(config, variables)

        assert result["server"]["path"] == "/Users/test/bin"
        assert result["server"]["user"] == "testuser"

    def test_expand_list(self):
        """Test expanding variables in lists."""
        config = {"args": ["--path", "${HOME}/bin"]}
        variables = {"HOME": "/Users/test"}

        result = expand_variables(config, variables)

        assert result["args"][1] == "/Users/test/bin"

    def test_no_variables(self):
        """Test config without variables."""
        config = {"path": "/usr/bin"}
        variables = {"HOME": "/Users/test"}

        result = expand_variables(config, variables)

        assert result["path"] == "/usr/bin"


class TestMergeJsonConfigs:
    """Test JSON configuration merging."""

    def test_merge_simple_configs(self):
        """Test merging two simple configurations."""
        existing = {"key1": "value1"}
        new = {"key2": "value2"}

        result = merge_json_configs(existing, new)

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"

    def test_merge_preserves_existing(self):
        """Test that existing values are preserved by default."""
        existing = {"key": "existing"}
        new = {"key": "new"}

        result = merge_json_configs(existing, new, preserve_existing=True)

        assert result["key"] == "existing"

    def test_merge_overwrites_when_not_preserving(self):
        """Test overwriting existing values when preserve=False."""
        existing = {"key": "existing"}
        new = {"key": "new"}

        result = merge_json_configs(existing, new, preserve_existing=False)

        assert result["key"] == "new"

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        existing = {"mcpServers": {"server1": {"command": "cmd1"}}}
        new = {"mcpServers": {"server2": {"command": "cmd2"}}}

        result = merge_json_configs(existing, new)

        assert "server1" in result["mcpServers"]
        assert "server2" in result["mcpServers"]
        assert result["mcpServers"]["server1"]["command"] == "cmd1"
        assert result["mcpServers"]["server2"]["command"] == "cmd2"

    def test_merge_preserves_existing_servers(self):
        """Test that existing MCP servers are preserved."""
        existing = {
            "mcpServers": {
                "existing-server": {"command": "existing", "args": ["--test"]},
                "shared-server": {"command": "old"},
            }
        }
        new = {
            "mcpServers": {
                "new-server": {"command": "new"},
                "shared-server": {"command": "new"},
            }
        }

        result = merge_json_configs(existing, new, preserve_existing=True)

        # All servers should be present
        assert "existing-server" in result["mcpServers"]
        assert "new-server" in result["mcpServers"]
        assert "shared-server" in result["mcpServers"]

        # Existing server should be unchanged
        assert result["mcpServers"]["existing-server"]["command"] == "existing"
        assert result["mcpServers"]["existing-server"]["args"] == ["--test"]

        # Shared server should keep existing value
        assert result["mcpServers"]["shared-server"]["command"] == "old"

        # New server should be added
        assert result["mcpServers"]["new-server"]["command"] == "new"


class TestLoadSaveJsonConfig:
    """Test loading and saving JSON configurations."""

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading a nonexistent file returns empty dict."""
        file_path = tmp_path / "nonexistent.json"

        result = load_json_config(file_path)

        assert result == {}

    def test_load_valid_json(self, tmp_path):
        """Test loading a valid JSON file."""
        file_path = tmp_path / "config.json"
        config = {"key": "value", "number": 42}

        with open(file_path, "w") as f:
            json.dump(config, f)

        result = load_json_config(file_path)

        assert result == config

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises error."""
        file_path = tmp_path / "invalid.json"

        with open(file_path, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(JSONConfigError, match="Invalid JSON"):
            load_json_config(file_path)

    def test_save_json_config(self, tmp_path):
        """Test saving JSON configuration."""
        file_path = tmp_path / "config.json"
        config = {"key": "value", "nested": {"inner": "data"}}

        save_json_config(file_path, config)

        # Verify file exists and contains correct data
        assert file_path.exists()

        with open(file_path) as f:
            loaded = json.load(f)

        assert loaded == config

    def test_save_creates_parent_directories(self, tmp_path):
        """Test that save creates parent directories."""
        file_path = tmp_path / "subdir" / "nested" / "config.json"
        config = {"key": "value"}

        save_json_config(file_path, config)

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_save_with_formatting(self, tmp_path):
        """Test that saved JSON is properly formatted."""
        file_path = tmp_path / "config.json"
        config = {"key": "value"}

        save_json_config(file_path, config, indent=4)

        content = file_path.read_text()

        # Should be pretty-printed
        assert "\n" in content
        assert "    " in content  # 4-space indent
        assert content.endswith("\n")  # Trailing newline


class TestValidateMcpConfig:
    """Test MCP configuration validation."""

    def test_validate_valid_config(self):
        """Test validating a valid MCP configuration."""
        config = {
            "mcpServers": {"server1": {"command": "cmd"}, "server2": {"command": "cmd2"}}
        }

        errors = validate_mcp_config(config)

        assert errors == []

    def test_validate_missing_servers_key(self):
        """Test validation fails when servers key is missing."""
        config = {"other": "data"}

        errors = validate_mcp_config(config)

        assert len(errors) > 0
        assert any("mcpServers" in err or "servers" in err for err in errors)

    def test_validate_servers_not_dict(self):
        """Test validation fails when servers is not a dict."""
        config = {"mcpServers": "not a dict"}

        errors = validate_mcp_config(config)

        assert len(errors) > 0
        assert any("dictionary" in err for err in errors)

    def test_validate_server_missing_command(self):
        """Test validation fails when server config missing command."""
        config = {"mcpServers": {"server1": {"args": ["--test"]}}}

        errors = validate_mcp_config(config)

        assert len(errors) > 0
        assert any("command" in err for err in errors)

    def test_validate_vscode_format(self):
        """Test validation works with VS Code 'servers' key."""
        config = {"servers": {"server1": {"command": "cmd"}}}

        errors = validate_mcp_config(config)

        assert errors == []


class TestGetStandardVariables:
    """Test standard variable generation."""

    def test_get_standard_variables_without_project(self):
        """Test getting standard variables without project root."""
        variables = get_standard_variables()

        assert "HOME" in variables
        assert "USER" in variables
        assert str(Path.home()) == variables["HOME"]

    def test_get_standard_variables_with_project(self, tmp_path):
        """Test getting standard variables with project root."""
        variables = get_standard_variables(tmp_path)

        assert "HOME" in variables
        assert "USER" in variables
        assert "PROJECT_ROOT" in variables
        assert str(tmp_path.resolve()) == variables["PROJECT_ROOT"]


class TestCreateMcpServerConfig:
    """Test MCP server configuration creation."""

    def test_create_minimal_config(self):
        """Test creating minimal server configuration."""
        config = create_mcp_server_config("kuzu-memory")

        assert config["command"] == "kuzu-memory"
        assert "args" not in config
        assert "env" not in config

    def test_create_config_with_args(self):
        """Test creating configuration with arguments."""
        config = create_mcp_server_config("kuzu-memory", args=["mcp", "serve"])

        assert config["command"] == "kuzu-memory"
        assert config["args"] == ["mcp", "serve"]

    def test_create_config_with_env(self):
        """Test creating configuration with environment variables."""
        config = create_mcp_server_config(
            "kuzu-memory", env={"PROJECT": "/path/to/project"}
        )

        assert config["command"] == "kuzu-memory"
        assert config["env"] == {"PROJECT": "/path/to/project"}

    def test_create_full_config(self):
        """Test creating complete configuration."""
        config = create_mcp_server_config(
            command="kuzu-memory",
            args=["mcp", "serve"],
            env={"PROJECT_ROOT": "/path"},
        )

        assert config["command"] == "kuzu-memory"
        assert config["args"] == ["mcp", "serve"]
        assert config["env"] == {"PROJECT_ROOT": "/path"}
