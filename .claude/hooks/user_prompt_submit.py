#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook - Enhance prompts with project context."""
import subprocess
import sys


def main() -> int:
    """Enhance user prompt with kuzu-memory context."""
    # Read original prompt from stdin
    prompt = sys.stdin.read().strip()

    if not prompt:
        # No prompt, pass through
        print(prompt)
        return 0

    try:
        # Call kuzu-memory enhance via CLI entry point
        result = subprocess.run(
            ["/Users/masa/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory", "memory", "enhance", prompt],
            capture_output=True,
            text=True,
            timeout=5.0,
        )

        if result.returncode == 0 and result.stdout:
            # Successfully enhanced
            print(result.stdout.strip())
        else:
            # Enhancement failed, use original
            if result.stderr:
                print(f"Enhancement failed: {result.stderr}", file=sys.stderr)
            print(prompt)

    except subprocess.TimeoutExpired:
        # Timeout, fallback to original
        print("Enhancement timed out", file=sys.stderr)
        print(prompt)
    except Exception as e:
        # Any error, fallback to original
        print(f"Enhancement error: {e}", file=sys.stderr)
        print(prompt)

    return 0


if __name__ == "__main__":
    sys.exit(main())
