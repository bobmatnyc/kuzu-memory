"""
TOML utility functions for MCP configuration management.

Provides TOML loading, saving, merging, and validation for MCP configs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

# Python 3.11+ has tomllib built-in (read-only)
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # Fallback to tomli for Python <3.11

# TOML writing requires third-party library
try:
    import tomli_w
except ImportError:
    raise ImportError("tomli_w is required for TOML writing. Install with: pip install tomli-w")

logger = logging.getLogger(__name__)


class TOMLConfigError(Exception):
    """Raised when TOML configuration operations fail."""

    pass


def load_toml_config(file_path: Path) -> dict[str, Any]:
    """
    Load TOML configuration from file.

    Args:
        file_path: Path to TOML file

    Returns:
        Configuration dictionary

    Raises:
        TOMLConfigError: If file cannot be loaded or parsed
    """
    try:
        if not file_path.exists():
            return {}

        # TOML requires binary mode
        with open(file_path, "rb") as f:
            config = tomllib.load(f)
            logger.info(f"Loaded TOML configuration from {file_path}")
            return config
    except tomllib.TOMLDecodeError as e:
        raise TOMLConfigError(f"Invalid TOML in {file_path}: {e}")
    except Exception as e:
        raise TOMLConfigError(f"Failed to load {file_path}: {e}")


def save_toml_config(file_path: Path, config: dict[str, Any]) -> None:
    """
    Save TOML configuration to file.

    Args:
        file_path: Path to save to
        config: Configuration dictionary

    Raises:
        TOMLConfigError: If file cannot be saved
    """
    try:
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write TOML with tomli_w (binary mode)
        with open(file_path, "wb") as f:
            tomli_w.dump(config, f)

        logger.info(f"Saved TOML configuration to {file_path}")
    except Exception as e:
        raise TOMLConfigError(f"Failed to save {file_path}: {e}")


def merge_toml_configs(
    existing: dict[str, Any], new: dict[str, Any], preserve_existing: bool = True
) -> dict[str, Any]:
    """
    Merge two TOML configurations, preserving existing MCP servers.

    Delegates to merge_json_configs since logic is format-agnostic.

    Args:
        existing: Existing configuration dictionary
        new: New configuration to merge in
        preserve_existing: If True, preserve existing server configs

    Returns:
        Merged configuration dictionary
    """
    from .json_utils import merge_json_configs

    return merge_json_configs(existing, new, preserve_existing)


def validate_toml_mcp_config(config: dict[str, Any]) -> list[str]:
    """
    Validate MCP server configuration from TOML.

    Delegates to validate_mcp_config since logic is format-agnostic.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    from .json_utils import validate_mcp_config

    return validate_mcp_config(config)
