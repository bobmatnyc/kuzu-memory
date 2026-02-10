# KuzuMemory: Memory Consolidation, Read Analytics & Smart Pruning
**Research Report**

**Date**: 2025-02-10
**Researcher**: Claude (Research Agent)
**Project**: kuzu-memory
**Focus**: NLP-based memory consolidation, read analytics, and smart pruning features

---

## Executive Summary

This research analyzes the kuzu-memory codebase to design three interconnected features:

1. **NLP-based Memory Consolidation** - Merge similar old memories using semantic similarity
2. **Read Analytics** - Track memory access patterns with minimal performance impact
3. **Smart Pruning** - Age and size-based cleanup with importance weighting

**Key Findings**:
- Existing infrastructure supports these features with minimal architectural changes
- Access tracking fields (`accessed_at`, `access_count`) already exist in schema
- Strong pruning foundation exists (`core/prune.py`) with multiple strategies
- Deduplication engine (`utils/deduplication.py`) provides similarity detection
- Embeddings cache infrastructure (`caching/embeddings_cache.py`) ready for consolidation

---

## Current Architecture Summary

### 1. Memory Model (`src/kuzu_memory/core/models.py`)

**Existing Fields (Lines 91-146)**:
```python
class Memory(BaseModel):
    # Core fields
    id: str
    content: str
    content_hash: str  # SHA256 for deduplication

    # Temporal tracking
    created_at: datetime
    valid_from: datetime | None
    valid_to: datetime | None
    accessed_at: datetime | None  # ✅ Already exists!
    access_count: int = 0         # ✅ Already exists!

    # Classification
    memory_type: MemoryType
    importance: float = 0.5       # ✅ Already exists!
    confidence: float = 1.0

    # Source tracking
    source_type: str
    agent_id: str
    user_id: str | None
    session_id: str | None

    # Metadata
    metadata: dict[str, Any]
    entities: list[str | dict[str, Any]]
```

**Key Methods**:
- `update_access()` (Line 242): Updates `accessed_at` and increments `access_count`
- `is_valid()` (Line 216): Checks temporal validity
- `is_expired()` (Line 238): Checks if memory has expired

**Verdict**: ✅ **Schema already supports read analytics** - no schema migration needed!

---

### 2. Graph Database Schema (`src/kuzu_memory/storage/schema.py`)

**Memory Node Table (Lines 23-40)**:
```cypher
CREATE NODE TABLE IF NOT EXISTS Memory (
    id STRING PRIMARY KEY,
    content STRING,
    content_hash STRING,
    created_at TIMESTAMP,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    accessed_at TIMESTAMP,     -- ✅ Already exists
    access_count INT32 DEFAULT 0,  -- ✅ Already exists
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

**Indices**:
- Kuzu uses automatic hash indexes on primary keys
- CSR-based adjacency list indices for edges (automatic)
- Columnar storage with vectorized execution (automatic)

**Note**: No traditional secondary indexes (CREATE INDEX) supported in Kuzu. Performance optimization relies on:
- Query structure (WHERE clauses, MATCH patterns)
- Primary key access
- Automatic columnar storage

---

### 3. Existing Cleanup Implementation (`src/kuzu_memory/core/prune.py`)

**Current Pruning Strategies (Lines 68-326)**:

1. **SafePruningStrategy** (Line 68):
   - Only git_sync source type
   - Older than 90 days
   - <2 changed files OR <200 bytes content
   - Expected: ~7% reduction, very low risk

2. **IntelligentPruningStrategy** (Line 123):
   - Only git_sync source type
   - Older than 90 days
   - NOT important commit types (feat, fix, perf, BREAKING)
   - <3 changed files
   - Expected: ~15-20% reduction, low risk

3. **AggressivePruningStrategy** (Line 183):
   - ALL source types except protected ones
   - >180 days OR (>60 days + <2 files) OR <300 bytes
   - Expected: ~30-50% reduction, moderate risk

4. **PercentagePruningStrategy** (Line 242):
   - Prune oldest X% of memories by creation date
   - Configurable percentage (default 30%)

**Protected Sources** (Line 329):
```python
PROTECTED_SOURCES = ["claude-code-hook", "cli", "project-initialization"]
```

**Key Methods**:
- `analyze()` (Line 360): Dry-run analysis without actually pruning
- `backup()` (Line 457): Create database backup before pruning
- `prune()` (Line 481): Execute pruning with optional backup

**Verdict**: ✅ **Strong pruning foundation exists** - extend with importance and access-based logic

---

### 4. Deduplication Engine (`src/kuzu_memory/utils/deduplication.py`)

**Three-Layer Deduplication (Lines 22-29)**:

1. **Exact Hash Matching** (SHA256)
2. **Normalized Text Comparison** (0.80 threshold)
3. **Semantic Similarity** (0.50 token overlap threshold)

**Key Methods**:
- `find_duplicates()` (Line 235): Find similar memories with similarity scores
- `_calculate_text_similarity()` (Line 136): SequenceMatcher for character-level similarity
- `_calculate_token_overlap()` (Line 154): Jaccard similarity for token-level matching
- `_is_update_or_correction()` (Line 193): Detect updates vs duplicates

**Verdict**: ✅ **Excellent foundation for consolidation** - can identify similar memories

---

### 5. Embeddings Cache Infrastructure (`src/kuzu_memory/caching/embeddings_cache.py`)

**Features (Lines 18-315)**:
- Efficient storage of high-dimensional vectors
- Content-based hashing for embedding deduplication
- Similarity result caching
- Memory-efficient numpy array storage
- Batch operations: `batch_get_embeddings()`

**Key Methods**:
- `cache_embedding()` (Line 57): Store embeddings with content
- `get_embedding()` (Line 87): Retrieve cached embeddings
- `cache_similarity_result()` (Line 116): Cache similarity calculations
- `get_similarity_result()` (Line 152): Retrieve cached similarity scores

**Verdict**: ✅ **Ready for semantic consolidation** - infrastructure exists

---

### 6. Configuration (`src/kuzu_memory/core/config.py`)

**Retention Config (Lines 101-109)**:
```python
@dataclass
class RetentionConfig:
    enable_auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    custom_retention: dict[str, int | None] = field(default_factory=dict)  # memory_type -> days
    max_total_memories: int = 100_000
    cleanup_batch_size: int = 1000
```

**Prune Config (Lines 148-158)**:
```python
@dataclass
class PruneConfig:
    enabled: bool = True
    strategy: str = "safe"  # safe, intelligent, aggressive
    always_backup: bool = True
    auto_trigger_db_size_mb: int = 2500  # Auto-trigger at 2.5 GB
    auto_trigger_memory_count: int = 75000  # Auto-trigger at 75k memories
    schedule: str = "weekly"  # never, weekly, monthly
    last_prune_timestamp: str | None = None
```

**Performance Config (Lines 90-98)**:
```python
@dataclass
class PerformanceConfig:
    max_recall_time_ms: float = 200.0  # Strict performance requirement
    max_generation_time_ms: float = 1000.0
    enable_performance_monitoring: bool = True
    log_slow_operations: bool = True
```

**Verdict**: ✅ **Configurable foundation** - extend with analytics and consolidation configs

---

## Design Recommendations

### Feature 1: Read Analytics (Minimal Performance Impact)

**Objective**: Track `last_accessed` and `access_count` without impacting <200ms recall latency.

#### Recommended Approach: **Option B - Async Background Updates**

**Rationale**:
- **Performance**: Zero impact on recall latency (non-blocking)
- **Accuracy**: Near real-time (1-2 second delay acceptable for analytics)
- **Complexity**: Low - use existing async infrastructure

**Implementation Strategy**:

1. **Non-Blocking Access Tracking**:
   - Store access events in memory queue during `attach_memories()`
   - Background worker processes queue asynchronously
   - No database writes during recall operation

2. **Batch Updates**:
   - Accumulate 50-100 access events
   - Write to database in single batch query
   - Reduces database round-trips by 50-100x

3. **Queue Structure**:
   ```python
   # src/kuzu_memory/monitoring/access_tracker.py
   class AccessTracker:
       def __init__(self, max_queue_size: int = 1000):
           self._access_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
           self._batch_size: int = 50
           self._flush_interval_seconds: float = 2.0
           self._worker_task: asyncio.Task | None = None

       async def track_access(self, memory_ids: list[str]) -> None:
           """Non-blocking: Add access event to queue."""
           for memory_id in memory_ids:
               await self._access_queue.put({
                   "memory_id": memory_id,
                   "accessed_at": datetime.now()
               })

       async def _background_worker(self) -> None:
           """Process queue in background."""
           while True:
               batch = []
               try:
                   # Collect batch
                   while len(batch) < self._batch_size:
                       item = await asyncio.wait_for(
                           self._access_queue.get(),
                           timeout=self._flush_interval_seconds
                       )
                       batch.append(item)
               except asyncio.TimeoutError:
                   pass  # Flush partial batch on timeout

               if batch:
                   await self._flush_batch(batch)
   ```

4. **Batch Update Query**:
   ```cypher
   UNWIND $accesses AS access
   MATCH (m:Memory {id: access.memory_id})
   SET m.accessed_at = TIMESTAMP(access.accessed_at),
       m.access_count = COALESCE(m.access_count, 0) + 1
   ```

**Performance Impact**:
- **Recall latency**: 0ms (no blocking operations)
- **Memory overhead**: ~8KB per 1000 queued events
- **Database load**: Reduced by 50-100x via batching

**Configuration Extension**:
```python
# Add to src/kuzu_memory/core/config.py
@dataclass
class AnalyticsConfig:
    enable_access_tracking: bool = True
    access_queue_size: int = 1000
    access_batch_size: int = 50
    access_flush_interval_seconds: float = 2.0
    track_recall_events: bool = True
    track_generation_events: bool = False  # Optional: track when memories are created
```

**Files to Modify**:
- `src/kuzu_memory/core/config.py` - Add `AnalyticsConfig`
- `src/kuzu_memory/monitoring/access_tracker.py` - New file for async tracking
- `src/kuzu_memory/recall/coordinator.py` - Integrate access tracking in `attach_memories()`
- `src/kuzu_memory/core/memory.py` - Start background worker on init

---

### Feature 2: NLP-Based Memory Consolidation

**Objective**: Merge similar old memories using semantic similarity and LLM summarization.

#### Recommended Approach: **Embedding-Based Clustering + LLM Summarization**

**Rationale**:
- **Accuracy**: Embeddings capture semantic similarity better than token overlap
- **Performance**: Pre-computed embeddings enable fast clustering
- **Quality**: LLM summarization preserves key information from merged memories

**Implementation Strategy**:

1. **Similarity Detection**:
   - Use existing `DeduplicationEngine` for initial filtering
   - Generate embeddings for candidate memories
   - Cluster similar memories using cosine similarity (threshold: 0.85)

2. **Consolidation Logic**:
   ```python
   # src/kuzu_memory/nlp/consolidation.py
   class MemoryConsolidator:
       def __init__(
           self,
           similarity_threshold: float = 0.85,
           min_age_days: int = 90,
           min_cluster_size: int = 3
       ):
           self.similarity_threshold = similarity_threshold
           self.min_age_days = min_age_days
           self.min_cluster_size = min_cluster_size
           self.embeddings_cache = EmbeddingsCache()

       async def find_consolidation_candidates(
           self,
           memory_store: MemoryStore
       ) -> list[MemoryCluster]:
           """Find clusters of similar old memories."""
           # Get old memories (>90 days)
           cutoff_date = datetime.now() - timedelta(days=self.min_age_days)
           old_memories = memory_store.get_memories_created_before(cutoff_date)

           # Filter by low access count (unused memories)
           candidates = [
               m for m in old_memories
               if m.access_count < 3  # Rarely accessed
           ]

           # Generate embeddings
           embeddings = await self._get_embeddings(candidates)

           # Cluster by similarity
           clusters = self._cluster_by_similarity(candidates, embeddings)

           return [c for c in clusters if len(c.memories) >= self.min_cluster_size]

       async def consolidate_cluster(
           self,
           cluster: MemoryCluster,
           llm_client: Any  # OpenAI, Anthropic, etc.
       ) -> Memory:
           """Merge cluster into single consolidated memory."""
           # Extract key information from all memories
           contents = [m.content for m in cluster.memories]

           # LLM summarization prompt
           prompt = f"""Consolidate these related memories into a single comprehensive summary:

           Memories:
           {chr(10).join(f"{i+1}. {c}" for i, c in enumerate(contents))}

           Create a consolidated summary that:
           - Preserves all unique information
           - Removes redundancy
           - Maintains factual accuracy
           - Is concise and clear
           """

           summary = await llm_client.generate(prompt)

           # Create consolidated memory
           consolidated = Memory(
               content=summary,
               memory_type=cluster.memories[0].memory_type,
               importance=max(m.importance for m in cluster.memories),
               confidence=min(m.confidence for m in cluster.memories),
               source_type="consolidation",
               metadata={
                   "consolidated_from": [m.id for m in cluster.memories],
                   "consolidation_date": datetime.now().isoformat(),
                   "original_count": len(cluster.memories)
               }
           )

           return consolidated

       async def archive_originals(
           self,
           original_memories: list[Memory],
           consolidated_memory: Memory,
           memory_store: MemoryStore
       ) -> None:
           """Archive original memories and link to consolidated version."""
           # Create archive relationships
           for original in original_memories:
               memory_store.create_relationship(
                   from_memory=original,
                   to_memory=consolidated_memory,
                   relationship_type="CONSOLIDATED_INTO",
                   metadata={"archived_at": datetime.now().isoformat()}
               )

               # Mark as archived (don't delete - keep for audit trail)
               original.metadata["archived"] = True
               original.metadata["archived_at"] = datetime.now().isoformat()
               memory_store.update_memory(original)
   ```

3. **Clustering Algorithm**:
   ```python
   def _cluster_by_similarity(
       self,
       memories: list[Memory],
       embeddings: dict[str, np.ndarray]
   ) -> list[MemoryCluster]:
       """Cluster memories by cosine similarity."""
       from sklearn.cluster import DBSCAN
       import numpy as np

       # Create embedding matrix
       memory_ids = list(embeddings.keys())
       embedding_matrix = np.array([embeddings[mid] for mid in memory_ids])

       # DBSCAN clustering (density-based)
       clustering = DBSCAN(
           eps=1 - self.similarity_threshold,  # Convert cosine sim to distance
           min_samples=self.min_cluster_size,
           metric='cosine'
       )

       labels = clustering.fit_predict(embedding_matrix)

       # Group memories by cluster
       clusters = {}
       for memory_id, label in zip(memory_ids, labels):
           if label == -1:  # Noise point (no cluster)
               continue
           if label not in clusters:
               clusters[label] = []
           clusters[label].append(memory_id)

       # Create MemoryCluster objects
       return [
           MemoryCluster(
               memories=[m for m in memories if m.id in cluster_ids],
               similarity_score=self._calculate_cluster_cohesion(cluster_ids, embeddings)
           )
           for cluster_ids in clusters.values()
       ]
   ```

**Configuration Extension**:
```python
@dataclass
class ConsolidationConfig:
    enabled: bool = False  # Opt-in feature
    similarity_threshold: float = 0.85  # Cosine similarity threshold
    min_age_days: int = 90  # Only consolidate old memories
    min_cluster_size: int = 3  # Minimum memories per cluster
    max_cluster_size: int = 10  # Maximum memories to merge at once
    require_low_access: bool = True  # Only consolidate rarely accessed memories
    max_access_count: int = 3  # Max access count for consolidation candidates
    preserve_originals: bool = True  # Archive originals instead of deleting
    schedule: str = "monthly"  # Consolidation frequency
```

**Files to Create/Modify**:
- `src/kuzu_memory/nlp/consolidation.py` - New consolidation engine
- `src/kuzu_memory/core/config.py` - Add `ConsolidationConfig`
- `src/kuzu_memory/storage/query_builder.py` - Add relationship creation for archiving
- `src/kuzu_memory/cli/consolidate_commands.py` - CLI for consolidation operations

---

### Feature 3: Smart Pruning (Access + Importance Based)

**Objective**: Extend existing pruning with access patterns and importance weighting.

#### Recommended Approach: **Multi-Factor Scoring System**

**Rationale**:
- **Precision**: Combines age, size, access, and importance for intelligent decisions
- **Safety**: Preserves important and frequently accessed memories
- **Flexibility**: Configurable thresholds per use case

**Implementation Strategy**:

1. **Pruning Score Formula**:
   ```python
   prune_score = (
       age_score * 0.35 +
       size_score * 0.20 +
       access_score * 0.30 +
       importance_score * 0.15
   )

   # Prune if score > threshold (e.g., 0.70)
   # Higher score = more likely to prune
   ```

2. **Score Calculations**:
   ```python
   # src/kuzu_memory/core/prune.py - New strategy class
   class SmartPruningStrategy(PruningStrategy):
       def __init__(
           self,
           prune_threshold: float = 0.70,
           max_age_days: int = 180,
           min_access_count: int = 5,
           min_importance: float = 0.3
       ):
           super().__init__(
               "smart",
               "Multi-factor pruning based on age, access, size, and importance"
           )
           self.prune_threshold = prune_threshold
           self.max_age_days = max_age_days
           self.min_access_count = min_access_count
           self.min_importance = min_importance

       def should_prune(self, memory: dict[str, Any]) -> tuple[bool, str]:
           """Calculate multi-factor prune score."""

           # Age score (0-1, higher = older)
           age_days = (datetime.now() - memory["created_at"]).days
           age_score = min(age_days / self.max_age_days, 1.0)

           # Size score (0-1, higher = smaller)
           content_size = len(memory.get("content", ""))
           size_score = 1.0 - min(content_size / 1000, 1.0)  # Normalize to 1KB

           # Access score (0-1, higher = less accessed)
           access_count = memory.get("access_count", 0)
           access_score = 1.0 - min(access_count / self.min_access_count, 1.0)

           # Access recency score (0-1, higher = older last access)
           accessed_at = memory.get("accessed_at")
           if accessed_at:
               days_since_access = (datetime.now() - accessed_at).days
               recency_score = min(days_since_access / 90, 1.0)
           else:
               recency_score = 1.0  # Never accessed

           # Combine access count and recency
           combined_access_score = (access_score + recency_score) / 2.0

           # Importance score (0-1, higher = less important)
           importance = memory.get("importance", 0.5)
           importance_score = 1.0 - importance

           # Calculate weighted score
           prune_score = (
               age_score * 0.35 +
               size_score * 0.20 +
               combined_access_score * 0.30 +
               importance_score * 0.15
           )

           # Decision
           should_prune = prune_score >= self.prune_threshold

           reason = (
               f"score={prune_score:.2f} "
               f"(age={age_score:.2f}, size={size_score:.2f}, "
               f"access={combined_access_score:.2f}, importance={importance_score:.2f})"
           )

           return should_prune, reason
   ```

3. **Protected Memory Rules**:
   - **Never prune**:
     - Importance ≥ 0.8 (high importance)
     - Access count ≥ 10 (frequently accessed)
     - Created within last 30 days (recent)
     - Source type in PROTECTED_SOURCES

4. **Archive vs Delete**:
   ```python
   def prune_with_archive(
       self,
       strategy_name: str = "smart",
       archive_instead_of_delete: bool = True
   ) -> PruneResult:
       """Prune memories with optional archiving."""

       # Find memories to prune
       to_prune = self._find_prune_candidates(strategy_name)

       if archive_instead_of_delete:
           # Move to archive table
           for memory in to_prune:
               self._archive_memory(memory)
               self._delete_memory(memory.id)
       else:
           # Hard delete
           for memory in to_prune:
               self._delete_memory(memory.id)
   ```

**Configuration Extension**:
```python
@dataclass
class SmartPruneConfig:
    enabled: bool = True
    prune_threshold: float = 0.70  # Prune score threshold (0-1)

    # Age weighting
    max_age_days: int = 180  # Normalize age to this value
    age_weight: float = 0.35

    # Size weighting
    max_size_bytes: int = 1000  # Normalize size to this value
    size_weight: float = 0.20

    # Access weighting
    min_access_count: int = 5  # Normalize access count
    max_access_recency_days: int = 90  # Normalize recency
    access_weight: float = 0.30

    # Importance weighting
    importance_weight: float = 0.15

    # Protection rules
    protect_high_importance: float = 0.8  # Never prune if importance >= this
    protect_high_access: int = 10  # Never prune if access_count >= this
    protect_recent_days: int = 30  # Never prune if created within this

    # Archive settings
    archive_instead_of_delete: bool = True
    archive_retention_days: int = 365  # Keep archives for 1 year
```

**Files to Modify**:
- `src/kuzu_memory/core/prune.py` - Add `SmartPruningStrategy` class
- `src/kuzu_memory/core/config.py` - Add `SmartPruneConfig`
- `src/kuzu_memory/storage/schema.py` - Add optional `ArchivedMemory` table
- `src/kuzu_memory/cli/prune_commands.py` - Extend CLI for smart pruning

---

## Performance Considerations

### Read Analytics Performance Impact

| Approach | Recall Latency | Write Latency | Memory Overhead | Accuracy |
|----------|---------------|---------------|-----------------|----------|
| **Sync Updates** | +10-15ms | N/A | 0 | 100% |
| **Async Updates** (✅ Recommended) | 0ms | 0ms | ~8KB/1000 events | 99.9% |
| **Batch Periodic** | 0ms | 0ms | ~16KB/2000 events | 95% (5min delay) |

**Verdict**: Async updates meet <200ms requirement with zero latency impact.

### Consolidation Performance

| Operation | Time Complexity | Performance |
|-----------|----------------|-------------|
| Embedding Generation | O(n × d) | ~50ms per memory |
| Similarity Computation | O(n²) or O(n log n) | DBSCAN: O(n log n) |
| LLM Summarization | O(cluster_size) | ~1-2s per cluster |
| Database Update | O(n) | ~10ms per memory |

**Estimated Total Time**: For 1000 old memories with 10% consolidation:
- Embedding generation: 1000 × 50ms = 50s
- Clustering: ~5s (DBSCAN with 1000 points)
- Summarization: 10 clusters × 2s = 20s
- Database updates: 100 memories × 10ms = 1s
- **Total: ~76 seconds** (one-time monthly operation)

**Verdict**: Acceptable for background/scheduled operation.

### Pruning Performance

| Strategy | Analysis Time | Prune Time | Memory Impact |
|----------|--------------|------------|---------------|
| Safe | ~1s | ~2s | 7% reduction |
| Intelligent | ~1s | ~3s | 15-20% reduction |
| Aggressive | ~1s | ~5s | 30-50% reduction |
| **Smart (New)** | ~1.5s | ~4s | 20-30% reduction |

**Verdict**: Smart pruning adds ~0.5s analysis overhead (scoring calculation) - acceptable.

---

## Implementation Priority

### Phase 1: Read Analytics (High Priority, Low Complexity)
**Timeline**: 1-2 weeks

1. ✅ **Schema validation** (no changes needed - fields exist)
2. Create `src/kuzu_memory/monitoring/access_tracker.py`
3. Integrate async tracking in `recall/coordinator.py`
4. Add configuration to `core/config.py`
5. Add CLI commands for analytics queries
6. Write unit tests

**Deliverables**:
- Non-blocking access tracking
- Batch update mechanism
- Analytics query API (`get_least_accessed`, `get_most_accessed`)

---

### Phase 2: Smart Pruning (Medium Priority, Medium Complexity)
**Timeline**: 2-3 weeks

1. Extend `SmartPruningStrategy` in `core/prune.py`
2. Implement multi-factor scoring system
3. Add archive mechanism (optional `ArchivedMemory` table)
4. Extend configuration with `SmartPruneConfig`
5. Add CLI commands for smart pruning
6. Write integration tests

**Deliverables**:
- Multi-factor pruning strategy
- Archive vs delete options
- Dry-run analysis with detailed scoring
- Automated thresholds based on database size

---

### Phase 3: Memory Consolidation (Low Priority, High Complexity)
**Timeline**: 3-4 weeks

1. Create `src/kuzu_memory/nlp/consolidation.py`
2. Implement embedding-based clustering
3. Integrate LLM summarization (pluggable: OpenAI, Anthropic, local)
4. Add archive relationship tracking
5. Extend configuration with `ConsolidationConfig`
6. Add CLI commands for consolidation
7. Write comprehensive tests

**Deliverables**:
- Automatic similarity detection
- LLM-based summarization
- Audit trail (link originals to consolidated)
- Configurable thresholds and schedules

---

## Files to Modify/Create

### New Files (6 total)
1. `src/kuzu_memory/monitoring/access_tracker.py` - Async access tracking
2. `src/kuzu_memory/nlp/consolidation.py` - Consolidation engine
3. `src/kuzu_memory/cli/analytics_commands.py` - CLI for analytics queries
4. `src/kuzu_memory/cli/consolidate_commands.py` - CLI for consolidation
5. `tests/unit/test_access_tracker.py` - Unit tests for access tracking
6. `tests/integration/test_consolidation.py` - Integration tests for consolidation

### Modified Files (5 total)
1. `src/kuzu_memory/core/config.py` - Add 3 new config dataclasses
2. `src/kuzu_memory/core/prune.py` - Add `SmartPruningStrategy`
3. `src/kuzu_memory/recall/coordinator.py` - Integrate access tracking
4. `src/kuzu_memory/storage/query_builder.py` - Add archive queries
5. `src/kuzu_memory/core/memory.py` - Start access tracker on init

---

## Risk Assessment

### Read Analytics Risks
- **Risk**: Queue overflow if database becomes slow
  - **Mitigation**: Set max queue size (1000 events) with backpressure

- **Risk**: Lost access data if process crashes
  - **Mitigation**: Periodic flush (2s interval) minimizes loss to ~100 events

### Consolidation Risks
- **Risk**: LLM summarization loses important details
  - **Mitigation**: Preserve originals with archive relationship

- **Risk**: Over-aggressive consolidation merges unrelated memories
  - **Mitigation**: High similarity threshold (0.85) and manual review mode

### Pruning Risks
- **Risk**: False positives (prune important memories)
  - **Mitigation**: Protected source types + importance/access thresholds

- **Risk**: Irreversible data loss
  - **Mitigation**: required backups (default: always_backup=True)

---

## Recommended Thresholds

### Access-Based Pruning
- **Rarely accessed**: `access_count < 3` AND `days_since_access > 90`
- **Never accessed**: `accessed_at == None` AND `age > 180 days`

### Importance-Based Protection
- **High importance**: `importance >= 0.8` (never prune)
- **Medium importance**: `importance >= 0.5` (require low access + old age)
- **Low importance**: `importance < 0.3` (aggressive pruning OK)

### Consolidation Candidates
- **Age**: `> 90 days old`
- **Access**: `access_count < 3`
- **Similarity**: `cosine_similarity >= 0.85`
- **Cluster size**: `3 ≤ cluster_size ≤ 10`

---

## Testing Strategy

### Unit Tests
1. **Access Tracker**:
   - Queue overflow handling
   - Batch flush logic
   - Error recovery

2. **Smart Pruning**:
   - Score calculation accuracy
   - Protected memory rules
   - Edge cases (missing fields)

3. **Consolidation**:
   - Clustering algorithm correctness
   - Embedding generation
   - Archive relationship creation

### Integration Tests
1. **End-to-End Analytics**:
   - Track access → flush to DB → query analytics
   - Performance: <200ms recall latency maintained

2. **End-to-End Pruning**:
   - Analyze → backup → prune → verify
   - Verify protected memories preserved

3. **End-to-End Consolidation**:
   - Find candidates → cluster → summarize → archive
   - Verify originals preserved with relationships

---

## Migration Path (If Schema Changes Needed)

**Current Verdict**: ✅ **No migration needed** - all fields exist in current schema.

**Future Schema Extensions** (optional):
```sql
-- Optional: Add ArchivedMemory table for soft deletes
CREATE NODE TABLE IF NOT EXISTS ArchivedMemory (
    id STRING PRIMARY KEY,
    original_memory_id STRING,
    content STRING,
    archived_at TIMESTAMP,
    archived_reason STRING,
    metadata STRING
);

-- Optional: Add consolidation relationship
CREATE REL TABLE IF NOT EXISTS CONSOLIDATED_INTO (
    FROM Memory TO Memory,
    consolidated_at TIMESTAMP,
    consolidation_method STRING,
    original_count INT32
);
```

---

## Open Questions

1. **LLM Integration**:
   - Which LLM provider? (OpenAI, Anthropic, local Ollama?)
   - Should consolidation be pluggable?
   - Fallback if LLM unavailable?

2. **Archive Retention**:
   - How long to keep archived memories? (1 year default?)
   - Separate archive pruning schedule?
   - Compressed archive storage?

3. **Performance Tuning**:
   - Should embedding generation be cached indefinitely?
   - Incremental clustering (update clusters on new memories)?
   - Parallel batch processing for large databases?

4. **User Control**:
   - Manual review before consolidation?
   - Undo consolidation feature?
   - Exclude specific memory types from consolidation?

---

## Conclusion

**Summary**:
- ✅ **Schema Ready**: Access tracking fields already exist
- ✅ **Strong Foundation**: Pruning and deduplication infrastructure in place
- ✅ **Minimal Risk**: Async access tracking has zero performance impact
- ✅ **Clear Path**: Phased implementation (analytics → pruning → consolidation)

**Recommended Next Steps**:
1. Implement async access tracking (Phase 1)
2. Extend pruning with smart strategy (Phase 2)
3. Add consolidation as opt-in feature (Phase 3)

**Estimated Total Timeline**: 6-9 weeks for all three features

---

**Research Complete**: 2025-02-10
**Next Action**: Review design with team and prioritize phases
