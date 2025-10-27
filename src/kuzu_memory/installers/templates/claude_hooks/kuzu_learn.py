#!/usr/bin/env python3
"""
Claude Code hook: Learn from conversations.
Parses transcript to extract last assistant response.

Production-ready version with:
- Full type hints (mypy compliant)
- Proper logging infrastructure
- Robust transcript finding
- Better error handling
- Configurable timeouts
"""

import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Configure logging
LOG_DIR = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
LOG_FILE = LOG_DIR / "kuzu_learn.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
    ],
)
logger = logging.getLogger(__name__)

# Configuration from environment
STORE_TIMEOUT = int(os.getenv("KUZU_STORE_TIMEOUT", "5"))
KUZU_COMMAND = os.getenv("KUZU_COMMAND", "{KUZU_COMMAND}")
SOURCE = os.getenv("KUZU_HOOK_SOURCE", "claude-code-hook")
AGENT_ID = os.getenv("KUZU_HOOK_AGENT_ID", "assistant")
PROJECT_DIR = os.getenv("CLAUDE_PROJECT_DIR", "")

# Deduplication cache file
CACHE_FILE = LOG_DIR / ".kuzu_learn_cache.json"
CACHE_TTL = 300  # 5 minutes in seconds


def get_content_hash(text: str) -> str:
    """
    Get a hash of the content for deduplication.

    Args:
        text: The text to hash

    Returns:
        SHA256 hash of the text
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_duplicate(text: str) -> bool:
    """
    Check if this content was recently stored.

    Uses a simple file-based cache with TTL to prevent duplicate storage
    when PostToolUse fires multiple times for parallel tool calls.

    Args:
        text: The text to check

    Returns:
        True if this is a duplicate (stored recently), False otherwise
    """
    try:
        content_hash = get_content_hash(text)
        current_time = time.time()

        # Load cache
        cache: dict[str, float] = {}
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    cache = json.load(f)
            except (OSError, json.JSONDecodeError):
                logger.warning("Failed to load cache, starting fresh")
                cache = {}

        # Clean expired entries
        cache = {k: v for k, v in cache.items() if current_time - v < CACHE_TTL}

        # Check if duplicate
        if content_hash in cache:
            age = current_time - cache[content_hash]
            logger.info(f"Duplicate detected (stored {age:.1f}s ago), skipping")
            return True

        # Not a duplicate - add to cache
        cache[content_hash] = current_time

        # Save cache
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f)
        except OSError as e:
            logger.warning(f"Failed to save cache: {e}")

        return False

    except Exception as e:
        logger.error(f"Error checking for duplicates: {e}")
        # On error, allow storage (fail open)
        return False


def find_transcript_file(transcript_path: str) -> Path | None:
    """
    Find the most recent transcript file.

    Handles the case where continued sessions use different transcript files
    than the original session_id suggests.

    Args:
        transcript_path: The transcript path from Claude Code

    Returns:
        Path to the most recent transcript file, or None if not found
    """
    try:
        path = Path(transcript_path)

        # Check if the specified file exists
        if path.exists() and path.is_file():
            logger.info(f"Using specified transcript: {path}")
            return path

        # If not, try to find the most recent transcript in the same directory
        if path.parent.exists():
            transcripts = list(path.parent.glob("*.jsonl"))

            if not transcripts:
                logger.warning(f"No transcript files found in {path.parent}")
                return None

            # Get the most recently modified transcript
            most_recent = max(transcripts, key=lambda p: p.stat().st_mtime)
            logger.info(f"Using most recent transcript: {most_recent}")
            return most_recent

        logger.warning(f"Transcript directory does not exist: {path.parent}")
        return None

    except Exception as e:
        logger.error(f"Error finding transcript file: {e}")
        return None


def parse_transcript_entry(line: str) -> dict[str, Any] | None:
    """
    Parse a single transcript line.

    Args:
        line: JSON line from transcript

    Returns:
        Parsed entry dict, or None if parsing fails
    """
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        logger.debug(f"Failed to parse transcript line: {e}")
        return None


def extract_assistant_text(entry: dict[str, Any]) -> str | None:
    """
    Extract text content from an assistant message entry.

    Args:
        entry: Transcript entry dictionary

    Returns:
        Assistant text if found, None otherwise
    """
    try:
        message = entry.get("message", {})

        if not isinstance(message, dict):
            return None

        if message.get("role") != "assistant":
            return None

        content = message.get("content", [])

        if not isinstance(content, list) or not content:
            return None

        # Extract text from content items (skip tool_use, tool_result, etc.)
        text_parts = [
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ]

        if not text_parts:
            return None

        text = " ".join(text_parts).strip()
        return text if text else None

    except Exception as e:
        logger.debug(f"Error extracting assistant text: {e}")
        return None


def find_last_assistant_message(transcript_file: Path) -> str | None:
    """
    Find the last assistant message in the transcript.

    Args:
        transcript_file: Path to transcript JSONL file

    Returns:
        Last assistant message text, or None if not found
    """
    try:
        with open(transcript_file, encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            logger.info("Transcript file is empty")
            return None

        # Search backwards for assistant messages
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue

            entry = parse_transcript_entry(line)
            if not entry:
                continue

            text = extract_assistant_text(entry)
            if text:
                logger.info(f"Found assistant message ({len(text)} chars)")
                return text

        logger.info("No assistant messages found in transcript")
        return None

    except FileNotFoundError:
        logger.error(f"Transcript file not found: {transcript_file}")
        return None
    except PermissionError:
        logger.error(f"Permission denied reading transcript: {transcript_file}")
        return None
    except Exception as e:
        logger.error(f"Error reading transcript: {e}")
        return None


def store_memory(text: str) -> bool:
    """
    Store text in kuzu-memory.

    Args:
        text: The text to store

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Storing memory ({len(text)} chars)")

        # Use 'memory store' which directly stores content
        # (not 'learn' - learn requires specific patterns)
        cmd = [
            KUZU_COMMAND,
            "memory",
            "store",
            text,
            "--source",
            SOURCE,
            "--agent-id",
            AGENT_ID,
        ]

        # Add project-root if CLAUDE_PROJECT_DIR is set
        if PROJECT_DIR:
            cmd.extend(["--project-root", PROJECT_DIR])

        result = subprocess.run(
            cmd,
            timeout=STORE_TIMEOUT,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("Memory stored successfully")
            return True
        else:
            logger.warning(f"Store failed with code {result.returncode}")
            if result.stderr:
                logger.warning(f"Store stderr: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Store timed out after {STORE_TIMEOUT}s")
        return False
    except FileNotFoundError:
        logger.error(f"kuzu-memory command not found: {KUZU_COMMAND}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error storing memory: {e}")
        return False


def main() -> None:
    """Main entry point for the hook."""
    try:
        logger.info("=== Hook called ===")

        # Read JSON from stdin
        try:
            input_data: dict[str, Any] = json.load(sys.stdin)
            hook_event = input_data.get("hook_event_name", "unknown")
            logger.info(f"Hook event: {hook_event}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from stdin: {e}")
            sys.exit(0)

        # Get transcript path
        transcript_path = input_data.get("transcript_path", "")

        if not transcript_path:
            logger.info("No transcript path provided")
            sys.exit(0)

        # Find the actual transcript file
        transcript_file = find_transcript_file(transcript_path)

        if not transcript_file:
            logger.warning("Could not find transcript file")
            sys.exit(0)

        # Extract last assistant message
        assistant_text = find_last_assistant_message(transcript_file)

        if not assistant_text:
            logger.info("No assistant message to store")
            sys.exit(0)

        # Validate text length (reasonable limits)
        if len(assistant_text) < 10:
            logger.info("Assistant message too short to store")
            sys.exit(0)

        max_text_length = 1000000  # 1MB reasonable limit
        if len(assistant_text) > max_text_length:
            logger.warning(
                f"Truncating long message: {len(assistant_text)} -> {max_text_length}"
            )
            assistant_text = assistant_text[:max_text_length]

        # Check for duplicates (prevents multiple PostToolUse events from storing same content)
        if is_duplicate(assistant_text):
            logger.info("Skipping duplicate memory (recently stored)")
            sys.exit(0)

        # Store the memory
        success = store_memory(assistant_text)

        if success:
            logger.info("Hook completed successfully")
        else:
            logger.warning("Hook completed but storage failed")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        print(f"<!-- kuzu-memory learn error: {e} -->", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
