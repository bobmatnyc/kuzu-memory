"""
Unit tests for project root caching optimization in hooks_commands.

Tests the caching mechanism that reduces project root discovery
from ~100ms to ~5ms by caching the result for 5 minutes.
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from kuzu_memory.cli.hooks_commands import (
    _cache_project_root,
    _get_cached_project_root,
)


def test_cache_project_root_writes_valid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that _cache_project_root writes valid JSON with timestamp."""
    cache_file = tmp_path / ".kuzu_project_root_cache.json"
    monkeypatch.setattr(
        "kuzu_memory.cli.hooks_commands.Path",
        lambda x: (
            cache_file.parent / cache_file.name
            if x == "/tmp/.kuzu_project_root_cache.json"
            else Path(x)
        ),
    )

    project_root = tmp_path / "my-project"
    project_root.mkdir()

    with patch("kuzu_memory.cli.hooks_commands.Path") as mock_path:
        mock_path.return_value = cache_file
        _cache_project_root(project_root)

    # Verify cache file was created with valid JSON
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    assert "path" in data
    assert "timestamp" in data
    assert data["path"] == str(project_root)
    assert isinstance(data["timestamp"], int | float)


def test_get_cached_project_root_returns_none_when_missing(tmp_path: Path) -> None:
    """Test that _get_cached_project_root returns None when cache doesn't exist."""
    cache_file = tmp_path / ".kuzu_project_root_cache.json"

    with patch("kuzu_memory.cli.hooks_commands.Path") as mock_path:
        mock_path.return_value = cache_file
        result = _get_cached_project_root()

    assert result is None


def test_get_cached_project_root_returns_none_when_expired(tmp_path: Path) -> None:
    """Test that _get_cached_project_root returns None when cache is expired (>5 min)."""
    cache_file = tmp_path / ".kuzu_project_root_cache.json"
    project_root = tmp_path / "my-project"
    project_root.mkdir()

    # Write expired cache (6 minutes old)
    expired_timestamp = time.time() - 360  # 6 minutes
    cache_file.write_text(json.dumps({"path": str(project_root), "timestamp": expired_timestamp}))

    with patch("kuzu_memory.cli.hooks_commands.Path") as mock_path:
        mock_path.return_value = cache_file
        result = _get_cached_project_root()

    assert result is None


def test_get_cached_project_root_returns_path_when_valid(tmp_path: Path) -> None:
    """Test that _get_cached_project_root returns cached path when valid and fresh."""
    cache_file = tmp_path / ".kuzu_project_root_cache.json"
    project_root = tmp_path / "my-project"
    project_root.mkdir()

    # Write fresh cache (1 minute old)
    fresh_timestamp = time.time() - 60  # 1 minute
    cache_file.write_text(json.dumps({"path": str(project_root), "timestamp": fresh_timestamp}))

    with patch("kuzu_memory.cli.hooks_commands.Path") as mock_path:
        mock_path.return_value = cache_file

        # Mock the Path() constructor to return real paths
        def path_constructor(path_str: str) -> Path:
            if path_str == "/tmp/.kuzu_project_root_cache.json":
                return cache_file
            return Path(path_str)

        mock_path.side_effect = path_constructor
        result = _get_cached_project_root()

    assert result == project_root


def test_get_cached_project_root_returns_none_when_path_missing(tmp_path: Path) -> None:
    """Test that _get_cached_project_root returns None when cached path no longer exists."""
    cache_file = tmp_path / ".kuzu_project_root_cache.json"
    nonexistent_path = tmp_path / "deleted-project"

    # Write cache pointing to nonexistent path (don't create the directory)
    cache_file.write_text(json.dumps({"path": str(nonexistent_path), "timestamp": time.time()}))

    with patch("kuzu_memory.cli.hooks_commands.Path") as mock_path:
        # Mock the Path() constructor
        def path_constructor(path_str: str) -> Path:
            if path_str == "/tmp/.kuzu_project_root_cache.json":
                return cache_file
            # Return real Path for nonexistent path (it won't exist)
            return Path(path_str)

        mock_path.side_effect = path_constructor
        result = _get_cached_project_root()

    # Should return None because nonexistent_path doesn't exist
    assert result is None


def test_cache_handles_json_decode_error_gracefully(tmp_path: Path) -> None:
    """Test that _get_cached_project_root handles corrupted JSON gracefully."""
    cache_file = tmp_path / ".kuzu_project_root_cache.json"

    # Write invalid JSON
    cache_file.write_text("{ invalid json }")

    with patch("kuzu_memory.cli.hooks_commands.Path") as mock_path:
        mock_path.return_value = cache_file
        result = _get_cached_project_root()

    # Should return None instead of raising exception
    assert result is None


def test_cache_handles_os_error_gracefully(tmp_path: Path) -> None:
    """Test that _cache_project_root handles OS errors gracefully."""
    # Create a directory where the cache file should be (causes write error)
    cache_dir = tmp_path / "cache_as_dir"
    cache_dir.mkdir()

    project_root = tmp_path / "my-project"
    project_root.mkdir()

    with patch("kuzu_memory.cli.hooks_commands.Path") as mock_path:
        # Make Path() return the directory when asked for cache file
        mock_path.return_value = cache_dir

        # Should not raise exception (silently fails)
        _cache_project_root(project_root)

    # Cache file should not exist (write failed silently)
    assert not (cache_dir / ".kuzu_project_root_cache.json").exists()


def test_cache_ttl_is_five_minutes() -> None:
    """Test that cache TTL is configured for 5 minutes (300 seconds)."""
    # This is a documentation test to ensure the TTL constant is correct
    # The actual value is checked in the implementation
    import inspect

    from kuzu_memory.cli.hooks_commands import _get_cached_project_root

    source = inspect.getsource(_get_cached_project_root)
    # Verify TTL is 300 seconds (5 minutes) in the source code
    assert "300" in source or 'time.time() - data.get("timestamp", 0) < 300' in source
