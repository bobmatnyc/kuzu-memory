#!/usr/bin/env python3
"""
Unit tests for Claude Code hooks.

Tests both kuzu_enhance.py and kuzu_learn.py hook functions.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "hooks"))

# Import hook modules
import kuzu_enhance
import kuzu_learn


class TestKuzuEnhanceHook:
    """Test kuzu_enhance.py hook functions."""

    def test_validate_input_valid_prompt(self):
        """Test validation with valid prompt."""
        input_data = {"prompt": "Test prompt"}
        result = kuzu_enhance.validate_input(input_data)
        assert result == "Test prompt"

    def test_validate_input_empty_prompt(self):
        """Test validation with empty prompt."""
        input_data = {"prompt": ""}
        result = kuzu_enhance.validate_input(input_data)
        assert result is None

    def test_validate_input_missing_prompt(self):
        """Test validation with missing prompt key."""
        input_data = {}
        result = kuzu_enhance.validate_input(input_data)
        assert result is None

    def test_validate_input_whitespace_only(self):
        """Test validation with whitespace-only prompt."""
        input_data = {"prompt": "   \n\t  "}
        result = kuzu_enhance.validate_input(input_data)
        assert result is None

    def test_validate_input_not_string(self):
        """Test validation when prompt is not a string."""
        input_data = {"prompt": 123}
        result = kuzu_enhance.validate_input(input_data)
        assert result is None

    def test_validate_input_not_dict(self):
        """Test validation when input is not a dictionary."""
        result = kuzu_enhance.validate_input("not a dict")
        assert result is None

    def test_validate_input_long_prompt(self):
        """Test validation with extremely long prompt."""
        long_prompt = "x" * 200000  # 200KB
        input_data = {"prompt": long_prompt}
        result = kuzu_enhance.validate_input(input_data)
        assert result is not None
        assert len(result) == 100000  # Should be truncated

    @patch("subprocess.run")
    def test_enhance_with_memory_success(self, mock_run):
        """Test successful memory enhancement."""
        mock_run.return_value = Mock(returncode=0, stdout="Enhanced context", stderr="")

        result = kuzu_enhance.enhance_with_memory("test prompt")
        assert result == "Enhanced context"

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "kuzu-memory" in call_args[0][0]
        assert "enhance" in call_args[0][0]

    @patch("subprocess.run")
    def test_enhance_with_memory_failure(self, mock_run):
        """Test failed memory enhancement."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error message")

        result = kuzu_enhance.enhance_with_memory("test prompt")
        assert result is None

    @patch("subprocess.run")
    def test_enhance_with_memory_timeout(self, mock_run):
        """Test memory enhancement timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 2)

        result = kuzu_enhance.enhance_with_memory("test prompt")
        assert result is None

    @patch("subprocess.run")
    def test_enhance_with_memory_command_not_found(self, mock_run):
        """Test when kuzu-memory command is not found."""
        mock_run.side_effect = FileNotFoundError()

        result = kuzu_enhance.enhance_with_memory("test prompt")
        assert result is None


class TestKuzuLearnHook:
    """Test kuzu_learn.py hook functions."""

    def test_find_transcript_file_exists(self, tmp_path):
        """Test finding transcript file that exists."""
        transcript = tmp_path / "test.jsonl"
        transcript.write_text("test content")

        result = kuzu_learn.find_transcript_file(str(transcript))
        assert result == transcript

    def test_find_transcript_file_missing(self, tmp_path):
        """Test finding transcript file that doesn't exist."""
        missing = tmp_path / "missing.jsonl"

        # Directory exists but file doesn't - should find most recent
        other_file = tmp_path / "other.jsonl"
        other_file.write_text("other content")

        result = kuzu_learn.find_transcript_file(str(missing))
        assert result == other_file

    def test_find_transcript_file_directory_missing(self):
        """Test when transcript directory doesn't exist."""
        result = kuzu_learn.find_transcript_file("/nonexistent/path/file.jsonl")
        assert result is None

    def test_parse_transcript_entry_valid(self):
        """Test parsing valid transcript entry."""
        line = '{"message": {"role": "assistant", "content": "test"}}'
        result = kuzu_learn.parse_transcript_entry(line)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_transcript_entry_invalid(self):
        """Test parsing invalid JSON."""
        result = kuzu_learn.parse_transcript_entry("invalid json")
        assert result is None

    def test_extract_assistant_text_valid(self):
        """Test extracting text from valid assistant message."""
        entry = {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "text", "text": "World"},
                ],
            }
        }
        result = kuzu_learn.extract_assistant_text(entry)
        assert result == "Hello World"

    def test_extract_assistant_text_with_tool_use(self):
        """Test extracting text with tool_use mixed in."""
        entry = {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check"},
                    {"type": "tool_use", "name": "bash", "input": "ls"},
                    {"type": "text", "text": "Found files"},
                ],
            }
        }
        result = kuzu_learn.extract_assistant_text(entry)
        assert result == "Let me check Found files"

    def test_extract_assistant_text_not_assistant(self):
        """Test extracting from non-assistant message."""
        entry = {
            "message": {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
        }
        result = kuzu_learn.extract_assistant_text(entry)
        assert result is None

    def test_extract_assistant_text_empty_content(self):
        """Test extracting from message with no text."""
        entry = {"message": {"role": "assistant", "content": []}}
        result = kuzu_learn.extract_assistant_text(entry)
        assert result is None

    def test_find_last_assistant_message(self, tmp_path):
        """Test finding last assistant message in transcript."""
        transcript = tmp_path / "test.jsonl"
        content = [
            '{"message": {"role": "user", "content": [{"type": "text", "text": "First"}]}}',
            '{"message": {"role": "assistant", "content": [{"type": "text", "text": "Response 1"}]}}',
            '{"message": {"role": "user", "content": [{"type": "text", "text": "Second"}]}}',
            '{"message": {"role": "assistant", "content": [{"type": "text", "text": "Response 2"}]}}',
        ]
        transcript.write_text("\n".join(content))

        result = kuzu_learn.find_last_assistant_message(transcript)
        assert result == "Response 2"

    def test_find_last_assistant_message_empty_file(self, tmp_path):
        """Test finding message in empty transcript."""
        transcript = tmp_path / "empty.jsonl"
        transcript.write_text("")

        result = kuzu_learn.find_last_assistant_message(transcript)
        assert result is None

    def test_find_last_assistant_message_no_assistant(self, tmp_path):
        """Test finding message when no assistant messages exist."""
        transcript = tmp_path / "test.jsonl"
        content = [
            '{"message": {"role": "user", "content": [{"type": "text", "text": "First"}]}}',
            '{"message": {"role": "user", "content": [{"type": "text", "text": "Second"}]}}',
        ]
        transcript.write_text("\n".join(content))

        result = kuzu_learn.find_last_assistant_message(transcript)
        assert result is None

    @patch("subprocess.run")
    def test_store_memory_success(self, mock_run):
        """Test successful memory storage."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = kuzu_learn.store_memory("Test memory content")
        assert result is True

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "kuzu-memory" in call_args[0][0]
        assert "store" in call_args[0][0]
        assert "Test memory content" in call_args[0][0]

    @patch("subprocess.run")
    def test_store_memory_failure(self, mock_run):
        """Test failed memory storage."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Storage failed")

        result = kuzu_learn.store_memory("Test memory")
        assert result is False

    @patch("subprocess.run")
    def test_store_memory_timeout(self, mock_run):
        """Test memory storage timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)

        result = kuzu_learn.store_memory("Test memory")
        assert result is False

    @patch("subprocess.run")
    def test_store_memory_command_not_found(self, mock_run):
        """Test when kuzu-memory command is not found."""
        mock_run.side_effect = FileNotFoundError()

        result = kuzu_learn.store_memory("Test memory")
        assert result is False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_enhance_empty_string(self):
        """Test enhancing empty string."""
        result = kuzu_enhance.validate_input({"prompt": ""})
        assert result is None

    def test_extract_malformed_entry(self):
        """Test extracting from malformed entry."""
        entry = {"not": "valid"}
        result = kuzu_learn.extract_assistant_text(entry)
        assert result is None

    def test_transcript_with_mixed_valid_invalid(self, tmp_path):
        """Test transcript with mix of valid and invalid lines."""
        transcript = tmp_path / "mixed.jsonl"
        content = [
            "invalid json line",
            '{"message": {"role": "assistant", "content": [{"type": "text", "text": "Valid"}]}}',
            "",  # empty line
            '{"incomplete": ',
        ]
        transcript.write_text("\n".join(content))

        result = kuzu_learn.find_last_assistant_message(transcript)
        assert result == "Valid"


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
