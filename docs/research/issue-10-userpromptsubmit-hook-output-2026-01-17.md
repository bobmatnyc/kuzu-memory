# Issue #10: UserPromptSubmit Hook Output Analysis

**Date**: 2026-01-17
**Issue**: https://github.com/bobmatnyc/kuzu-memory/issues/10
**Status**: Root cause identified

## Problem Statement

Users see `<system-reminder>UserPromptSubmit hook success: Success</system-reminder>` messages in their Claude Code conversations when the `hooks enhance` command executes successfully.

### Current User Experience

Every time a user submits a prompt:
```
<system-reminder>
UserPromptSubmit hook success: Success
</system-reminder>
```

This message appears before Claude's response, creating conversation noise.

## Root Cause Analysis

### The Hook Flow

1. **Hook Configuration** (`src/kuzu_memory/installers/claude_hooks.py:542-552`)
   ```python
   "UserPromptSubmit": [
       {
           "matcher": "*",
           "hooks": [
               {
                   "type": "command",
                   "command": f"{kuzu_memory_path} hooks enhance",
               }
           ],
       }
   ]
   ```

2. **Hook Command** (`src/kuzu_memory/cli/hooks_commands.py:331-430`)
   - Reads JSON from stdin
   - Enhances prompt with project memories
   - Outputs to stdout
   - Exits with JSON response

### The Actual Problem

Looking at the code in `hooks_commands.py:405-423`:

```python
if memories:
    # Format as context
    enhancement_parts = ["# Relevant Project Context"]
    for mem in memories:
        enhancement_parts.append(f"\n- {mem.content}")

    enhancement = "\n".join(enhancement_parts)
    logger.info(f"Enhancement generated ({len(enhancement)} chars)")
    print(enhancement)  # ← Prints enhancement to stdout
else:
    logger.info("No relevant memories found")

memory.close()

# ...exception handling...

_exit_hook_with_json()  # ← ALWAYS called at line 423
```

### The _exit_hook_with_json() Function

Located at `hooks_commands.py:24-35`:

```python
def _exit_hook_with_json(continue_execution: bool = True) -> None:
    """
    Exit hook with valid JSON output for Claude Code hooks API.

    Claude Code requires hooks to output JSON to stdout when exiting with code 0.
    This ensures proper communication with the hooks system.

    Args:
        continue_execution: Whether Claude Code should continue execution (default: True)
    """
    print(json.dumps({"continue": continue_execution}))  # ← Prints JSON to stdout
    sys.exit(0)
```

## The Issue

The hook outputs **TWO things to stdout**:

1. **Enhancement content** (when memories found): `print(enhancement)` at line 413
2. **JSON response** (always): `print(json.dumps({"continue": True}))` at line 34

### Claude Code's Interpretation

According to Claude Code hooks documentation:
- For `UserPromptSubmit` hooks with exit code 0, **stdout is added to the context**
- The `<system-reminder>` wrapper and "Success" message appear to be Claude Code's way of displaying hook output

The problem is that when there are NO memories to enhance (the `else` branch at line 415), the hook still outputs:
```json
{"continue": true}
```

This JSON output is what Claude Code is showing as `<system-reminder>UserPromptSubmit hook success: Success</system-reminder>`.

## Solution

The hook should use the **JSON `additionalContext` format** as documented in Claude Code hooks API, rather than mixing plain text output with JSON control messages.

### Current Output Pattern (INCORRECT)

```
# Relevant Project Context
- Memory 1
- Memory 2
{"continue": true}
```

### Correct Output Pattern

**Option 1: JSON-only output (Recommended)**
```json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "# Relevant Project Context\n- Memory 1\n- Memory 2"
  }
}
```

**Option 2: Silent on empty (Alternative)**
- Exit with code 0 and NO output when there are no memories
- Only output when there's actual enhancement content

## Files Requiring Changes

### Primary Fix Location

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/hooks_commands.py`

**Function**: `hooks_enhance()` (lines 331-430)

**Changes Required**:

1. Remove direct `print(enhancement)` at line 413
2. Modify `_exit_hook_with_json()` to accept optional context
3. Pass enhancement content through JSON response structure

### Modified _exit_hook_with_json() Signature

```python
def _exit_hook_with_json(
    continue_execution: bool = True,
    additional_context: str | None = None,
    hook_event: str | None = None
) -> None:
    """
    Exit hook with valid JSON output for Claude Code hooks API.

    Args:
        continue_execution: Whether Claude Code should continue execution
        additional_context: Optional context to inject (for UserPromptSubmit/SessionStart)
        hook_event: Hook event name (e.g., "UserPromptSubmit")
    """
    response = {"continue": continue_execution}

    if additional_context and hook_event:
        response["hookSpecificOutput"] = {
            "hookEventName": hook_event,
            "additionalContext": additional_context
        }

    print(json.dumps(response))
    sys.exit(0)
```

### Modified hooks_enhance() Logic

Replace lines 405-423 with:

```python
if memories:
    # Format as context
    enhancement_parts = ["# Relevant Project Context"]
    for mem in memories:
        enhancement_parts.append(f"\n- {mem.content}")

    enhancement = "\n".join(enhancement_parts)
    logger.info(f"Enhancement generated ({len(enhancement)} chars)")

    memory.close()
    _exit_hook_with_json(
        continue_execution=True,
        additional_context=enhancement,
        hook_event="UserPromptSubmit"
    )
else:
    logger.info("No relevant memories found")
    memory.close()
    _exit_hook_with_json()  # No additional context
```

## Impact Analysis

### Affected Commands

1. **hooks enhance** (UserPromptSubmit) - PRIMARY ISSUE
2. **hooks session-start** (SessionStart) - May have same issue
3. **hooks learn** (PostToolUse) - Different behavior (no stdout context injection)

### Testing Requirements

1. Test with memories available → Should inject context without visible message
2. Test without memories → Should have no visible output
3. Test error conditions → Verify JSON response format
4. Verify Claude Code receives and applies context correctly

## Additional Considerations

### Other Hooks May Need Updates

- `hooks_session_start()` (lines 433-516) - Uses same pattern
- `hooks_learn()` (lines 519-738) - Uses same pattern but for different event

All three hooks use `_exit_hook_with_json()` and may benefit from the unified JSON output format.

## References

- **Claude Code Hooks Documentation**: https://code.claude.com/docs/en/hooks
- **GitHub Issue #10**: https://github.com/bobmatnyc/kuzu-memory/issues/10
- **Hook Configuration**: `src/kuzu_memory/installers/claude_hooks.py`
- **Hook Implementation**: `src/kuzu_memory/cli/hooks_commands.py`

## Recommendation

Implement **Option 1 (JSON-only output)** for consistency with Claude Code hooks API specification. This ensures:

- Silent operation on success
- Proper context injection using official API
- No visible hook status messages
- Cleaner user experience
- Better compatibility with future Claude Code updates
