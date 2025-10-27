#!/usr/bin/env python3
"""
Fix incorrectly added type annotations in function calls.

The batch_fix_types.py script incorrectly added type annotations to
function/method *arguments* instead of *parameters*. This script reverts those.
"""
import re
from pathlib import Path


def fix_function_call_annotations(content: str) -> str:
    """Remove type annotations from function call arguments."""
    # Pattern: function_call(arg1, arg2: type, arg3)
    # Should be: function_call(arg1, arg2, arg3)

    # Fix: argname: type | None -> argname
    content = re.sub(r'(\w+):\s*str\s*\|\s*None(?=[,\)])', r'\1', content)

    # Fix: argname: str -> argname
    content = re.sub(r'(\w+):\s*str(?=[,\)])', r'\1', content)

    # Fix: argname: bool -> argname
    content = re.sub(r'(\w+):\s*bool(?=[,\)])', r'\1', content)

    # Fix: argname: int -> argname
    content = re.sub(r'(\w+):\s*int(?=[,\)])', r'\1', content)

    return content


def main() -> None:
    """Fix all Python files in src/kuzu_memory."""
    src_dir = Path("src/kuzu_memory")

    if not src_dir.exists():
        print("Error: src/kuzu_memory directory not found")
        return

    py_files = list(src_dir.rglob("*.py"))
    fixed_count = 0

    for py_file in py_files:
        content = py_file.read_text()
        fixed_content = fix_function_call_annotations(content)

        if fixed_content != content:
            py_file.write_text(fixed_content)
            fixed_count += 1
            print(f"Fixed: {py_file}")

    print(f"\n{fixed_count} files fixed")


if __name__ == "__main__":
    main()
