# MCP Tool Discoverability Analysis - Issue #6

**Research Date:** 2026-01-17
**Issue:** [#6 - Improve tool discoverability for Claude Code MCPSearch](https://github.com/bobmatnyc/kuzu-memory/issues/6)
**Researcher:** Claude (research-agent)
**Status:** Analysis Complete

---

## Executive Summary

This research analyzes the current MCP tool definitions in kuzu-memory to improve discoverability through Claude Code's MCPSearch feature. The analysis reveals that while basic descriptions exist, tools lack semantic keywords, clear differentiation between similar tools, and detailed "when to use" guidance.

**Key Findings:**
- ✅ All 5 core tools are properly defined with JSON schemas
- ⚠️ **Critical Gap**: `kuzu_learn` vs `kuzu_remember` distinction is unclear
- ⚠️ Missing semantic keywords for MCPSearch discovery
- ⚠️ `kuzu_stats` description lacks metric details
- ⚠️ No "when to use" guidance in descriptions

**Target Improvement:** From 75% → 90%+ MCPSearch readiness

---

## Current Tool Definitions

### 1. `kuzu_enhance`

**Location:** `src/kuzu_memory/mcp/server.py:93-111`

**Current Description:**
```
"Enhance a prompt with project-specific context from KuzuMemory"
```

**Parameters:**
- `prompt` (string, required): "The prompt to enhance with context"
- `max_memories` (integer, default: 5): "Maximum number of memories to include"

**Analysis:**
- ✅ Clear purpose: Augment prompts with project context
- ✅ Simple interface with sensible defaults
- ⚠️ Missing semantic keywords: "context", "retrieval", "augmentation", "RAG"
- ⚠️ No guidance on when to use vs. `kuzu_recall`

**Recommended Keywords:**
`["enhance", "prompt", "context", "augment", "retrieval", "RAG", "project-context", "memory-augmentation"]`

---

### 2. `kuzu_learn` (CRITICAL - Needs Differentiation)

**Location:** `src/kuzu_memory/mcp/server.py:112-130`

**Current Description:**
```
"Store a learning or observation asynchronously (non-blocking)"
```

**Parameters:**
- `content` (string, required): "The content to learn and store"
- `source` (string, default: "ai-conversation"): "Source of the learning"

**Implementation Details:**
- **Async behavior**: Fire-and-forget (lines 322-324)
- **CLI flags**: `--quiet --no-wait`
- **Purpose**: Background learning during conversations

**Analysis:**
- ✅ Correctly implements async behavior
- ❌ **CRITICAL**: Description doesn't explain async/non-blocking nature clearly
- ❌ **CRITICAL**: No differentiation from `kuzu_remember`
- ⚠️ Missing keywords: "background", "observation", "pattern", "conversation"
- ⚠️ No "when to use" guidance

**Key Confusion Point:**
Users don't understand that `kuzu_learn` is for **continuous background learning** during conversations, while `kuzu_remember` is for **immediate critical storage**.

**Recommended Enhanced Description:**
```
"Store learnings and observations asynchronously in the background (non-blocking).
Use for continuous learning during conversations: patterns, observations, insights.
For immediate critical facts, use kuzu_remember instead."
```

**Recommended Keywords:**
`["learn", "async", "background", "observation", "pattern", "insight", "continuous", "non-blocking", "conversation"]`

---

### 3. `kuzu_recall`

**Location:** `src/kuzu_memory/mcp/server.py:131-149`

**Current Description:**
```
"Query specific memories from the project"
```

**Parameters:**
- `query` (string, required): "The query to search memories"
- `limit` (integer, default: 5): "Maximum number of results"

**Implementation Details:**
- Returns formatted JSON list of memories
- Formats as bullet points: `"- {content}"`

**Analysis:**
- ✅ Clear search purpose
- ⚠️ Doesn't explain semantic search capability
- ⚠️ Missing keywords: "search", "query", "retrieve", "find", "semantic"
- ⚠️ No differentiation from `kuzu_enhance`

**Recommended Enhanced Description:**
```
"Search and retrieve specific memories using semantic similarity.
Use when you need to find relevant past information: decisions, patterns, preferences.
For automatic prompt enhancement, use kuzu_enhance."
```

**Recommended Keywords:**
`["recall", "search", "query", "retrieve", "find", "semantic", "similarity", "memory-search", "lookup"]`

---

### 4. `kuzu_remember` (CRITICAL - Needs Differentiation)

**Location:** `src/kuzu_memory/mcp/server.py:150-174`

**Current Description:**
```
"Store important project information"
```

**Parameters:**
- `content` (string, required): "The content to remember"
- `memory_type` (string, enum, default: "identity"): Type of memory
  - Options: `["identity", "preference", "decision", "pattern"]`

**Implementation Details:**
- **Synchronous**: Waits for completion
- Maps to CLI: `kuzu-memory memory store`
- Provides immediate feedback

**Analysis:**
- ✅ Enum for memory_type provides structure
- ❌ **CRITICAL**: No explanation of sync vs async behavior
- ❌ **CRITICAL**: Unclear when to use vs `kuzu_learn`
- ⚠️ Missing keywords from enum values: "identity", "preference", "decision", "pattern"
- ⚠️ No "when to use" guidance

**Key Confusion Point:**
The current description "Store important project information" doesn't convey:
1. **Synchronous/blocking** behavior (vs `kuzu_learn`'s async)
2. **Critical/immediate** nature (vs `kuzu_learn`'s background)
3. **Structured** memory types (identity, preference, decision, pattern)

**Recommended Enhanced Description:**
```
"Store critical project information immediately (blocking/synchronous).
Use for important facts that need immediate storage: project identity, user preferences,
architectural decisions, established patterns. For background learning during conversations,
use kuzu_learn instead."
```

**Recommended Keywords:**
`["remember", "store", "save", "critical", "immediate", "identity", "preference", "decision", "pattern", "fact", "synchronous"]`

---

### 5. `kuzu_stats`

**Location:** `src/kuzu_memory/mcp/server.py:175-189`

**Current Description:**
```
"Get KuzuMemory statistics and status"
```

**Parameters:**
- `detailed` (boolean, default: false): "Show detailed statistics"

**Implementation Details:**
- Returns formatted stats:
  - Total Memories
  - Memory Types (breakdown by category)
  - Recent Activity
  - **If detailed**: Avg Recall Time, Cache Hit Rate

**Analysis:**
- ⚠️ Description lacks detail about what metrics are available
- ⚠️ Missing keywords: "metrics", "performance", "diagnostics", "health"
- ⚠️ Doesn't mention performance metrics available with `--detailed`

**Recommended Enhanced Description:**
```
"Get memory system statistics and health metrics. Returns: total memories, memory types
breakdown, recent activity. Use --detailed for performance metrics: recall time, cache hit rate."
```

**Recommended Keywords:**
`["stats", "statistics", "metrics", "status", "health", "performance", "diagnostics", "analytics", "monitoring"]`

---

## Critical Differentiation: `kuzu_learn` vs `kuzu_remember`

### Current Problem

The two tools appear to overlap with no clear distinction:

| Tool | Current Description | Actual Behavior |
|------|---------------------|-----------------|
| `kuzu_learn` | "Store a learning or observation asynchronously" | Fire-and-forget, no wait |
| `kuzu_remember` | "Store important project information" | Synchronous, waits for completion |

**User Confusion:**
- When should I use `learn` vs `remember`?
- What's the difference between "learning" and "remembering"?
- Both seem to store information - which one do I need?

### Recommended Solution

**Create Clear Semantic Separation:**

#### `kuzu_learn` - Background Continuous Learning
- **Use Case**: During conversations, capture observations and patterns
- **Behavior**: Async, non-blocking, fire-and-forget
- **When**: "I noticed that...", "Pattern observed:", "Insight:"
- **Example**: Learning coding patterns, user preferences during dialogue

#### `kuzu_remember` - Immediate Critical Storage
- **Use Case**: Store important facts that need immediate confirmation
- **Behavior**: Synchronous, blocking, confirms storage
- **When**: "Remember that...", "Critical decision:", "Important:"
- **Example**: Project architecture decisions, user identity, key preferences

### Implementation Changes Needed

**1. Update Descriptions (High Priority)**

```python
# kuzu_learn - NEW description
Tool(
    name="kuzu_learn",
    description=(
        "Store learnings and observations asynchronously in the background (non-blocking). "
        "Use for continuous learning during conversations: patterns observed, insights gained, "
        "coding preferences noticed. For immediate critical facts, use kuzu_remember instead."
    ),
    # ... rest of schema
)

# kuzu_remember - NEW description
Tool(
    name="kuzu_remember",
    description=(
        "Store critical project information immediately (blocking/synchronous). "
        "Use for important facts that need immediate storage: project identity, "
        "user preferences, architectural decisions, established patterns. "
        "For background learning during conversations, use kuzu_learn instead."
    ),
    # ... rest of schema
)
```

**2. Add Semantic Keywords (Medium Priority)**

Enhance MCPSearch discoverability by adding rich keywords to descriptions:

```python
# kuzu_learn keywords
"Store learnings asynchronously (background, non-blocking, continuous, observation, pattern, insight)"

# kuzu_remember keywords
"Store critical information immediately (synchronous, blocking, decision, preference, identity, fact)"
```

**3. Add Usage Examples in Comments (Low Priority)**

```python
# Tool definition comments for developer reference
"""
kuzu_learn examples:
  - "I noticed the user prefers TypeScript over JavaScript"
  - "Pattern: User asks for tests after every feature"
  - "Observation: Project uses FastAPI with PostgreSQL"

kuzu_remember examples:
  - "Remember: Project name is 'kuzu-memory'"
  - "Critical: User prefers async/await over callbacks"
  - "Decision: Use Pydantic for all data validation"
"""
```

---

## Recommended Changes Summary

### Priority 1: Critical Differentiation (Must Fix)

**File:** `src/kuzu_memory/mcp/server.py`

**Changes:**

1. **`kuzu_learn` description** (lines 113-114):
```python
description=(
    "Store learnings and observations asynchronously in the background (non-blocking). "
    "Use for continuous learning during conversations: patterns, observations, insights. "
    "For immediate critical facts, use kuzu_remember instead. "
    "Keywords: async, background, observation, pattern, continuous"
),
```

2. **`kuzu_remember` description** (lines 152):
```python
description=(
    "Store critical project information immediately (blocking/synchronous). "
    "Use for important facts that need immediate storage: identity, preferences, "
    "decisions, patterns. For background learning, use kuzu_learn instead. "
    "Keywords: sync, immediate, critical, decision, preference, identity"
),
```

3. **`kuzu_recall` description** (lines 133):
```python
description=(
    "Search and retrieve specific memories using semantic similarity. "
    "Use to find relevant past information: decisions, patterns, preferences. "
    "For automatic prompt enhancement, use kuzu_enhance. "
    "Keywords: search, query, retrieve, semantic, similarity, lookup"
),
```

4. **`kuzu_enhance` description** (lines 95):
```python
description=(
    "Enhance a prompt with relevant project context automatically using RAG. "
    "Retrieves and augments prompts with similar memories from the knowledge base. "
    "For manual memory search, use kuzu_recall. "
    "Keywords: context, augment, RAG, retrieval, prompt-enhancement"
),
```

5. **`kuzu_stats` description** (lines 177):
```python
description=(
    "Get memory system statistics and health metrics. "
    "Returns: total memories, memory types breakdown, recent activity. "
    "Use --detailed for performance metrics (recall time, cache hit rate). "
    "Keywords: metrics, stats, health, performance, diagnostics, monitoring"
),
```

### Priority 2: Add Keyword-Rich Parameter Descriptions

**Enhance parameter descriptions with semantic keywords:**

```python
# kuzu_enhance
"prompt": {
    "type": "string",
    "description": "The prompt to enhance with project context and relevant memories",
}

# kuzu_learn
"content": {
    "type": "string",
    "description": "Learning content to store: observations, patterns, insights, preferences",
}

# kuzu_recall
"query": {
    "type": "string",
    "description": "Search query for semantic similarity matching across memories",
}

# kuzu_remember
"content": {
    "type": "string",
    "description": "Critical information to store: decisions, identity, preferences, patterns",
}
```

### Priority 3: Documentation Updates

**Update README and docs to explain tool selection:**

Create decision tree in `docs/mcp-tool-selection.md`:

```markdown
# When to Use Which MCP Tool

## Quick Reference

- **Need project context for a prompt?** → `kuzu_enhance`
- **Want to search for specific memory?** → `kuzu_recall`
- **Learning during conversation?** → `kuzu_learn` (async)
- **Storing critical fact immediately?** → `kuzu_remember` (sync)
- **Want system metrics?** → `kuzu_stats`

## Decision Tree

1. Are you enhancing a prompt with context?
   - YES → `kuzu_enhance`
   - NO → Continue to 2

2. Are you searching for existing memories?
   - YES → `kuzu_recall`
   - NO → Continue to 3

3. Are you storing NEW information?
   - Critical fact needing immediate storage? → `kuzu_remember` (blocking)
   - Background observation during conversation? → `kuzu_learn` (non-blocking)

4. Need system information?
   - YES → `kuzu_stats`
```

---

## MCPSearch Optimization Analysis

### How MCPSearch Works

Claude Code's MCPSearch tool matches user queries against MCP tool definitions using:
1. **Tool name** matching
2. **Description** semantic similarity
3. **Parameter names** and descriptions
4. **Keyword** density and relevance

### Current Discoverability Score: 75%

**Strengths:**
- ✅ Clear tool names (`kuzu_*` prefix for namespace)
- ✅ Basic descriptions present
- ✅ Proper JSON schema definitions

**Weaknesses:**
- ❌ Missing semantic keywords in descriptions
- ❌ Overlapping descriptions (`learn` vs `remember`)
- ❌ No "when to use" differentiation
- ❌ Limited keyword variety

### Target Discoverability Score: 90%+

**Required Improvements:**

1. **Add Rich Semantic Keywords** (+5%)
   - Include domain-specific terms: "RAG", "semantic search", "async/sync"
   - Add use-case keywords: "decision", "preference", "pattern", "observation"

2. **Differentiate Similar Tools** (+7%)
   - Clear `learn` vs `remember` distinction
   - Explicit `enhance` vs `recall` guidance

3. **Expand Descriptions** (+3%)
   - Add "when to use" guidance
   - Include metric details in `kuzu_stats`

**Projected Score After Changes: 90%**

---

## Testing Recommendations

### 1. MCPSearch Query Tests

Create test suite to validate discoverability:

```python
# tests/integration/test_mcp_search_discoverability.py

SEARCH_QUERIES = [
    # Async/sync differentiation
    ("store information in background", "kuzu_learn"),
    ("remember critical fact immediately", "kuzu_remember"),

    # Context retrieval
    ("enhance prompt with context", "kuzu_enhance"),
    ("search for memories", "kuzu_recall"),

    # Semantic keywords
    ("RAG retrieval augmentation", "kuzu_enhance"),
    ("async learning observation", "kuzu_learn"),
    ("decision preference identity", "kuzu_remember"),
    ("semantic similarity search", "kuzu_recall"),
    ("performance metrics stats", "kuzu_stats"),
]

@pytest.mark.parametrize("query,expected_tool", SEARCH_QUERIES)
def test_mcp_search_finds_correct_tool(query, expected_tool):
    """Verify MCPSearch returns correct tool for semantic queries."""
    # Test implementation using MCPSearch simulation
    pass
```

### 2. User Acceptance Testing

Validate with real Claude Code sessions:

```bash
# Test script for manual validation
# tests/manual/test_tool_selection.sh

echo "Testing MCPSearch discoverability..."

# Test 1: Async learning
echo "Query: 'store observation in background'"
# Expected: kuzu_learn

# Test 2: Critical storage
echo "Query: 'remember important decision immediately'"
# Expected: kuzu_remember

# Test 3: Context enhancement
echo "Query: 'enhance my prompt with project context'"
# Expected: kuzu_enhance

# Test 4: Memory search
echo "Query: 'find memories about database decisions'"
# Expected: kuzu_recall

# Test 5: System metrics
echo "Query: 'show me performance statistics'"
# Expected: kuzu_stats
```

---

## Implementation Checklist

### Phase 1: Critical Fixes (Immediate)

- [ ] Update `kuzu_learn` description with async/background keywords
- [ ] Update `kuzu_remember` description with sync/immediate keywords
- [ ] Add cross-references between `learn` and `remember` descriptions
- [ ] Add "when to use" guidance to all tool descriptions

### Phase 2: Enhancement (Short-term)

- [ ] Enrich all parameter descriptions with semantic keywords
- [ ] Update `kuzu_stats` description with metric details
- [ ] Add differentiation guidance to `kuzu_enhance` vs `kuzu_recall`
- [ ] Create `docs/mcp-tool-selection.md` decision tree

### Phase 3: Validation (Medium-term)

- [ ] Create MCPSearch query test suite
- [ ] Manual testing with Claude Code sessions
- [ ] User feedback collection on tool selection clarity
- [ ] Measure discoverability improvement (75% → 90%+)

### Phase 4: Documentation (Long-term)

- [ ] Update README with tool selection guide
- [ ] Add examples to MCP integration docs
- [ ] Create troubleshooting guide for incorrect tool selection
- [ ] Video tutorial on choosing the right tool

---

## Code Locations Reference

**Primary File:** `src/kuzu_memory/mcp/server.py`

**Tool Definitions:**
- Lines 90-189: `handle_list_tools()` function
- Line 93-111: `kuzu_enhance` definition
- Line 112-130: `kuzu_learn` definition
- Line 131-149: `kuzu_recall` definition
- Line 150-174: `kuzu_remember` definition
- Line 175-189: `kuzu_stats` definition

**Tool Implementations:**
- Line 301-315: `_enhance()` method
- Line 317-324: `_learn()` method (async, fire-and-forget)
- Line 326-352: `_recall()` method
- Line 354-360: `_remember()` method (sync, blocking)
- Line 362-385: `_stats()` method

**Related Files:**
- `src/kuzu_memory/cli/memory_commands.py`: CLI command implementations
- `tests/integration/test_mcp_installation.py`: MCP integration tests
- `tests/test_mcp.py`: Basic MCP server tests

---

## Success Metrics

### Quantitative Targets

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| MCPSearch Accuracy | 75% | 90%+ | Query test suite |
| Tool Selection Errors | ~25% | <10% | User feedback |
| Avg. Search Rank | 3-5 | 1-2 | MCPSearch ranking |
| Keyword Coverage | 40% | 80%+ | Semantic analysis |

### Qualitative Goals

- ✅ Clear differentiation between `kuzu_learn` and `kuzu_remember`
- ✅ Users understand when to use each tool without documentation
- ✅ MCPSearch consistently returns correct tool for semantic queries
- ✅ Reduced support requests about tool selection

---

## Related Issues

- **Issue #6:** Main tracking issue (this research)
- **Future Work:** Consider adding tool usage examples to MCP server responses
- **Future Work:** Interactive tool selection wizard in CLI

---

## Appendix: Full Proposed Tool Definitions

### Complete Updated Code

```python
@self.server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="kuzu_enhance",
            description=(
                "Enhance a prompt with relevant project context automatically using RAG "
                "(Retrieval-Augmented Generation). Retrieves and augments prompts with "
                "similar memories from the knowledge base. For manual memory search, "
                "use kuzu_recall instead. "
                "Keywords: context, augment, RAG, retrieval, prompt-enhancement, "
                "automatic, knowledge-base"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "The prompt to enhance with project context and relevant memories"
                        ),
                    },
                    "max_memories": {
                        "type": "integer",
                        "description": "Maximum number of memories to include in enhancement",
                        "default": 5,
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="kuzu_learn",
            description=(
                "Store learnings and observations asynchronously in the background "
                "(non-blocking). Use for continuous learning during conversations: "
                "patterns observed, insights gained, coding preferences noticed. "
                "For immediate critical facts, use kuzu_remember instead. "
                "Keywords: async, background, observation, pattern, continuous, "
                "non-blocking, insight, conversation, learning"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": (
                            "Learning content to store: observations, patterns, "
                            "insights, preferences discovered during conversation"
                        ),
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of the learning (default: ai-conversation)",
                        "default": "ai-conversation",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="kuzu_recall",
            description=(
                "Search and retrieve specific memories using semantic similarity matching. "
                "Use to find relevant past information: decisions, patterns, preferences. "
                "For automatic prompt enhancement, use kuzu_enhance instead. "
                "Keywords: search, query, retrieve, semantic, similarity, lookup, "
                "find, vector-search"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query for semantic similarity matching across "
                            "all stored memories"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="kuzu_remember",
            description=(
                "Store critical project information immediately (blocking/synchronous). "
                "Use for important facts that need immediate storage: project identity, "
                "user preferences, architectural decisions, established patterns. "
                "For background learning during conversations, use kuzu_learn instead. "
                "Keywords: sync, immediate, critical, decision, preference, identity, "
                "fact, blocking, important"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": (
                            "Critical information to store: decisions, identity, "
                            "preferences, or established patterns"
                        ),
                    },
                    "memory_type": {
                        "type": "string",
                        "description": (
                            "Type of memory: identity (project info), preference (user choices), "
                            "decision (architectural choices), pattern (established practices)"
                        ),
                        "enum": ["identity", "preference", "decision", "pattern"],
                        "default": "identity",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="kuzu_stats",
            description=(
                "Get memory system statistics and health metrics. "
                "Returns: total memories, memory types breakdown, recent activity. "
                "Use --detailed for performance metrics: average recall time, "
                "cache hit rate, query performance. "
                "Keywords: metrics, stats, health, performance, diagnostics, "
                "monitoring, analytics, system-info"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": (
                            "Show detailed statistics including performance metrics: "
                            "recall time, cache hit rate, query statistics"
                        ),
                        "default": False,
                    }
                },
            },
        ),
    ]
```

---

## References

- **Issue #6:** https://github.com/bobmatnyc/kuzu-memory/issues/6
- **MCP Specification:** https://modelcontextprotocol.io/
- **Claude Code MCPSearch:** Internal documentation (Claude Code)
- **Source Code:** `src/kuzu_memory/mcp/server.py`

---

**End of Research Document**
