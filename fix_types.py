#!/usr/bin/env python3
"""
Script to fix common mypy --strict type errors across the codebase.
"""
import re
import sys
from pathlib import Path
from typing import Pattern


def add_return_none_to_functions(content: str) -> str:
    """Add -> None to functions missing return type annotations."""
    # Pattern for click commands and regular functions without return types
    patterns: list[tuple[Pattern[str], str]] = [
        # Click commands with decorators
        (
            re.compile(r'(@[\w\.]+\([^\)]*\)\s*\n)+def (\w+)\(([^)]*)\):'),
            lambda m: m.group(0)[:-2] + ' -> None:'
        ),
        # Regular functions without return types (but not already typed)
        (
            re.compile(r'^def (\w+)\(([^)]*)\):\s*$', re.MULTILINE),
            lambda m: m.group(0)[:-2] + ' -> None:' if '-> ' not in m.group(0) else m.group(0)
        ),
    ]

    for pattern, replacement in patterns:
        content = pattern.sub(replacement, content)

    return content


def fix_click_context_types(content: str) -> str:
    """Fix click.Context parameter types."""
    # Pattern: def func(ctx, ...)
    content = re.sub(
        r'def (\w+)\(ctx,',
        r'def \1(ctx: click.Context,',
        content
    )
    return content


def fix_common_parameter_types(content: str) -> str:
    """Fix common parameter types in click commands."""
    replacements = [
        (r', debug(?=[,)])', r', debug: bool'),
        (r', verbose(?=[,)])', r', verbose: bool'),
        (r', force(?=[,)])', r', force: bool'),
        (r', quiet(?=[,)])', r', quiet: bool'),
        (r', detailed(?=[,)])', r', detailed: bool'),
        (r', advanced(?=[,)])', r', advanced: bool'),
        (r', skip_demo(?=[,)])', r', skip_demo: bool'),
        (r', enable_cli(?=[,)])', r', enable_cli: bool'),
        (r', disable_cli(?=[,)])', r', disable_cli: bool'),
        (r', explain_ranking(?=[,)])', r', explain_ranking: bool'),
        (r', use_sync(?=[,)])', r', use_sync: bool'),
        (r', config(?=[,)])', r', config: str | None'),
        (r', db_path(?=[,)])', r', db_path: str | None'),
        (r', project_root(?=[,)])', r', project_root: str | None'),
        (r', config_path(?=[,)])', r', config_path: str | None'),
        (r', source(?=[,)])', r', source: str'),
        (r', metadata(?=[,)])', r', metadata: str | None'),
        (r', session_id(?=[,)])', r', session_id: str | None'),
        (r', agent_id(?=[,)])', r', agent_id: str'),
        (r', user_id(?=[,)])', r', user_id: str'),
        (r', prompt(?=[,)])', r', prompt: str'),
        (r', content(?=[,)])', r', content: str'),
        (r', response(?=[,)])', r', response: str'),
        (r', feedback(?=[,)])', r', feedback: str | None'),
        (r', topic(?=[,)])', r', topic: str | None'),
        (r', max_memories(?=[,)])', r', max_memories: int'),
        (r', recent(?=[,)])', r', recent: int'),
        (r', limit(?=[,)])', r', limit: int'),
        (r', strategy(?=[,)])', r', strategy: str'),
        (r', memory_id(?=[,)])', r', memory_id: str | None'),
        (r', memory_type(?=[,)])', r', memory_type: str | None'),
        # output_format is special
        (r', output_format(?=[,)])', r', output_format: str'),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    return content


def add_typing_imports(content: str) -> str:
    """Add Any to typing imports if needed."""
    if 'from typing import' in content:
        # Check if Any is already imported
        if 'Any' not in content.split('from typing import')[1].split('\n')[0]:
            # Add Any to existing import
            content = re.sub(
                r'from typing import ([^\n]+)',
                r'from typing import Any, \1',
                content,
                count=1
            )
    else:
        # Add new typing import after pathlib import
        content = re.sub(
            r'(from pathlib import Path\n)',
            r'\1from typing import Any\n',
            content,
            count=1
        )

    return content


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python fix_types.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    # Read file
    content = file_path.read_text()

    # Apply fixes
    content = add_typing_imports(content)
    content = fix_click_context_types(content)
    content = fix_common_parameter_types(content)
    # Note: return type fixes are complex with decorators, handle manually

    # Write back
    file_path.write_text(content)
    print(f"Fixed types in {file_path}")


if __name__ == "__main__":
    main()
