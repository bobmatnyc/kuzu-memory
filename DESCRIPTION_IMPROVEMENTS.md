# MCP Tool Description Improvements - Issue #6

## Overview

Enhanced MCP tool descriptions in `src/kuzu_memory/mcp/server.py` for better discoverability in Claude Code MCPSearch. All changes are **non-breaking** (description strings only, no API changes).

## Changes Made

### 1. `kuzu_enhance` - RAG Prompt Augmentation

**Before:**
```
"Enhance a prompt with project-specific context from KuzuMemory"
```

**After:**
```
"RAG prompt augmentation: Enhance prompts with project-specific context
from KuzuMemory using semantic search and vector similarity. Performs
context injection by retrieving relevant project memories, patterns, and
learnings to augment the input prompt. Use this for context-aware AI
responses that understand project history and domain knowledge."
```

**Keywords added:** RAG, semantic search, context injection, prompt augmentation, vector similarity

---

### 2. `kuzu_learn` - Async Background Learning

**Before:**
```
"Store a learning or observation asynchronously (non-blocking)"
```

**After:**
```
"ASYNC/BACKGROUND/NON-BLOCKING continuous learning: Store observations,
insights, and learnings asynchronously during conversations without waiting
for confirmation. Ideal for capturing context, patterns, and evolving
understanding as they emerge. Returns immediately without blocking.

When to use: Ongoing conversation learnings, observations, insights,
context capture during development sessions.

When NOT to use: Critical facts requiring immediate confirmation (use
kuzu_remember instead for synchronous storage of important decisions,
preferences, or facts that must be stored immediately)."
```

**Keywords added:** ASYNC, BACKGROUND, NON-BLOCKING, continuous learning
**Cross-reference:** Links to `kuzu_remember` for comparison
**Guidance:** Clear "when to use" and "when NOT to use" sections

---

### 3. `kuzu_recall` - Semantic Memory Retrieval

**Before:**
```
"Query specific memories from the project"
```

**After:**
```
"Semantic memory retrieval: Query project memories using vector search and
similarity matching. Performs semantic search across stored learnings,
patterns, decisions, and context to find relevant information based on
meaning rather than exact keyword matches. Returns memories ranked by
relevance score and temporal decay weighting. Use this to retrieve
project-specific knowledge, past decisions, learned patterns, or context
from previous conversations."
```

**Keywords added:** semantic, vector search, similarity, retrieval, meaning-based
**Parameter improvements:**
- `query`: "Semantic query to search memories (meaning-based, not keyword matching)"
- `limit`: "Maximum number of results to return (default: 5, higher values return more memories)"

---

### 4. `kuzu_remember` - Sync Immediate Storage

**Before:**
```
"Store important project information"
```

**After:**
```
"SYNC/IMMEDIATE/BLOCKING critical fact storage: Store important decisions,
preferences, or facts that must be confirmed immediately. This operation
waits for database confirmation before returning, ensuring the memory is
durably persisted. Use for critical information that requires immediate
storage verification.

When to use: Important decisions, user preferences, project constraints,
architectural choices, critical facts that need immediate confirmation.

For background learning during conversations: Use kuzu_learn instead
(async, non-blocking, ideal for continuous context capture without waiting)."
```

**Keywords added:** SYNC, IMMEDIATE, BLOCKING, critical
**Cross-reference:** Links to `kuzu_learn` for background learning
**Guidance:** Clear "when to use" section
**Parameter improvements:**
- `content`: "The critical content to store immediately with confirmation"
- `memory_type`: Expanded enum descriptions (identity, preference, decision, pattern)

---

### 5. `kuzu_stats` - Health Check & Diagnostics

**Before:**
```
"Get KuzuMemory statistics and status"
```

**After:**
```
"Health check and diagnostics: Get KuzuMemory system statistics, health
metrics, and monitoring data. Returns memory counts by type, database size,
index health status, recent activity summary, and performance statistics.
Use this for system health monitoring, troubleshooting, capacity planning,
and understanding memory system usage patterns.

Metrics returned: Total memory count, memory type distribution
(identity/preference/decision/pattern), database storage size, recent
activity timestamp, and optionally (with detailed=true): average recall
time, cache hit rate, embedding generation performance, and query
optimization statistics."
```

**Keywords added:** health check, diagnostics, metrics, monitoring
**Detailed metrics list:** Comprehensive list of what's returned
**Parameter improvements:**
- `detailed`: "Show detailed statistics including performance metrics, cache statistics, and query optimization data (default: false)"

---

## Key Improvements

### 1. Semantic Keywords for MCPSearch Discovery
All tools now include domain-specific keywords that match natural language search queries:
- RAG, semantic search, vector similarity
- ASYNC/SYNC, blocking/non-blocking
- Health check, diagnostics, monitoring

### 2. Clear Differentiation: `kuzu_learn` vs `kuzu_remember`
**Critical distinction emphasized:**
- `kuzu_learn`: ASYNC/BACKGROUND/NON-BLOCKING - for continuous learning
- `kuzu_remember`: SYNC/IMMEDIATE/BLOCKING - for critical facts

### 3. Cross-References Between Related Tools
- `kuzu_learn` → references `kuzu_remember` for critical facts
- `kuzu_remember` → references `kuzu_learn` for background learning

### 4. "When to Use" Guidance
Each tool includes practical guidance on when (and when NOT) to use it.

### 5. Enhanced Parameter Descriptions
All parameters now have clearer descriptions with examples and defaults.

---

## Verification

### Keywords Verification
```bash
python3 verify_descriptions.py
```

**Results:**
```
✅ All keywords present for kuzu_enhance: ['RAG', 'semantic search', 'context injection', 'prompt augmentation']
✅ All keywords present for kuzu_learn: ['ASYNC', 'BACKGROUND', 'NON-BLOCKING', 'continuous learning']
✅ Cross-reference to kuzu_remember found
✅ All keywords present for kuzu_recall: ['semantic', 'vector search', 'similarity', 'retrieval']
✅ All keywords present for kuzu_remember: ['SYNC', 'IMMEDIATE', 'BLOCKING', 'critical']
✅ Cross-reference to kuzu_learn found
✅ All keywords present for kuzu_stats: ['health', 'diagnostics', 'metrics', 'monitoring']
```

### Code Quality
```bash
make format  # ✅ Passed - all files formatted
```

### MCP Tests
```bash
uv run pytest tests/mcp/ -v  # ✅ Running (367 tests in progress)
```

---

## Impact

### For MCPSearch Discovery
Users can now find tools using natural language queries:
- "RAG context injection" → finds `kuzu_enhance`
- "async learning" → finds `kuzu_learn`
- "semantic search memories" → finds `kuzu_recall`
- "store critical decision" → finds `kuzu_remember`
- "system health diagnostics" → finds `kuzu_stats`

### For Developers
- Clear understanding of when to use each tool
- Better parameter documentation
- Cross-references guide tool selection

### Non-Breaking Change
- Only description strings modified
- No API changes
- No schema changes
- All existing integrations continue to work

---

## Files Modified

- `src/kuzu_memory/mcp/server.py` - Enhanced tool descriptions (lines 93-233)

---

## Next Steps

1. ✅ Descriptions updated with semantic keywords
2. ✅ Code formatted and verified
3. ⏳ MCP tests running (367 tests in progress)
4. 📋 Ready to commit once tests complete

---

**Status:** ✅ Complete - Awaiting final test results
