#!/usr/bin/env python3
"""
Claude Code hook: Enhance prompts with kuzu-memory context.
Reads JSON from stdin per Claude Code hooks API.

Production-ready version with:
- Full type hints (mypy compliant)
- Proper logging infrastructure
- Input validation
- Configurable timeouts
"""
import json
import logging
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging
LOG_DIR = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
LOG_FILE = LOG_DIR / "kuzu_enhance.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment
ENHANCE_TIMEOUT = int(os.getenv("KUZU_ENHANCE_TIMEOUT", "2"))
KUZU_COMMAND = os.getenv("KUZU_COMMAND", "kuzu-memory")


def validate_input(input_data: Dict[str, Any]) -> Optional[str]:
    """
    Validate input data and extract prompt.

    Args:
        input_data: JSON data from Claude Code

    Returns:
        The prompt string if valid, None otherwise
    """
    if not isinstance(input_data, dict):
        logger.warning("Input data is not a dictionary")
        return None

    prompt = input_data.get("prompt", "")

    if not prompt:
        logger.info("No prompt found in input")
        return None

    if not isinstance(prompt, str):
        logger.warning(f"Prompt is not a string: {type(prompt)}")
        return None

    if len(prompt.strip()) == 0:
        logger.info("Prompt is empty after stripping whitespace")
        return None

    # Basic validation - check for extremely long prompts
    max_prompt_length = 100000  # 100KB reasonable limit
    if len(prompt) > max_prompt_length:
        logger.warning(f"Prompt too long: {len(prompt)} chars (max {max_prompt_length})")
        return prompt[:max_prompt_length]

    return prompt


def enhance_with_memory(prompt: str) -> Optional[str]:
    """
    Call kuzu-memory to enhance the prompt with context.

    Args:
        prompt: The user's prompt to enhance

    Returns:
        Enhanced context if successful, None otherwise
    """
    try:
        logger.info(f"Enhancing prompt ({len(prompt)} chars)")

        result = subprocess.run(
            [KUZU_COMMAND, "memory", "enhance", prompt, "--format", "plain"],
            capture_output=True,
            text=True,
            timeout=ENHANCE_TIMEOUT
        )

        logger.info(f"kuzu-memory returned: {result.returncode}")

        if result.returncode != 0:
            if result.stderr:
                logger.warning(f"kuzu-memory stderr: {result.stderr[:200]}")
            return None

        enhancement = result.stdout.strip()

        if enhancement:
            logger.info(f"Enhancement generated ({len(enhancement)} chars)")
            return enhancement
        else:
            logger.info("No enhancement generated")
            return None

    except subprocess.TimeoutExpired:
        logger.error(f"kuzu-memory timed out after {ENHANCE_TIMEOUT}s")
        return None
    except FileNotFoundError:
        logger.error(f"kuzu-memory command not found: {KUZU_COMMAND}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling kuzu-memory: {e}")
        return None


def main() -> None:
    """Main entry point for the hook."""
    try:
        logger.info("=== Hook called ===")

        # Read JSON from stdin (official Claude Code API)
        try:
            input_data: Dict[str, Any] = json.load(sys.stdin)
            logger.debug(f"Input keys: {list(input_data.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from stdin: {e}")
            sys.exit(0)

        # Validate and extract prompt
        prompt = validate_input(input_data)
        if not prompt:
            sys.exit(0)

        # Enhance with memory
        enhancement = enhance_with_memory(prompt)

        # Output enhancement to stdout if available
        # Claude Code will inject this into context
        if enhancement:
            print(enhancement)
            logger.info("Enhancement sent to stdout")
        else:
            logger.info("No enhancement to output")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        sys.exit(0)
    except Exception as e:
        # Graceful failure - don't block Claude
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        print(f"<!-- kuzu-memory error: {e} -->", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
