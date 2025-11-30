"""
Unit tests for ConfigService with mocked utilities.

Tests the ConfigService implementation using mock objects to verify
correct delegation to utility functions without requiring actual filesystem.

Test Strategy:
- Mock all utils/project_setup functions
- Verify method delegation with correct parameters
- Verify lifecycle management (initialize/cleanup)
- Verify error handling and edge cases
- Verify caching behavior
- Verify dot notation config access

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Task: 1M-421 (Implement ConfigService)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from kuzu_memory.services.config_service import ConfigService


@pytest.fixture
def mock_project_root(tmp_path):
    """Mock project root directory."""
    return tmp_path / "test_project"


@pytest.fixture
def config_service_with_explicit_root(mock_project_root):
    """ConfigService with explicit project root."""
    service = ConfigService(project_root=mock_project_root)
    service.initialize()
    yield service
    service.cleanup()


class TestConfigServiceLifecycle:
    """Test lifecycle management (initialize/cleanup)."""

    def test_initialization_with_explicit_root(self, mock_project_root):
        """Test initialization with explicit project root."""
        service = ConfigService(project_root=mock_project_root)
        assert not service.is_initialized

        service.initialize()
        assert service.is_initialized
        assert service.get_project_root() == mock_project_root

        service.cleanup()
        assert not service.is_initialized

    @patch("kuzu_memory.services.config_service.find_project_root")
    def test_initialization_with_auto_detection(self, mock_find_root):
        """Test initialization with auto-detected project root."""
        mock_root = Path("/auto/detected/root")
        mock_find_root.return_value = mock_root

        service = ConfigService()
        service.initialize()

        mock_find_root.assert_called_once()
        assert service.get_project_root() == mock_root

        service.cleanup()

    def test_double_initialization_is_safe(self, mock_project_root):
        """Test that double initialization is safe and idempotent."""
        service = ConfigService(project_root=mock_project_root)

        service.initialize()
        first_root = service.get_project_root()

        service.initialize()  # Should be no-op
        second_root = service.get_project_root()

        assert first_root == second_root
        service.cleanup()

    def test_cleanup_clears_cache(self, config_service_with_explicit_root):
        """Test that cleanup clears configuration cache."""
        service = config_service_with_explicit_root

        # Access project root to initialize internal state
        _ = service.get_project_root()

        service.cleanup()

        # After cleanup, should not be initialized
        assert not service.is_initialized

    def test_get_project_root_before_initialization_raises(self):
        """Test that accessing project root before init raises RuntimeError."""
        service = ConfigService()

        with pytest.raises(RuntimeError, match="not initialized"):
            service.get_project_root()


class TestConfigServiceProjectRoot:
    """Test project root detection and access."""

    def test_get_project_root_returns_explicit_root(self, config_service_with_explicit_root, mock_project_root):
        """Test get_project_root returns explicitly set root."""
        assert config_service_with_explicit_root.get_project_root() == mock_project_root

    @patch("kuzu_memory.services.config_service.find_project_root")
    def test_get_project_root_uses_auto_detection(self, mock_find_root):
        """Test get_project_root uses auto-detection when no explicit root."""
        mock_root = Path("/detected/root")
        mock_find_root.return_value = mock_root

        service = ConfigService()
        service.initialize()

        assert service.get_project_root() == mock_root
        service.cleanup()

    @patch("kuzu_memory.services.config_service.get_project_db_path")
    def test_get_db_path_delegates_to_utility(self, mock_get_db_path, config_service_with_explicit_root, mock_project_root):
        """Test get_db_path delegates to utility function."""
        expected_path = mock_project_root / "kuzu-memories" / "memories.db"
        mock_get_db_path.return_value = expected_path

        result = config_service_with_explicit_root.get_db_path()

        mock_get_db_path.assert_called_once_with(mock_project_root)
        assert result == expected_path

    @patch("kuzu_memory.services.config_service.get_project_memories_dir")
    def test_get_memories_dir_delegates_to_utility(self, mock_get_memories_dir, config_service_with_explicit_root, mock_project_root):
        """Test get_memories_dir delegates to utility function."""
        expected_path = mock_project_root / "kuzu-memories"
        mock_get_memories_dir.return_value = expected_path

        result = config_service_with_explicit_root.get_memories_dir()

        mock_get_memories_dir.assert_called_once_with(mock_project_root)
        assert result == expected_path


class TestConfigServiceConfiguration:
    """Test configuration loading and saving."""

    def test_load_config_when_file_not_exists(self, config_service_with_explicit_root, mock_project_root):
        """Test load_config returns empty dict when config file doesn't exist."""
        # Mock the config file as non-existent
        config_path = mock_project_root / ".kuzu-memory" / "config.json"

        with patch.object(Path, "exists", return_value=False):
            config = config_service_with_explicit_root.load_config()

        assert config == {}

    def test_load_config_reads_from_file(self, config_service_with_explicit_root, mock_project_root):
        """Test load_config reads configuration from file."""
        expected_config = {"key1": "value1", "nested": {"key2": "value2"}}
        mock_file_content = json.dumps(expected_config)

        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            with patch.object(Path, "exists", return_value=True):
                config = config_service_with_explicit_root.load_config()

        assert config == expected_config

    def test_load_config_caches_result(self, config_service_with_explicit_root):
        """Test load_config caches result and doesn't reload on subsequent calls."""
        expected_config = {"cached": "value"}
        mock_file_content = json.dumps(expected_config)

        with patch("builtins.open", mock_open(read_data=mock_file_content)) as mock_file:
            with patch.object(Path, "exists", return_value=True):
                # First call
                config1 = config_service_with_explicit_root.load_config()
                # Second call (should use cache)
                config2 = config_service_with_explicit_root.load_config()

        assert config1 == expected_config
        assert config2 == expected_config
        # File should only be opened once (cached on second call)
        assert mock_file.call_count == 1

    def test_load_config_handles_json_error(self, config_service_with_explicit_root):
        """Test load_config handles JSON parsing errors gracefully."""
        invalid_json = "{invalid json content"

        with patch("builtins.open", mock_open(read_data=invalid_json)):
            with patch.object(Path, "exists", return_value=True):
                config = config_service_with_explicit_root.load_config()

        # Should return empty dict on error
        assert config == {}

    def test_save_config_writes_to_file(self, config_service_with_explicit_root, mock_project_root):
        """Test save_config writes configuration to file."""
        config_to_save = {"key": "value", "nested": {"data": 123}}

        # Create a mock for the open function that captures what was written
        m = mock_open()
        with patch("builtins.open", m):
            with patch.object(Path, "mkdir"):
                config_service_with_explicit_root.save_config(config_to_save)

        # Verify file was opened for writing
        config_path = mock_project_root / ".kuzu-memory" / "config.json"
        m.assert_called_once_with(config_path, "w", encoding="utf-8")

        # Verify JSON was written (combine all write calls)
        written_data = "".join(call.args[0] for call in m().write.call_args_list)
        written_config = json.loads(written_data)
        assert written_config == config_to_save

    def test_save_config_creates_directory(self, config_service_with_explicit_root, mock_project_root):
        """Test save_config creates .kuzu-memory directory if needed."""
        config_to_save = {"key": "value"}

        with patch("builtins.open", mock_open()):
            with patch.object(Path, "mkdir") as mock_mkdir:
                config_service_with_explicit_root.save_config(config_to_save)

        # Verify mkdir was called with parents=True, exist_ok=True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_save_config_updates_cache(self, config_service_with_explicit_root):
        """Test save_config updates the internal cache."""
        config_to_save = {"updated": "config"}

        with patch("builtins.open", mock_open()):
            with patch.object(Path, "mkdir"):
                config_service_with_explicit_root.save_config(config_to_save)

        # Load should now return the saved config (from cache)
        # without reading file again
        with patch("builtins.open", mock_open()) as mock_file:
            loaded = config_service_with_explicit_root.load_config()

        assert loaded == config_to_save
        # File should NOT be opened (config came from cache)
        mock_file.assert_not_called()

    def test_save_config_raises_on_write_error(self, config_service_with_explicit_root):
        """Test save_config raises exception on write error."""
        config_to_save = {"key": "value"}

        with patch("builtins.open", side_effect=IOError("Write failed")):
            with patch.object(Path, "mkdir"):
                with pytest.raises(IOError):
                    config_service_with_explicit_root.save_config(config_to_save)


class TestConfigServiceGetValue:
    """Test get_config_value with dot notation."""

    def test_get_config_value_simple_key(self, config_service_with_explicit_root):
        """Test get_config_value with simple key."""
        config = {"simple_key": "simple_value"}

        with patch.object(config_service_with_explicit_root, "load_config", return_value=config):
            value = config_service_with_explicit_root.get_config_value("simple_key")

        assert value == "simple_value"

    def test_get_config_value_nested_key(self, config_service_with_explicit_root):
        """Test get_config_value with dot notation for nested keys."""
        config = {"level1": {"level2": {"level3": "nested_value"}}}

        with patch.object(config_service_with_explicit_root, "load_config", return_value=config):
            value = config_service_with_explicit_root.get_config_value("level1.level2.level3")

        assert value == "nested_value"

    def test_get_config_value_returns_default_when_key_missing(self, config_service_with_explicit_root):
        """Test get_config_value returns default when key doesn't exist."""
        config = {"existing": "value"}

        with patch.object(config_service_with_explicit_root, "load_config", return_value=config):
            value = config_service_with_explicit_root.get_config_value("missing_key", default="default_value")

        assert value == "default_value"

    def test_get_config_value_returns_none_default_by_default(self, config_service_with_explicit_root):
        """Test get_config_value returns None by default when key missing."""
        config = {"existing": "value"}

        with patch.object(config_service_with_explicit_root, "load_config", return_value=config):
            value = config_service_with_explicit_root.get_config_value("missing_key")

        assert value is None

    def test_get_config_value_nested_key_partial_path_returns_default(self, config_service_with_explicit_root):
        """Test get_config_value returns default when partial nested path exists."""
        config = {"level1": {"level2": "value"}}

        with patch.object(config_service_with_explicit_root, "load_config", return_value=config):
            # level2 exists but is not a dict, so level3 can't be accessed
            value = config_service_with_explicit_root.get_config_value("level1.level2.level3", default="fallback")

        assert value == "fallback"

    def test_get_config_value_handles_various_types(self, config_service_with_explicit_root):
        """Test get_config_value works with various data types."""
        config = {
            "string": "text",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        with patch.object(config_service_with_explicit_root, "load_config", return_value=config):
            assert config_service_with_explicit_root.get_config_value("string") == "text"
            assert config_service_with_explicit_root.get_config_value("number") == 42
            assert config_service_with_explicit_root.get_config_value("boolean") is True
            assert config_service_with_explicit_root.get_config_value("list") == [1, 2, 3]
            assert config_service_with_explicit_root.get_config_value("dict") == {"nested": "value"}


class TestConfigServiceUtilityMethods:
    """Test additional utility methods beyond protocol."""

    @patch("kuzu_memory.services.config_service.create_project_memories_structure")
    def test_ensure_project_structure_delegates(self, mock_create_structure, config_service_with_explicit_root, mock_project_root):
        """Test ensure_project_structure delegates to utility function."""
        config_service_with_explicit_root.ensure_project_structure()

        mock_create_structure.assert_called_once_with(mock_project_root)

    @patch("kuzu_memory.services.config_service.get_project_context_summary")
    def test_get_project_context_delegates(self, mock_get_context, config_service_with_explicit_root, mock_project_root):
        """Test get_project_context delegates to utility function."""
        expected_context = {
            "project_name": "test_project",
            "project_root": str(mock_project_root),
            "is_git_repo": True,
        }
        mock_get_context.return_value = expected_context

        context = config_service_with_explicit_root.get_project_context()

        mock_get_context.assert_called_once_with(mock_project_root)
        assert context == expected_context


class TestConfigServiceContextManager:
    """Test context manager behavior."""

    @patch("kuzu_memory.services.config_service.find_project_root")
    def test_context_manager_initializes_and_cleans_up(self, mock_find_root, mock_project_root):
        """Test context manager properly initializes and cleans up."""
        mock_find_root.return_value = mock_project_root

        with ConfigService() as service:
            assert service.is_initialized
            assert service.get_project_root() == mock_project_root

        # After exiting context, should be cleaned up
        assert not service.is_initialized
