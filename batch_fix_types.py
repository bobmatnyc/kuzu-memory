#!/usr/bin/env python3
"""
Batch fix type annotations across the codebase for mypy --strict compliance.

This script automates common type annotation patterns.
"""
import re
import sys
from pathlib import Path
from typing import Callable


def fix_file(file_path: Path) -> tuple[int, int]:
    """
    Fix type annotations in a single file.

    Returns:
        Tuple of (original_errors, remaining_errors)
    """
    content = file_path.read_text()
    original = content

    # Fix 1: Add typing imports if needed
    if "from typing import" not in content and ("def " in content or "class " in content):
        # Add after pathlib import or at beginning
        if "from pathlib import Path" in content:
            content = content.replace(
                "from pathlib import Path\n",
                "from pathlib import Path\nfrom typing import Any\n",
                1
            )
        elif "import " in content:
            # Add after first import block
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    # Find end of import block
                    j = i
                    while j < len(lines) and (lines[j].startswith("import ") or lines[j].startswith("from ") or not lines[j].strip()):
                        j += 1
                    lines.insert(j, "from typing import Any")
                    content = "\n".join(lines)
                    break

    # Fix 2: Add click.Context type to ctx parameters
    if "import click" in content:
        # def func(ctx, ...) -> def func(ctx: click.Context, ...)
        content = re.sub(
            r'\bdef (\w+)\(ctx,',
            r'def \1(ctx: click.Context,',
            content
        )
        # def func(ctx) -> def func(ctx: click.Context)
        content = re.sub(
            r'\bdef (\w+)\(ctx\):',
            r'def \1(ctx: click.Context):',
            content
        )

    # Fix 3: Add return type -> None to functions that don't return
    # This is tricky with decorators, so we'll be conservative
    # Only add if function clearly has no return statement
    def add_return_none(match: re.Match[str]) -> str:
        func_def = match.group(0)
        func_body = match.group(2) if len(match.groups()) >= 2 else ""

        # Check if function has return statement
        if "return " in func_body:
            return func_def

        # Check if return type already specified
        if " -> " in func_def:
            return func_def

        # Add -> None before the colon
        return func_def.replace("):", ") -> None:")

    # Fix 4: Add common parameter types for CLI commands
    common_params = [
        (r', debug(?=[,)])', r', debug: bool'),
        (r', verbose(?=[,)])', r', verbose: bool'),
        (r', force(?=[,)])', r', force: bool'),
        (r', quiet(?=[,)])', r', quiet: bool'),
        (r', detailed(?=[,)])', r', detailed: bool'),
        (r', advanced(?=[,)])', r', advanced: bool'),
        (r', skip_demo(?=[,)])', r', skip_demo: bool'),
        (r', validate(?=[,)])', r', validate: bool'),
        (r', show_project(?=[,)])', r', show_project: bool'),
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
        (r', output_format(?=[,)])', r', output_format: str'),
        (r', project(?=[,)])', r', project: str | None'),
        (r', ai_system(?=[,)])', r', ai_system: str'),
        (r', confirm(?=[,)])', r', confirm: bool'),
    ]

    for pattern, replacement in common_params:
        content = re.sub(pattern, replacement, content)

    # Fix 5: Fix ending parameters (no comma after)
    ending_params = [
        (r', debug\)', r', debug: bool)'),
        (r', verbose\)', r', verbose: bool)'),
        (r', force\)', r', force: bool)'),
        (r', quiet\)', r', quiet: bool)'),
        (r', detailed\)', r', detailed: bool)'),
        (r', topic\)', r', topic: str | None)'),
        (r', output_format\)', r', output_format: str)'),
        (r', confirm\)', r', confirm: bool)'),
    ]

    for pattern, replacement in ending_params:
        content = re.sub(pattern, replacement, content)

    # Write if changed
    if content != original:
        file_path.write_text(content)
        return (1, 0)  # Mark as modified
    return (0, 0)


def main() -> None:
    """Main entry point."""
    src_dir = Path("src/kuzu_memory")

    if not src_dir.exists():
        print("Error: src/kuzu_memory directory not found")
        sys.exit(1)

    # Find all Python files
    py_files = list(src_dir.rglob("*.py"))

    print(f"Found {len(py_files)} Python files")
    print("Fixing type annotations...")

    modified_count = 0
    for py_file in sorted(py_files):
        modified, _ = fix_file(py_file)
        if modified:
            modified_count += 1
            try:
                rel_path = py_file.relative_to(Path.cwd())
            except ValueError:
                rel_path = py_file
            print(f"  Fixed: {rel_path}")

    print(f"\nModified {modified_count} files")
    print("\nRun 'mypy src/kuzu_memory --strict --ignore-missing-imports' to check remaining errors")


if __name__ == "__main__":
    main()
