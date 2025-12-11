# Phase 11 - Mypy Commands Reference

Quick reference commands for executing Phase 11 mypy type safety work.

## Status Checking Commands

### Count total errors
```bash
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "error:" | wc -l
```

### Errors by directory
```bash
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "error:" | awk -F/ '{if (NF >= 3) print $3}' | sort | uniq -c | sort -rn
```

### Top files by error count
```bash
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "error:" | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -20
```

### Error types breakdown
```bash
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "\[.*\]$" | grep -oE '\[[a-z-]+\]$' | sort | uniq -c | sort -rn
```

## Targeted File Analysis

### Analyze specific file
```bash
python3 -m mypy src/kuzu_memory/cli/commands_backup.py --strict 2>&1 | grep "error:"
```

### Count errors in specific file
```bash
python3 -m mypy src/kuzu_memory/cli/commands_backup.py --strict 2>&1 | grep "error:" | wc -l
```

### Error types in specific file
```bash
python3 -m mypy src/kuzu_memory/cli/commands_backup.py --strict 2>&1 | grep "\[.*\]$" | grep -oE '\[[a-z-]+\]$' | sort | uniq -c | sort -rn
```

## Quick Fix Patterns

### Find all [no-untyped-def] errors
```bash
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "\[no-untyped-def\]"
```

### Find all [unreachable] code
```bash
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "\[unreachable\]"
```

### Find all [no-untyped-call] errors
```bash
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "\[no-untyped-call\]"
```

## Progress Tracking

### Before/After comparison
```bash
# Save current state
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "error:" | wc -l > /tmp/before.txt

# After fixes, compare
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "error:" | wc -l > /tmp/after.txt
echo "Before: $(cat /tmp/before.txt)"
echo "After:  $(cat /tmp/after.txt)"
echo "Fixed:  $(($(cat /tmp/before.txt) - $(cat /tmp/after.txt)))"
```

### Save detailed output for review
```bash
python3 -m mypy src/kuzu_memory/ --strict 2>&1 > /tmp/mypy_full_output.txt
```

## Phase-Specific Commands

### Phase 1: Quick Wins - Find all simple fixes
```bash
# Missing return type annotations
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "\[no-untyped-def\]" > /tmp/phase1_targets.txt

# Unreachable code (easy deletions)
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "\[unreachable\]" >> /tmp/phase1_targets.txt

echo "Phase 1 targets saved to /tmp/phase1_targets.txt"
```

### Phase 2: CLI Focus - Analyze CLI directory
```bash
# All CLI errors
python3 -m mypy src/kuzu_memory/cli/ --strict 2>&1 | grep "error:" > /tmp/phase2_cli_errors.txt

# commands_backup.py specifically
python3 -m mypy src/kuzu_memory/cli/commands_backup.py --strict 2>&1 | grep "error:" > /tmp/phase2_backup_errors.txt
```

### Phase 3: Integration Focus - Analyze integrations
```bash
# All integration errors
python3 -m mypy src/kuzu_memory/integrations/ --strict 2>&1 | grep "error:" > /tmp/phase3_integration_errors.txt

# Auggie files specifically
python3 -m mypy src/kuzu_memory/integrations/auggie*.py --strict 2>&1 | grep "error:" > /tmp/phase3_auggie_errors.txt
```

### Phase 4: Final Sweep - Find remaining issues
```bash
# All remaining errors
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "error:" > /tmp/phase4_remaining.txt

# Unused type: ignore comments
python3 -m mypy src/kuzu_memory/ --strict 2>&1 | grep "Unused.*type: ignore" > /tmp/phase4_unused_ignores.txt
```

## Verification Commands

### Run full strict check (should be zero errors at completion)
```bash
python3 -m mypy src/kuzu_memory/ --strict
```

### Check specific module is clean
```bash
python3 -m mypy src/kuzu_memory/cli/commands_backup.py --strict && echo "✅ No errors!"
```

### Run with coverage report
```bash
python3 -m mypy src/kuzu_memory/ --strict --any-exprs-report /tmp/mypy_reports/
```

## Common Fix Patterns

### Add return type annotation
```python
# Before
def my_function(x: str):
    print(x)

# After
def my_function(x: str) -> None:
    print(x)
```

### Remove unreachable code
```python
# Before
def check_value(x: int) -> str:
    if x > 0:
        return "positive"
    else:
        return "negative"
    print("unreachable")  # [unreachable]

# After
def check_value(x: int) -> str:
    if x > 0:
        return "positive"
    else:
        return "negative"
```

### Fix untyped function call
```python
# Before
def helper():  # [no-untyped-def]
    return "value"

def caller() -> str:
    return helper()  # [no-untyped-call]

# After
def helper() -> str:
    return "value"

def caller() -> str:
    return helper()  # Now typed!
```

## CI/CD Integration

### Pre-commit check (for future use)
```bash
# Add to .pre-commit-config.yaml
# - repo: https://github.com/pre-commit/mirrors-mypy
#   rev: 'v1.8.0'
#   hooks:
#     - id: mypy
#       args: [--strict]
```

### GitHub Actions check (for future use)
```yaml
# Add to .github/workflows/type-check.yml
# - name: Type check with mypy
#   run: python3 -m mypy src/kuzu_memory/ --strict
```

## Troubleshooting

### Reveal type of expression
```python
# Add to code temporarily
reveal_type(some_variable)  # mypy will show inferred type
```

### Ignore specific error (last resort)
```python
# Use sparingly, document why
result = some_call()  # type: ignore[no-untyped-call]  # External library
```

### Check mypy version
```bash
python3 -m mypy --version
```

---

**Note**: All commands assume you're running from the project root directory.
