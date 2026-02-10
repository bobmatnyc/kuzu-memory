"""
Configuration loading utilities for KuzuMemory.

Provides utilities for loading configuration from files, environment variables,
and providing sensible defaults with validation.
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from ..core.config import KuzuMemoryConfig
from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Configuration loader with support for multiple sources.

    Loads configuration from files, environment variables, and provides
    defaults with proper validation and error handling.
    """

    def __init__(self) -> None:
        """Initialize configuration loader."""
        self.env_prefix = "KUZU_MEMORY_"

        # Default configuration search paths
        self.default_config_paths = [
            Path.home() / ".kuzu-memory" / "config.yaml",
            Path.home() / ".kuzu-memory" / "config.yml",
            Path("kuzu_memory_config.yaml"),
            Path("kuzu_memory_config.yml"),
            # Legacy location for backward compatibility
            Path(".kuzu_memory/config.yaml"),
            Path("/etc/kuzu_memory/config.yaml"),
        ]

    def load_config(
        self,
        config_path: str | Path | None = None,
        config_dict: dict[str, Any] | None = None,
        load_from_env: bool = True,
        auto_discover: bool = True,
    ) -> KuzuMemoryConfig:
        """
        Load configuration from multiple sources.

        Args:
            config_path: Explicit path to configuration file
            config_dict: Configuration dictionary to use
            load_from_env: Whether to load from environment variables
            auto_discover: Whether to auto-discover config files

        Returns:
            KuzuMemoryConfig instance

        Raises:
            ConfigurationError: If configuration loading fails
        """
        try:
            # Start with default configuration
            config_data = self._get_default_config()

            # Load from file if specified or auto-discovered
            file_config = None
            if config_path:
                file_config = self._load_from_file(Path(config_path))
            elif auto_discover:
                file_config = self._auto_discover_config()

            if file_config:
                config_data = self._merge_configs(config_data, file_config)

            # Load from environment variables
            if load_from_env:
                env_config = self._load_from_environment()
                if env_config:
                    config_data = self._merge_configs(config_data, env_config)

            # Override with explicit config dict
            if config_dict:
                config_data = self._merge_configs(config_data, config_dict)

            # Create and validate configuration
            config = KuzuMemoryConfig.from_dict(config_data)
            config.validate()

            logger.info("Configuration loaded successfully")
            return config

        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration values."""
        return {
            "version": "1.0",
            "debug": False,
            "log_level": "INFO",
            "storage": {
                "max_size_mb": 50.0,
                "auto_compact": True,
                "backup_on_corruption": True,
                "connection_pool_size": 5,
                "query_timeout_ms": 5000,
            },
            "recall": {
                "max_memories": 10,
                "default_strategy": "auto",
                "strategies": ["keyword", "entity", "temporal"],
                "strategy_weights": {"keyword": 0.4, "entity": 0.4, "temporal": 0.2},
                "min_confidence_threshold": 0.1,
                "enable_caching": True,
                "cache_size": 1000,
                "cache_ttl_seconds": 300,
            },
            "extraction": {
                "min_memory_length": 5,
                "max_memory_length": 1000,
                "enable_entity_extraction": True,
                "enable_pattern_compilation": True,
                "custom_patterns": {},
                "pattern_weights": {
                    "identity": 1.0,
                    "preference": 0.9,
                    "decision": 0.9,
                    "pattern": 0.7,
                    "solution": 0.7,
                    "status": 0.3,
                    "context": 0.5,
                },
            },
            "performance": {
                "max_recall_time_ms": 100.0,
                "max_generation_time_ms": 100.0,
                "enable_performance_monitoring": True,
                "log_slow_operations": True,
                "enable_metrics_collection": False,
            },
            "retention": {
                "enable_auto_cleanup": True,
                "cleanup_interval_hours": 24,
                "custom_retention": {},
                "max_total_memories": 100000,
                "cleanup_batch_size": 1000,
            },
        }

    def _load_from_file(self, config_path: Path) -> dict[str, Any] | None:
        """Load configuration from a YAML file."""
        try:
            if not config_path.exists():
                logger.warning(f"Configuration file not found: {config_path}")
                return None

            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict):
                raise ConfigurationError(
                    f"Configuration file must contain a YAML dictionary: {config_path}"
                )

            logger.info(f"Loaded configuration from {config_path}")
            return config_data

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration file {config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration file {config_path}: {e}")

    def _auto_discover_config(self) -> dict[str, Any] | None:
        """Auto-discover configuration file from default paths."""
        for config_path in self.default_config_paths:
            if config_path.exists():
                logger.info(f"Auto-discovered configuration file: {config_path}")
                return self._load_from_file(config_path)

        logger.debug("No configuration file auto-discovered")
        return None

    def _load_from_environment(self) -> dict[str, Any] | None:
        """Load configuration from environment variables."""
        env_config: dict[str, Any] = {}

        # Map environment variables to config structure
        env_mappings = {
            f"{self.env_prefix}DEBUG": ("debug", self._parse_bool),
            f"{self.env_prefix}LOG_LEVEL": ("log_level", str),
            f"{self.env_prefix}DB_MAX_SIZE_MB": ("storage.max_size_mb", float),
            f"{self.env_prefix}DB_AUTO_COMPACT": (
                "storage.auto_compact",
                self._parse_bool,
            ),
            f"{self.env_prefix}DB_CONNECTION_POOL_SIZE": (
                "storage.connection_pool_size",
                int,
            ),
            f"{self.env_prefix}DB_QUERY_TIMEOUT_MS": ("storage.query_timeout_ms", int),
            f"{self.env_prefix}RECALL_MAX_MEMORIES": ("recall.max_memories", int),
            f"{self.env_prefix}RECALL_DEFAULT_STRATEGY": (
                "recall.default_strategy",
                str,
            ),
            f"{self.env_prefix}RECALL_ENABLE_CACHING": (
                "recall.enable_caching",
                self._parse_bool,
            ),
            f"{self.env_prefix}RECALL_CACHE_SIZE": ("recall.cache_size", int),
            f"{self.env_prefix}RECALL_CACHE_TTL_SECONDS": (
                "recall.cache_ttl_seconds",
                int,
            ),
            f"{self.env_prefix}EXTRACTION_MIN_LENGTH": (
                "extraction.min_memory_length",
                int,
            ),
            f"{self.env_prefix}EXTRACTION_MAX_LENGTH": (
                "extraction.max_memory_length",
                int,
            ),
            f"{self.env_prefix}EXTRACTION_ENABLE_ENTITIES": (
                "extraction.enable_entity_extraction",
                self._parse_bool,
            ),
            f"{self.env_prefix}EXTRACTION_COMPILE_PATTERNS": (
                "extraction.enable_pattern_compilation",
                self._parse_bool,
            ),
            f"{self.env_prefix}PERFORMANCE_MAX_RECALL_TIME_MS": (
                "performance.max_recall_time_ms",
                float,
            ),
            f"{self.env_prefix}PERFORMANCE_MAX_GENERATION_TIME_MS": (
                "performance.max_generation_time_ms",
                float,
            ),
            f"{self.env_prefix}PERFORMANCE_ENABLE_MONITORING": (
                "performance.enable_performance_monitoring",
                self._parse_bool,
            ),
            f"{self.env_prefix}PERFORMANCE_LOG_SLOW_OPS": (
                "performance.log_slow_operations",
                self._parse_bool,
            ),
            f"{self.env_prefix}RETENTION_ENABLE_AUTO_CLEANUP": (
                "retention.enable_auto_cleanup",
                self._parse_bool,
            ),
            f"{self.env_prefix}RETENTION_CLEANUP_INTERVAL_HOURS": (
                "retention.cleanup_interval_hours",
                int,
            ),
            f"{self.env_prefix}RETENTION_MAX_TOTAL_MEMORIES": (
                "retention.max_total_memories",
                int,
            ),
        }

        found_env_vars = False
        for env_var, (config_path, parser) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    parsed_value: Any = parser(value)  # type: ignore[operator]  # Parser is Callable[[str], Any]
                    self._set_nested_config(env_config, config_path, parsed_value)
                    found_env_vars = True
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse environment variable {env_var}={value}: {e}")

        if found_env_vars:
            logger.info("Loaded configuration from environment variables")
            return env_config

        return None

    def _parse_bool(self, value: str) -> bool:
        """Parse boolean value from string."""
        return value.lower() in ("true", "1", "yes", "on", "enabled")

    def _set_nested_config(self, config: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested configuration value using dot notation."""
        keys = path.split(".")
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _merge_configs(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge two configuration dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def save_config(self, config: KuzuMemoryConfig, config_path: Path) -> None:
        """
        Save configuration to a YAML file.

        Args:
            config: Configuration to save
            config_path: Path where to save the configuration

        Raises:
            ConfigurationError: If saving fails
        """
        try:
            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert config to dictionary
            config_dict = config.to_dict()

            # Save to YAML file
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2, sort_keys=True)

            logger.info(f"Configuration saved to {config_path}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {config_path}: {e}")

    def create_example_config(self, config_path: Path) -> None:
        """
        Create an example configuration file with all options documented.

        Args:
            config_path: Path where to create the example config
        """
        try:
            # Get default configuration
            default_config = KuzuMemoryConfig.default()

            # Save with comments
            self.save_config(default_config, config_path)

            logger.info(f"Example configuration created at {config_path}")

        except Exception as e:
            raise ConfigurationError(f"Failed to create example configuration: {e}")

    def get_config_info(self, project_root: Path | None = None) -> dict[str, Any]:
        """
        Get information about the loaded configuration.

        Args:
            project_root: Project root directory to check for config files

        Returns:
            Dictionary with config information including source and path
        """
        info = {"source": "default", "path": None}

        if project_root:
            # Check for project-specific config
            project_config_paths = [
                project_root / ".kuzu-memory" / "config.yaml",
                project_root / ".kuzu-memory" / "config.yml",
                project_root / ".kuzu-memory" / "config.json",
            ]

            for config_path in project_config_paths:
                if config_path.exists():
                    info["source"] = "project"
                    info["path"] = str(config_path)
                    return info

        # Check default paths
        for config_path in self.default_config_paths:
            if config_path.exists():
                info["source"] = "user"
                info["path"] = str(config_path)
                return info

        return info


# Global config loader instance
_global_loader: ConfigLoader | None = None


def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader instance."""
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfigLoader()
    return _global_loader


def load_config_from_file(config_path: str | Path) -> KuzuMemoryConfig:
    """
    Convenience function to load configuration from a file.

    Args:
        config_path: Path to configuration file

    Returns:
        KuzuMemoryConfig instance
    """
    return get_config_loader().load_config(config_path=config_path)


def load_config_auto() -> KuzuMemoryConfig:
    """
    Convenience function to auto-load configuration from default sources.

    Returns:
        KuzuMemoryConfig instance
    """
    return get_config_loader().load_config()
