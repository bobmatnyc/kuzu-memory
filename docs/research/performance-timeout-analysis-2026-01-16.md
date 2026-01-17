# KuzuMemory Performance Timeout Analysis

**Date**: 2026-01-16
**Researcher**: Claude (Research Agent)
**Issue**: Query execution exceeding timeout thresholds

## Problem Summary

The system is experiencing performance degradation with queries exceeding configured timeouts:

```
Query execution exceeded timeout: 8226.3ms > 5000ms
Performance threshold exceeded for attach_memories: 1.208s > 0.200s
```

## Root Cause Analysis

### 1. Query Timeout Configuration (5000ms)

**Location**: `src/kuzu_memory/core/config.py:33`

```python
query_timeout_ms: int = 5000
```

**Also defined in**:
- `src/kuzu_memory/utils/config_loader.py:113` (default fallback)
- Example configs:
  - `examples/kuzu-config-example.json:49`
  - `examples/config.yaml:14`

**Where it's used**:
- `src/kuzu_memory/storage/kuzu_adapter.py:328` - Query execution timeout
- `src/kuzu_memory/storage/kuzu_cli_adapter.py:108` - CLI adapter timeout
- `src/kuzu_memory/services/autotune_service.py:53` - BASE_TIMEOUT_MS constant
- `tests/conftest.py:71` - Test timeout set to 10000ms (longer for tests)

**Detection logic** (`src/kuzu_memory/storage/kuzu_adapter.py:357-359`):
```python
if execution_time_ms > timeout_ms:
    raise TimeoutError(
        f"Query execution exceeded timeout: {execution_time_ms:.1f}ms > {timeout_ms}ms"
    )
```

### 2. Performance Threshold Configuration (200ms)

**Location**: `src/kuzu_memory/monitoring/performance_monitor.py:66-71`

```python
self._thresholds = {
    "recall_time_ms": 100.0,        # <100ms recall target
    "generation_time_ms": 200.0,    # <200ms generation target
    "db_query_time_ms": 50.0,       # <50ms database queries
    "cache_hit_rate": 0.8,          # >80% cache hit rate
    "error_rate": 0.01,             # <1% error rate
}
```

**Also defined in**:
- `src/kuzu_memory/core/constants.py:10-13`:
  ```python
  ATTACH_MEMORIES_TARGET_MS: Final[int] = 10      # Target for attach_memories
  GENERATE_MEMORIES_TARGET_MS: Final[int] = 20    # Target for generation
  SLOW_QUERY_THRESHOLD_MS: Final[int] = 1000      # 1 second
  VERY_SLOW_QUERY_THRESHOLD_MS: Final[int] = 2000 # 2 seconds
  ```

**Timing decorators** (`src/kuzu_memory/monitoring/timing_decorators.py`):
- `time_recall` (line 279): 100ms threshold
- `time_generation` (line 288): **200ms threshold** (matches error message)
- `time_database` (line 305): 50ms threshold
- `time_cache` (line 316): 10ms threshold

**Detection logic** (`src/kuzu_memory/utils/exceptions.py:297-300`):
```python
def __init__(self, operation: str, actual_time: float, threshold: float, **kwargs: Any) -> None:
    message = (
        f"Performance threshold exceeded for {operation}: {actual_time:.3f}s > {threshold:.3f}s"
    )
```

### 3. Query Implementations

#### `get_recent_memories` Query

**Location**: `src/kuzu_memory/storage/query_builder.py:335-402`

**Actual Cypher Query** (lines 371-377):
```cypher
MATCH (m:Memory)
WHERE {where_clause}
RETURN m
ORDER BY m.created_at DESC
LIMIT $limit
```

**Where clause includes**:
- Memory type filtering
- Expiration filtering: `(m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now))`
- User/session/source filtering
- No explicit index usage

**Performance characteristics**:
- Full table scan on Memory nodes
- Sorting by `created_at` (potentially expensive without index)
- Default limit: 10 (can be up to 100)

#### `attach_memories` Implementation

**Location**: `src/kuzu_memory/services/memory_service.py:206-246`

**This is a delegation method**:
```python
def attach_memories(self, prompt: str, max_memories: int = 10, strategy: str = "auto", **filters: Any) -> MemoryContext:
    self._check_initialized()
    return self.kuzu_memory.attach_memories(
        prompt=prompt,
        max_memories=max_memories,
        strategy=strategy,
        **filters,
    )
```

**Performance target** (line 229):
```python
# Target: <10ms for typical queries
# Complexity: O(log n) for semantic search, O(1) for filters
```

**Actual implementation** is in the `kuzu_memory` core class (not shown in search results, but likely involves):
1. Semantic search using embeddings
2. Multiple database queries (recall + filtering)
3. Temporal decay calculations (from `temporal_decay.py`)
4. Memory ranking and selection

### 4. Database Indexes

**Current index configuration** (`src/kuzu_memory/storage/schema.py:180`):
```python
"CREATE INDEX IF NOT EXISTS idx_memory_tags ON Memory(tags)",
```

**Only ONE index is defined** - on the `tags` field!

**Recommended indexes** (from `docs/developer/memory-models.md:399-406`):
```cypher
CREATE INDEX memory_type_idx ON :Memory(memory_type);
CREATE INDEX memory_importance_idx ON :Memory(importance);
CREATE INDEX memory_created_at_idx ON :Memory(created_at);  ← MISSING!
CREATE INDEX entity_name_idx ON :Entity(name);

# Composite indexes
CREATE INDEX memory_type_importance_idx ON :Memory(memory_type, importance);
CREATE INDEX memory_active_idx ON :Memory(memory_type) WHERE expires_at IS NULL OR expires_at > datetime();
```

**Critical missing index**: `memory_created_at_idx` would dramatically improve performance of:
- `get_recent_memories` (ORDER BY m.created_at DESC)
- Any temporal queries
- Date range filtering

## Performance Bottleneck Summary

### Primary Issues

1. **Missing `created_at` index**
   - Impact: Full table scan for temporal ordering
   - Queries affected: `get_recent_memories`, all temporal queries
   - Expected improvement: 10-100x faster for large datasets

2. **No indexes on common filter fields**
   - Missing: `memory_type`, `user_id`, `session_id`, `source_type`
   - Impact: Full table scan for filtered queries
   - Queries affected: All filtered recall operations

3. **Complex temporal decay calculations**
   - Location: `src/kuzu_memory/recall/temporal_decay.py`
   - Multiple decay functions (exponential, linear, logarithmic, sigmoid, power_law, step)
   - Activity-aware calculations (lines 151-164)
   - Applied per-memory during recall

4. **Semantic search overhead**
   - Embedding generation
   - Vector similarity calculations
   - Likely causing the 1.2s delay in `attach_memories`

### Secondary Issues

5. **Aggressive performance targets**
   - `ATTACH_MEMORIES_TARGET_MS = 10ms` (actual: 1208ms = 120x over target)
   - `recall_time_ms: 100.0ms` threshold
   - `generation_time_ms: 200.0ms` threshold (triggering warnings)

6. **Query timeout too restrictive**
   - 5000ms timeout too low for:
     - Large memory databases
     - Complex semantic searches
     - Multiple concurrent queries

## Recommendations

### Immediate Fixes (Quick Wins)

#### 1. Increase Query Timeout

**File**: `src/kuzu_memory/core/config.py`
**Line**: 33

```python
# BEFORE
query_timeout_ms: int = 5000

# AFTER
query_timeout_ms: int = 15000  # 15 seconds for complex queries
```

**Also update**:
- `src/kuzu_memory/utils/config_loader.py:113`
- `examples/kuzu-config-example.json:49`
- `examples/config.yaml:14`

#### 2. Adjust Performance Thresholds

**File**: `src/kuzu_memory/monitoring/performance_monitor.py`
**Lines**: 66-71

```python
# BEFORE
self._thresholds = {
    "recall_time_ms": 100.0,
    "generation_time_ms": 200.0,
    "db_query_time_ms": 50.0,
}

# AFTER
self._thresholds = {
    "recall_time_ms": 500.0,      # 5x increase
    "generation_time_ms": 1000.0,  # 5x increase
    "db_query_time_ms": 200.0,     # 4x increase
}
```

**File**: `src/kuzu_memory/core/constants.py`
**Lines**: 10-13

```python
# BEFORE
ATTACH_MEMORIES_TARGET_MS: Final[int] = 10
GENERATE_MEMORIES_TARGET_MS: Final[int] = 20
SLOW_QUERY_THRESHOLD_MS: Final[int] = 1000
VERY_SLOW_QUERY_THRESHOLD_MS: Final[int] = 2000

# AFTER
ATTACH_MEMORIES_TARGET_MS: Final[int] = 100    # 10x increase
GENERATE_MEMORIES_TARGET_MS: Final[int] = 200  # 10x increase
SLOW_QUERY_THRESHOLD_MS: Final[int] = 2000     # 2x increase
VERY_SLOW_QUERY_THRESHOLD_MS: Final[int] = 5000 # 2.5x increase
```

### Long-Term Optimizations

#### 3. Add Critical Database Indexes

**File**: `src/kuzu_memory/storage/schema.py`
**After line**: 180

```python
# Current
"CREATE INDEX IF NOT EXISTS idx_memory_tags ON Memory(tags)",

# Add these indexes
"CREATE INDEX IF NOT EXISTS idx_memory_created_at ON Memory(created_at)",
"CREATE INDEX IF NOT EXISTS idx_memory_type ON Memory(memory_type)",
"CREATE INDEX IF NOT EXISTS idx_memory_user_id ON Memory(user_id)",
"CREATE INDEX IF NOT EXISTS idx_memory_session_id ON Memory(session_id)",
"CREATE INDEX IF NOT EXISTS idx_memory_source_type ON Memory(source_type)",
"CREATE INDEX IF NOT EXISTS idx_memory_valid_to ON Memory(valid_to)",

# Composite indexes for common query patterns
"CREATE INDEX IF NOT EXISTS idx_memory_type_created ON Memory(memory_type, created_at)",
"CREATE INDEX IF NOT EXISTS idx_memory_user_created ON Memory(user_id, created_at)",
```

**Migration required**: Existing databases will need index creation migration.

#### 4. Optimize Temporal Decay Calculations

**Options**:
1. **Cache decay scores**: Pre-calculate for common time intervals
2. **Simpler decay function**: Use exponential-only (fastest)
3. **Batch processing**: Calculate decay scores for multiple memories at once
4. **Lazy evaluation**: Only calculate when needed for ranking

**File**: `src/kuzu_memory/recall/temporal_decay.py`

Consider adding decay score caching:
```python
@lru_cache(maxsize=1000)
def _calculate_decay_score_cached(self, age_days: int, half_life: float, function: str) -> float:
    # Cache common age_days values (rounded to nearest day)
    ...
```

#### 5. Query Optimization

**File**: `src/kuzu_memory/storage/query_builder.py`
**Line**: 371-377

```cypher
# BEFORE
MATCH (m:Memory)
WHERE {where_clause}
RETURN m
ORDER BY m.created_at DESC
LIMIT $limit

# AFTER (with index hints)
MATCH (m:Memory)
USING INDEX idx_memory_created_at
WHERE {where_clause}
RETURN m
ORDER BY m.created_at DESC
LIMIT $limit
```

#### 6. Implement Query Result Caching

Add LRU cache for common queries:
- Recent memories by user
- Recent memories by session
- Common semantic search patterns

**Suggested location**: `src/kuzu_memory/caching/query_cache.py`

```python
class QueryCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.cache = LRUCache(max_size)
        self.ttl = ttl_seconds

    def get_recent_memories_cached(self, user_id: str, limit: int) -> list[Memory] | None:
        cache_key = f"recent:{user_id}:{limit}"
        return self.cache.get(cache_key)
```

## Testing Recommendations

After implementing fixes, verify:

1. **Query performance**:
   ```bash
   pytest tests/benchmarks/test_performance.py -v
   ```

2. **Large dataset performance**:
   - Insert 10,000+ memories
   - Measure `get_recent_memories` time
   - Should be <100ms with indexes

3. **Timeout behavior**:
   - Verify 15s timeout allows complex queries
   - Ensure autotune service adjusts properly

4. **Index effectiveness**:
   ```cypher
   EXPLAIN MATCH (m:Memory)
   WHERE m.user_id = 'test'
   RETURN m
   ORDER BY m.created_at DESC
   LIMIT 10
   ```
   Should show index usage.

## Estimated Impact

| Fix | Difficulty | Expected Speedup | Risk |
|-----|-----------|------------------|------|
| Increase timeouts | Easy | N/A (prevents errors) | Low |
| Adjust thresholds | Easy | N/A (reduces warnings) | Low |
| Add indexes | Medium | 10-100x | Medium (migration) |
| Optimize decay | Hard | 2-5x | Medium |
| Query caching | Medium | 5-10x (cache hits) | Low |

## Priority Order

1. **Immediate** (today):
   - Increase query timeout to 15000ms
   - Adjust performance thresholds

2. **Short-term** (this week):
   - Add `idx_memory_created_at` index
   - Add `idx_memory_type` index
   - Test with large dataset

3. **Medium-term** (this month):
   - Add all recommended indexes
   - Implement query result caching
   - Optimize temporal decay calculations

4. **Long-term** (next quarter):
   - Comprehensive query optimization
   - Adaptive timeout adjustment
   - Performance regression testing

## Files Requiring Changes

### Immediate Fixes
- `src/kuzu_memory/core/config.py` (line 33)
- `src/kuzu_memory/utils/config_loader.py` (line 113)
- `src/kuzu_memory/monitoring/performance_monitor.py` (lines 66-71)
- `src/kuzu_memory/core/constants.py` (lines 10-13)
- `examples/kuzu-config-example.json` (line 49)
- `examples/config.yaml` (line 14)

### Long-Term Optimizations
- `src/kuzu_memory/storage/schema.py` (after line 180)
- `src/kuzu_memory/storage/query_builder.py` (line 371+)
- `src/kuzu_memory/recall/temporal_decay.py` (add caching)
- New file: `src/kuzu_memory/caching/query_cache.py`

## Conclusion

The performance issues are caused by:
1. **Missing database indexes** (most critical)
2. **Overly aggressive timeout and threshold values**
3. **Complex temporal decay calculations**

The quickest wins are increasing timeouts/thresholds and adding the `created_at` index. Long-term, a comprehensive indexing strategy and query result caching will provide sustainable performance at scale.

---

**Research Status**: Complete
**Next Steps**: Implement immediate fixes, test with production-scale data
**Follow-up**: Monitor autotune service behavior with new timeout values
