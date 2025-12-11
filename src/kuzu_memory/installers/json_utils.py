"""
JSON utility functions for MCP configuration management.

Provides JSON merging, validation, and variable expansion for MCP configs.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JSONConfigError(Exception):
    """Raised when JSON configuration operations fail."""

    pass


def expand_variables(config: dict[str, Any], variables: dict[str, str]) -> dict[str, Any]:
    """
    Expand variables in JSON configuration.

    Recursively replaces ${VARIABLE_NAME} with actual values.

    Args:
        config: Configuration dictionary
        variables: Variable mappings {name: value}

    Returns:
        Configuration with variables expanded
    """

    def expand_value(value: Any) -> Any:
        """Recursively expand variables in value."""
        if isinstance(value, str):
            # Replace all ${VAR} patterns
            result = value
            for var_name, var_value in variables.items():
                result = result.replace(f"${{{var_name}}}", var_value)
            return result
        elif isinstance(value, dict):
            return {k: expand_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_value(item) for item in value]
        return value

    return expand_value(config)  # type: ignore[no-any-return]  # Recursive dict/list structure returns Any


def merge_json_configs(
    existing: dict[str, Any], new: dict[str, Any], preserve_existing: bool = True
) -> dict[str, Any]:
    """
    Merge two JSON configurations, preserving existing MCP servers.

    Args:
        existing: Existing configuration
        new: New configuration to merge
        preserve_existing: If True, existing values take precedence

    Returns:
        Merged configuration

    Example:
        >>> existing = {"mcpServers": {"server1": {...}}}
        >>> new = {"mcpServers": {"server2": {...}}}
        >>> merged = merge_json_configs(existing, new)
        >>> # Result: {"mcpServers": {"server1": {...}, "server2": {...}}}
    """
    result = existing.copy()

    for key, new_value in new.items():
        if key not in result:
            # Key doesn't exist, add it
            result[key] = new_value
        elif isinstance(result[key], dict) and isinstance(new_value, dict):
            # Both are dicts, merge recursively
            result[key] = merge_json_configs(result[key], new_value, preserve_existing)
        elif preserve_existing:
            # Preserve existing value
            logger.debug(f"Preserving existing value for key: {key}")
        else:
            # Overwrite with new value
            result[key] = new_value

    return result


def load_json_config(file_path: Path) -> dict[str, Any]:
    """
    Load JSON configuration from file.

    Args:
        file_path: Path to JSON file

    Returns:
        Configuration dictionary

    Raises:
        JSONConfigError: If file cannot be loaded or parsed
    """
    try:
        if not file_path.exists():
            return {}

        with open(file_path, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]  # JSON returns Any for dynamic structure
    except json.JSONDecodeError as e:
        raise JSONConfigError(f"Invalid JSON in {file_path}: {e}")
    except Exception as e:
        raise JSONConfigError(f"Failed to load {file_path}: {e}")


def save_json_config(file_path: Path, config: dict[str, Any], indent: int = 2) -> None:
    """
    Save JSON configuration to file.

    Args:
        file_path: Path to save to
        config: Configuration dictionary
        indent: JSON indentation level

    Raises:
        JSONConfigError: If file cannot be saved
    """
    try:
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write with pretty formatting
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=indent, ensure_ascii=False)
            f.write("\n")  # Add trailing newline

        logger.info(f"Saved JSON configuration to {file_path}")
    except Exception as e:
        raise JSONConfigError(f"Failed to save {file_path}: {e}")


def validate_mcp_config(config: dict[str, Any]) -> list[str]:
    """
    Validate MCP server configuration.

    Args:
        config: MCP configuration dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check for mcpServers key (most common) or servers (VS Code variant)
    if "mcpServers" not in config and "servers" not in config:
        errors.append("Missing 'mcpServers' or 'servers' key in configuration")
        return errors

    # Validate each server
    servers_key = "mcpServers" if "mcpServers" in config else "servers"
    servers = config.get(servers_key, {})

    if not isinstance(servers, dict):
        errors.append(f"'{servers_key}' must be a dictionary")
        return errors

    for server_name, server_config in servers.items():
        if not isinstance(server_config, dict):
            errors.append(f"Server '{server_name}' configuration must be a dictionary")
            continue

        # Check required fields
        if "command" not in server_config:
            errors.append(f"Server '{server_name}' missing required 'command' field")

    return errors


def get_standard_variables(project_root: Path | None = None) -> dict[str, str]:
    """
    Get standard variable mappings for MCP configurations.

    Args:
        project_root: Project root directory (optional)

    Returns:
        Dictionary of variable mappings
    """
    variables = {
        "HOME": str(Path.home()),
        "USER": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
    }

    if project_root:
        variables["PROJECT_ROOT"] = str(project_root.resolve())

    return variables


def create_mcp_server_config(
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create a standard MCP server configuration.

    Args:
        command: Command to run the MCP server
        args: Command arguments (optional)
        env: Environment variables (optional)

    Returns:
        MCP server configuration dictionary
    """
    config: dict[str, Any] = {"command": command}

    if args:
        config["args"] = args

    if env:
        config["env"] = env

    return config


def _needs_mcp_args_fix(server_name: str, server_config: dict[str, Any]) -> bool:
    """
    Check if server config needs args fix.

    Only fixes kuzu-memory servers with outdated patterns:
    - ["mcp", "serve"]
    - ["-m", "kuzu_memory.mcp.server"]

    Args:
        server_name: Name of the MCP server
        server_config: Server configuration dictionary

    Returns:
        True if fix is needed, False otherwise
    """
    # Only fix kuzu-memory servers
    if "kuzu-memory" not in server_name.lower():
        return False

    # Check if args field exists and is a list
    args = server_config.get("args")
    if not isinstance(args, list) or len(args) < 2:
        return False

    # Check for broken patterns
    # Pattern 1: ["mcp", "serve"]
    if args[0] == "mcp" and args[1] == "serve":
        return True

    # Pattern 2: ["-m", "kuzu_memory.mcp.server"]
    if args[0] == "-m" and args[1] == "kuzu_memory.mcp.server":
        return True

    return False


def _fix_mcp_args(args: list[Any]) -> list[Any]:
    """
    Fix MCP args by converting old patterns to ["mcp"].

    Transforms:
    - ["mcp", "serve", ...] to ["mcp", ...]
    - ["-m", "kuzu_memory.mcp.server", ...] to ["mcp", ...]

    Args:
        args: List of command arguments

    Returns:
        Fixed arguments list
    """
    if len(args) >= 2:
        # Pattern 1: ["mcp", "serve", ...]
        if args[0] == "mcp" and args[1] == "serve":
            # Remove "serve" but preserve any other args
            return [args[0], *args[2:]]

        # Pattern 2: ["-m", "kuzu_memory.mcp.server", ...]
        if args[0] == "-m" and args[1] == "kuzu_memory.mcp.server":
            # Replace with ["mcp"] and preserve any other args
            return ["mcp", *args[2:]]

    return args


def _needs_command_fix(server_name: str, server_config: dict[str, Any]) -> bool:
    """
    Check if server config needs command fix.

    Detects:
    1. Python command with -m kuzu_memory.mcp.server args pattern
    2. Full path to kuzu-memory binary (e.g., /path/to/pipx/venvs/kuzu-memory/bin/kuzu-memory)

    Only fixes kuzu-memory servers.

    Args:
        server_name: Name of the MCP server
        server_config: Server configuration dictionary

    Returns:
        True if command needs to be fixed
    """
    # Only fix kuzu-memory servers
    if "kuzu-memory" not in server_name.lower():
        return False

    command = server_config.get("command", "")
    if not isinstance(command, str):
        return False

    # Pattern 1: Check if command ends with 'python' and args are python module pattern
    if command.endswith("python"):
        args = server_config.get("args")
        if isinstance(args, list) and len(args) >= 2:
            if args[0] == "-m" and args[1] == "kuzu_memory.mcp.server":
                return True

    # Pattern 2: Check if command is a full path to kuzu-memory binary
    # Should be just "kuzu-memory", not a path
    if "/" in command or "\\" in command:
        # It's a path - check if it ends with kuzu-memory
        if command.endswith("kuzu-memory") or "kuzu-memory" in command:
            return True

    return False


def _fix_command(command: str) -> str:
    """
    Fix command from python path to kuzu-memory.

    Args:
        command: Original command (e.g., /path/to/python)

    Returns:
        Fixed command (kuzu-memory)
    """
    return "kuzu-memory"


def fix_broken_mcp_args(config: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """
    Fix broken MCP server arguments and commands in configuration.

    Detects and fixes outdated patterns:
    - Args: ["mcp", "serve"] -> ["mcp"]
    - Args: ["-m", "kuzu_memory.mcp.server"] -> ["mcp"]
    - Command: /path/to/python (with -m args) -> kuzu-memory
    - Command: /full/path/to/kuzu-memory -> kuzu-memory

    Handles both root-level mcpServers and project-specific configurations.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (fixed_config, list_of_fixes_applied)

    Example:
        >>> config = {"mcpServers": {"kuzu-memory": {"command": "kuzu", "args": ["mcp", "serve"]}}}
        >>> fixed, fixes = fix_broken_mcp_args(config)
        >>> # fixed["mcpServers"]["kuzu-memory"]["args"] == ["mcp"]
        >>> # fixes == ["Fixed kuzu-memory: args ['mcp', 'serve'] -> ['mcp']"]
    """
    fixes: list[str] = []
    result = config.copy()

    # Fix root-level mcpServers
    if "mcpServers" in result and isinstance(result["mcpServers"], dict):
        for server_name, server_config in result["mcpServers"].items():
            if not isinstance(server_config, dict):
                continue

            # Check both fixes before applying (since fixing args changes detection logic)
            needs_args_fix = _needs_mcp_args_fix(server_name, server_config)
            needs_cmd_fix = _needs_command_fix(server_name, server_config)

            # Fix args if needed
            if needs_args_fix:
                old_args = server_config["args"].copy()
                new_args = _fix_mcp_args(old_args)
                result["mcpServers"][server_name]["args"] = new_args
                fixes.append(f"Fixed {server_name}: args {old_args} -> {new_args}")
                logger.debug(f"Fixed broken MCP args in {server_name}: {old_args} -> {new_args}")

            # Fix command if needed (for python -m pattern)
            if needs_cmd_fix:
                old_command = server_config["command"]
                new_command = _fix_command(old_command)
                result["mcpServers"][server_name]["command"] = new_command
                fixes.append(f"Fixed {server_name}: command '{old_command}' -> '{new_command}'")
                logger.debug(
                    f"Fixed broken MCP command in {server_name}: '{old_command}' -> '{new_command}'"
                )

    # Fix project-specific configurations (Claude Hooks pattern)
    if "projects" in result and isinstance(result["projects"], dict):
        for project_path, project_config in result["projects"].items():
            if not isinstance(project_config, dict):
                continue

            if "mcpServers" in project_config and isinstance(project_config["mcpServers"], dict):
                for server_name, server_config in project_config["mcpServers"].items():
                    if not isinstance(server_config, dict):
                        continue

                    # Check both fixes before applying (since fixing args changes detection logic)
                    needs_args_fix = _needs_mcp_args_fix(server_name, server_config)
                    needs_cmd_fix = _needs_command_fix(server_name, server_config)

                    # Fix args if needed
                    if needs_args_fix:
                        old_args = server_config["args"].copy()
                        new_args = _fix_mcp_args(old_args)
                        result["projects"][project_path]["mcpServers"][server_name]["args"] = (
                            new_args
                        )
                        fixes.append(
                            f"Fixed {server_name} in project {project_path}: args {old_args} -> {new_args}"
                        )
                        logger.debug(
                            f"Fixed broken MCP args in {server_name} (project {project_path}): {old_args} -> {new_args}"
                        )

                    # Fix command if needed (for python -m pattern)
                    if needs_cmd_fix:
                        old_command = server_config["command"]
                        new_command = _fix_command(old_command)
                        result["projects"][project_path]["mcpServers"][server_name]["command"] = (
                            new_command
                        )
                        fixes.append(
                            f"Fixed {server_name} in project {project_path}: command '{old_command}' -> '{new_command}'"
                        )
                        logger.debug(
                            f"Fixed broken MCP command in {server_name} (project {project_path}): '{old_command}' -> '{new_command}'"
                        )

    return result, fixes
