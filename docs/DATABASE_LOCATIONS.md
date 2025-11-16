# KuzuMemory Database Locations

## Overview

KuzuMemory uses different database locations depending on the context:

## 1. Project-Specific Database (Recommended)
**Location**: `<project-root>/kuzu-memories/memories.db`

This is used when:
- Running commands from within a project directory
- A git repository or project indicator file is found
- Using `kuzu-memory init` in a project

**Size in this project**: 13.41 MB (primary database with project memories)

## 2. Global/Default Database
**Location**: `.kuzu_memory/memories.db`

This is used when:
- No project context is detected
- Running from a non-project directory
- Using the Python API directly without specifying a path

**Size in this project**: 4.53 MB (fallback/testing database)

## 3. Database Priority

When KuzuMemory runs, it checks for databases in this order:
1. **Project database** (`kuzu-memories/memories.db`) - if in a project
2. **Default database** (`.kuzu_memory/memories.db`) - if no project found
3. **Custom path** - if explicitly specified via `--db-path` or API

## Usage Examples

### CLI in Project
```bash
# Uses kuzu-memories/memories.db automatically
cd /path/to/project
kuzu-memory recall "test"
```

### CLI Global
```bash
# Uses .kuzu_memory/memories.db
cd /tmp
kuzu-memory recall "test"
```

### Python API
```python
from kuzu_memory import KuzuMemory
from pathlib import Path

# Project-specific
memory = KuzuMemory(db_path=Path("kuzu-memories/memories.db"))

# Default
memory = KuzuMemory()  # Uses .kuzu_memory/memories.db

# Custom
memory = KuzuMemory(db_path=Path("/custom/path/memories.db"))
```

## Best Practices

1. **For Projects**: Always use `kuzu-memory init` to create project-specific database
2. **For Libraries**: Use the project database to maintain context
3. **For Scripts**: Can use either depending on needs
4. **For Testing**: Use a separate test database path

## Current Status

> **Note**: Historical status from v1.1.1. Current version is v1.4.47. See [CHANGELOG.md](../CHANGELOG.md) for latest updates.

- ✅ Project detection working correctly
- ✅ Both database locations functional
- ✅ All initialization issues resolved
- ✅ Recall and storage working properly

## Migration

If you need to consolidate databases, use:
```bash
python scripts/consolidate-databases.py
```

This will safely merge databases with backup creation.