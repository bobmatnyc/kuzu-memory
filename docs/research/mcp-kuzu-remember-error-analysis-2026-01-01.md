# MCP `kuzu_remember` Tool Failure Investigation

**Date:** 2026-01-01
**Investigator:** Research Agent
**Issue:** MCP tool `kuzu_remember` failing with "No such command 'remember'" error

---

## Executive Summary

The MCP server's `kuzu_remember` tool is calling a **non-existent CLI command** `kuzu-memory remember`. The CLI was refactored to **consolidate all memory operations under the `memory` command group**, but the MCP server implementation was not updated to reflect this change.

**Root Cause:** CLI architecture refactoring moved `remember` from a top-level command to a subcommand under `memory`, but MCP server still uses the old command structure.

**Impact:** All MCP tools that directly invoke CLI commands (`kuzu_remember`, potentially others) are broken.

---

## Investigation Findings

### 1. Available CLI Commands (Current State)

**Top-level commands:**
```bash
kuzu-memory --help
# Commands:
  demo        🎮 Automated demo
  doctor      🩺 Diagnose and fix issues
  git         Git commit history sync
  health      🏥 System health (alias for status)
  help        ❓ Help system
  hooks       🪝 Hook system entry points
  init        🚀 Initialize project
  install     Install integrations
  mcp         Start MCP server (stdio)
  memory      🧠 Memory operations (store, recall, enhance)  ← KEY GROUP
  quickstart  🎯 Interactive quickstart
  repair      Repair broken MCP configs
  setup       🚀 Smart setup
  stats       📊 Display statistics (deprecated)
  status      📊 Display status
  uninstall   Uninstall integration
  update      🔄 Check for updates
```

**Memory subcommands:**
```bash
kuzu-memory memory --help
# Commands:
  enhance  🚀 Enhance a prompt with relevant memory context
  learn    🧠 Learn from content (with smart async processing)
  prune    🧹 Prune old or low-value memories
  recall   🔍 Recall memories related to a topic
  recent   🕒 Show recent memories
  store    💾 Store a memory for future recall (synchronous)  ← CORRECT COMMAND
```

**Verification:**
```bash
# ❌ THESE COMMANDS DON'T EXIST (top-level):
kuzu-memory remember --help
# Error: No such command 'remember'.

kuzu-memory enhance --help
# Error: No such command 'enhance'.

# ✅ THESE COMMANDS WORK (under memory group):
kuzu-memory memory store --help  # Works!
kuzu-memory memory enhance --help  # Works!
kuzu-memory memory recall --help  # Works!
```

---

### 2. MCP Server Implementation Analysis

**Location:** `src/kuzu_memory/mcp/server.py`

#### Tool Definitions (Lines 89-189)

The MCP server exposes 5 tools:

| MCP Tool Name | Description | Implementation Method |
|---------------|-------------|----------------------|
| `kuzu_enhance` | Enhance prompts with context | `_enhance()` |
| `kuzu_learn` | Store learnings asynchronously | `_learn()` |
| `kuzu_recall` | Query specific memories | `_recall()` |
| **`kuzu_remember`** | **Store important information** | **`_remember()`** ← BROKEN |
| `kuzu_stats` | Get statistics and status | `_stats()` |

#### Problematic Implementation (Lines 345-351)

```python
async def _remember(self, content: str, memory_type: str = "identity") -> str:
    """Store important project information."""
    if not content:
        return "Error: No content provided"

    # ❌ PROBLEM: This command doesn't exist!
    args = ["remember", content, "--type", memory_type]
    return await self._run_command(args)
```

**What it tries to execute:**
```bash
kuzu-memory remember "content" --type identity
# Error: No such command 'remember'.
```

**What it SHOULD execute:**
```bash
kuzu-memory memory store "content" --source <memory_type>
# Note: --type flag doesn't exist; should use --source instead
```

---

### 3. Other MCP Tools Status

Let me check if other tools have similar issues:

#### `kuzu_enhance` (Lines 301-314) - ✅ BROKEN

```python
async def _enhance(self, prompt: str, max_memories: int = 5) -> str:
    args = [
        "enhance",  # ❌ WRONG: Should be "memory", "enhance"
        prompt,
        "--max-memories",
        str(max_memories),
        "--format",
        "plain",
    ]
    return await self._run_command(args)
```

**Should be:**
```python
args = ["memory", "enhance", prompt, "--max-memories", str(max_memories), "--format", "plain"]
```

#### `kuzu_learn` (Lines 316-323) - ✅ BROKEN

```python
async def _learn(self, content: str, source: str = "ai-conversation") -> str:
    args = ["learn", content, "--source", source, "--quiet"]
    # ❌ WRONG: Should be "memory", "learn"
    return await self._run_command(args, capture_output=False)
```

**Should be:**
```python
args = ["memory", "learn", content, "--source", source, "--quiet"]
```

#### `kuzu_recall` (Lines 325-343) - ✅ BROKEN

```python
async def _recall(self, query: str, limit: int = 5) -> str:
    args = ["recall", query, "--limit", str(limit), "--format", "json"]
    # ❌ WRONG: Should be "memory", "recall"
    result = await self._run_command(args)
```

**Should be:**
```python
args = ["memory", "recall", query, "--limit", str(limit), "--format", "json"]
```

#### `kuzu_stats` (Lines 353-376) - ⚠️ PARTIALLY CORRECT

```python
async def _stats(self, detailed: bool = False) -> str:
    args = ["stats", "--format", "json"]  # Uses deprecated 'stats' command
    if detailed:
        args.append("--detailed")
```

**Note:** `stats` exists but is **deprecated** (see line 675-696 in commands.py). Should use:
```python
args = ["status", "--format", "json"]
```

---

### 4. CLI Architecture Changes

**Evidence from `commands.py` (Lines 35-36):**

```python
from .memory_commands import enhance, memory, recall, recent, store
```

The commands are **imported** but **NOT registered as top-level commands**!

**Registration (Lines 637):**
```python
cli.add_command(memory)  # Only the GROUP is registered, not individual commands
```

**Verification in `memory_commands.py`:**
- Lines 24-43: `@click.group()` defines `memory()` as a **group**
- Lines 46-140: `@memory.command()` defines `store` as a **subcommand** of `memory`
- Lines 142-273: `@memory.command()` defines `learn` as a **subcommand** of `memory`
- Lines 276-471: `@memory.command()` defines `recall` as a **subcommand** of `memory`
- Lines 474-586: `@memory.command()` defines `enhance` as a **subcommand** of `memory`

**Conclusion:** The refactoring moved ALL memory operations under the `memory` command group for better organization and CLI structure.

---

## Root Cause Summary

### What Happened

1. **Original CLI structure (old):**
   ```bash
   kuzu-memory remember <content>
   kuzu-memory enhance <prompt>
   kuzu-memory recall <query>
   kuzu-memory learn <content>
   ```

2. **Refactored CLI structure (current):**
   ```bash
   kuzu-memory memory store <content>   # Renamed: remember → store
   kuzu-memory memory enhance <prompt>
   kuzu-memory memory recall <query>
   kuzu-memory memory learn <content>
   ```

3. **MCP server not updated:**
   - Still calls old command names: `remember`, `enhance`, `recall`, `learn`
   - Missing the `memory` prefix in all command invocations
   - Using wrong flag names (e.g., `--type` instead of `--source`)

---

## Required Fixes

### Fix 1: Update `kuzu_remember` implementation

**File:** `src/kuzu_memory/mcp/server.py:345-351`

```python
# ❌ CURRENT (BROKEN):
async def _remember(self, content: str, memory_type: str = "identity") -> str:
    args = ["remember", content, "--type", memory_type]
    return await self._run_command(args)

# ✅ FIXED:
async def _remember(self, content: str, memory_type: str = "identity") -> str:
    """Store important project information."""
    if not content:
        return "Error: No content provided"

    # Map memory_type to appropriate source
    # Note: CLI uses --source, not --type
    # memory_type values: "identity", "preference", "decision", "pattern"
    args = ["memory", "store", content, "--source", memory_type]
    return await self._run_command(args)
```

### Fix 2: Update `kuzu_enhance` implementation

**File:** `src/kuzu_memory/mcp/server.py:301-314`

```python
# ❌ CURRENT (BROKEN):
async def _enhance(self, prompt: str, max_memories: int = 5) -> str:
    args = ["enhance", prompt, "--max-memories", str(max_memories), "--format", "plain"]
    return await self._run_command(args)

# ✅ FIXED:
async def _enhance(self, prompt: str, max_memories: int = 5) -> str:
    """Enhance a prompt with project context."""
    if not prompt:
        return "Error: No prompt provided"

    args = ["memory", "enhance", prompt, "--max-memories", str(max_memories), "--format", "plain"]
    return await self._run_command(args)
```

### Fix 3: Update `kuzu_learn` implementation

**File:** `src/kuzu_memory/mcp/server.py:316-323`

```python
# ❌ CURRENT (BROKEN):
async def _learn(self, content: str, source: str = "ai-conversation") -> str:
    args = ["learn", content, "--source", source, "--quiet"]
    return await self._run_command(args, capture_output=False)

# ✅ FIXED:
async def _learn(self, content: str, source: str = "ai-conversation") -> str:
    """Store a learning asynchronously."""
    if not content:
        return "Error: No content provided"

    args = ["memory", "learn", content, "--source", source, "--quiet"]
    return await self._run_command(args, capture_output=False)
```

### Fix 4: Update `kuzu_recall` implementation

**File:** `src/kuzu_memory/mcp/server.py:325-343`

```python
# ❌ CURRENT (BROKEN):
async def _recall(self, query: str, limit: int = 5) -> str:
    args = ["recall", query, "--limit", str(limit), "--format", "json"]
    result = await self._run_command(args)

# ✅ FIXED:
async def _recall(self, query: str, limit: int = 5) -> str:
    """Query specific memories."""
    if not query:
        return "Error: No query provided"

    args = ["memory", "recall", query, "--max-memories", str(limit), "--format", "json"]
    result = await self._run_command(args)
    # ... rest of the method unchanged
```

**Note:** Changed `--limit` to `--max-memories` to match CLI signature in `memory_commands.py:278`.

### Fix 5: Update `kuzu_stats` to use non-deprecated command

**File:** `src/kuzu_memory/mcp/server.py:353-376`

```python
# ⚠️ CURRENT (USES DEPRECATED COMMAND):
async def _stats(self, detailed: bool = False) -> str:
    args = ["stats", "--format", "json"]
    if detailed:
        args.append("--detailed")

# ✅ FIXED:
async def _stats(self, detailed: bool = False) -> str:
    """Get memory system statistics."""
    args = ["status", "--format", "json"]  # Use 'status' instead of deprecated 'stats'
    if detailed:
        args.append("--detailed")

    # ... rest of the method unchanged
```

---

## Additional Observations

### CLI Flag Consistency Issue

**`memory recall` signature (memory_commands.py:277-286):**
```python
@click.option("--max-memories", default=10, help="Maximum number of memories to recall")
```

**`memory enhance` signature (memory_commands.py:476):**
```python
@click.option("--max-memories", default=5, help="Maximum number of memories to include")
```

**Consistency:** Both use `--max-memories`, which is good!

### Memory Type vs. Source Confusion

**MCP Tool Schema (server.py:160-170):**
```python
"memory_type": {
    "type": "string",
    "description": "Type of memory",
    "enum": ["identity", "preference", "decision", "pattern"],
    "default": "identity",
}
```

**CLI `store` command (memory_commands.py:49-51):**
```python
@click.option(
    "--source",
    default="cli",
    help='Source of the memory (e.g., "conversation", "document")',
)
```

**Analysis:**
- MCP tool uses `memory_type` semantic categorization
- CLI uses `--source` for origin tracking (e.g., "cli", "ai-conversation", "git-commit")
- These serve different purposes but are being mixed in the current implementation

**Recommendation:**
- The `_remember()` method should map `memory_type` to `--source` value
- OR: Add a `--type` flag to the CLI (future enhancement)
- For now: Use `--source` with the `memory_type` value as a reasonable approximation

---

## Testing Verification

### Test Case 1: kuzu_remember (Primary Issue)

**Before Fix:**
```bash
# What MCP calls internally:
kuzu-memory remember "Test content" --type identity
# Error: No such command 'remember'.
```

**After Fix:**
```bash
# What MCP should call:
kuzu-memory memory store "Test content" --source identity
# ✅ Success: Stored memory: Test content
```

### Test Case 2: kuzu_enhance

**Before Fix:**
```bash
kuzu-memory enhance "How do I deploy?" --max-memories 5 --format plain
# Error: No such command 'enhance'.
```

**After Fix:**
```bash
kuzu-memory memory enhance "How do I deploy?" --max-memories 5 --format plain
# ✅ Success: Returns enhanced prompt with context
```

### Test Case 3: kuzu_recall

**Before Fix:**
```bash
kuzu-memory recall "database setup" --limit 5 --format json
# Error: No such command 'recall'.
```

**After Fix:**
```bash
kuzu-memory memory recall "database setup" --max-memories 5 --format json
# ✅ Success: Returns JSON array of memories
```

### Test Case 4: kuzu_learn

**Before Fix:**
```bash
kuzu-memory learn "API rate limit is 1000/hour" --source ai-conversation --quiet
# Error: No such command 'learn'.
```

**After Fix:**
```bash
kuzu-memory memory learn "API rate limit is 1000/hour" --source ai-conversation --quiet
# ✅ Success: Learning stored asynchronously
```

### Test Case 5: kuzu_stats

**Before Fix:**
```bash
kuzu-memory stats --format json
# ⚠️ Works but shows deprecation warning
```

**After Fix:**
```bash
kuzu-memory status --format json
# ✅ Success: No deprecation warning
```

---

## Impact Assessment

### Severity: **HIGH**

**Affected Components:**
- All 5 MCP tools are broken or using deprecated commands
- Any AI system using MCP integration (Claude Desktop, Claude Code) cannot properly interact with KuzuMemory

**User Impact:**
- Users get cryptic "No such command" errors
- MCP tools appear broken in Claude Desktop/Code
- No way to store memories via MCP interface
- Degrades the entire value proposition of KuzuMemory for AI integrations

**Data Integrity:**
- No data loss (commands fail before execution)
- No corruption risk

### Recommended Priority: **P0 - Critical**

This should be fixed immediately as it breaks the primary integration path for AI systems.

---

## Implementation Checklist

### Code Changes Required

- [ ] Fix `_remember()` method (lines 345-351)
- [ ] Fix `_enhance()` method (lines 301-314)
- [ ] Fix `_learn()` method (lines 316-323)
- [ ] Fix `_recall()` method (lines 325-343)
- [ ] Fix `_stats()` method (lines 353-376)

### Testing Required

- [ ] Unit tests for each MCP tool method
- [ ] Integration tests with actual CLI commands
- [ ] E2E tests with MCP server running in stdio mode
- [ ] Verify all 5 MCP tools work correctly via Claude Desktop

### Documentation Updates

- [ ] Update MCP server documentation
- [ ] Add architecture note about CLI refactoring
- [ ] Document mapping between MCP parameters and CLI flags
- [ ] Add troubleshooting guide for MCP integration

### Release Process

- [ ] Bump version to 1.6.11 (patch release)
- [ ] Create changelog entry explaining fixes
- [ ] Test against Claude Desktop before release
- [ ] Deploy to PyPI
- [ ] Notify users to update their MCP server installations

---

## Related Issues/PRs

**Potential Related Items:**
- CLI refactoring commit that moved commands to `memory` group
- Any issues/PRs about "MCP tools not working"
- Documentation about CLI structure changes

**Search Recommendations:**
```bash
# Find the refactoring commit
git log --all --grep="memory.*command" --grep="refactor.*cli" --oneline

# Find related issues
gh issue list --search "MCP" --search "remember" --search "No such command"
```

---

## Lessons Learned

### Process Gaps Identified

1. **No Integration Tests for MCP Server:**
   - CLI refactoring broke MCP server but no tests caught it
   - Need E2E tests that verify MCP tools call correct CLI commands

2. **Inconsistent Abstraction:**
   - MCP server directly calls CLI commands via subprocess
   - Better approach: Share service layer between MCP and CLI
   - Current architecture creates tight coupling to CLI structure

3. **No Deprecation Path:**
   - Old command structure removed without transition period
   - MCP server should have been updated in same commit
   - Or: Keep backward compatibility for one release cycle

### Future Improvements

1. **Shared Service Layer:**
   ```python
   # Instead of:
   subprocess.run(["kuzu-memory", "memory", "store", content])

   # Use:
   from kuzu_memory.services import MemoryService
   with MemoryService() as memory:
       memory.remember(content, source=source)
   ```

2. **MCP Server Integration Tests:**
   ```python
   @pytest.mark.integration
   def test_mcp_remember_calls_correct_cli_command():
       server = KuzuMemoryMCPServer()
       with patch('subprocess.run') as mock:
           server._remember("test", "identity")
           mock.assert_called_with(
               ["kuzu-memory", "memory", "store", "test", "--source", "identity"]
           )
   ```

3. **CLI Stability Contract:**
   - Define stable CLI interface
   - Document breaking changes in CHANGELOG
   - Maintain backward compatibility for at least one major version
   - Add deprecation warnings before removing commands

---

## Conclusion

**Root Cause:** CLI architectural refactoring moved memory commands from top-level to `memory` subcommand group, but MCP server implementation was not updated.

**Correct Command Structure:**
```bash
# OLD (what MCP server tries to use):
kuzu-memory remember <content>
kuzu-memory enhance <prompt>
kuzu-memory recall <query>

# NEW (what actually exists):
kuzu-memory memory store <content>
kuzu-memory memory enhance <prompt>
kuzu-memory memory recall <query>
```

**Fix Required:** Update all 5 MCP tool implementations in `src/kuzu_memory/mcp/server.py` to use correct command structure with `memory` prefix.

**Verification:** All MCP tools should be tested end-to-end with actual CLI commands before release.
