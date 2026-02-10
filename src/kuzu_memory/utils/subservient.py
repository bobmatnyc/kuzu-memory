"""
Subservient mode detection for managed installations.

Provides utilities to detect and manage subservient mode, where kuzu-memory
is installed and managed by a parent framework (like Claude MPM) that handles
hook installation centrally.
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def is_subservient_mode(project_root: Path | None = None) -> bool:
    """
    Check if kuzu-memory is running in subservient mode.

    Detection order (priority):
    1. Environment variable: KUZU_MEMORY_MODE=subservient
    2. Config file: .kuzu-memory-config with mode=subservient

    Args:
        project_root: Project root to check for config file

    Returns:
        True if subservient mode detected, False otherwise
    """
    # Priority 1: Environment variable
    env_mode = os.getenv("KUZU_MEMORY_MODE", "").lower()
    if env_mode in ("subservient", "managed", "delegated"):
        logger.info(f"Subservient mode detected via KUZU_MEMORY_MODE={env_mode}")
        return True

    # Priority 2: Config file (if project_root provided)
    if project_root:
        config_data = get_subservient_config(project_root)
        if config_data:
            managed_by = config_data.get("managed_by", "unknown")
            logger.info(
                f"Subservient mode detected via .kuzu-memory-config (managed_by: {managed_by})"
            )
            return True

    return False


def get_subservient_config(project_root: Path) -> dict[str, Any] | None:
    """
    Read subservient mode configuration from .kuzu-memory-config.

    Args:
        project_root: Project root directory

    Returns:
        Dict with 'mode', 'managed_by', and 'version' keys, or None if not in subservient mode
    """
    config_path = project_root / ".kuzu-memory-config"
    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            logger.warning(".kuzu-memory-config is not a valid YAML dict")
            return None

        mode = config.get("mode", "").lower()
        if mode in ("subservient", "managed"):
            return {
                "mode": mode,
                "managed_by": config.get("managed_by", "unknown"),
                "version": config.get("version", "1.0"),
            }

    except yaml.YAMLError as e:
        logger.debug(f"Failed to parse .kuzu-memory-config: {e}")
    except Exception as e:
        logger.debug(f"Error reading .kuzu-memory-config: {e}")

    return None


def create_subservient_config(
    project_root: Path,
    managed_by: str = "unknown",
) -> Path:
    """
    Create .kuzu-memory-config file to mark subservient mode.

    Args:
        project_root: Project root directory
        managed_by: Name of parent framework managing this installation

    Returns:
        Path to created config file

    Raises:
        OSError: If config file cannot be created
    """
    config_path = project_root / ".kuzu-memory-config"

    config = {
        "mode": "subservient",
        "managed_by": managed_by,
        "version": "1.0",
    }

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)

        logger.info(f"Created subservient config at {config_path} (managed_by={managed_by})")
        return config_path

    except Exception as e:
        logger.error(f"Failed to create subservient config: {e}")
        raise


def remove_subservient_config(project_root: Path) -> bool:
    """
    Remove .kuzu-memory-config file to exit subservient mode.

    Args:
        project_root: Project root directory

    Returns:
        True if file was removed, False if it didn't exist
    """
    config_path = project_root / ".kuzu-memory-config"

    if not config_path.exists():
        logger.debug("No .kuzu-memory-config file to remove")
        return False

    try:
        config_path.unlink()
        logger.info(f"Removed subservient config from {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to remove subservient config: {e}")
        raise
