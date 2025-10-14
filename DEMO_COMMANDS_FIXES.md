# Demo and Quickstart Commands - Required Fixes

**File**: `src/kuzu_memory/cli/commands.py`
**Issue**: Click's Sentinel object being passed to ctx.invoke() causes JSON serialization errors
**Priority**: CRITICAL - Blocks production deployment

---

## Fix Summary

All `ctx.invoke()` calls must provide explicit values (including None) for ALL parameters, even optional ones. Click's Sentinel object fails when code tries to serialize or use it as a value.

---

## Command Signatures Reference

```python
# From init_commands.py
def init(ctx, force: bool, config_path)
# Options: --force (flag), --config-path PATH

# From memory_commands.py
def store(ctx, content, source, session_id, agent_id, metadata)
# Argument: content (required)
# Options: --source (default="cli"), --session-id, --agent-id (default="cli"), --metadata

def recall(ctx, prompt, max_memories, strategy, session_id, agent_id, output_format, explain_ranking)
# Argument: prompt (required)
# Options: --max-memories (default=10), --strategy (default="hybrid"),
#          --session-id, --agent-id (default="cli"),
#          --format/output_format (default="simple"), --explain-ranking (flag)

def enhance(ctx, prompt, max_memories, output_format)
# Argument: prompt (required)
# Options: --max-memories (default=5), --format/output_format (default="context")

def recent(ctx, limit, output_format)
# Options: --limit (default=10), --format/output_format (default="table")

# From status_commands.py
def status(ctx, validate: bool, show_project: bool, detailed: bool, output_format: str)
# Options: --validate (flag), --project/show_project (flag),
#          --detailed (flag), --format/output_format (default="text")
```

---

## DEMO COMMAND FIXES (Lines 349-509)

### Fix 1: Line 384 - init invocation

**Current (BROKEN)**:
```python
try:
    ctx.invoke(init)
except SystemExit:
    # Already initialized, that's fine
    rich_print("✅ Database already initialized!", style="green")
```

**Fixed**:
```python
try:
    ctx.invoke(init, force=False, config_path=None)
except SystemExit:
    # Already initialized, that's fine
    rich_print("✅ Database already initialized!", style="green")
```

---

### Fix 2: Line 428 - store invocation

**Current (BROKEN)**:
```python
for i, (content, source) in enumerate(sample_memories, 1):
    rich_print(f"{i}. Storing: {content[:80]}...", style="dim")
    ctx.invoke(store, content=content, source=source)
    time.sleep(0.3)
```

**Fixed**:
```python
for i, (content, source) in enumerate(sample_memories, 1):
    rich_print(f"{i}. Storing: {content[:80]}...", style="dim")
    ctx.invoke(store, content=content, source=source,
               session_id=None, agent_id="demo", metadata=None)
    time.sleep(0.3)
```

---

### Fix 3: Line 440 - recall invocation

**Current**:
```python
ctx.invoke(recall, prompt=query, max_memories=3, output_format="simple")
```

**Fixed** (add missing params):
```python
ctx.invoke(recall, prompt=query, max_memories=3, strategy="hybrid",
           session_id=None, agent_id="demo", output_format="simple",
           explain_ranking=False)
```

---

### Fix 4: Line 456 - enhance invocation

**Current**:
```python
ctx.invoke(enhance, prompt=original_prompt, max_memories=3, output_format="context")
```

**Fixed** (already has all params):
```python
# This one is actually OK - has all required params
ctx.invoke(enhance, prompt=original_prompt, max_memories=3, output_format="context")
```

---

### Fix 5: Line 464 - status invocation

**Current**:
```python
ctx.invoke(status, detailed=False, output_format="text")
```

**Fixed** (add missing flags):
```python
ctx.invoke(status, validate=False, show_project=False,
           detailed=False, output_format="text")
```

---

### Fix 6: Line 472 - recent invocation

**Current**:
```python
ctx.invoke(recent, limit=5, output_format="table")
```

**Fixed** (already has all params):
```python
# This one is OK - has all params
ctx.invoke(recent, limit=5, output_format="table")
```

---

## QUICKSTART COMMAND FIXES (Lines 145-347)

### Fix 7: Line 175 - init invocation

**Current (BROKEN)**:
```python
if not db_path.exists():
    rich_print("Initializing KuzuMemory for this project...")
    ctx.invoke(init)
else:
    rich_print("✅ Project already initialized!")
```

**Fixed**:
```python
if not db_path.exists():
    rich_print("Initializing KuzuMemory for this project...")
    ctx.invoke(init, force=False, config_path=None)
else:
    rich_print("✅ Project already initialized!")
```

---

### Fix 8: Line 191 - store invocation

**Current (BROKEN)**:
```python
if rich_confirm("Would you like to store your first memory?", default=True):
    sample_memory = rich_prompt(
        "Enter something about your project",
        default="This is a Python project using KuzuMemory for AI memory",
    )
    ctx.invoke(store, content=sample_memory, source="quickstart")
```

**Fixed**:
```python
if rich_confirm("Would you like to store your first memory?", default=True):
    sample_memory = rich_prompt(
        "Enter something about your project",
        default="This is a Python project using KuzuMemory for AI memory",
    )
    ctx.invoke(store, content=sample_memory, source="quickstart",
               session_id=None, agent_id="quickstart", metadata=None)
```

---

### Fix 9: Line 204 - enhance invocation

**Current**:
```python
ctx.invoke(enhance, prompt=sample_prompt, max_memories=3, output_format="context")
```

**Fixed** (already has all params):
```python
# This one is OK - has all params
ctx.invoke(enhance, prompt=sample_prompt, max_memories=3, output_format="context")
```

---

### Fix 10: Line 214 - status invocation

**Current (BROKEN)**:
```python
rich_print("\n📊 Step 4: Project Status")
ctx.invoke(status, detailed=False, output_format="text")
```

**Fixed**:
```python
rich_print("\n📊 Step 4: Project Status")
ctx.invoke(status, validate=False, show_project=False,
           detailed=False, output_format="text")
```

---

### Fix 11: Line 223 - recent invocation

**Current**:
```python
if rich_confirm("Would you like to view your recent memories?", default=True):
    ctx.invoke(recent, limit=5, output_format="text")
    time.sleep(1)
```

**Fixed** (already has all params):
```python
# This one is OK - has all params
if rich_confirm("Would you like to view your recent memories?", default=True):
    ctx.invoke(recent, limit=5, output_format="text")
    time.sleep(1)
```

---

### Fix 12: Lines 254-261 - recall invocation

**Current**:
```python
ctx.invoke(
    recall,
    prompt=query,
    max_memories=5,
    strategy="hybrid",
    session_id=None,
    agent_id="cli",
    output_format="simple",
    explain_ranking=False,
)
```

**Fixed** (already has all params):
```python
# This one is OK - has all params
ctx.invoke(
    recall,
    prompt=query,
    max_memories=5,
    strategy="hybrid",
    session_id=None,
    agent_id="cli",
    output_format="simple",
    explain_ranking=False,
)
```

---

## Summary of Required Changes

| Line | Function | Status | Params to Add |
|------|----------|--------|--------------|
| 384 | demo → init | ❌ BROKEN | `force=False, config_path=None` |
| 428 | demo → store | ❌ BROKEN | `session_id=None, agent_id="demo", metadata=None` |
| 440 | demo → recall | ⚠️ INCOMPLETE | `strategy="hybrid", session_id=None, agent_id="demo", explain_ranking=False` |
| 456 | demo → enhance | ✅ OK | None needed |
| 464 | demo → status | ❌ BROKEN | `validate=False, show_project=False` |
| 472 | demo → recent | ✅ OK | None needed |
| 175 | quickstart → init | ❌ BROKEN | `force=False, config_path=None` |
| 191 | quickstart → store | ❌ BROKEN | `session_id=None, agent_id="quickstart", metadata=None` |
| 204 | quickstart → enhance | ✅ OK | None needed |
| 214 | quickstart → status | ❌ BROKEN | `validate=False, show_project=False` |
| 223 | quickstart → recent | ✅ OK | None needed |
| 254-261 | quickstart → recall | ✅ OK | None needed |

**Total Fixes Required**: 7 critical, 1 incomplete
**Estimated Fix Time**: 15-20 minutes
**Testing Time**: 10-15 minutes

---

## Testing Checklist

After applying fixes:

- [ ] `python3 -m py_compile src/kuzu_memory/cli/commands.py` (syntax check)
- [ ] `pipx install --force .` (reinstall with fixes)
- [ ] `cd /tmp/test-demo && kuzu-memory demo` (test demo in clean dir)
- [ ] Verify all 8 steps complete successfully
- [ ] `cd /tmp/test-quickstart && kuzu-memory quickstart` (test quickstart)
- [ ] Test with existing database (should not crash)
- [ ] Verify visual formatting looks correct
- [ ] Check logs for any unexpected errors

---

## Root Cause Explanation

When you use `ctx.invoke(command, param1=value1)`, Click:

1. Receives the explicitly provided parameters (param1)
2. For any missing optional parameters, uses its internal `Sentinel` object
3. Passes `Sentinel` to the invoked command function

The problem occurs when the command tries to:
- Serialize `Sentinel` to JSON → ERROR
- Use `Sentinel` as a path → ERROR
- Pass `Sentinel` to type-checking code → ERROR

**Solution**: Always provide explicit values (including `None`) for ALL parameters.

---

## Prevention Strategy

**Future `ctx.invoke()` Best Practice**:

```python
# ❌ BAD - Will break with Sentinel errors
ctx.invoke(some_command, required_param=value)

# ✅ GOOD - Explicit values for all params
ctx.invoke(some_command,
           required_param=value,
           optional_param1=None,
           optional_param2=default_value,
           flag_param=False)
```

**Add to code review checklist**:
- All `ctx.invoke()` calls provide ALL parameters
- No assumptions about Click's default handling
- Integration tests cover command invocation paths

---

**Fix Priority**: CRITICAL - Must fix before release
**Estimated Total Time**: 30 minutes (fixes + testing)
**Review Required**: Yes - verify all invocations updated correctly
