#!/usr/bin/env python3
"""Claude Code PostToolUse hook - Learn from tool usage."""
import json
import subprocess
import sys


def main() -> int:
    """Learn from tool usage events."""
    # Read tool usage data from stdin
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        # Invalid JSON, nothing to learn
        return 0

    # Extract relevant content to learn from
    tool = data.get("tool", "")
    content = data.get("content", "")

    # Only learn from file operations (Edit, Write)
    if not content or tool not in ["Edit", "Write"]:
        return 0

    try:
        # Call kuzu-memory learn via CLI entry point (async with --quiet)
        subprocess.run(
            ["/Users/masa/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory", "memory", "learn", content, "--quiet"],
            check=False,  # Don't raise on error
            timeout=1.0,
        )
    except subprocess.TimeoutExpired:
        # Learning timed out, but don't block
        print("Learning timed out", file=sys.stderr)
    except Exception as e:
        # Learning failed, but don't block
        print(f"Learning error: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
