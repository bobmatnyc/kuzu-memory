# Bug Investigation: `kuzu-memory init` fails with EEXIST when `.kuzu-memory` is a file

**Date**: 2026-03-28
**Status**: Root cause identified
**Severity**: High - blocks initialization entirely, suggested fix (`--force`) also fails

---

## Error Report

```
ERROR: Failed to initialize MemoryService: Failed to initialize components:
Failed to initialize database: Failed to initialize connection pool:
Failed to initialize database at '/Users/masa/Projects/hot-flash/.kuzu-memory/memories.db':
the parent directory '/Users/masa/Projects/hot-flash/.kuzu-memory' already exists
but kuzu could not create the database inside it
(kuzu reported: [Errno 17] File exists: '/Users/masa/Projects/hot-flash/.kuzu-memory').
Run 'kuzu-memory init --force' to recreate the database.
```

---

## Root Cause

**`.kuzu-memory` is a regular FILE, not a directory.**

In the hot-flash project at `/Users/masa/Projects/hot-flash/`:

```
-rw-r--r--  1 masa  staff  1097728 Mar 23 23:36 .kuzu-memory   ← it's a FILE (1MB kuzu db)
drwxr-xr-x  5 masa  staff      160 Mar 28 14:08 .kuzu-memory-backups
-rw-r--r--  1 masa  staff       56 Mar 28 14:08 .kuzu-memory-config
drwxr-xr-x  2 masa  staff       64 Mar 28 14:08 kuzu-memories
```

An older version of kuzu created the database as a single file named `.kuzu-memory` directly in the project root, rather than as a directory containing `memories.db`.

The modern code (post-PR #34) expects the structure:
```
.kuzu-memory/           ← directory
└── memories.db         ← file inside it
```

But the project has:
```
.kuzu-memory            ← FILE (the old database)
```

---

## Exact Code Path Trace

### 1. `get_project_memories_dir(project_root)` — `utils/project_setup.py:142`

```python
new_path = root / ".kuzu-memory"
legacy_path = root / "kuzu-memories"
if not new_path.exists() and legacy_path.exists():
    return legacy_path
return new_path  # Returns the FILE path as if it were a directory
```

`new_path.exists()` returns `True` because a FILE named `.kuzu-memory` exists.
The function returns the FILE path without checking whether it's a file or directory.

### 2. `get_project_db_path(project_root)` — `utils/project_setup.py:172`

```python
memories_dir = get_project_memories_dir(project_root)
return memories_dir / "memories.db"  # Returns FILE/.kuzu-memory/memories.db
```

Returns `.kuzu-memory/memories.db` where `.kuzu-memory` is a FILE, not a directory.

### 3. `init_commands.py` — line 98

```python
if db_path.exists() and not force:
    sys.exit(1)
```

`db_path` is `.kuzu-memory/memories.db`. Since parent is a FILE, this path can never exist.
`db_path.exists()` returns `False`. The early-exit check is skipped — **proceeds to init**.

### 4. `create_project_memories_structure(root, force=False)` — `utils/project_setup.py:186`

```python
if memories_dir.exists():
    if not force:
        result["existed"] = True
        return result  # Returns {'existed': True} — BUG: treats FILE as existing directory
```

`memories_dir.exists()` is `True` (the FILE exists). With `force=False`, returns `{'existed': True}`.
No check for `memories_dir.is_dir()`. The code falsely believes the directory exists and is fine.

### 5. `SetupService.initialize_project()` — `services/setup_service.py:175`

```python
success = result.get("created", False) or result.get("existed", False)
# => False or True => True  (BUG: success=True even though directory doesn't exist)
```

### 6. `KuzuConnectionPool._create_connection()` — `storage/kuzu_adapter.py:93`

```python
self.db_path.parent.mkdir(parents=True, exist_ok=True)
# db_path.parent = .kuzu-memory (which is a FILE)
# mkdir() on a path that exists as a FILE raises OSError(EEXIST=17)
# even with exist_ok=True! (exist_ok only suppresses EEXIST for directories)
```

`mkdir(exist_ok=True)` suppresses `EEXIST` only when the target is already a directory.
When the target is a **file**, it raises `OSError([Errno 17] File exists)` regardless.

### 7. Error catch in `_create_connection()` — `storage/kuzu_adapter.py:110`

```python
except OSError as e:
    if e.errno == _errno_mod.EEXIST:
        raise DatabaseError(
            f"Failed to initialize database at '{self.db_path}': "
            f"the parent directory '{self.db_path.parent}' already exists "
            f"but kuzu could not create the database inside it "
            f"(kuzu reported: {e}). "
            f"Run 'kuzu-memory init --force' to recreate the database."
        )
```

This catch was written to handle **old kuzu (< 0.6)** behavior where kuzu itself called
`mkdir()` internally without `exist_ok`. However, it is now **incorrectly** triggered when
`db_path.parent` is a **file** (not a directory), because `mkdir()` on a file path also
raises `EEXIST`.

The error message says "the parent directory... already exists" — **this is incorrect**.
The parent is a FILE, not a directory.

---

## Why `--force` Also Fails

The suggested fix in the error message (`kuzu-memory init --force`) also fails.

With `force=True`, `create_project_memories_structure` calls `shutil.rmtree(memories_dir)`.
But `memories_dir` is a FILE, and `shutil.rmtree()` raises `NotADirectoryError` on files:

```
NotADirectoryError: [Errno 20] Not a directory: '/Users/masa/Projects/hot-flash/.kuzu-memory'
```

This causes `result['success'] = False`, and `init_commands.py` prints:
```
Project initialization failed: Initialization failed: [Errno 20] Not a directory: ...
```

**Neither `kuzu-memory init` nor `kuzu-memory init --force` work.**

---

## Error Message Chain

```
BaseService.logger.error(f"Failed to initialize MemoryService: {e}")
  ↑ logs but re-raises
KuzuMemory._initialize_components(): DatabaseError("Failed to initialize components: {e}")
  ↑ wraps and raises
KuzuAdapter.initialize(): DatabaseError("Failed to initialize database: {e}")
  ↑ wraps and raises
KuzuConnectionPool.initialize(): DatabaseError("Failed to initialize connection pool: {e}")
  ↑ wraps and raises
_create_connection(): DatabaseError("Failed to initialize database at '...memories.db': ...")
  ↑ caught from OSError(EEXIST) raised by db_path.parent.mkdir()
```

---

## Affected Files

| File | Location of Bug |
|------|----------------|
| `src/kuzu_memory/utils/project_setup.py` | `get_project_memories_dir()` line 164: no `is_dir()` check |
| `src/kuzu_memory/utils/project_setup.py` | `create_project_memories_structure()` line 222: treats file as existing dir |
| `src/kuzu_memory/storage/kuzu_adapter.py` | `_create_connection()` line 110: EEXIST error message says "directory" not "file or directory" |

---

## Recommended Fix

### Option A: Fix `get_project_memories_dir()` to detect file-vs-directory

```python
def get_project_memories_dir(project_root: Path | None = None) -> Path:
    root = project_root if project_root is not None else find_project_root()
    if root is None:
        raise ValueError("Could not determine project root directory")

    new_path = root / ".kuzu-memory"
    legacy_path = root / "kuzu-memories"

    # Handle legacy case: .kuzu-memory is a FILE (old kuzu database format)
    # In old kuzu versions the entire db was a single file named .kuzu-memory
    if new_path.exists() and new_path.is_file():
        # Do NOT treat a file as a memory directory; fall through to new_path
        # so callers get the expected directory path and can handle migration.
        pass
    elif not new_path.exists() and legacy_path.exists() and legacy_path.is_dir():
        return legacy_path

    return new_path
```

### Option B: Fix `create_project_memories_structure()` to handle file collision

In the `force=True` branch, use `os.remove()` or `Path.unlink()` when the target is a file,
and `shutil.rmtree()` only when it's a directory:

```python
if memories_dir.exists():
    if not force:
        result["existed"] = True
        if not memories_dir.is_dir():
            result["error"] = f"Path exists as a file, not a directory: {memories_dir}"
        return result
    else:
        if memories_dir.is_file():
            memories_dir.unlink()  # Remove the old single-file database
        else:
            shutil.rmtree(memories_dir)
```

### Option C: Fix `_create_connection()` error message and handle file case

```python
except OSError as e:
    if e.errno == _errno_mod.EEXIST:
        parent = self.db_path.parent
        if parent.is_file():
            raise DatabaseError(
                f"Failed to initialize database at '{self.db_path}': "
                f"'{parent}' exists as a file (old kuzu database format). "
                f"Run 'kuzu-memory init --force' to migrate to the new format."
            )
        raise DatabaseError(
            f"Failed to initialize database at '{self.db_path}': "
            f"the parent directory '{parent}' already exists "
            f"but kuzu could not create the database inside it "
            f"(kuzu reported: {e}). "
            f"Run 'kuzu-memory init --force' to recreate the database."
        )
```

### Recommended approach

Apply **Option B** (the most comprehensive fix) plus the error message improvement from
**Option C**. The `create_project_memories_structure()` function is the canonical place
to handle filesystem state — it should correctly handle the file-collision case with `force`.

Additionally, `--force` should work as advertised. The fix: when `memories_dir.is_file()`,
use `memories_dir.unlink()` rather than `shutil.rmtree()`.

---

## Migration Note

The old `.kuzu-memory` FILE is a kuzu database and contains data. Before removing it,
the fix should either:
1. Back it up to `.kuzu-memory-backups/` (a directory that already exists in hot-flash)
2. Warn the user that the old database will be removed

---

## Kuzu Version Context

- **Current installed kuzu version**: 0.11.3
- **Minimum required kuzu version**: `kuzu>=0.4.0` (per `pyproject.toml`)
- **Old kuzu behavior (< 0.6)**: called `mkdir(parent)` internally without `exist_ok`
  - This was handled by the EEXIST catch in `_create_connection()`
  - That catch is now **incorrectly** triggering for the file-collision case
- **kuzu 0.11.3 behavior**: requires parent dir to exist, creates the db file inside it
  - Does NOT call `mkdir()` internally — raises `RuntimeError` for directory paths

---

## Verification

Confirmed by reproducing the exact failure:
```python
# .kuzu-memory is a FILE
kuzu_file = Path("/project/.kuzu-memory")
kuzu_file.write_bytes(b"old db")

db_path = kuzu_file / "memories.db"
db_path.parent.mkdir(parents=True, exist_ok=True)
# => OSError: [Errno 17] File exists: '/project/.kuzu-memory'
# exist_ok=True does NOT suppress EEXIST when target is a file
```
