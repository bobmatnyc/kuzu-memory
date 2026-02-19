# Memory Merge Command Research

**Date**: 2026-02-19
**Researcher**: Research Agent
**Objective**: Design a `kuzu-memory memory merge` command to import memories from another database

---

## Executive Summary

This research provides a comprehensive analysis of the kuzu-memory codebase to design a new `memory merge` command that can import memories from one Kùzu database into another. The command will follow existing patterns from the `cleanup` command group and leverage the existing `DeduplicationEngine` for conflict resolution.

**Key Findings**:
- ✅ Cleanup command provides excellent pattern for database operations
- ✅ DeduplicationEngine can handle duplicate detection (0.95 threshold)
- ✅ KuzuAdapter supports multiple concurrent database connections
- ✅ Memory schema includes content_hash for exact deduplication
- ⚠️ Need to handle different database instances (source + target)
- ⚠️ Relationship preservation requires careful planning

**Recommended Approach**: Create `memory merge` subcommand under memory group with dry-run/execute pattern, using DeduplicationEngine for conflict resolution and batch insertion for performance.

---

## 1. Existing Cleanup Command Path

### CLI Layer: `src/kuzu_memory/cli/cleanup_commands.py`

**Command Group Structure**:
```python
@click.group()
def cleanup() -> None:
    """🧹 Memory cleanup and maintenance operations."""
    pass

@cleanup.command()
@click.option("--dry-run/--execute", default=True, ...)
@click.option("--yes", is_flag=True, ...)
@click.option("--db-path", type=click.Path(), ...)
@click.pass_context
def stale(ctx: click.Context, ...) -> None:
    # Cleanup implementation
```

**Key Patterns Observed**:
1. **Command Group**: Uses `@click.group()` decorator for subcommands
2. **Options**: Consistent use of `--dry-run/--execute`, `--yes`, `--db-path`
3. **Context Passing**: Uses `@click.pass_context` for database path resolution
4. **Rich Output**: Uses `rich_print()` and `rich_panel()` for user feedback
5. **Service Manager**: Uses `ServiceManager.memory_service()` for lifecycle management

**Database Path Resolution**:
```python
def _resolve_db_path(ctx: click.Context, db_path: str | None) -> Path:
    """Resolve database path from context or argument."""
    from ..utils.project_setup import get_project_db_path

    if db_path:
        return Path(db_path)
    elif ctx.obj and ctx.obj.get("project_root"):
        return get_project_db_path(ctx.obj["project_root"])
    else:
        return get_project_db_path()
```

**Direct Database Access Pattern** (from `cleanup_commands.py`):
```python
# Pattern 1: Direct adapter access (for read-only queries)
config = KuzuMemoryConfig.default()
adapter = KuzuAdapter(db_path_obj, config)
adapter.initialize()

query = """
    MATCH (m:Memory)
    WHERE m.accessed_at < $cutoff_date
    RETURN m.id, m.content, m.created_at
"""

with adapter._pool.get_connection() as conn:
    result = conn.execute(query, {"cutoff_date": cutoff_iso})
    rows = result.get_as_pl()

# Pattern 2: Service Manager (for complex operations)
with ServiceManager.memory_service(db_path=db_path_obj, enable_git_sync=False) as mem_service:
    all_memories = mem_service.get_recent_memories(limit=100000)
```

### Service Layer: `src/kuzu_memory/services/memory_service.py`

**MemoryService Structure**:
```python
class MemoryService(BaseService):
    """Service layer for memory operations."""

    def __init__(self, db_path: Path, enable_git_sync: bool = True, config: dict | None = None):
        self._db_path = db_path
        self._enable_git_sync = enable_git_sync
        self._kuzu_memory: KuzuMemory | None = None

    def _do_initialize(self) -> None:
        """Initialize KuzuMemory instance."""
        self._kuzu_memory = KuzuMemory(
            db_path=self._db_path,
            enable_git_sync=self._enable_git_sync,
            config=self._config,
        )
        self._kuzu_memory.__enter__()

    @property
    def kuzu_memory(self) -> KuzuMemory:
        """Access underlying KuzuMemory instance."""
        if not self._kuzu_memory:
            raise RuntimeError("MemoryService not initialized")
        return self._kuzu_memory

    def remember(self, content: str, source: str, ...) -> str:
        """Store a new memory."""
        self._check_initialized()
        return self.kuzu_memory.remember(content=content, source=source, ...)
```

**Key Service Methods** (delegated to KuzuMemory):
- `remember()`: Store memory with automatic classification
- `get_recent_memories(limit)`: Retrieve recent memories
- `attach_memories(prompt, max_memories)`: Context-aware recall
- `get_memory_count()`: Database statistics
- `get_database_size()`: File size metrics

### Core Layer: `src/kuzu_memory/storage/kuzu_adapter.py`

**KuzuAdapter Connection Management**:
```python
class KuzuConnectionPool:
    """Connection pool for Kuzu database connections."""

    def __init__(self, db_path: Path, pool_size: int = 5):
        self.db_path = db_path
        self._pool: Queue[Any] = Queue(maxsize=pool_size)
        self._database: Any = None  # kuzu.Database instance

    def _create_connection(self) -> Any:
        """Create a new Kuzu connection using shared database instance."""
        if self._database is None:
            self._database = kuzu.Database(str(self.db_path))
        connection = kuzu.Connection(self._database)
        return connection

    @contextmanager
    def get_connection(self, timeout: float = 5.0) -> Iterator[Any]:
        """Get a connection from the pool."""
        connection = self._pool.get(timeout=timeout)
        try:
            yield connection
        finally:
            self._pool.put(connection, timeout=1.0)
```

**Important Insight**: Kùzu uses a **shared database instance** pattern where:
- One `kuzu.Database` instance per database file
- Multiple `kuzu.Connection` instances share the database
- Connection pool manages concurrent access

**Critical for Merge Command**: We need to handle **two separate database instances** (source and target), which means:
```python
# Source database (read-only)
source_db = kuzu.Database(str(source_path))
source_conn = kuzu.Connection(source_db)

# Target database (read-write)
target_db = kuzu.Database(str(target_path))
target_conn = kuzu.Connection(target_db)
```

---

## 2. Memory Service Architecture

### Core Memory Operations

**Memory Storage Flow**:
```
CLI Command (memory_commands.py)
    ↓
ServiceManager.memory_service() [context manager]
    ↓
MemoryService (services/memory_service.py) [thin wrapper]
    ↓
KuzuMemory (core/memory.py) [business logic]
    ↓
MemoryStore (storage/memory_store.py) [extraction + storage]
    ↓
KuzuAdapter (storage/kuzu_adapter.py) [database operations]
    ↓
Kùzu Database [graph storage]
```

**ServiceManager Pattern** (`src/kuzu_memory/cli/service_manager.py`):
```python
class ServiceManager:
    """Factory for creating service instances with lifecycle management."""

    @staticmethod
    @contextmanager
    def memory_service(
        db_path: Path | None = None,
        enable_git_sync: bool = True
    ) -> Iterator[MemoryService]:
        """Create and manage MemoryService lifecycle."""
        service = MemoryService(db_path, enable_git_sync)
        service.initialize()
        try:
            yield service
        finally:
            service.cleanup()
```

**Best Practice**: Use ServiceManager for managed lifecycle, direct adapter for low-level queries.

---

## 3. Database Schema

### Memory Node Structure

**Schema Definition** (`src/kuzu_memory/storage/schema.py`):
```sql
CREATE NODE TABLE IF NOT EXISTS Memory (
    id STRING PRIMARY KEY,
    content STRING,
    content_hash STRING,
    created_at TIMESTAMP,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    accessed_at TIMESTAMP,
    access_count INT32 DEFAULT 0,
    memory_type STRING,
    importance FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 1.0,
    source_type STRING DEFAULT 'conversation',
    agent_id STRING DEFAULT 'default',
    user_id STRING,
    session_id STRING,
    metadata STRING DEFAULT '{}'
);
```

**Key Fields for Merge**:
- **id**: UUID primary key (will conflict on merge - need new IDs)
- **content**: Text content (deduplicate on this)
- **content_hash**: SHA256 hash for exact deduplication
- **created_at**: Original creation timestamp (preserve)
- **memory_type**: Cognitive type (episodic, semantic, procedural, working, sensory, preference)
- **source_type**: Origin identifier (e.g., "conversation", "cli", "git-commit")
- **metadata**: JSON string with additional context

**Other Node Tables**:
```sql
Entity (id, name, entity_type, normalized_name, mention_count)
Session (id, user_id, agent_id, created_at, memory_count)
ArchivedMemory (id, original_id, content, archived_at, prune_score)
```

**Relationship Tables**:
```sql
MENTIONS (FROM Memory TO Entity)
RELATES_TO (FROM Memory TO Memory)
BELONGS_TO_SESSION (FROM Memory TO Session)
CO_OCCURS_WITH (FROM Entity TO Entity)
CONSOLIDATED_INTO (FROM Memory TO Memory)
```

**Merge Complexity**: Relationships require:
1. **ID Remapping**: Source memory IDs → New target memory IDs
2. **Entity Preservation**: Merge entity nodes or create new ones
3. **Relationship Recreation**: Update foreign keys to new IDs

---

## 4. CLI Registration Pattern

### Command Registration in `src/kuzu_memory/cli/commands.py`

**Import Pattern**:
```python
from .memory_commands import memory  # Import command group
from .cleanup_commands import cleanup
from .consolidate_commands import consolidate

# Register commands
cli.add_command(memory)    # Memory operations
cli.add_command(cleanup)   # Cleanup operations
cli.add_command(consolidate)  # Consolidation operations
```

**Memory Command Group** (`src/kuzu_memory/cli/memory_commands.py`):
```python
@click.group()
def memory() -> None:
    """🧠 Memory operations (store, recall, enhance)."""
    pass

# Subcommands
@memory.command()
def store(...): pass

@memory.command()
def learn(...): pass

@memory.command()
def recall(...): pass

@memory.command()
def enhance(...): pass

@memory.command()
def recent(...): pass

@memory.command()
def prune(...): pass
```

**Recommendation**: Add `merge` as a subcommand under `memory` group:
```python
@memory.command()
@click.argument("source_db", type=click.Path(exists=True))
@click.option("--strategy", type=click.Choice(["skip", "update", "merge"]), default="skip")
@click.option("--dry-run/--execute", default=True)
@click.option("--yes", is_flag=True)
@click.pass_context
def merge(ctx, source_db, strategy, dry_run, yes):
    """Merge memories from another database."""
    pass
```

---

## 5. Existing Import/Export Functionality

### No Built-in Export/Import

**Current State**: No explicit export/import commands found.

**Backup Functionality** (`src/kuzu_memory/storage/memory_store_backup.py`):
- File exists but appears to be a backup copy of `memory_store.py`
- Not an actual backup/restore mechanism

**Database File Copying**:
- Kùzu database is file-based (directory with `.kuzu` extension)
- Manual copy is possible: `cp -r source.kuzu target.kuzu`
- No built-in export to JSON/CSV

**Workaround Strategy**: Direct database-to-database merge using Cypher queries.

---

## 6. Deduplication Strategy

### DeduplicationEngine Analysis

**Engine Location**: `src/kuzu_memory/utils/deduplication.py`

**Three-Layer Deduplication**:
```python
class DeduplicationEngine:
    def __init__(
        self,
        exact_threshold: float = 1.0,        # SHA256 exact match
        near_threshold: float = 0.80,        # Normalized similarity
        semantic_threshold: float = 0.50,    # Token overlap
        min_length_for_similarity: int = 10,
        enable_update_detection: bool = True
    ):
        self.near_threshold = near_threshold
        self.semantic_threshold = semantic_threshold
```

**Deduplication Layers**:
1. **Exact Hash Matching**: SHA256 on `content_hash` field
2. **Normalized Text Comparison**: Case-insensitive, whitespace-normalized (80% threshold)
3. **Semantic Similarity**: Token overlap and sequence matching (50% threshold)

**Usage in Cleanup Command** (`cleanup_commands.py:229-335`):
```python
# Initialize deduplication engine
dedup = DeduplicationEngine(
    near_threshold=threshold,          # Default 0.95
    semantic_threshold=threshold,       # Default 0.95
    enable_update_detection=False,
)

# Find duplicate clusters
for mem in all_memories:
    duplicates = dedup.find_duplicates(
        mem.content,
        [m for m in all_memories if m.id != mem.id]
    )

    if duplicates:
        # Keep memory with highest access_count or most recent
        cluster_memories.sort(
            key=lambda x: (x.access_count, x.created_at),
            reverse=True
        )
        keeper = cluster_memories[0]
        to_remove = cluster_memories[1:]
```

**Merge Strategy Recommendations**:

**Option 1: Skip Duplicates (Default)**
- Use `content_hash` exact match
- Fast and safe (no data modification)
- Simple implementation

**Option 2: Update Existing**
- Use near_threshold=0.95 similarity
- Update metadata, access_count, importance
- Preserve newer information

**Option 3: Merge Metadata**
- Combine metadata from both memories
- Aggregate access_count, importance
- Create relationship (CONSOLIDATED_INTO)

---

## 7. Recommended Merge Command Design

### Command Specification

**CLI Interface**:
```bash
# Dry-run preview (default)
kuzu-memory memory merge /path/to/source.kuzu --dry-run

# Execute with confirmation
kuzu-memory memory merge /path/to/source.kuzu --execute

# Execute without confirmation
kuzu-memory memory merge /path/to/source.kuzu --execute --yes

# Custom deduplication strategy
kuzu-memory memory merge /path/to/source.kuzu --strategy update --execute

# Custom threshold
kuzu-memory memory merge /path/to/source.kuzu --threshold 0.90 --execute
```

**Options**:
```python
@memory.command()
@click.argument("source_db", type=click.Path(exists=True), required=True)
@click.option(
    "--strategy",
    type=click.Choice(["skip", "update", "merge"]),
    default="skip",
    help="Conflict resolution strategy (default: skip duplicates)"
)
@click.option(
    "--threshold",
    type=float,
    default=0.95,
    help="Similarity threshold for duplicate detection (default: 0.95)"
)
@click.option(
    "--dry-run/--execute",
    default=True,
    help="Preview changes without executing (default: dry-run)"
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts (use with --execute)"
)
@click.option(
    "--preserve-ids",
    is_flag=True,
    help="Attempt to preserve original memory IDs (may cause conflicts)"
)
@click.option(
    "--skip-relationships",
    is_flag=True,
    help="Import memories only, skip relationship recreation"
)
@click.option(
    "--db-path",
    type=click.Path(),
    help="Target database path (overrides project default)"
)
@click.pass_context
def merge(
    ctx: click.Context,
    source_db: str,
    strategy: str,
    threshold: float,
    dry_run: bool,
    yes: bool,
    preserve_ids: bool,
    skip_relationships: bool,
    db_path: str | None
) -> None:
    """
    🔀 Merge memories from another database.

    Imports memories from a source Kùzu database into the current project's
    database with intelligent deduplication and conflict resolution.

    \b
    🎯 STRATEGIES:
      skip   - Skip duplicate memories (fast, safe)
      update - Update existing memories with new metadata
      merge  - Merge metadata and create CONSOLIDATED_INTO relationship

    \b
    🎮 EXAMPLES:
      # Preview merge from backup
      kuzu-memory memory merge /backups/project.kuzu --dry-run

      # Execute merge with skip strategy
      kuzu-memory memory merge /backups/project.kuzu --execute

      # Merge with metadata update
      kuzu-memory memory merge /backups/project.kuzu --strategy update --execute

      # Aggressive merge with lower threshold
      kuzu-memory memory merge /other/db.kuzu --threshold 0.85 --execute --yes
    """
```

### Implementation Strategy

**Phase 1: Basic Memory Import**
1. Read all memories from source database
2. Check for duplicates in target using `content_hash`
3. Insert non-duplicate memories with new UUIDs
4. Report statistics

**Phase 2: Deduplication**
1. Integrate `DeduplicationEngine` with configurable threshold
2. Implement conflict resolution strategies (skip/update/merge)
3. Track keeper vs. removed memories

**Phase 3: Relationship Preservation**
1. Create ID mapping: `source_id -> target_id`
2. Recreate MENTIONS relationships (entity merging)
3. Recreate RELATES_TO relationships (memory-to-memory)
4. Recreate BELONGS_TO_SESSION relationships (session merging)

**Phase 4: Advanced Features**
1. Entity node merging (by normalized_name)
2. Session merging (by session_id)
3. Metadata conflict resolution
4. Progress tracking for large databases

### Database Operation Flow

**Step 1: Open Both Databases**
```python
import kuzu

# Source database (read-only)
source_db_path = Path(source_db)
source_db = kuzu.Database(str(source_db_path))
source_conn = kuzu.Connection(source_db)

# Target database (read-write via adapter)
target_db_path = _resolve_db_path(ctx, db_path)
target_config = KuzuMemoryConfig.default()
target_adapter = KuzuAdapter(target_db_path, target_config)
target_adapter.initialize()
```

**Step 2: Extract Source Memories**
```python
# Query all memories from source
source_query = """
    MATCH (m:Memory)
    RETURN m.id AS id,
           m.content AS content,
           m.content_hash AS content_hash,
           m.created_at AS created_at,
           m.memory_type AS memory_type,
           m.importance AS importance,
           m.source_type AS source_type,
           m.metadata AS metadata
    ORDER BY m.created_at ASC
"""

result = source_conn.execute(source_query)
source_memories = result.get_as_pl()
```

**Step 3: Check for Duplicates in Target**
```python
# Get existing content hashes from target
with target_adapter._pool.get_connection() as target_conn:
    target_query = """
        MATCH (m:Memory)
        RETURN m.content_hash AS content_hash, m.id AS id
    """
    result = target_conn.execute(target_query)
    existing_hashes = {row["content_hash"]: row["id"] for row in result.get_as_pl()}

# Filter source memories
new_memories = []
duplicate_memories = []

for mem in source_memories:
    if mem["content_hash"] in existing_hashes:
        duplicate_memories.append((mem, existing_hashes[mem["content_hash"]]))
    else:
        new_memories.append(mem)
```

**Step 4: Insert New Memories**
```python
from uuid import uuid4

# Batch insert for performance
insert_query = """
    CREATE (m:Memory {
        id: $id,
        content: $content,
        content_hash: $content_hash,
        created_at: $created_at,
        memory_type: $memory_type,
        importance: $importance,
        source_type: $source_type,
        metadata: $metadata,
        accessed_at: NULL,
        access_count: 0
    })
"""

with target_adapter._pool.get_connection() as target_conn:
    for mem in new_memories:
        params = {
            "id": str(uuid4()),  # New UUID for target
            "content": mem["content"],
            "content_hash": mem["content_hash"],
            "created_at": mem["created_at"],
            "memory_type": mem["memory_type"],
            "importance": mem["importance"],
            "source_type": f"{mem['source_type']}-merged",
            "metadata": mem["metadata"]
        }
        target_conn.execute(insert_query, params)
```

**Step 5: Handle Duplicates (by Strategy)**
```python
if strategy == "skip":
    # Do nothing
    pass

elif strategy == "update":
    # Update metadata, importance, access_count
    update_query = """
        MATCH (m:Memory {id: $target_id})
        SET m.importance = $importance,
            m.metadata = $metadata,
            m.accessed_at = $now
    """
    with target_adapter._pool.get_connection() as target_conn:
        for source_mem, target_id in duplicate_memories:
            params = {
                "target_id": target_id,
                "importance": source_mem["importance"],
                "metadata": source_mem["metadata"],
                "now": datetime.now().isoformat()
            }
            target_conn.execute(update_query, params)

elif strategy == "merge":
    # Create CONSOLIDATED_INTO relationship
    merge_query = """
        MATCH (target:Memory {id: $target_id})
        CREATE (merged:Memory {
            id: $merged_id,
            content: $content,
            content_hash: $content_hash,
            created_at: $created_at,
            memory_type: 'episodic',
            importance: $importance,
            source_type: 'merged'
        })
        CREATE (merged)-[:CONSOLIDATED_INTO {
            consolidation_date: $now,
            similarity_score: 1.0
        }]->(target)
    """
    # Implementation details...
```

**Step 6: Report Results**
```python
rich_panel(
    f"{'Preview' if dry_run else 'Merge Complete'} - Memory Import",
    title="🔀 Merge Results",
    style="blue" if dry_run else "green"
)

rich_print(f"\n📊 Import Summary:", style="bold blue")
rich_print(f"   Source: {source_db_path}", style="dim")
rich_print(f"   Target: {target_db_path}", style="dim")
rich_print(f"\n   Total memories in source: {len(source_memories)}", style="yellow")
rich_print(f"   New memories imported: {len(new_memories)}", style="green")
rich_print(f"   Duplicates found: {len(duplicate_memories)}", style="yellow")

if strategy == "update":
    rich_print(f"   Memories updated: {len(duplicate_memories)}", style="cyan")
elif strategy == "merge":
    rich_print(f"   Memories merged: {len(duplicate_memories)}", style="cyan")

if dry_run:
    rich_print("\nRun with --execute to apply changes.", style="dim")
```

---

## 8. Performance Considerations

### Database Connection Management

**Issue**: Kùzu uses file-based locking
**Solution**: Read source in one pass, close connection before writing to target

**Optimized Flow**:
```python
# Phase 1: Read from source
source_memories = read_all_from_source(source_db_path)

# Phase 2: Process in memory
new_memories, duplicates = deduplicate(source_memories, target_db_path)

# Phase 3: Batch write to target
batch_insert(new_memories, target_db_path)
```

### Batch Operations

**Recommendation**: Use batched inserts for >1000 memories
```python
BATCH_SIZE = 1000

for i in range(0, len(new_memories), BATCH_SIZE):
    batch = new_memories[i:i+BATCH_SIZE]
    # Execute batch insert
```

### Progress Reporting

**For Large Databases** (>10,000 memories):
```python
from tqdm import tqdm

for mem in tqdm(new_memories, desc="Importing memories"):
    # Insert memory
```

---

## 9. Testing Strategy

### Unit Tests

**Test Cases**:
1. **test_merge_empty_source**: Merge from empty database
2. **test_merge_no_duplicates**: All memories are new
3. **test_merge_all_duplicates**: All memories exist in target
4. **test_merge_partial_duplicates**: Mixed scenario
5. **test_merge_strategy_skip**: Verify skip behavior
6. **test_merge_strategy_update**: Verify update behavior
7. **test_merge_strategy_merge**: Verify merge relationships
8. **test_merge_dry_run**: Ensure no changes in dry-run mode
9. **test_merge_invalid_source_path**: Error handling
10. **test_merge_corrupted_source_db**: Error handling

### Integration Tests

**Test Scenarios**:
1. Merge two real project databases
2. Merge backup to main database
3. Merge with relationship preservation
4. Merge with entity deduplication
5. Performance test with 10,000+ memories

---

## 10. Implementation Checklist

**Phase 1: Basic Implementation** (MVP)
- [ ] Create `merge` command in `memory_commands.py`
- [ ] Implement `_resolve_db_path()` helper
- [ ] Add basic source database reading
- [ ] Add exact hash deduplication
- [ ] Add dry-run preview
- [ ] Add execute mode with confirmation
- [ ] Add statistics reporting

**Phase 2: Deduplication**
- [ ] Integrate `DeduplicationEngine`
- [ ] Implement "skip" strategy
- [ ] Implement "update" strategy
- [ ] Implement "merge" strategy (with CONSOLIDATED_INTO)
- [ ] Add configurable threshold option

**Phase 3: Relationship Preservation**
- [ ] Create ID mapping system
- [ ] Recreate MENTIONS relationships
- [ ] Recreate RELATES_TO relationships
- [ ] Recreate BELONGS_TO_SESSION relationships
- [ ] Add `--skip-relationships` flag

**Phase 4: Advanced Features**
- [ ] Entity node merging
- [ ] Session merging
- [ ] Metadata conflict resolution
- [ ] Progress bar for large imports
- [ ] Batch insert optimization

**Phase 5: Testing & Documentation**
- [ ] Unit tests for all strategies
- [ ] Integration tests for real scenarios
- [ ] Performance benchmarks
- [ ] User documentation
- [ ] Example workflows

---

## 11. File Paths & Code References

### Key Files for Implementation

**CLI Layer**:
- `src/kuzu_memory/cli/memory_commands.py` - Add `@memory.command() def merge()`
- `src/kuzu_memory/cli/cli_utils.py` - Reuse `rich_print()`, `rich_panel()`
- `src/kuzu_memory/cli/service_manager.py` - Use `ServiceManager` pattern

**Service Layer**:
- `src/kuzu_memory/services/memory_service.py` - Thin wrapper for operations
- `src/kuzu_memory/services/base.py` - Base service lifecycle

**Core Layer**:
- `src/kuzu_memory/storage/kuzu_adapter.py` - Database connection management
- `src/kuzu_memory/storage/schema.py` - Schema queries and DDL
- `src/kuzu_memory/utils/deduplication.py` - Deduplication engine

**Models**:
- `src/kuzu_memory/core/models.py` - Memory, MemoryType, MemoryContext
- `src/kuzu_memory/core/config.py` - KuzuMemoryConfig

### Code Snippets for Reuse

**1. Database Path Resolution** (from `cleanup_commands.py:916-934`):
```python
def _resolve_db_path(ctx: click.Context, db_path: str | None) -> Path:
    from ..utils.project_setup import get_project_db_path

    if db_path:
        return Path(db_path)
    elif ctx.obj and ctx.obj.get("project_root"):
        return get_project_db_path(ctx.obj["project_root"])
    else:
        return get_project_db_path()
```

**2. Direct Adapter Access** (from `cleanup_commands.py:713-741`):
```python
config = KuzuMemoryConfig.default()
adapter = KuzuAdapter(db_path_obj, config)
adapter.initialize()

query = """
    MATCH (m:Memory)
    RETURN m.id, m.content, m.content_hash
"""

with adapter._pool.get_connection() as conn:
    result = conn.execute(query)
    rows = result.get_as_pl()
```

**3. Deduplication Setup** (from `cleanup_commands.py:298-303`):
```python
dedup = DeduplicationEngine(
    near_threshold=threshold,
    semantic_threshold=threshold,
    enable_update_detection=False,
)

duplicates = dedup.find_duplicates(
    mem.content,
    [m for m in all_memories if m.id != mem.id]
)
```

**4. Confirmation Prompt** (from `cleanup_commands.py:196-204`):
```python
if not yes:
    rich_print(
        f"⚠️  WARNING: About to merge {len(new_memories)} memories!",
        style="bold red"
    )
    confirm = click.confirm("\nDo you want to continue?", default=False)
    if not confirm:
        rich_print("\n❌ Merge cancelled by user", style="yellow")
        return
```

**5. Statistics Reporting** (from `cleanup_commands.py:836-853`):
```python
rich_panel(
    f"Analysis Complete ({analysis_time_ms:.0f}ms)",
    title="📋 Merge Report",
    style="green"
)

rich_print("\n🔍 Summary:", style="bold blue")
rich_print(f"   Memories to import: {len(new_memories)}", style="green")
rich_print(f"   Duplicates found: {len(duplicates)}", style="yellow")

rich_print("\n💾 Expected Changes:", style="bold blue")
rich_print(f"   New memories: +{len(new_memories)}")
rich_print(f"   Total after merge: {total_memories + len(new_memories)}")
```

---

## 12. Risk Assessment

### High Risk
- **Database Corruption**: Writing to locked/corrupted target database
  - **Mitigation**: Validate target database health before merge
  - **Mitigation**: Create automatic backup before execute mode

- **ID Conflicts**: Source memory IDs collide with target IDs
  - **Mitigation**: Always generate new UUIDs for imported memories
  - **Mitigation**: Maintain ID mapping for relationship recreation

### Medium Risk
- **Memory Bloat**: Importing large databases without deduplication
  - **Mitigation**: Default to skip strategy with 0.95 threshold
  - **Mitigation**: Show preview of duplicates in dry-run

- **Relationship Loss**: Failing to preserve memory relationships
  - **Mitigation**: Phase 3 implementation with ID remapping
  - **Mitigation**: Add `--skip-relationships` flag for fast imports

### Low Risk
- **Metadata Conflicts**: Merging conflicting metadata
  - **Mitigation**: Strategy-based resolution (skip/update/merge)
  - **Mitigation**: Preserve both versions in merge strategy

- **Performance Degradation**: Slow imports for large databases
  - **Mitigation**: Batch insert optimization
  - **Mitigation**: Progress bar for user feedback

---

## 13. Alternative Approaches Considered

### Approach 1: JSON Export/Import (Rejected)
**Pros**: Human-readable, portable, version-controlled
**Cons**: Loses graph relationships, slow for large datasets, requires schema mapping
**Verdict**: Not suitable for database-to-database merge

### Approach 2: SQL Dump/Restore (Rejected)
**Pros**: Fast, preserves exact schema
**Cons**: Kùzu doesn't support SQL dumps, no deduplication
**Verdict**: Not applicable to Kùzu architecture

### Approach 3: Cypher LOAD CSV (Rejected)
**Pros**: Native Kùzu support for bulk import
**Cons**: Requires export step, doesn't handle relationships, no deduplication
**Verdict**: Useful for external data import, not for database merge

### Approach 4: Direct Database Merge (Selected)
**Pros**: Preserves relationships, efficient, supports deduplication
**Cons**: More complex implementation, requires ID remapping
**Verdict**: Best fit for kuzu-memory use cases

---

## 14. Future Enhancements

**Version 2 Features**:
1. **Selective Merge**: Filter by memory_type, source_type, date range
2. **Conflict Resolution UI**: Interactive mode for resolving conflicts
3. **Incremental Merge**: Track last merge timestamp, import only new memories
4. **Bidirectional Sync**: Keep two databases in sync
5. **Remote Merge**: Merge from remote database via network
6. **Export to JSON**: Complement merge with export functionality
7. **Merge Preview**: Show detailed diff before execute

**Performance Optimizations**:
1. Parallel processing for large datasets
2. Streaming import (don't load all memories in memory)
3. Compressed transfer for remote merge
4. Delta encoding for incremental sync

---

## 15. Conclusion

The `memory merge` command is highly feasible and can be implemented following existing patterns from the `cleanup` command. The recommended approach is:

1. **Start with MVP** (Phase 1): Basic import with exact hash deduplication
2. **Add flexibility** (Phase 2): Strategy-based conflict resolution
3. **Preserve relationships** (Phase 3): Full graph database merge
4. **Optimize** (Phase 4): Performance and user experience improvements

**Estimated Effort**:
- Phase 1 (MVP): 4-6 hours
- Phase 2 (Deduplication): 3-4 hours
- Phase 3 (Relationships): 6-8 hours
- Phase 4 (Polish): 3-4 hours
- Testing: 4-6 hours
- **Total**: 20-28 hours

**Key Success Factors**:
- Reuse existing patterns (cleanup command, deduplication engine)
- Follow established CLI conventions (dry-run, confirmation, rich output)
- Maintain data integrity (new IDs, relationship preservation)
- Provide clear user feedback (statistics, progress, errors)

---

**Research Complete**
**Next Steps**: Begin Phase 1 implementation with basic merge command
