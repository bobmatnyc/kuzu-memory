# Storage, Recall, and Indexing Efficiency Analysis

**Date**: 2026-04-01
**Scope**: kuzu-memory project — storage efficiency, recall query strategy, indexing, memory classification, optimization tools
**Database under analysis**: `.kuzu-memory/memories.db` (12 MB on disk, 1,015 memories)

---

## Executive Summary

The database has five compounding problems that explain both the 12 MB size and the all-`episodic` / empty `kuzu_project_context` symptoms:

1. **`knowledge_type` column does not exist in the live schema** — the field was never migrated into the on-disk database. All project-context queries return empty results as a direct consequence.
2. **`content_hash` is NULL for every row** — deduplication is structurally broken. 105 exact-duplicate session-start strings, 31+ test-data strings, and many doubled git commit messages live in the database.
3. **All 1,015 memories have `valid_to` set and 410 are already expired** — expired records are never purged automatically; they accumulate silently.
4. **git_sync metadata is ~20 KB per commit row** — 489 commit records account for roughly 1.4 MB of text, with file diffs, per-file stats, and 146-item `changed_files` lists stored in a JSON blob in the `metadata` STRING column.
5. **Recall is keyword + entity graph traversal only — no vector/semantic search** — `caching/embeddings_cache.py` exists but is never wired into the recall path; there is no embedding stored in the database. "Vector similarity" in docs refers to Python-side cosine similarity that is never executed in practice.

---

## 1. Current State Analysis

### 1.1 Schema — What Is Actually on Disk

**File**: `src/kuzu_memory/storage/schema.py`, line 23-42

The `schema.py` source defines a `Memory` node table with 17 fields including `knowledge_type STRING DEFAULT 'note'` and `project_tag STRING DEFAULT ''`.

**Reality in the live database** (confirmed with `CALL TABLE_INFO("Memory")`):

| Column # | Name | Type | Present in schema.py? |
|---|---|---|---|
| 0–8, 10–15 | id, content, content_hash, timestamps, memory_type, importance, confidence, source_type, agent_id, user_id, session_id, metadata | STRING/TIMESTAMP/FLOAT/INT32 | Yes |
| **missing** | **knowledge_type** | **STRING** | **Yes in source, NOT in DB** |
| **missing** | **project_tag** | **STRING** | **Yes in source, NOT in DB** |

The database was created at schema version `1.0` and no migration has added these columns. The migration manager (`src/kuzu_memory/migrations/manager.py`) and the `cognitive_types.py` migration exist, but `migration_state.json` shows `{}` — no migrations have run.

### 1.2 Memory Distribution (Actual)

```
Total memories: 1,015
memory_type:    episodic  1,015 (100%)
knowledge_type: [column does not exist]
importance:     0.5 for all 1,015 memories
```

**Source-type breakdown:**
| source_type | count | avg content chars | approx total text |
|---|---|---|---|
| git_sync | 489 | 872 | ~427 KB |
| identity | 421 | 18 | ~7.6 KB |
| claude-code-session | 105 | 30 | ~3.2 KB |

**Content_hash:** NULL for all 1,015 rows.

**Expiry:** All 1,015 rows have `valid_to` set (none are permanent). 410 rows are already past expiry as of 2026-04-01.

**Entities:** 0 Entity nodes, 0 MENTIONS relationships. Entity extraction runs in code but results are discarded before being stored (see §1.5).

### 1.3 Storage Size Breakdown

Total on disk: **12 MB** for `memories.db` + 944 B WAL.

Estimated content breakdown based on query results:

| Layer | Estimated size |
|---|---|
| git_sync content (commit messages, avg 872 chars × 489) | ~427 KB |
| git_sync metadata JSON (avg ~20 KB × 489) | ~9.8 MB |
| identity + session content | ~11 KB |
| Kuzu internal storage overhead (columnar, page alignment) | ~1.7 MB |
| **Total** | **~12 MB** |

The `metadata` field is the dominant storage consumer. A single `git_sync` record carries: `commit_sha` (40 chars), `commit_author`, `commit_committer`, `commit_timestamp`, `branch`, `changed_files` (list of up to 146 filenames), `file_stats` (dict of per-file insertions/deletions), and `file_categories`. One record inspected was 20,503 characters; five records inspected ranged 31,051–31,851 characters in metadata alone.

### 1.4 Indexing Strategy

**File**: `src/kuzu_memory/storage/schema.py`, line 116-122

```python
# NOTE: Kuzu does not support traditional secondary indexes (CREATE INDEX).
INDICES_DDL = ""
```

`INDICES_DDL` is an empty string. No secondary indexes exist.

Kuzu provides:
- Automatic hash index on primary key (`id`)
- CSR adjacency list indexes for edge tables (unused — 0 MENTIONS)
- Columnar storage with vectorized scan

**Consequence:** Every recall query is a full table scan of all 1,015 Memory nodes, filtered by string `CONTAINS` or `IN` list comparisons. There is no index on `memory_type`, `created_at`, `importance`, `valid_to`, or (the missing) `knowledge_type`.

Kuzu does support `CREATE VECTOR INDEX` and `CREATE FTS_INDEX` via function calls (documented in schema.py comment). Neither has been created.

### 1.5 Recall and Query Efficiency

**Files**: `src/kuzu_memory/recall/strategies.py`, `src/kuzu_memory/recall/coordinator.py`

The recall path (`attach_memories` → `RecallCoordinator._auto_recall`) runs three strategies serially:

**KeywordRecallStrategy** (`strategies.py:208-246`):
```cypher
MATCH (m:Memory)
WHERE (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($current_time))
AND (LOWER(m.content) CONTAINS LOWER($keyword_0) OR ...)
RETURN m ORDER BY m.created_at DESC, m.importance DESC LIMIT $limit
```
- Full scan every call (no index on `content` or `valid_to`)
- `valid_to` filter hits 410 already-expired rows that are never cleaned up — every recall touches them

**EntityRecallStrategy** (`strategies.py:326-358`):
```cypher
MATCH (e:Entity)-[:MENTIONS]-(m:Memory)
WHERE e.normalized_name IN $entity_names
```
- Always returns 0 results because Entity table is empty (entity storage path in `query_builder.py:store_memory_entities` is called from `memory_store.py:_store_memory_in_database`, but the `generate_memories` path used by `kuzu_learn` never populates `content_hash`, `knowledge_type`, or entities into the database correctly — see §1.6)

**TemporalRecallStrategy**: Returns nothing unless prompt contains literal keywords like "recent", "today", etc.

**No vector/semantic search exists in the recall path.** `caching/embeddings_cache.py` caches embeddings between invocations of the Python-side scoring, but `_calculate_relevance_score` in `coordinator.py:290-335` only computes Jaccard word overlap — it never calls the embedding model. The `sentence-transformers/all-MiniLM-L6-v2` model is available (it is what the vector search index uses) but is not used at recall time.

**Temporal decay** (`recall/temporal_decay.py`): Sophisticated multi-function engine (exponential, sigmoid, power-law). However, it is only called from `coordinator.py:_calculate_relevance_score` indirectly — it is NOT called at all in the current coordinator. Decay scores are computed in `TemporalDecayEngine` but the coordinator's `_rank_memories` method uses only `importance`, `confidence`, `memory_type` boost, Jaccard overlap, and a simple `(30 - days_old) / 30` recency term inline (`coordinator.py:331`). The `TemporalDecayEngine` object is never instantiated in the coordinator.

### 1.6 Memory Classification Gap

**Why all 605/1,015 memories are `episodic`:**

**Path 1: `kuzu_learn` → `BackgroundLearner._process_learn_task` → `generate_memories`**

`background_learner.py:166`:
```python
memory_ids = memory.kuzu_memory.generate_memories(
    content=task.content, metadata=task.metadata, source=task.source
)
```
`generate_memories` in `memory_store.py:138-153` creates `Memory` objects with `memory_type=extracted_memory.memory_type` (classified by NLP) but `knowledge_type` is never set — it inherits the model default of `KnowledgeType.NOTE`. Then `store_memory_in_database` in `query_builder.py:210-224` issues a `CREATE (m:Memory {...})` that does NOT include `knowledge_type` or `content_hash` in the field list. Since `knowledge_type` does not exist in the live schema, this would fail silently even if it were set.

**Path 2: `kuzu_remember` → `memory.py:remember`**

`core/memory.py:469-536`: The `remember()` method correctly resolves `knowledge_type` from the string parameter (line 507-512) and stores it in the `Memory` object. However, `query_builder.py:store_memory_in_database` never writes `knowledge_type` or `content_hash` to the CREATE statement.

**Why `content_hash` is NULL for all rows:**

`Memory.from_dict` and `Memory.__init__` (via `model_validator`) generate a SHA256 `content_hash` (`models.py:244-249`). But the `store_memory_in_database` CREATE query in `query_builder.py:210-224` only writes `id`, `content`, `source_type`, `memory_type`, `created_at`, `valid_to`, `user_id`, `session_id`, `agent_id`, `metadata` — `content_hash` is absent from the CREATE statement.

**Root cause chain:**
1. `knowledge_type` column was added to `schema.py` but no `ALTER TABLE` migration was run → column doesn't exist in the live DB
2. `query_builder.py:store_memory_in_database` never writes `content_hash` or `knowledge_type` even when the column exists
3. `kuzu_learn` uses `generate_memories` which hardcodes `memory_type=extracted_memory.memory_type` (from NLP classifier) but classifier output defaults heavily to `episodic` for conversational content
4. No auto-classification of `knowledge_type` exists anywhere — it is purely caller-supplied via `kuzu_remember`; `kuzu_learn` has no `knowledge_type` parameter

**Why `kuzu_project_context` returns empty:**

`server.py:795-820` queries `WHERE m.knowledge_type = $kt`. Since the column does not exist in the schema, Kuzu would throw `Cannot find property knowledge_type`. The `try/except Exception: return []` in `_by_type` silently swallows the error and returns empty lists for all categories.

### 1.7 `kuzu_optimize` — What It Actually Does

**File**: `src/kuzu_memory/mcp/server.py:918-1300`

Three strategies:
- `top_accessed`: Queries memories with `access_count > 0`, groups by content similarity (Levenshtein on Python side), and in non-dry-run mode creates `CONSOLIDATED_INTO` relationships. Does not delete anything.
- `stale_cleanup`: Queries `accessed_at < (now - 90 days)` OR `valid_to < now`. In non-dry-run mode, moves qualifying rows to `ArchivedMemory` table and deletes from `Memory`.
- `consolidate_similar`: Same as top_accessed logic.

Default is `dry_run=True` so by default no changes are made. The expired 410 records would be caught by `stale_cleanup` if `dry_run=False` were passed.

---

## 2. Identified Inefficiencies (Ranked by Impact)

### [CRITICAL] Missing `knowledge_type` column — `kuzu_project_context` always empty

**Impact**: Complete functional failure. All project context (gotchas, architecture, patterns, rules, conventions) returns empty. This is the single highest-priority fix.

**Root cause**: Schema was updated in code (`schema.py:33`) but no `ALTER TABLE Memory ADD COLUMN knowledge_type STRING DEFAULT 'note'` migration was run against the live database.

**Files**: `src/kuzu_memory/storage/schema.py:33`, `src/kuzu_memory/migrations/`

---

### [CRITICAL] `query_builder.py` does not write `content_hash` or `knowledge_type`

**Impact**: Deduplication is entirely broken (all `content_hash` NULL → duplicate checker using `content_hash` always misses). Memories stored via `kuzu_remember` with explicit `knowledge_type` are silently discarded.

**File**: `src/kuzu_memory/storage/query_builder.py:210-224`

The CREATE statement is missing at minimum: `content_hash`, `knowledge_type`, `project_tag`, `importance`, `confidence`, `access_count`, `valid_from`, `accessed_at`.

---

### [HIGH] 410 expired memories accumulate without cleanup

**Impact**: Every recall query scans all 1,015 rows including 410 that will never match (already expired). No automatic cleanup runs. `valid_to` is set for ALL rows including `identity` source memories that should be permanent.

**Root cause**: `MemoryType.get_default_retention` returns `timedelta(days=30)` for `EPISODIC` (the default for all memories). Since every memory is classified as `episodic`, every memory expires in 30 days. There is no scheduled cleanup — `cleanup_expired_memories` in `kuzu_adapter.py:655` must be called manually.

---

### [HIGH] Massive metadata bloat in git_sync records

**Impact**: git_sync `metadata` averages ~20 KB per row (146-item `changed_files` list + per-file stats). 489 commits × ~20 KB = ~9.8 MB of the 12 MB database is git metadata that is never queried by any recall or context tool. The content text is only 427 KB.

**File**: `src/kuzu_memory/integrations/auto_git_sync.py` (the git sync manager that populates metadata)

---

### [HIGH] 105 duplicate "Session started" memories + many other exact duplicates

**Impact**: `content_hash` dedup is non-functional, so each Claude Code session appended another identical "Session started in kuzu-memory" record. 31 "Test memory for E2E workflow" duplicates, 30 "Session state test", etc.

---

### [MEDIUM] No vector embedding stored — semantic recall is pure keyword Jaccard

**Impact**: `kuzu_recall` and `kuzu_enhance` use keyword overlap scoring only. The `sentence-transformers/all-MiniLM-L6-v2` model is referenced but never called during recall. Two memories with the same meaning but different words will not be matched.

**Files**: `src/kuzu_memory/recall/coordinator.py:290-335`, `src/kuzu_memory/caching/embeddings_cache.py` (exists but unused in recall path)

---

### [MEDIUM] `TemporalDecayEngine` instantiated but never used in recall

**Impact**: The sophisticated decay algorithms (`recall/temporal_decay.py`) are dead code in the recall pipeline. The coordinator computes a simplified inline recency boost instead.

**File**: `src/kuzu_memory/recall/coordinator.py:331`

---

### [MEDIUM] Entity extraction never reaches the database

**Impact**: EntityRecallStrategy returns 0 results for every query because Entity table has 0 rows. `store_memory_entities` is called but the CREATE in `query_builder.py:243+` appears to require entities to be pre-populated, and the `generate_memories` path never stores `content_hash` which the entity dedup logic depends on.

---

### [LOW] Full table scans on every recall — no secondary indexes

**Impact**: At 1,015 rows this is fast (<5 ms), but at 10,000+ rows this will degrade. No FTS index on `content`, no index on `created_at`, `memory_type`, or `valid_to`.

**File**: `src/kuzu_memory/storage/schema.py:116-122` (`INDICES_DDL = ""`)

---

### [LOW] `kuzu_learn` has no `knowledge_type` parameter — auto-classify gap

**Impact**: The `kuzu_learn` MCP tool (the high-frequency learning path) has no way to set `knowledge_type`. Every background-learned memory defaults to `note`. Even after the schema migration, background-learned memories will never be auto-promoted.

**File**: `src/kuzu_memory/mcp/server.py:127-155` (inputSchema for `kuzu_learn`), `src/kuzu_memory/async_memory/background_learner.py:54-90`

---

## 3. Specific Optimization Recommendations

### Fix 1 (CRITICAL): Run schema migration for `knowledge_type` and `project_tag`

**Effort**: 1 hour

Create a migration that runs:
```sql
ALTER TABLE Memory ADD COLUMN knowledge_type STRING DEFAULT 'note';
ALTER TABLE Memory ADD COLUMN project_tag STRING DEFAULT '';
```

Register it in `src/kuzu_memory/migrations/manager.py` and record in `migration_state.json`. After this, `kuzu_project_context` will query an existing column (though results will all be `'note'` until memories are re-stored with correct types).

---

### Fix 2 (CRITICAL): Patch `query_builder.py` CREATE statement to write all fields

**Effort**: 30 minutes

**File**: `src/kuzu_memory/storage/query_builder.py:210-224`

The CREATE query must include `content_hash`, `knowledge_type`, `project_tag`, `importance`, `confidence`, `access_count`, `valid_from`, `accessed_at`. Currently 8 of 17 schema fields are silently dropped on every write.

---

### Fix 3 (HIGH): Purge expired memories and fix expiry defaults

**Effort**: 2 hours

1. Run `kuzu_optimize` with `strategy="stale_cleanup", dry_run=false` to archive the 410 expired records.
2. Fix `MemoryType.get_default_retention` so `EPISODIC` entries from `identity` source get `None` (never expires) rather than 30 days. The existing `memory_type=EPISODIC` for all memories means everything expires, which is wrong for user preferences and project identity.
3. Add automatic cleanup to the MCP server startup or the `Stop` hook.

---

### Fix 4 (HIGH): Truncate git_sync metadata before storage

**Effort**: 3 hours

**File**: `src/kuzu_memory/integrations/auto_git_sync.py`

Before storing metadata, strip or truncate:
- `changed_files`: store count only (`"changed_files_count": 146`) not the full list
- `file_stats`: omit or cap at top 10 changed files
- `file_categories`: omit entirely (derivable from `changed_files` if needed)

This would reduce git_sync metadata from ~20 KB to ~300 bytes per record, cutting ~9.5 MB from the database.

---

### Fix 5 (HIGH): Deduplicate existing records and enforce hash-based dedup going forward

**Effort**: 2 hours

1. One-time: run exact-content dedup query to delete duplicates (keep oldest), particularly for `source_type IN ('claude-code-session', 'identity')`.
2. Fix `query_builder.py` (Fix 2) to write `content_hash`.
3. Before each INSERT, check for existing `content_hash` match and skip/update.

---

### Fix 6 (MEDIUM): Add `knowledge_type` parameter to `kuzu_learn`

**Effort**: 2 hours

**File**: `src/kuzu_memory/mcp/server.py:127-155`, `src/kuzu_memory/async_memory/background_learner.py:54-90`

Add optional `knowledge_type` to `kuzu_learn` inputSchema. Pass through `MemoryTask.metadata`. In `_process_learn_task`, extract from metadata and forward to `generate_memories`. This allows hooks to tag learnings as `gotcha`, `pattern`, etc. at capture time.

---

### Fix 7 (MEDIUM): Wire `TemporalDecayEngine` into recall ranking

**Effort**: 3 hours

**File**: `src/kuzu_memory/recall/coordinator.py:290-335`

Replace the inline `(30 - days_old) / 30` recency term with a call to `TemporalDecayEngine.calculate_temporal_score`. The engine is already implemented and tested; it just needs to be instantiated in `RecallCoordinator.__init__` and called in `_calculate_relevance_score`.

---

### Fix 8 (MEDIUM): Store embeddings and add vector index for semantic recall

**Effort**: 1–2 days

Add `embedding FLOAT[384]` column to Memory table (384 dims for `all-MiniLM-L6-v2`). On each `remember`/`learn`, generate embedding and store it. At recall time, generate query embedding and use Kuzu's `CREATE_VECTOR_INDEX` / cosine similarity for ANN search. This replaces keyword Jaccard with true semantic similarity, which is the documented intended behavior.

---

### Fix 9 (LOW): Add FTS index on `content` for keyword recall

**Effort**: 1 hour

```sql
CALL CREATE_FTS_INDEX('Memory', 'content_fts', ['content'])
```

Replace `LOWER(m.content) CONTAINS LOWER($keyword)` in `KeywordRecallStrategy` with FTS query. At 1,015 rows the gain is minimal; at 10,000+ rows this prevents query time from becoming quadratic.

---

## 4. Recommended Priority Order

| Priority | Fix | Estimated effort | Expected impact |
|---|---|---|---|
| 1 | Schema migration (knowledge_type + project_tag) | 1h | Unblocks project_context |
| 2 | Patch query_builder CREATE statement | 30m | Fixes dedup + knowledge_type write |
| 3 | Truncate git_sync metadata | 3h | Reduces DB ~9.5 MB (80% shrink) |
| 4 | Purge expired memories + fix expiry defaults | 2h | Removes 40% dead rows, fixes identity permanence |
| 5 | Dedup existing records | 2h | Removes ~130 noise records |
| 6 | Add knowledge_type to kuzu_learn | 2h | Enables classification going forward |
| 7 | Wire TemporalDecayEngine | 3h | Improves recall ranking quality |
| 8 | Embeddings + vector index | 1-2d | Enables true semantic recall |
| 9 | FTS index on content | 1h | Future-proofs keyword recall at scale |

Fixes 1–5 together would reduce the database to approximately 1.5–2 MB and make all MCP tools functional as documented. Fixes 6–7 improve quality. Fix 8 is a significant architectural enhancement.
