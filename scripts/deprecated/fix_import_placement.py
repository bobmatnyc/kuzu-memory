#!/usr/bin/env python3
"""
Fix misplaced 'from typing import Any' statements.

The batch script incorrectly inserted 'from typing import Any' lines
in the middle of multi-line from...import statements.
"""
from pathlib import Path


def fix_imports(content: str) -> str:
    """Fix import placement issues."""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if current line starts a from...import and next line is 'from typing import Any'
        if (line.startswith('from ') and
            i + 1 < len(lines) and
            lines[i + 1] == 'from typing import Any'):
            # This is the problematic pattern
            # We need to find the end of the current from...import statement

            # If the current line ends with a parenthesis, it's multi-line
            if '(' in line and ')' not in line:
                # Multi-line import
                result.append(line)
                i += 1
                # Skip the 'from typing import Any' line
                i += 1
                # Continue with rest of multi-line import
                while i < len(lines) and ')' not in lines[i-1]:
                    result.append(lines[i])
                    i += 1
            else:
                # Single line import
                result.append(line)
                i += 1
                # Skip the 'from typing import Any' line
                i += 1
        else:
            result.append(line)
            i += 1

    # Now find the first import block and insert 'from typing import Any' there
    # Find first import
    for i, line in enumerate(result):
        if line.startswith('import ') or line.startswith('from '):
            # Find end of import block
            j = i
            while j < len(result):
                if result[j].strip() and not result[j].startswith('import ') and not result[j].startswith('from ') and not result[j].strip().startswith(')'):
                    break
                j += 1
            # Check if 'from typing import Any' already exists
            import_block = result[i:j]
            if 'from typing import Any' not in import_block:
                # Insert it before the first import
                result.insert(i, 'from typing import Any')
            break

    return '\n'.join(result)


def main() -> None:
    """Fix all Python files."""
    src_dir = Path("src/kuzu_memory")

    if not src_dir.exists():
        print("Error: src/kuzu_memory directory not found")
        return

    py_files = list(src_dir.rglob("*.py"))
    fixed_count = 0

    for py_file in py_files:
        try:
            content = py_file.read_text()
            fixed_content = fix_imports(content)

            if fixed_content != content:
                py_file.write_text(fixed_content)
                fixed_count += 1
                print(f"Fixed: {py_file}")
        except Exception as e:
            print(f"Error fixing {py_file}: {e}")

    print(f"\n{fixed_count} files fixed")


if __name__ == "__main__":
    main()
