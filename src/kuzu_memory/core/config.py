"""
Configuration management for KuzuMemory.

Provides flexible configuration with defaults, validation, and support
for both programmatic and file-based configuration.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]  # yaml has incomplete type stubs


# Local exception to avoid circular dependency
class ConfigurationError(Exception):
    """Configuration-related error."""

    pass


# Removed validation import to avoid circular dependency


@dataclass
class StorageConfig:
    """Storage-related configuration."""

    max_size_mb: float = 50.0
    auto_compact: bool = True
    backup_on_corruption: bool = True
    connection_pool_size: int = 5
    query_timeout_ms: int = 5000
    use_cli_adapter: bool = False  # Use Kuzu CLI adapter for better performance
    max_write_retries: int = (
        10  # Increased from 3 to handle higher concurrency (Kuzu single-write limitation)
    )
    write_retry_backoff_ms: int = 100  # Base backoff time in ms (exponential increase)


@dataclass
class RecallConfig:
    """Memory recall configuration."""

    max_memories: int = 10
    default_strategy: str = "auto"
    strategies: list[str] = field(default_factory=lambda: ["keyword", "entity", "temporal"])
    strategy_weights: dict[str, float] = field(
        default_factory=lambda: {"keyword": 0.4, "entity": 0.4, "temporal": 0.2}
    )
    min_confidence_threshold: float = 0.1
    enable_caching: bool = True
    cache_size: int = 1000
    cache_ttl_seconds: int = 300


@dataclass
class MemoryConfig:
    """Memory creation and user tagging configuration."""

    auto_tag_git_user: bool = True  # Auto-populate user_id from git
    user_id_override: str | None = None  # Manual override for user_id
    enable_multi_user: bool = True  # Enable multi-user features


@dataclass
class ExtractionConfig:
    """Memory extraction configuration."""

    min_memory_length: int = 5
    max_memory_length: int = 1000
    enable_entity_extraction: bool = True
    enable_pattern_compilation: bool = True
    enable_nlp_classification: bool = False  # NLP adds ~90ms, disabled by default for performance
    custom_patterns: dict[str, str] = field(default_factory=dict)
    pattern_weights: dict[str, float] = field(
        default_factory=lambda: {
            "identity": 1.0,
            "preference": 0.9,
            "decision": 0.9,
            "pattern": 0.7,
            "solution": 0.7,
            "status": 0.3,
            "context": 0.5,
        }
    )


@dataclass
class PerformanceConfig:
    """Performance monitoring and limits."""

    max_recall_time_ms: float = 200.0
    max_generation_time_ms: float = 1000.0  # Increased to 1 second for async operations
    enable_performance_monitoring: bool = True
    log_slow_operations: bool = True
    enable_metrics_collection: bool = False


@dataclass
class RetentionConfig:
    """Memory retention policies."""

    enable_auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    custom_retention: dict[str, int | None] = field(default_factory=dict)  # memory_type -> days
    max_total_memories: int = 100_000
    cleanup_batch_size: int = 1000


@dataclass
class GitSyncConfig:
    """Git commit history synchronization configuration."""

    enabled: bool = True
    last_sync_timestamp: str | None = None  # ISO8601 timestamp
    last_commit_sha: str | None = None
    branch_include_patterns: list[str] = field(
        default_factory=lambda: ["main", "master", "develop", "feature/*", "bugfix/*"]
    )
    branch_exclude_patterns: list[str] = field(
        default_factory=lambda: ["tmp/*", "test/*", "experiment/*"]
    )
    significant_prefixes: list[str] = field(
        default_factory=lambda: [
            "feat:",
            "fix:",
            "refactor:",
            "perf:",
            "BREAKING CHANGE",
        ]
    )
    skip_patterns: list[str] = field(
        default_factory=lambda: ["wip", "tmp", "chore:", "style:", "docs:"]
    )
    min_message_length: int = 5  # Allow concise conventional commits like "fix: auth"
    include_merge_commits: bool = True
    auto_sync_on_push: bool = True

    # Automatic sync configuration
    auto_sync_enabled: bool = True  # Enable automatic sync
    auto_sync_on_enhance: bool = True  # Sync when enhance is called
    auto_sync_on_learn: bool = False  # Sync when learn is called (optional, may be slow)
    auto_sync_interval_hours: int = 24  # How often to sync (0 = never, periodic only)
    auto_sync_max_commits: int = 50  # Max commits per auto-sync to prevent blocking


@dataclass
class PruneConfig:
    """Memory pruning configuration."""

    enabled: bool = True  # Enable pruning functionality
    strategy: str = "safe"  # Default pruning strategy (safe, intelligent, aggressive)
    always_backup: bool = True  # Always create backup before pruning
    auto_trigger_db_size_mb: int = 2500  # Auto-trigger pruning at 2.5 GB
    auto_trigger_memory_count: int = 75000  # Auto-trigger pruning at 75k memories
    schedule: str = "weekly"  # Auto-prune schedule (never, weekly, monthly)
    last_prune_timestamp: str | None = None  # ISO8601 timestamp of last prune


@dataclass
class KuzuMemoryConfig:
    """
    Main configuration class for KuzuMemory.

    Provides comprehensive configuration with sensible defaults,
    validation, and support for loading from files.
    """

    # Sub-configurations
    storage: StorageConfig = field(default_factory=StorageConfig)
    recall: RecallConfig = field(default_factory=RecallConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    git_sync: GitSyncConfig = field(default_factory=GitSyncConfig)
    prune: PruneConfig = field(default_factory=PruneConfig)

    # Global settings
    version: str = "1.0"
    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "KuzuMemoryConfig":
        """
        Create configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            KuzuMemoryConfig instance

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Basic validation of the configuration dictionary
            if not isinstance(config_dict, dict):
                raise ValueError("Configuration must be a dictionary")
            validated_config = config_dict

            # Create sub-configurations
            storage_config = StorageConfig()
            if "storage" in validated_config:
                storage_data = validated_config["storage"]
                for key, value in storage_data.items():
                    if hasattr(storage_config, key):
                        setattr(storage_config, key, value)

            recall_config = RecallConfig()
            if "recall" in validated_config:
                recall_data = validated_config["recall"]
                for key, value in recall_data.items():
                    if hasattr(recall_config, key):
                        setattr(recall_config, key, value)

            memory_config = MemoryConfig()
            if "memory" in validated_config:
                memory_data = validated_config["memory"]
                for key, value in memory_data.items():
                    if hasattr(memory_config, key):
                        setattr(memory_config, key, value)

            extraction_config = ExtractionConfig()
            if "extraction" in validated_config:
                extraction_data = validated_config["extraction"]
                for key, value in extraction_data.items():
                    if hasattr(extraction_config, key):
                        setattr(extraction_config, key, value)

            performance_config = PerformanceConfig()
            if "performance" in validated_config:
                performance_data = validated_config["performance"]
                for key, value in performance_data.items():
                    if hasattr(performance_config, key):
                        setattr(performance_config, key, value)

            retention_config = RetentionConfig()
            if "retention" in validated_config:
                retention_data = validated_config["retention"]
                for key, value in retention_data.items():
                    if hasattr(retention_config, key):
                        setattr(retention_config, key, value)

            git_sync_config = GitSyncConfig()
            if "git_sync" in validated_config:
                git_sync_data = validated_config["git_sync"]
                for key, value in git_sync_data.items():
                    if hasattr(git_sync_config, key):
                        setattr(git_sync_config, key, value)

            prune_config = PruneConfig()
            if "prune" in validated_config:
                prune_data = validated_config["prune"]
                for key, value in prune_data.items():
                    if hasattr(prune_config, key):
                        setattr(prune_config, key, value)

            # Create main configuration
            return cls(
                storage=storage_config,
                recall=recall_config,
                memory=memory_config,
                extraction=extraction_config,
                performance=performance_config,
                retention=retention_config,
                git_sync=git_sync_config,
                prune=prune_config,
                version=validated_config.get("version", "1.0"),
                debug=validated_config.get("debug", False),
                log_level=validated_config.get("log_level", "INFO"),
            )

        except Exception as e:
            raise ConfigurationError(f"Failed to create configuration from dict: {e}")

    @classmethod
    def from_file(cls, config_path: str | Path) -> "KuzuMemoryConfig":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            KuzuMemoryConfig instance

        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        try:
            config_path = Path(config_path)

            if not config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {config_path}")

            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict):
                raise ConfigurationError("Configuration file must contain a YAML dictionary")

            return cls.from_dict(config_data)

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration file: {e}")

    @classmethod
    def default(cls) -> "KuzuMemoryConfig":
        """Create configuration with all default values."""
        return cls()

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "version": self.version,
            "debug": self.debug,
            "log_level": self.log_level,
            "storage": {
                "max_size_mb": self.storage.max_size_mb,
                "auto_compact": self.storage.auto_compact,
                "backup_on_corruption": self.storage.backup_on_corruption,
                "connection_pool_size": self.storage.connection_pool_size,
                "query_timeout_ms": self.storage.query_timeout_ms,
                "max_write_retries": self.storage.max_write_retries,
                "write_retry_backoff_ms": self.storage.write_retry_backoff_ms,
            },
            "recall": {
                "max_memories": self.recall.max_memories,
                "default_strategy": self.recall.default_strategy,
                "strategies": self.recall.strategies,
                "strategy_weights": self.recall.strategy_weights,
                "min_confidence_threshold": self.recall.min_confidence_threshold,
                "enable_caching": self.recall.enable_caching,
                "cache_size": self.recall.cache_size,
                "cache_ttl_seconds": self.recall.cache_ttl_seconds,
            },
            "memory": {
                "auto_tag_git_user": self.memory.auto_tag_git_user,
                "user_id_override": self.memory.user_id_override,
                "enable_multi_user": self.memory.enable_multi_user,
            },
            "extraction": {
                "min_memory_length": self.extraction.min_memory_length,
                "max_memory_length": self.extraction.max_memory_length,
                "enable_entity_extraction": self.extraction.enable_entity_extraction,
                "enable_pattern_compilation": self.extraction.enable_pattern_compilation,
                "custom_patterns": self.extraction.custom_patterns,
                "pattern_weights": self.extraction.pattern_weights,
            },
            "performance": {
                "max_recall_time_ms": self.performance.max_recall_time_ms,
                "max_generation_time_ms": self.performance.max_generation_time_ms,
                "enable_performance_monitoring": self.performance.enable_performance_monitoring,
                "log_slow_operations": self.performance.log_slow_operations,
                "enable_metrics_collection": self.performance.enable_metrics_collection,
            },
            "retention": {
                "enable_auto_cleanup": self.retention.enable_auto_cleanup,
                "cleanup_interval_hours": self.retention.cleanup_interval_hours,
                "custom_retention": self.retention.custom_retention,
                "max_total_memories": self.retention.max_total_memories,
                "cleanup_batch_size": self.retention.cleanup_batch_size,
            },
            "git_sync": {
                "enabled": self.git_sync.enabled,
                "last_sync_timestamp": self.git_sync.last_sync_timestamp,
                "last_commit_sha": self.git_sync.last_commit_sha,
                "branch_include_patterns": self.git_sync.branch_include_patterns,
                "branch_exclude_patterns": self.git_sync.branch_exclude_patterns,
                "significant_prefixes": self.git_sync.significant_prefixes,
                "skip_patterns": self.git_sync.skip_patterns,
                "min_message_length": self.git_sync.min_message_length,
                "include_merge_commits": self.git_sync.include_merge_commits,
                "auto_sync_on_push": self.git_sync.auto_sync_on_push,
                "auto_sync_enabled": self.git_sync.auto_sync_enabled,
                "auto_sync_on_enhance": self.git_sync.auto_sync_on_enhance,
                "auto_sync_on_learn": self.git_sync.auto_sync_on_learn,
                "auto_sync_interval_hours": self.git_sync.auto_sync_interval_hours,
                "auto_sync_max_commits": self.git_sync.auto_sync_max_commits,
            },
        }

    def save_to_file(self, config_path: str | Path) -> None:
        """
        Save configuration to YAML file.

        Args:
            config_path: Path where to save the configuration

        Raises:
            ConfigurationError: If file cannot be written
        """
        try:
            config_path = Path(config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration file: {e}")

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate storage config
        if self.storage.max_size_mb <= 0:
            raise ConfigurationError("storage.max_size_mb must be positive")

        if self.storage.connection_pool_size <= 0:
            raise ConfigurationError("storage.connection_pool_size must be positive")

        # Validate recall config
        if self.recall.max_memories <= 0:
            raise ConfigurationError("recall.max_memories must be positive")

        if not self.recall.strategies:
            raise ConfigurationError("recall.strategies cannot be empty")

        valid_strategies = {"keyword", "entity", "temporal", "auto"}
        for strategy in self.recall.strategies:
            if strategy not in valid_strategies:
                raise ConfigurationError(f"Invalid recall strategy: {strategy}")

        # Validate extraction config
        if self.extraction.min_memory_length <= 0:
            raise ConfigurationError("extraction.min_memory_length must be positive")

        if self.extraction.max_memory_length <= self.extraction.min_memory_length:
            raise ConfigurationError(
                "extraction.max_memory_length must be greater than min_memory_length"
            )

        # Validate performance config
        if self.performance.max_recall_time_ms <= 0:
            raise ConfigurationError("performance.max_recall_time_ms must be positive")

        if self.performance.max_generation_time_ms <= 0:
            raise ConfigurationError("performance.max_generation_time_ms must be positive")
