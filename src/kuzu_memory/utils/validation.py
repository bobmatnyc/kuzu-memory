"""
Input validation utilities for KuzuMemory.

Provides comprehensive validation for user inputs, configuration,
and internal data to prevent errors and security issues.
"""

import re
from pathlib import Path
from typing import Any

from .exceptions import ValidationError

# Constants for validation limits
MAX_TEXT_LENGTH = 100_000  # 100KB of text
MAX_MEMORY_COUNT = 1000  # Max memories per operation
MAX_PATH_LENGTH = 255  # Max file path length
MIN_CONFIDENCE = 0.0  # Min confidence score
MAX_CONFIDENCE = 1.0  # Max confidence score

# Regex patterns for validation
VALID_MEMORY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]{1,64}$")
VALID_ENTITY_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-_\.]{1,100}$")
SAFE_TEXT_PATTERN = re.compile(r"^[\w\s\.\,\!\?\-\(\)\[\]\{\}:;\'\"@#$%&*+=<>/\\|`~]*$", re.UNICODE)


def validate_text_input(
    text: str,
    field_name: str = "text",
    min_length: int = 1,
    max_length: int = MAX_TEXT_LENGTH,
) -> str:
    """
    Validate text input for memory operations.

    Args:
        text: Text to validate
        field_name: Name of the field for error messages
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Cleaned and validated text

    Raises:
        ValidationError: If text is invalid
    """
    if not isinstance(text, str):
        raise ValidationError(field_name, str(type(text)), "must be a string")

    if not text.strip():
        raise ValidationError(field_name, text, "cannot be empty or whitespace-only")

    if len(text) < min_length:
        raise ValidationError(
            field_name,
            f"{len(text)} chars",
            f"must be at least {min_length} characters long",
        )

    if len(text) > max_length:
        raise ValidationError(
            field_name,
            f"{len(text)} chars",
            f"exceeds maximum length of {max_length} characters",
        )

    # Check for potentially dangerous content
    if "\x00" in text:
        raise ValidationError(field_name, "contains null bytes", "null bytes not allowed")

    # Normalize whitespace
    cleaned_text = " ".join(text.split())

    return cleaned_text


def validate_memory_id(memory_id: str) -> str:
    """
    Validate memory ID format.

    Args:
        memory_id: Memory ID to validate

    Returns:
        Validated memory ID

    Raises:
        ValidationError: If ID format is invalid
    """
    if not isinstance(memory_id, str):
        raise ValidationError("memory_id", str(type(memory_id)), "must be a string")

    if not VALID_MEMORY_ID_PATTERN.match(memory_id):
        raise ValidationError(
            "memory_id",
            memory_id,
            "must contain only alphanumeric characters, hyphens, and underscores (1-64 chars)",
        )

    return memory_id


def validate_confidence_score(confidence: float, field_name: str = "confidence") -> float:
    """
    Validate confidence score.

    Args:
        confidence: Confidence score to validate
        field_name: Name of the field for error messages

    Returns:
        Validated confidence score

    Raises:
        ValidationError: If confidence is invalid
    """
    if not isinstance(confidence, int | float):
        raise ValidationError(field_name, str(type(confidence)), "must be a number")

    if not (MIN_CONFIDENCE <= confidence <= MAX_CONFIDENCE):
        raise ValidationError(
            field_name,
            str(confidence),
            f"must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}",
        )

    return float(confidence)


def validate_database_path(db_path: str | Path) -> Path:
    """
    Validate database path.

    Args:
        db_path: Database path to validate

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path is invalid
    """
    if isinstance(db_path, str):
        if len(db_path.strip()) == 0:
            raise ValidationError("db_path", db_path, "cannot be empty")
        db_path = Path(db_path)
    elif not isinstance(db_path, Path):
        raise ValidationError("db_path", str(type(db_path)), "must be a string or Path object")

    # Convert to absolute path for validation
    abs_path = db_path.resolve()

    if len(str(abs_path)) > MAX_PATH_LENGTH:
        raise ValidationError(
            "db_path", str(abs_path), f"exceeds maximum length of {MAX_PATH_LENGTH}"
        )

    # Check if parent directory is writable (if it exists)
    parent_dir = abs_path.parent
    if parent_dir.exists() and not parent_dir.is_dir():
        raise ValidationError(
            "db_path", str(parent_dir), "parent path exists but is not a directory"
        )

    return db_path


def validate_config_dict(config: dict[str, Any]) -> dict[str, Any]:
    """
    Validate configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Validated configuration dictionary

    Raises:
        ValidationError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ValidationError("config", str(type(config)), "must be a dictionary")

    # Validate specific configuration keys
    validated_config = {}

    # Storage configuration
    if "storage" in config:
        storage_config = config["storage"]
        if not isinstance(storage_config, dict):
            raise ValidationError(
                "config.storage", str(type(storage_config)), "must be a dictionary"
            )

        if "max_size_mb" in storage_config:
            max_size = storage_config["max_size_mb"]
            if not isinstance(max_size, int | float) or max_size <= 0:
                raise ValidationError(
                    "config.storage.max_size_mb",
                    str(max_size),
                    "must be a positive number",
                )

        validated_config["storage"] = storage_config

    # Recall configuration
    if "recall" in config:
        recall_config = config["recall"]
        if not isinstance(recall_config, dict):
            raise ValidationError("config.recall", str(type(recall_config)), "must be a dictionary")

        if "max_memories" in recall_config:
            max_memories = recall_config["max_memories"]
            if not isinstance(max_memories, int) or max_memories <= 0:
                raise ValidationError(
                    "config.recall.max_memories",
                    str(max_memories),
                    "must be a positive integer",
                )

        validated_config["recall"] = recall_config

    # Copy other valid keys
    for key, value in config.items():
        if key not in validated_config:
            validated_config[key] = value

    return validated_config


def validate_entity_name(entity_name: str) -> str:
    """
    Validate entity name.

    Args:
        entity_name: Entity name to validate

    Returns:
        Validated entity name

    Raises:
        ValidationError: If entity name is invalid
    """
    if not isinstance(entity_name, str):
        raise ValidationError("entity_name", str(type(entity_name)), "must be a string")

    if not entity_name.strip():
        raise ValidationError("entity_name", entity_name, "cannot be empty or whitespace-only")

    if not VALID_ENTITY_NAME_PATTERN.match(entity_name):
        raise ValidationError(
            "entity_name",
            entity_name,
            "contains invalid characters or exceeds length limit (100 chars)",
        )

    return entity_name.strip()


def validate_memory_list(memories: list[Any], max_count: int = MAX_MEMORY_COUNT) -> list[Any]:
    """
    Validate list of memories.

    Args:
        memories: List of memories to validate
        max_count: Maximum allowed count

    Returns:
        Validated memory list

    Raises:
        ValidationError: If memory list is invalid
    """
    if not isinstance(memories, list):
        raise ValidationError("memories", str(type(memories)), "must be a list")

    if len(memories) > max_count:
        raise ValidationError(
            "memories",
            f"{len(memories)} items",
            f"exceeds maximum count of {max_count}",
        )

    return memories


def sanitize_for_database(text: str) -> str:
    """
    Sanitize text for safe database storage.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text safe for database storage
    """
    # Remove null bytes and control characters
    sanitized = "".join(char for char in text if ord(char) >= 32 or char in "\t\n\r")

    # Normalize whitespace
    sanitized = " ".join(sanitized.split())

    # Truncate if too long
    if len(sanitized) > MAX_TEXT_LENGTH:
        sanitized = sanitized[: MAX_TEXT_LENGTH - 3] + "..."

    return sanitized
