# Architecture Analysis: DB Location Migration & MCP Export/Import Tools

**Date**: 2026-02-25
**Scope**: Database path configuration, MCP server implementation, Memory schema, Temporal logic

---

## A) Database Path Configuration

### Current Default DB Path

There are **two competing path conventions** currently in the codebase:

**1. Project-scoped path (primary, used by CLI and services)**

Defined in `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/utils/project_setup.py`:

```python
def get_project_memories_dir(project_root: Path | None = None) -> Path:
    root = project_root or find_project_root()
    return root / "kuzu-memories"          # <-- visible directory at project root

def get_project_db_path(project_root: Path | None = None) -> Path:
    memories_dir = get_project_memories_dir(project_root)
    return memories_dir / "memories.db"    # <-- {project_root}/kuzu-memories/memories.db
```

This is what all CLI commands (init, setup, memory commands, hooks) use.

**2. Global fallback path (used by `get_database_path()` in `__init__.py`)**

```python
# src/kuzu_memory/__init__.py line 147
db_path = Path.home() / ".kuzu-memory" / "memories.db"
```

**3. Client API path (used by `KuzuMemoryClient`)**

```python
# src/kuzu_memory/client.py line 126
self._db_path = Path(db_path) if db_path else self._project_root / ".kuzu-memory" / "memories.db"
```

Note: the client defaults to `{project_root}/.kuzu-memory/memories.db` (hidden dir), not `kuzu-memories/`.

### Summary of DB Path Locations

| Context | Path | Notes |
|---|---|---|
| CLI commands via `setup`/`init` | `{project_root}/kuzu-memories/memories.db` | Committed to git (README encourages this) |
| `KuzuMemoryClient` API | `{project_root}/.kuzu-memory/memories.db` | Hidden directory, diverges from CLI |
| `get_database_path()` global | `~/.kuzu-memory/memories.db` | Global fallback (home dir) |
| MCP server `_get_db_path()` | `{project_root}/kuzu-memories` or `.kuzu-memories` | Kuzu dir, not the `.db` file |

**Key inconsistency**: The CLI creates `kuzu-memories/memories.db` (visible, git-committable), but `KuzuMemoryClient` defaults to `.kuzu-memory/memories.db` (hidden). Migration target `.kuzu-memory/` is already in `.gitignore` twice.

### How `setup` Command Configures DB Location

File: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/setup_commands.py`

```python
# setup_commands.py lines 181-182
memories_dir = get_project_memories_dir(project_root)   # project_root/kuzu-memories
db_path = get_project_db_path(project_root)             # project_root/kuzu-memories/memories.db
```

The `setup` command delegates to `init` (which calls `SetupService`), which calls
`create_project_memories_structure()` in `project_setup.py`. This creates:
- `{project_root}/kuzu-memories/` directory
- `{project_root}/kuzu-memories/memories.db` (Kuzu database)
- `{project_root}/kuzu-memories/README.md`
- `{project_root}/kuzu-memories/.gitignore` (only ignores `*.tmp`, `*.log`, `.DS_Store`)
- `{project_root}/kuzu-memories/project_info.md`

### Current .gitignore Entries for DB Paths

File: `/Users/masa/Projects/kuzu-memory/.gitignore`

```
# Kuzu database files (lines 165-168)
*.kuzu
kuzu_db/
*.db

# Memory system specific (lines 201-208)
.kuzu_memory/              # Primary database location (standardized) - comment is misleading
kuzu-memories/             # Legacy database location (to be consolidated)
.test_kuzu_memory/         # Test database (ephemeral)
.kuzu-memory-backups/      # Database backups (keep for safety)
memory_data/               # Legacy memory data
memory_cache/              # Memory cache files
*.memory                   # Memory export files

# Added by Claude MPM (lines 252-267 section)
.kuzu-memory/              # Hidden dot-dir convention
kuzu-memories/             # Also ignored here (duplicate)
```

**Notable**: Both `kuzu-memories/` AND `.kuzu-memory/` are currently gitignored in the project's own `.gitignore`. However, the `kuzu-memories/.gitignore` that is *generated inside* that directory only ignores `*.tmp`, `*.log`, `.DS_Store` — so the database would be committed from *that* project's perspective.

The migration target `.kuzu-memory/` (hidden directory convention) is already well-represented in `.gitignore`.

---

## B) MCP Server Implementation

### Key Files

| File | Role |
|---|---|
| `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/server.py` | Main MCP server class (78KB) |
| `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/__main__.py` | Entry point |
| `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/run_server.py` | Server runner |
| `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/queue_processor.py` | Async queue for learn ops |
| `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/protocol.py` | Protocol definitions |
| `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/testing/` | Testing utilities |

### How Tools Are Registered

The MCP server uses the **MCP Python SDK decorator pattern**. Tools are registered inside
`_setup_handlers()` using the `@self.server.list_tools()` decorator on an inner async function:

```python
class KuzuMemoryMCPServer:
    def __init__(self, project_root: Path | None = None) -> None:
        self.server = Server("kuzu-memory")
        self._setup_handlers()

    def _setup_handlers(self) -> None:

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """Enumerate available tools."""
            return [
                Tool(
                    name="kuzu_enhance",
                    description="...",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "..."},
                            "max_memories": {"type": "integer", "default": 5},
                        },
                        "required": ["prompt"],
                    },
                ),
                Tool(name="kuzu_learn", ...),
                Tool(name="kuzu_recall", ...),
                Tool(name="kuzu_remember", ...),
                Tool(name="kuzu_stats", ...),
                Tool(name="kuzu_optimize", ...),
                Tool(name="kuzu_merge", ...),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Dispatch tool calls."""
            if name == "kuzu_enhance":
                result = await self._enhance(...)
            elif name == "kuzu_learn":
                result = await self._learn(...)
            # ... etc.
            return [TextContent(type="text", text=result)]
```

### Tool Function Signature Pattern

**Registration** (in `handle_list_tools`):
```python
Tool(
    name="kuzu_<tool_name>",          # prefix convention
    description="...",                 # Long descriptive string
    inputSchema={                       # JSON Schema object
        "type": "object",
        "properties": {
            "param": {
                "type": "string|integer|boolean|number",
                "description": "...",
                "default": ...,        # Optional default
                "enum": [...],         # Optional enum values
            },
        },
        "required": ["required_param"],
    },
)
```

**Implementation** (private async method):
```python
async def _<tool_name>(self, param1: type, param2: type = default) -> str:
    """Brief description."""
    args = ["kuzu-memory", "subcommand", param1, "--flag", str(param2)]
    return await self._run_command(args)
```

Most tools delegate to the CLI via `_run_command()`, which runs subprocess calls to `kuzu-memory` CLI commands. The exceptions are `kuzu_optimize` and `kuzu_merge` which use the Python API directly.

### How MCP Server Connects to Memory Service

**Primary method**: Subprocess delegation via `_run_command()`:
```python
async def _run_command(self, args: list[str], capture_output: bool = True) -> str:
    cmd = ["kuzu-memory", *args]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=self.project_root,        # <-- Working directory determines DB path
    )
```

**Secondary method** (optimize/merge): Direct `KuzuAdapter` instantiation:
```python
db_path = self._get_db_path()         # project_root/kuzu-memories or .kuzu-memories
config = KuzuMemoryConfig.default()
db_adapter = KuzuAdapter(db_path, config)
db_adapter.initialize()
```

The `_get_db_path()` method in the MCP server:
```python
def _get_db_path(self) -> Path:
    """Get path to Kuzu database for current project."""
    db_path = self.project_root / "kuzu-memories"
    if not db_path.exists():
        db_path = self.project_root / ".kuzu-memories"  # fallback
    return db_path
```

Note: `_get_db_path()` returns the **directory** (the Kuzu DB dir), not the `memories.db` file.
This is because `KuzuAdapter` takes the directory path, whereas `MemoryService` takes the `.db` file path.

### Currently Registered MCP Tools

| Tool | Purpose | Implementation |
|---|---|---|
| `kuzu_enhance` | RAG prompt augmentation | CLI subprocess: `memory enhance` |
| `kuzu_learn` | Async background learning | CLI subprocess fire-and-forget: `memory learn --no-wait` |
| `kuzu_recall` | Semantic memory retrieval | CLI subprocess: `memory recall` |
| `kuzu_remember` | Sync blocking memory store | CLI subprocess: `memory store` |
| `kuzu_stats` | Health/diagnostics | CLI subprocess: `status` |
| `kuzu_optimize` | Memory optimization | Direct Python API via KuzuAdapter |
| `kuzu_merge` | Cross-database merge | Direct Python API via KuzuAdapter |

---

## C) Memory Schema & Source Types

### Memory Node Schema (from `storage/schema.py`)

```cypher
CREATE NODE TABLE IF NOT EXISTS Memory (
    id             STRING PRIMARY KEY,
    content        STRING,
    content_hash   STRING,              -- SHA256 for deduplication
    created_at     TIMESTAMP,
    valid_from     TIMESTAMP,
    valid_to       TIMESTAMP,           -- NULL = never expires
    accessed_at    TIMESTAMP,
    access_count   INT32 DEFAULT 0,
    memory_type    STRING,              -- cognitive type enum
    importance     FLOAT DEFAULT 0.5,
    confidence     FLOAT DEFAULT 1.0,
    source_type    STRING DEFAULT 'conversation',
    agent_id       STRING DEFAULT 'default',
    user_id        STRING,              -- nullable (multi-user)
    session_id     STRING,             -- nullable
    metadata       STRING DEFAULT '{}'  -- JSON blob
);
```

### Memory Model Fields (from `core/models.py` Pydantic model)

The Pydantic `Memory` model adds an `entities` field (not in DB schema directly, stored in metadata):

```python
class Memory(BaseModel):
    id: str                              # UUID
    content: str                         # 1..100,000 chars
    content_hash: str                    # SHA256 of normalized content
    created_at: datetime
    valid_from: datetime | None
    valid_to: datetime | None            # None = never expires
    accessed_at: datetime | None
    access_count: int                    # >= 0
    memory_type: MemoryType              # Enum: episodic|semantic|procedural|working|sensory|preference
    importance: float                    # 0.0..1.0
    confidence: float                    # 0.0..1.0
    source_type: str                     # Free-form string, default "conversation"
    agent_id: str                        # Default "default"
    user_id: str | None
    session_id: str | None
    metadata: dict[str, Any]             # JSON dict
    entities: list[str | dict]           # Extracted entities (NOT in DB schema - stored via MENTIONS edges)
```

### MemoryType Enum (Cognitive Types)

```python
class MemoryType(str, Enum):
    EPISODIC   = "episodic"    # Events, 30-day expiry, importance 0.7
    SEMANTIC   = "semantic"    # Facts, never expires, importance 1.0
    PROCEDURAL = "procedural"  # Instructions/patterns, never expires, importance 0.9
    WORKING    = "working"     # Current tasks, 1-day expiry, importance 0.5
    SENSORY    = "sensory"     # Ephemeral, 6-hour expiry, importance 0.3
    PREFERENCE = "preference"  # User prefs, never expires, importance 0.9
```

Legacy type migration map (for backward compatibility):
```python
"identity"   -> SEMANTIC
"preference" -> PREFERENCE
"decision"   -> EPISODIC
"pattern"    -> PROCEDURAL
"solution"   -> PROCEDURAL
"status"     -> WORKING
"context"    -> EPISODIC
```

### Source Type Values

The `source_type` field is a free-form string. Known values used in the codebase:

| Source Value | Where Used | Description |
|---|---|---|
| `"conversation"` | Default in schema DDL | Baseline fallback |
| `"ai-conversation"` | MCP `kuzu_learn` tool | AI assistant learning |
| `"git_sync"` | `integrations/git_sync.py:358` | Commit history sync |
| `"async"` | `async_memory/queue_manager.py:49` | Async queue default |
| `"async-cli"` | `async_memory/async_cli.py:88` | Async CLI operations |
| `"api"` | `client.py:204` | KuzuMemoryClient API calls |
| `"extraction"` | `ExtractedMemory.to_memory()` | Pattern extraction |
| `"batch"` | Code examples/docs | Batch imports |
| `"manual"` | CLAUDE.md examples | Manual CLI store |
| memory_type string | `_remember()` in MCP server | Passed as source (bug: line 515 uses memory_type as --source) |

**Note**: The `git_sync` source is special — it is the only source that the `SafePruningStrategy` will prune (`prune.py:91`: `if memory.get("source_type") != "git_sync": return False`).

---

## D) Timestamp & Temporal Logic

### How Timestamps Are Stored

All timestamps are `TIMESTAMP` type in Kuzu. In the Pydantic model they are Python `datetime` objects.
The `to_dict()` method passes them as `datetime` objects directly to Kuzu (not strings).

Fields:
- `created_at` — Set to `datetime.now()` at creation
- `valid_from` — Set to `datetime.now()` at creation (memory becomes valid immediately)
- `valid_to` — Set based on `MemoryType` retention policy:
  - `EPISODIC` → `created_at + 30 days`
  - `WORKING` → `created_at + 1 day`
  - `SENSORY` → `created_at + 6 hours`
  - `SEMANTIC`, `PROCEDURAL`, `PREFERENCE` → `None` (never expires)
- `accessed_at` — Updated on each recall via `update_access()`

### Temporal Decay System

File: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/recall/temporal_decay.py`
Used by: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/recall/ranking.py`

The `TemporalDecayEngine` calculates a recency score during ranking (not stored):

```python
# ranking.py - decay rates by memory type
decay_rates = {
    MemoryType.SENSORY:    0.25,   # Very fast (6 hours half-life)
    MemoryType.WORKING:    1,      # Fast (1 day half-life)
    MemoryType.EPISODIC:   30,     # Medium (30 days half-life)
    MemoryType.PROCEDURAL: 365,    # Slow (1 year)
    MemoryType.SEMANTIC:   365,    # Almost none
    MemoryType.PREFERENCE: 365,    # Almost none
}

# Exponential decay formula:
recency_score = math.exp(-age_days / decay_period)
```

The `TemporalDecayEngine` in `temporal_decay.py` extends this with:
- Multiple decay functions: `EXPONENTIAL`, `LINEAR`, `LOGARITHMIC`, `SIGMOID`, `POWER_LAW`, `STEP`
- Memory-type-specific minimum scores (SEMANTIC never goes below 0.8, PREFERENCE stays ≥ 0.6)
- Recency boost: memories within 24h get 1.5x multiplier by default
- Adaptive decay: configurable via `temporal_decay` config section

### Time-Based Filtering in Queries

Two mechanisms:
1. **Hard expiry**: `valid_to` field — queries filter out expired memories:
   ```cypher
   WHERE m.valid_to IS NULL OR m.valid_to > $current_time
   ```
2. **Soft ranking**: `TemporalDecayEngine` reduces ranking score of old memories without deleting them

The stale cleanup optimization (in `kuzu_optimize`) uses 90-day `accessed_at` threshold for archiving.

---

## Key File Paths Summary

| Purpose | File Path |
|---|---|
| DB path logic | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/utils/project_setup.py` |
| Global DB path fallback | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/__init__.py:147` |
| Client API default path | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/client.py:126` |
| MCP server | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/server.py` |
| MCP server DB path method | `server.py:543` `_get_db_path()` |
| Memory schema (DDL) | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/storage/schema.py` |
| Memory Pydantic model | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/core/models.py` |
| MemoryType enum | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/core/models.py:30` |
| Git sync (source "git_sync") | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/integrations/git_sync.py:358` |
| Temporal decay engine | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/recall/temporal_decay.py` |
| Ranking with decay | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/recall/ranking.py` |
| Setup command | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/setup_commands.py` |
| Init command | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/init_commands.py` |
| CLI root (db_path override) | `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/commands.py:234` |
| .gitignore | `/Users/masa/Projects/kuzu-memory/.gitignore` |

---

## Implementation Notes for Planned Changes

### 1. Migrating DB to `.kuzu-memory/`

The target path `.kuzu-memory/` is already used by `KuzuMemoryClient` and `get_database_path()`.
Migration requires changing:

- `get_project_memories_dir()` in `project_setup.py` — change `"kuzu-memories"` to `".kuzu-memory"`
- `get_project_db_path()` — verify it still returns `{dir}/memories.db`
- `KuzuMemoryMCPServer._get_db_path()` — update fallback logic in `server.py:543-550`
- `.gitignore` — `.kuzu-memory/` is already present; remove `kuzu-memories/` entry or keep both

Watch out for:
- The `_find_project_root()` in `server.py:76` looks for `kuzu-memories` directory as a project indicator
- README generated in `create_memories_readme()` references `kuzu-memories` path strings

### 2. New MCP Tools for Export/Import

Pattern to follow (see existing `kuzu_merge` tool as closest analog):

**Step 1: Add Tool to `handle_list_tools()` in `server.py`**:
```python
Tool(
    name="kuzu_export",
    description="Export all memories to a portable file format for backup or migration...",
    inputSchema={
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["json", "csv"],
                "default": "json",
                "description": "Export format",
            },
            "output_path": {
                "type": "string",
                "description": "Path to write export file (default: auto-generated)",
            },
            "include_source": {
                "type": "string",
                "description": "Filter by source_type (e.g. 'git_sync', 'ai-conversation')",
            },
        },
    },
),
Tool(
    name="kuzu_import",
    description="Import memories from a previously exported file...",
    inputSchema={
        "type": "object",
        "properties": {
            "source_path": {
                "type": "string",
                "description": "Path to import file",
            },
            "strategy": {
                "type": "string",
                "enum": ["skip", "update", "merge"],
                "default": "skip",
            },
            "dry_run": {"type": "boolean", "default": True},
        },
        "required": ["source_path"],
    },
),
```

**Step 2: Add dispatch in `handle_call_tool()`**:
```python
elif name == "kuzu_export":
    output_path = arguments.get("output_path")
    fmt = arguments.get("format", "json")
    include_source = arguments.get("include_source")
    result = await self._export(
        str(fmt),
        str(output_path) if output_path else None,
        str(include_source) if include_source else None,
    )
elif name == "kuzu_import":
    source_path = arguments.get("source_path", "")
    strategy = arguments.get("strategy", "skip")
    dry_run = arguments.get("dry_run", True)
    result = await self._import(str(source_path), str(strategy), bool(dry_run))
```

**Step 3: Implement private methods** (choose CLI delegation or direct API):

Option A — CLI delegation (simpler, consistent with enhance/learn/recall):
```python
async def _export(self, fmt: str, output_path: str | None, include_source: str | None) -> str:
    args = ["memory", "export", "--format", fmt]
    if output_path:
        args.extend(["--output", output_path])
    if include_source:
        args.extend(["--source", include_source])
    return await self._run_command(args)
```

Option B — Direct Python API (consistent with optimize/merge, more control):
```python
async def _export(self, fmt: str, output_path: str | None, ...) -> str:
    db_path = self._get_db_path()
    config = KuzuMemoryConfig.default()
    db_adapter = KuzuAdapter(db_path, config)
    db_adapter.initialize()
    # ... query and serialize memories
```

The `kuzu_merge` tool already implements import-like functionality (merging another DB).
For a JSON/CSV export/import, Option A (CLI delegation) is recommended to keep the MCP server thin
and avoid duplicating export logic.

---

## ArchivedMemory Node Schema

Also in `storage/schema.py`, for completeness:

```cypher
CREATE NODE TABLE IF NOT EXISTS ArchivedMemory (
    id           STRING PRIMARY KEY,
    original_id  STRING,
    content      STRING,
    memory_type  STRING,
    source_type  STRING,
    importance   FLOAT,
    created_at   TIMESTAMP,
    archived_at  TIMESTAMP,
    prune_score  FLOAT,
    prune_reason STRING,
    expires_at   TIMESTAMP
);
```
