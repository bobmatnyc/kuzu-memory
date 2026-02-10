# kuzu_optimize MCP Tool

## Overview

The `kuzu_optimize` tool enables LLMs (like Claude) to proactively optimize memory storage during conversations. This is the final component of the Smart Memory Cleanup system (Phase 4 of Issue #19).

## Purpose

Allows AI assistants to:
- Detect memory clutter during long sessions
- Consolidate redundant or similar memories
- Archive stale memories not accessed in 90+ days
- Improve recall performance by optimizing context

## Tool Specification

### Name
`kuzu_optimize`

### Description
LLM-initiated memory optimization: Compact and optimize frequently-accessed memories to improve recall performance and reduce context clutter. Use proactively when you notice redundant memories, stale content, or performance degradation during conversations.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `strategy` | string (enum) | "top_accessed" | Optimization strategy to use |
| `limit` | integer | 20 | Maximum number of memories to process |
| `dry_run` | boolean | true | If true, only analyze without making changes |

### Strategies

#### 1. `top_accessed`
**Purpose**: Refresh/consolidate most-used memories for faster recall

**How it works**:
- Queries memories with highest access counts (>5 accesses)
- Uses NLP similarity detection to find near-duplicates
- Suggests consolidation opportunities
- Focuses on frequently-used context to maximize impact

**Best for**:
- Long conversations with repeated queries
- When recall returns similar results
- Optimizing "hot" memories that slow down retrieval

**Example**:
```json
{
  "strategy": "top_accessed",
  "limit": 20,
  "dry_run": true
}
```

#### 2. `stale_cleanup`
**Purpose**: Archive memories not accessed in 90+ days

**How it works**:
- Uses SmartPruningStrategy to identify stale candidates
- Filters for memories with no access in 90+ days
- Archives to ArchivedMemory table (30-day recovery window)
- Removes from active memory storage

**Best for**:
- End-of-project cleanup
- Reducing database size
- When context feels bloated with old information

**Example**:
```json
{
  "strategy": "stale_cleanup",
  "limit": 50,
  "dry_run": false
}
```

#### 3. `consolidate_similar`
**Purpose**: Merge similar memories into summaries

**How it works**:
- Uses ConsolidationEngine to cluster related memories
- Creates consolidated summaries preserving key information
- Only consolidates low-access memories (≤5 accesses)
- Only consolidates older memories (>30 days)

**Best for**:
- Large codebases with redundant learnings
- When memory count grows unwieldy
- Reducing noise in recall results

**Example**:
```json
{
  "strategy": "consolidate_similar",
  "limit": 30,
  "dry_run": true
}
```

## Response Format

```json
{
  "status": "completed",
  "strategy": "top_accessed",
  "dry_run": true,
  "results": {
    "memories_analyzed": 150,
    "optimization_candidates": 12,
    "actions_taken": [
      {
        "action": "consolidation_candidate",
        "memory_ids": ["abc123", "def456"],
        "similarity": "0.85",
        "match_type": "near_duplicate"
      }
    ],
    "space_saved_bytes": 4096,
    "estimated_recall_improvement": "15%"
  },
  "suggestions": [
    "Found 12 consolidation opportunities among top-accessed memories",
    "Run with dry_run=false to consolidate similar memories"
  ]
}
```

## Usage Patterns

### 1. Proactive Maintenance During Long Sessions

**Scenario**: LLM detects context is getting cluttered

```
User: "Can you remind me what we discussed about the authentication system?"
LLM: [notices recall returning many similar results]
LLM: [calls kuzu_optimize(strategy="top_accessed", dry_run=true)]
LLM: "I found 8 similar memories about authentication. Would you like me to consolidate them for faster recall?"
```

### 2. User-Requested Cleanup

**Scenario**: User asks for memory cleanup

```
User: "My memory seems cluttered with old project notes"
LLM: [calls kuzu_optimize(strategy="stale_cleanup", dry_run=true)]
LLM: "I found 23 memories not accessed in 90+ days (total 15KB). Would you like me to archive them?"
User: "Yes"
LLM: [calls kuzu_optimize(strategy="stale_cleanup", dry_run=false)]
LLM: "Done! Archived 23 old memories. They'll be available for 30 days if you need to restore them."
```

### 3. End-of-Session Optimization

**Scenario**: LLM optimizes before ending long session

```
User: "Thanks, I'm done for today"
LLM: [calls kuzu_optimize(strategy="consolidate_similar", dry_run=true)]
LLM: "Before we finish, I noticed 5 memory clusters that could be consolidated. This would reduce clutter by ~20%. Should I optimize them?"
User: "Sure"
LLM: [calls kuzu_optimize(strategy="consolidate_similar", dry_run=false)]
LLM: "Optimized! Your memory is now more compact and recalls should be faster."
```

### 4. Performance Degradation Detection

**Scenario**: Recall operations are slow

```
[LLM notices recall taking >100ms consistently]
LLM: "I notice memory retrieval is slower than usual. Let me check for optimization opportunities..."
LLM: [calls kuzu_optimize(strategy="top_accessed", limit=50, dry_run=false)]
LLM: "I've consolidated 12 frequently-used memories. Recall should be about 15% faster now."
```

## Integration with Smart Cleanup Components

The `kuzu_optimize` tool integrates with the complete Smart Memory Cleanup system:

### Phase 1: AccessTracker
- Provides access count data for `top_accessed` strategy
- Tracks which memories are "hot" vs "cold"
- Enables zero-latency read analytics

### Phase 2: SmartPruningStrategy
- Powers `stale_cleanup` strategy
- Provides retention scoring for pruning decisions
- Enforces protection rules (never prune preferences, high-importance memories)

### Phase 3: ConsolidationEngine
- Powers `consolidate_similar` strategy
- Uses NLP clustering to find related memories
- Creates summaries preserving key information

## Safety Features

### Dry-Run by Default
- All operations default to `dry_run=true`
- Shows what would be changed without modifying data
- Requires explicit `dry_run=false` to make changes

### Protection Rules
Never optimizes:
- Memories with importance ≥ 0.8
- Memories accessed ≥10 times
- Memories younger than 30 days
- Preference and user configuration memories
- Memories from protected sources (claude-code-hook, cli, project-initialization)

### Recovery Window
- Archived memories kept for 30 days
- Can be restored if needed
- Automatic expiration after recovery window

## Performance Considerations

### Target Latencies
- Analysis (dry-run): <500ms
- Optimization: <2000ms for 20 memories
- Scales linearly with `limit` parameter

### Best Practices
1. Start with `dry_run=true` to preview changes
2. Use smaller `limit` values for faster responses (10-20)
3. Run `top_accessed` most frequently (lowest overhead)
4. Run `consolidate_similar` less frequently (highest computation)
5. Run `stale_cleanup` periodically (weekly/monthly)

## Error Handling

### Common Errors

**Database Not Found**
```json
{
  "status": "error",
  "error": "Memory database not found. Initialize with 'kuzu-memory setup' first."
}
```

**Unknown Strategy**
```json
{
  "status": "error",
  "error": "Unknown strategy: invalid_strategy"
}
```

**Optimization Failure**
```json
{
  "status": "error",
  "strategy": "top_accessed",
  "error": "Failed to execute optimization: [detailed error message]"
}
```

## Testing

See `tests/mcp/test_optimize_tool.py` for comprehensive test coverage:
- Tool registration verification
- Each strategy (top_accessed, stale_cleanup, consolidate_similar)
- Error handling (missing database, unknown strategy)
- Mock-based unit tests for fast execution

Run tests:
```bash
uv run pytest tests/mcp/test_optimize_tool.py -v
```

## Related Documentation

- [Smart Memory Cleanup Design](research/memory-consolidation-analytics-pruning-2025-02-10.md)
- [AccessTracker](../src/kuzu_memory/monitoring/access_tracker.py)
- [SmartPruningStrategy](../src/kuzu_memory/core/smart_pruning.py)
- [ConsolidationEngine](../src/kuzu_memory/nlp/consolidation.py)

## Future Enhancements

Potential improvements for future versions:

1. **Adaptive Thresholds**: Learn optimal thresholds based on usage patterns
2. **Incremental Optimization**: Spread optimization across multiple small operations
3. **User Preferences**: Learn when user wants automatic vs manual optimization
4. **Performance Metrics**: Track recall latency improvement after optimization
5. **Scheduling**: Automatic periodic optimization during idle periods

---

**Version**: 1.7.0 (Phase 4 of Smart Memory Cleanup)
**Status**: Implemented and tested
**Related Issue**: #19
