"""
Unit tests for hooks commands.

Tests CR character normalization (Fix #12) and async/sync learn modes (Fix #15).
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import the function we need to test
# Note: Since find_last_assistant_message is defined inside hooks_commands.py
# as a local function, we need to import the module and access it indirectly
from kuzu_memory.cli import hooks_commands


class TestFindLastAssistantMessage:
    """Test cases for find_last_assistant_message function."""

    def test_normalizes_crlf_line_endings(self, tmp_path: Path):
        """Test that CRLF line endings are normalized (Fix #12)."""
        # Create a transcript with Windows-style line endings
        transcript_file = tmp_path / "transcript.jsonl"

        # Create a valid JSONL entry with CR characters in the text
        message = {
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Line 1\r\nLine 2\r\nLine 3"}],
            }
        }

        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")

        # Call the module-level function
        result = hooks_commands._find_last_assistant_message(transcript_file)

        # Verify CR characters are removed
        assert result is not None
        assert "\r" not in result
        assert result == "Line 1\nLine 2\nLine 3"

    def test_normalizes_cr_only_line_endings(self, tmp_path: Path):
        """Test that CR-only line endings are normalized (old Mac style)."""
        transcript_file = tmp_path / "transcript.jsonl"

        message = {
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Line 1\rLine 2\rLine 3"}],
            }
        }

        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")

        result = hooks_commands._find_last_assistant_message(transcript_file)

        assert result is not None
        assert "\r" not in result
        assert result == "Line 1\nLine 2\nLine 3"

    def test_normalizes_mixed_line_endings(self, tmp_path: Path):
        """Test that mixed line endings (CRLF, CR, LF) are normalized."""
        transcript_file = tmp_path / "transcript.jsonl"

        message = {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Line 1\r\nLine 2\rLine 3\nLine 4"}
                ],
            }
        }

        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")

        result = hooks_commands._find_last_assistant_message(transcript_file)

        assert result is not None
        assert "\r" not in result
        assert result == "Line 1\nLine 2\nLine 3\nLine 4"

    def test_handles_multiple_content_blocks_with_cr(self, tmp_path: Path):
        """Test that CR normalization works with multiple content blocks."""
        transcript_file = tmp_path / "transcript.jsonl"

        message = {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Block 1\r\nwith CR"},
                    {"type": "text", "text": "Block 2\rmore CR"},
                ],
            }
        }

        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")

        result = hooks_commands._find_last_assistant_message(transcript_file)

        # Result should be joined with space and CR normalized
        assert result is not None
        assert "\r" not in result
        # Content blocks are joined with space
        assert "Block 1\nwith CR Block 2\nmore CR" == result

    def test_unix_line_endings_unchanged(self, tmp_path: Path):
        """Test that Unix line endings (LF only) remain unchanged."""
        transcript_file = tmp_path / "transcript.jsonl"

        message = {
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Line 1\nLine 2\nLine 3"}],
            }
        }

        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")

        result = hooks_commands._find_last_assistant_message(transcript_file)

        assert result is not None
        assert result == "Line 1\nLine 2\nLine 3"

    def test_no_line_endings(self, tmp_path: Path):
        """Test content without any line endings."""
        transcript_file = tmp_path / "transcript.jsonl"

        message = {
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Single line content"}],
            }
        }

        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(message) + "\n")

        result = hooks_commands._find_last_assistant_message(transcript_file)

        assert result is not None
        assert result == "Single line content"

    def test_finds_last_assistant_message(self, tmp_path: Path):
        """Test that function finds the last assistant message correctly."""
        transcript_file = tmp_path / "transcript.jsonl"

        # Create multiple messages, last one should be returned
        messages = [
            {
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "User message"}],
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "First assistant\r\nmessage"}],
                }
            },
            {
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "Another user message"}],
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Last assistant\r\nmessage"}],
                }
            },
        ]

        with open(transcript_file, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = hooks_commands._find_last_assistant_message(transcript_file)

        # Should return last assistant message with CR normalized
        assert result is not None
        assert "\r" not in result
        assert result == "Last assistant\nmessage"

    def test_empty_transcript_returns_none(self, tmp_path: Path):
        """Test that empty transcript returns None."""
        transcript_file = tmp_path / "empty.jsonl"

        # Create empty file
        transcript_file.touch()

        result = hooks_commands._find_last_assistant_message(transcript_file)

        assert result is None

    def test_no_assistant_messages_returns_none(self, tmp_path: Path):
        """Test that transcript with no assistant messages returns None."""
        transcript_file = tmp_path / "transcript.jsonl"

        # Only user messages
        messages = [
            {
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "User message 1"}],
                }
            },
            {
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "User message 2"}],
                }
            },
        ]

        with open(transcript_file, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        result = hooks_commands._find_last_assistant_message(transcript_file)

        assert result is None

    def test_malformed_json_skipped(self, tmp_path: Path):
        """Test that malformed JSON lines are skipped."""
        transcript_file = tmp_path / "transcript.jsonl"

        with open(transcript_file, "w", encoding="utf-8") as f:
            # Malformed JSON
            f.write("{invalid json}\n")
            # Valid message
            f.write(
                json.dumps(
                    {
                        "message": {
                            "role": "assistant",
                            "content": [
                                {"type": "text", "text": "Valid message\r\nwith CR"}
                            ],
                        }
                    }
                )
                + "\n"
            )

        result = hooks_commands._find_last_assistant_message(transcript_file)

        # Should find the valid message and normalize CR
        assert result is not None
        assert "\r" not in result
        assert result == "Valid message\nwith CR"


class TestHooksLearnAsync:
    """Test cases for async/sync learn modes (Fix #15)."""

    def test_kuzu_memory_auto_sync_parameter(self, tmp_path: Path):
        """Test that KuzuMemory accepts auto_sync parameter (Fix #15)."""
        # This is a direct test of the KuzuMemory class to verify
        # the auto_sync parameter is accepted and stored correctly.
        from kuzu_memory.core.memory import KuzuMemory

        db_path = tmp_path / "test.db"

        # Test with auto_sync=False (used in hooks for faster startup)
        memory = KuzuMemory(db_path=db_path, auto_sync=False, enable_git_sync=False)

        # Verify the attribute is set correctly
        assert hasattr(memory, "_auto_sync")
        assert memory._auto_sync is False

        memory.close()

        # Test with auto_sync=True (default behavior)
        memory = KuzuMemory(db_path=db_path, auto_sync=True, enable_git_sync=False)

        assert hasattr(memory, "_auto_sync")
        assert memory._auto_sync is True

        memory.close()

    def test_hooks_learn_has_sync_flag(self):
        """Test that hooks learn command has --sync flag option."""
        # Verify the command structure includes the --sync flag
        from click.testing import CliRunner
        from kuzu_memory.cli.hooks_commands import hooks_group

        runner = CliRunner()
        result = runner.invoke(hooks_group, ["learn", "--help"])

        # Should show the --sync option in help
        assert "--sync" in result.output
        assert "Run synchronously" in result.output or "blocking" in result.output
