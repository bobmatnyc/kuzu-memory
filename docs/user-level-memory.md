# User-Level Memory — Design Specification

**Status**: Planned
**Version target**: 1.7.0
**Author**: Architecture team
**Date**: 2026-03-13

---

## Overview

kuzu-memory currently operates in **project mode**: each project has its own isolated database.
High-quality, generalizable memories (architectural decisions, gotchas, patterns) never leave
the project that discovered them.

**User-level memory** adds a second mode where a shared `~/.kuzu-memory/user.db` receives
promoted copies of valuable memories from any project, making cross-project knowledge available
at session start — without sacrificing the speed of project-local queries.

---

## Mode Comparison

| Aspect | `project` mode (default) | `user` mode |
|--------|--------------------------|-------------|
| Database(s) | One per project | Project DB + `~/.kuzu-memory/user.db` |
| Cross-project patterns | No | Yes (via promotion) |
| Write concurrency | One writer per project | One writer per project + async user DB writer |
| Session-start query | Single DB | Parallel: project + user |
| Isolation | Full | Memories tagged with `project_tag` |
| Mode switch | N/A | All-or-nothing; can't mix per-project |
| Rollback | N/A | Stop promotion; user DB is additive |

**Mode is all-or-nothing**: either all kuzu-memory instances use user mode, or none do.
Mixing modes within the same user account is not supported.

---

## Architecture

```
Session start (user mode)
    ↓
    ├── query project DB  ─────────────────────────┐
    │   (recent work, project-specific memories)    ├── merge → inject into prompt
    └── query user DB  ────────────────────────────┘
        (cross-project rules, patterns, gotchas,
         architecture decisions)

Session end / MemoryService.__exit__() (user mode)
    ↓
    scan project DB for promotion candidates
    filter: knowledge_type ∈ {rule, pattern, gotcha, architecture}
            AND importance ≥ 0.8
            AND NOT already in user DB (content_hash dedupe)
    ↓
    async write to user DB with project_tag = current project name
```

### Key design decisions

**1. Promotion is async and happens at session end**

Writing to the user DB is fire-and-forget. The session-end promotion does not block
the CLI or MCP tool response. If promotion fails (e.g., file lock contention), it is
logged and retried on the next session end — memories are never lost, only delayed.

**2. Deduplication via content_hash**

`Memory.content_hash` (SHA256 of content) prevents the same insight from being
promoted multiple times across sessions. The user DB stores one canonical copy;
subsequent identical discoveries are no-ops.

**3. project_tag for namespace tracking**

Each memory in the user DB carries `project_tag` (the project directory basename,
e.g. `kuzu-memory`). This enables:
- Filtering user DB queries to exclude the current project (avoid duplicates)
- Auditing which project each memory came from
- Future per-project rollback from user DB

**4. Quality filter is tight by design**

The promotion filter (`knowledge_type` + `importance ≥ 0.8`) ensures the user DB
stays small — in the hundreds of memories, not tens of thousands. This is critical
for keeping embedding search fast at the user level.

---

## Performance Analysis

### Promotion (session end, async)

| Step | Cost |
|------|------|
| Scan project DB for candidates | ~5–20ms (indexed query on knowledge_type + importance) |
| Deduplicate via content_hash | ~2ms per candidate (hash lookup, not embedding search) |
| Write to user DB (per memory) | ~10–30ms (single Kùzu write) |
| Total for typical session | <100ms, runs in background thread |

Promotion does not block the foreground session. All writes use retry + jitter for
file-lock contention between concurrent Claude instances.

### Session start (user mode — additional query)

| Step | Cost |
|------|------|
| User DB query (top patterns by knowledge_type) | ~5–15ms (small DB, indexed) |
| Project DB query (recent work) | ~10–30ms (existing behavior) |
| Parallel execution overhead | ~0ms (concurrent.futures.ThreadPoolExecutor) |
| Additional latency vs project mode | **+5–15ms** |

This is within the 100ms enhancement budget. The user DB query runs in parallel with
the existing project DB query, so the wall-clock addition is only the delta.

### User DB size estimate

Assuming 5 projects, 20 sessions/day each, 5% of memories qualify for promotion,
average 50 memories/session:

```
5 projects × 20 sessions × 50 memories × 5% = 250 promoted/day
At 0.8+ importance threshold, real rate closer to 20–50/day
User DB reaches 1000 memories after ~1 month → still fast
```

Periodic pruning of low-importance memories from the user DB (via existing prune
infrastructure) keeps the ceiling bounded.

---

## Configuration

New sub-config added to `KuzuMemoryConfig`:

```yaml
# ~/.kuzu-memory/config.yaml  (user-level config)
user:
  mode: user                    # "project" (default) or "user"
  user_db_path: ~/.kuzu-memory/user.db   # overridable
  promotion_min_importance: 0.8
  promotion_knowledge_types:
    - rule
    - pattern
    - gotcha
    - architecture
  project_tag: ""               # auto-derived from cwd basename if empty
```

Environment variable overrides:

```bash
KUZU_MEMORY_MODE=user
KUZU_MEMORY_USER_DB_PATH=/custom/path/user.db
KUZU_MEMORY_PROMOTION_MIN_IMPORTANCE=0.9
```

Config resolution order (highest wins):
1. Environment variables
2. Project-level `.kuzu-memory/config.yaml`
3. User-level `~/.kuzu-memory/config.yaml`
4. Built-in defaults

---

## Schema Changes

### Memory and ArchivedMemory tables

New field added via migration `v1_6_46_project_tag`:

```sql
ALTER TABLE Memory ADD project_tag STRING DEFAULT ''
ALTER TABLE ArchivedMemory ADD project_tag STRING DEFAULT ''
```

This field is populated:
- **Project DB**: always empty string (project is implicit from DB path)
- **User DB**: set to the source project basename at promotion time

---

## New Service: UserMemoryService

```python
class UserMemoryService:
    """Manages the user-level cross-project memory database."""

    def promote(self, memory: Memory, project_tag: str) -> bool:
        """Promote a single memory to user DB. Returns True if written, False if duplicate."""

    def promote_batch(self, memories: list[Memory], project_tag: str) -> int:
        """Promote a list of memories. Returns count actually written."""

    def recall(self, query: str, limit: int = 10) -> list[Memory]:
        """Semantic recall from user DB only."""

    def get_patterns(
        self,
        knowledge_types: list[KnowledgeType] | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        """Return top memories by knowledge_type, sorted by importance."""

    def get_stats(self) -> dict[str, Any]:
        """Return user DB size, type breakdown, top projects."""
```

---

## MemoryService Changes

In `user` mode, `MemoryService.__exit__()` calls:

```python
def _promote_eligible_memories(self) -> int:
    """
    Async promotion of high-quality memories to user DB at session end.
    Called from __exit__ in user mode. Non-blocking (background thread).
    Returns count of memories queued for promotion.
    """
```

The promotion filter query:

```cypher
MATCH (m:Memory)
WHERE m.knowledge_type IN ['rule', 'pattern', 'gotcha', 'architecture']
  AND m.importance >= $min_importance
  AND m.valid_to IS NULL OR m.valid_to > $now
RETURN m
ORDER BY m.importance DESC
LIMIT 100
```

---

## New MCP Tools

### `kuzu_project_context`

Returns a structured context bundle for the current project — replaces the current
piecemeal recall approach. Designed for MPM session-resume injection.

```json
{
  "recent_work": "SOA migration complete. Threading deadlock fixed. MCP tools now call service layer directly.",
  "gotchas": [
    {"content": "KuzuConnectionPool._lock must be RLock", "importance": 0.95},
    {"content": "Never cache write operations with @cached_method", "importance": 0.9}
  ],
  "architecture": [
    {"content": "All CLI uses ServiceManager.memory_service() context manager", "importance": 0.95}
  ],
  "patterns": [...],
  "rules": [...],
  "conventions": [...]
}
```

### `kuzu_user_context` (user mode only)

Same structure as `kuzu_project_context` but queries the user DB, excluding memories
tagged with the current project (those are in `kuzu_project_context`).

---

## CLI Commands

```bash
# Initialize user mode (one-time setup)
kuzu-memory user setup

# Check user DB status
kuzu-memory user status

# Manually promote memories from current project
kuzu-memory user promote [--dry-run] [--min-importance 0.8]

# Migrate from project mode to user mode
kuzu-memory user migrate [--projects /path1 /path2 ...]

# Show cross-project patterns
kuzu-memory user patterns [--type gotcha|rule|pattern|architecture]
```

---

## Migration Path: project → user mode

### Step 1: Setup user DB

```bash
kuzu-memory user setup
```

Creates `~/.kuzu-memory/user.db`, initializes schema, sets `mode: user` in
`~/.kuzu-memory/config.yaml`.

### Step 2: Initial promotion from existing projects (optional)

```bash
kuzu-memory user migrate --projects ~/Projects/project-a ~/Projects/project-b
```

Scans each project's DB, promotes eligible memories. Shows preview with `--dry-run`.

### Step 3: Verify

```bash
kuzu-memory user status
# User DB: ~/.kuzu-memory/user.db
# Mode: user
# Total memories: 47
# By type: rule=12, pattern=18, gotcha=8, architecture=9
# From projects: kuzu-memory (23), my-api (15), dashboard (9)
```

### Step 4: All new sessions now use user mode

No further action needed. Existing Claude Code hooks and MCP server configuration
remain unchanged — mode is read from config automatically.

### Rollback

```bash
# Revert to project mode (stop promotion, ignore user DB)
kuzu-memory user disable

# Or manually: edit ~/.kuzu-memory/config.yaml
# user:
#   mode: project
```

User DB is not deleted on disable. Re-enabling user mode resumes from existing state.

---

## MPM Integration

The `mpm-session-resume` skill should call `kuzu_project_context` (and `kuzu_user_context`
in user mode) at session start, injecting results into the first agent delegation.

```
PM session start (user mode):
    1. kuzu_project_context → project-specific recent work + gotchas
    2. kuzu_user_context    → cross-project rules + patterns
    3. Merge both contexts  → inject into Research/Engineer agent context block
```

This replaces static CLAUDE.md reading with dynamic, recency-weighted, type-filtered context.

---

## Implementation Order

1. Schema migration `v1_6_46_project_tag` — adds `project_tag` field
2. `UserConfig` sub-config in `KuzuMemoryConfig`
3. `UserMemoryService` — new service
4. `MemoryService._promote_eligible_memories()` — session-end hook
5. MCP tools `kuzu_project_context` + `kuzu_user_context`
6. CLI `kuzu-memory user *` commands
7. Integration tests
8. Version bump to 1.7.0

---

## Open Questions

- **Embedding model consistency**: User DB promotion assumes the same embedding model
  across all contributing projects. If a project uses a different model, promoted memories
  will have incompatible embedding vectors. Mitigation: store embedding model name with
  each memory; skip promotion if model differs from user DB default.

- **User DB backup**: Since user DB aggregates insights across all projects, it should
  be included in standard backup recommendations. A `kuzu-memory user export` command
  is a natural addition.

- **Privacy**: User DB lives in home directory. For shared machines or CI environments,
  user mode should be explicitly disabled or pointed to an ephemeral path.
