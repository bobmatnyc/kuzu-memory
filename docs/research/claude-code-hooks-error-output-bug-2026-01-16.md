# Claude Code Hooks ERROR Output Bug

**Research Date**: 2026-01-16
**Issue**: kuzu-memory hooks output "ERROR:" text to stderr instead of valid JSON to stdout
**Impact**: Breaks Claude Code integration when errors occur in hooks

## Problem Summary

Claude Code hooks require **JSON-only output to stdout** when exiting with code 0. When kuzu-memory hooks encounter errors, they:

1. ❌ Write `logger.error("ERROR: ...")` to stderr
2. ❌ Exit with code 0 (success)
3. ❌ Provide no JSON output to stdout

This violates the Claude Code hooks API contract and causes hook failures to be silent or result in invalid JSON parsing errors.

## Root Cause Analysis

### Files Affected

**Primary File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/hooks_commands.py`

**Hook Commands**:
- `hooks enhance` (line 302-400): UserPromptSubmit hook handler
- `hooks session-start` (line 402-484): SessionStart hook handler
- `hooks learn` (line 486-698): PostToolUse hook handler

### Error Output Patterns Found

All three hook commands follow this **broken pattern**:

```python
try:
    # ... hook logic ...
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON from stdin: {e}")  # ❌ stderr only
    sys.exit(0)  # ❌ Exit code 0 with no stdout
except Exception as e:
    logger.error(f"Error enhancing prompt: {e}")  # ❌ stderr only
    sys.exit(0)  # ❌ Exit code 0 with no stdout
```

**Issues**:
1. **No stdout output**: Hooks exit without writing JSON to stdout
2. **Exit code 0**: Signals success to Claude Code despite errors
3. **stderr only**: Claude Code ignores stderr with exit code 0

### Specific Error Locations

#### hooks_commands.py:340 (hooks enhance)
```python
340:        logger.error(f"Failed to parse JSON from stdin: {e}")
341:        sys.exit(0)
```

#### hooks_commands.py:390 (hooks enhance)
```python
390:        logger.error(f"Error enhancing prompt: {e}")
391:        sys.exit(0)
```

#### hooks_commands.py:398 (hooks enhance)
```python
398:    logger.error(f"Unhandled exception: {e}", exc_info=True)
399:    sys.exit(0)
```

#### hooks_commands.py:440 (hooks session-start)
```python
440:        logger.error(f"Failed to parse JSON from stdin: {e}")
441:        sys.exit(0)
```

#### hooks_commands.py:470 (hooks session-start)
```python
470:        logger.error(f"Error storing session start memory: {e}")
471:        sys.exit(0)
```

#### hooks_commands.py:481 (hooks session-start)
```python
481:    logger.error(f"Unhandled exception: {e}", exc_info=True)
482:    sys.exit(0)
```

#### hooks_commands.py:617 (hooks learn)
```python
617:        logger.error(f"Failed to parse JSON from stdin: {e}")
618:        sys.exit(0)
```

#### hooks_commands.py:688 (hooks learn)
```python
688:        logger.error(f"Error storing memory: {e}")
689:        sys.exit(0)
```

#### hooks_commands.py:696 (hooks learn)
```python
696:    logger.error(f"Unhandled exception: {e}", exc_info=True)
697:    sys.exit(0)
```

## Claude Code Hooks API Specification

### Exit Code Behavior

| Exit Code | Stdout Processing | Stderr Usage | Behavior |
|-----------|------------------|--------------|----------|
| **0** | ✅ JSON parsed | ❌ Ignored | Success - JSON required |
| **2** | ❌ Ignored | ✅ Used as error | Blocking error - no JSON |
| **Other** | ❌ Ignored | ⚠️ Verbose only | Non-blocking error |

### Success Output (Exit Code 0)

**UserPromptSubmit / SessionStart Hooks**:
```json
{
  "continue": true,
  "suppressOutput": false,
  "systemMessage": "Optional warning",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Context to inject"
  }
}
```

**Alternative for UserPromptSubmit/SessionStart**: Plain text stdout is also valid.

**PostToolUse Hook**:
```json
{
  "continue": true,
  "decision": "block",  // Optional: only if blocking
  "reason": "Explanation",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Additional context for Claude"
  }
}
```

### Error Output (Exit Code 2)

When using **blocking error** mode (exit code 2):
- ✅ Write error message to stderr
- ❌ Do NOT write JSON to stdout
- ✅ Claude Code displays stderr directly to user

```bash
echo "Database connection failed" >&2
exit 2
```

### Silent Success (Exit Code 0)

For hooks that should do nothing on error (skip enhancement/learning):
- ✅ Write minimal JSON to stdout: `{"continue": true}`
- ❌ Do NOT write to stderr (ignored with exit 0)
- ✅ Exit with code 0

```bash
echo '{"continue": true}'
exit 0
```

## Recommended Fix Strategy

### Option 1: Silent Success (Recommended for kuzu-memory)

**Use Case**: Hooks should fail gracefully without blocking Claude Code

**Implementation**:
```python
import json
import sys

try:
    # Hook logic
    result = enhance_prompt(prompt)
    print(result)  # Plain text or JSON
except Exception as e:
    # Log error to file (not stderr)
    logger.error(f"Error enhancing prompt: {e}")

    # Output minimal success JSON to stdout
    print(json.dumps({"continue": true}))

    # Exit with success code
    sys.exit(0)
```

**Benefits**:
- ✅ Hooks never block Claude Code workflow
- ✅ Errors logged to file for debugging
- ✅ Graceful degradation (no enhancement is better than broken hook)

### Option 2: Blocking Error (Use Sparingly)

**Use Case**: Critical errors that should stop Claude Code execution

**Implementation**:
```python
import sys

try:
    # Critical hook logic
    validate_environment()
except Exception as e:
    # Write error to stderr (no JSON)
    print(f"[kuzu-memory] {e}", file=sys.stderr)

    # Exit with blocking error code
    sys.exit(2)
```

**When to Use**:
- Database corruption detected
- Security policy violation
- Project integrity at risk

**Benefits**:
- ✅ Prevents Claude Code from proceeding with bad state
- ✅ Error message shown directly to user
- ⚠️ Interrupts user workflow (use carefully)

## Proposed Code Changes

### hooks_commands.py:hooks_enhance (Line 302-400)

**Before**:
```python
try:
    input_data = json.load(sys.stdin)
    logger.debug(f"Input keys: {list(input_data.keys())}")
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON from stdin: {e}")
    sys.exit(0)  # ❌ WRONG: No JSON output
```

**After**:
```python
import json
import sys

try:
    input_data = json.load(sys.stdin)
    logger.debug(f"Input keys: {list(input_data.keys())}")
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON from stdin: {e}")
    # Output minimal success JSON
    print(json.dumps({"continue": true}))
    sys.exit(0)
```

### Pattern to Apply Across All Hooks

**Replace ALL error handling blocks** with:

```python
except Exception as e:
    logger.error(f"Error in hook: {e}")
    # Silent success - allow Claude Code to continue
    print(json.dumps({"continue": true}))
    sys.exit(0)
```

**OR for critical errors**:

```python
except CriticalError as e:
    # Blocking error - stop Claude Code
    print(f"[kuzu-memory] {e}", file=sys.stderr)
    sys.exit(2)
```

## Testing Strategy

### Unit Tests

**Test File**: `tests/unit/cli/test_hooks_commands.py`

```python
def test_hooks_enhance_json_parse_error_returns_valid_json():
    """Hook should output valid JSON even when stdin is malformed."""
    runner = CliRunner()
    result = runner.invoke(
        hooks_enhance,
        input="invalid json{",
    )

    # Should exit successfully
    assert result.exit_code == 0

    # Should output valid JSON
    output = json.loads(result.stdout)
    assert output["continue"] is True


def test_hooks_enhance_error_continues_gracefully():
    """Hook should continue on errors without blocking Claude Code."""
    runner = CliRunner()

    # Simulate database error by using non-existent project
    with patch("kuzu_memory.cli.hooks_commands.find_project_root", return_value=None):
        result = runner.invoke(
            hooks_enhance,
            input=json.dumps({"prompt": "test"}),
        )

    # Should exit successfully (not block)
    assert result.exit_code == 0

    # Should output valid JSON
    output = json.loads(result.stdout)
    assert output["continue"] is True
```

### Integration Tests

**Test Claude Code Integration**:

```bash
# Test hooks with real Claude Code JSON input
echo '{"prompt": "test prompt", "session_id": "abc123"}' | \
  kuzu-memory hooks enhance

# Expected output (success case):
# Relevant Project Context
# - Memory 1
# - Memory 2

# Expected output (error case):
# {"continue": true}

# Exit code should ALWAYS be 0
echo $?  # Should print: 0
```

## Impact Assessment

### Current Behavior (Broken)

1. **Error occurs** in hook (e.g., database unavailable)
2. ❌ Hook logs error to stderr
3. ❌ Hook exits with code 0
4. ❌ No JSON output to stdout
5. ❌ Claude Code tries to parse empty stdout as JSON
6. ❌ Claude Code fails with JSON parse error
7. ❌ User sees cryptic error message

### Fixed Behavior (Silent Success)

1. **Error occurs** in hook (e.g., database unavailable)
2. ✅ Hook logs error to file (for debugging)
3. ✅ Hook outputs `{"continue": true}` to stdout
4. ✅ Hook exits with code 0
5. ✅ Claude Code parses JSON successfully
6. ✅ Claude Code continues without enhancement
7. ✅ User workflow uninterrupted

### Fixed Behavior (Blocking Error - Optional)

1. **Critical error** occurs (e.g., corrupted database)
2. ✅ Hook writes error to stderr
3. ✅ Hook exits with code 2
4. ✅ Claude Code shows error to user
5. ✅ User can fix issue before proceeding

## References

- **Claude Code Hooks API**: https://code.claude.com/docs/en/hooks
- **Hook Examples**: https://github.com/disler/claude-code-hooks-mastery
- **kuzu-memory Installation**: https://github.com/bobmatnyc/kuzu-memory

## Sources

- [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)
- [A developer's guide to settings.json in Claude Code (2025)](https://www.eesel.ai/blog/settings-json-claude-code)
- [GitHub - disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery)

## Next Steps

1. ✅ Document issue in research file
2. ⬜ Create GitHub issue for tracking
3. ⬜ Implement fix in hooks_commands.py
4. ⬜ Add unit tests for error handling
5. ⬜ Add integration tests with sample JSON
6. ⬜ Update documentation with error behavior
7. ⬜ Release patch version (1.6.16)
