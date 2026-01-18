"""
Unit tests for hooks commands, specifically testing CR character normalization.

Tests the find_last_assistant_message() function to ensure carriage return
characters from transcript files don't leak into the REPL (Fix #12).
"""

import json
import tempfile
from pathlib import Path

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
                "content": [{"type": "text", "text": "Line 1\r\nLine 2\rLine 3\nLine 4"}],
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
            {"message": {"role": "user", "content": [{"type": "text", "text": "User message"}]}},
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
            {"message": {"role": "user", "content": [{"type": "text", "text": "User message 1"}]}},
            {"message": {"role": "user", "content": [{"type": "text", "text": "User message 2"}]}},
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
                            "content": [{"type": "text", "text": "Valid message\r\nwith CR"}],
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
