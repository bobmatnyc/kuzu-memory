# Testing and Quality Assurance for Claude Code Hooks

## Overview

This directory contains production-ready Claude Code hooks with comprehensive testing, type checking, and logging infrastructure.

---

## Unit Tests

### Location
`tests/test_hooks.py` - Comprehensive test suite for both hooks

### Running Tests

**Install pytest** (if not already installed):
```bash
pip install pytest pytest-cov
```

**Run all tests**:
```bash
pytest tests/test_hooks.py -v
```

**Run with coverage**:
```bash
pytest tests/test_hooks.py --cov=.claude/hooks --cov-report=html
```

**Run specific test class**:
```bash
pytest tests/test_hooks.py::TestKuzuEnhanceHook -v
pytest tests/test_hooks.py::TestKuzuLearnHook -v
```

**Run specific test**:
```bash
pytest tests/test_hooks.py::TestKuzuEnhanceHook::test_validate_input_valid_prompt -v
```

### Test Coverage

The test suite covers:
- ✅ Input validation (valid, invalid, edge cases)
- ✅ Subprocess success and failure scenarios
- ✅ Timeout handling
- ✅ Command not found errors
- ✅ Transcript file finding (exists, missing, directory missing)
- ✅ JSON parsing (valid, invalid, malformed)
- ✅ Text extraction from messages
- ✅ Memory storage (success, failure, timeout)
- ✅ Edge cases (empty files, mixed content, etc.)

### Example Test Output
```
tests/test_hooks.py::TestKuzuEnhanceHook::test_validate_input_valid_prompt PASSED
tests/test_hooks.py::TestKuzuEnhanceHook::test_enhance_with_memory_success PASSED
tests/test_hooks.py::TestKuzuLearnHook::test_find_transcript_file_exists PASSED
tests/test_hooks.py::TestKuzuLearnHook::test_store_memory_success PASSED

=================== 30 passed in 0.45s ===================
```

---

## Type Checking with mypy

### Installation
```bash
pip install mypy
```

### Running Type Checks

**Check hooks**:
```bash
mypy .claude/hooks/kuzu_enhance.py .claude/hooks/kuzu_learn.py
```

**Or use the configuration file**:
```bash
mypy --config-file mypy.ini
```

**Check with strict mode**:
```bash
mypy --strict .claude/hooks/kuzu_enhance.py
```

### Configuration

The `mypy.ini` file provides:
- Python 3.11+ type checking
- Moderate strictness (can increase over time)
- Colored, pretty output
- Per-module rules
- Incremental checking with caching

### Example Output
```
Success: no issues found in 2 source files
```

---

## Log Rotation

### Option 1: Automatic Rotation (logrotate)

**System-wide installation** (requires sudo):
```bash
sudo cp .claude/hooks/logrotate.conf /etc/logrotate.d/kuzu-hooks
sudo chmod 644 /etc/logrotate.d/kuzu-hooks
```

**User-specific installation** (no sudo):
```bash
# Copy config to home directory
cp .claude/hooks/logrotate.conf ~/.logrotate.conf

# Add to crontab (runs daily at midnight)
crontab -e
# Add this line:
0 0 * * * /usr/sbin/logrotate ~/.logrotate.conf
```

**Test rotation**:
```bash
logrotate -f ~/.logrotate.conf
```

### Option 2: Manual Rotation Script

**Run manual rotation**:
```bash
.claude/hooks/rotate_logs.sh
```

**Add to crontab for automatic rotation**:
```bash
crontab -e
# Add this line (runs daily at 2 AM):
0 2 * * * /path/to/.claude/hooks/rotate_logs.sh >> /tmp/kuzu_rotation.log 2>&1
```

### Rotation Behavior

**Default settings**:
- Rotate daily
- Keep 7 days of logs
- Compress old logs with gzip
- Skip if log is empty

**Customization**:
Edit `logrotate.conf` to change:
- Rotation frequency (daily, weekly, monthly)
- Number of rotations to keep
- Compression settings
- File size thresholds

---

## Continuous Monitoring

### Watch Logs in Real-Time
```bash
# Both logs
tail -f /tmp/kuzu_enhance.log /tmp/kuzu_learn.log

# Just enhance
tail -f /tmp/kuzu_enhance.log

# Just learn
tail -f /tmp/kuzu_learn.log
```

### Check for Errors
```bash
# Find errors in logs
grep ERROR /tmp/kuzu_*.log

# Count errors
grep -c ERROR /tmp/kuzu_*.log

# Last 10 errors
grep ERROR /tmp/kuzu_*.log | tail -10
```

### Log Statistics
```bash
# Lines in each log
wc -l /tmp/kuzu_*.log

# Log sizes
ls -lh /tmp/kuzu_*.log

# Today's activity
grep "$(date +%Y-%m-%d)" /tmp/kuzu_learn.log | wc -l
```

---

## Environment Configuration

### Available Variables

```bash
# Log directory (default: /tmp)
export KUZU_HOOK_LOG_DIR="/var/log/kuzu"

# Timeouts (in seconds)
export KUZU_ENHANCE_TIMEOUT="2"
export KUZU_STORE_TIMEOUT="5"

# Command path (if not in PATH)
export KUZU_COMMAND="/usr/local/bin/kuzu-memory"

# Memory metadata
export KUZU_HOOK_SOURCE="claude-code-hook"
export KUZU_HOOK_AGENT_ID="assistant"
```

### Example: Custom Setup

```bash
# Create custom log directory
mkdir -p ~/logs/kuzu-hooks

# Configure environment
cat >> ~/.zshrc << 'EOF'
export KUZU_HOOK_LOG_DIR="$HOME/logs/kuzu-hooks"
export KUZU_ENHANCE_TIMEOUT="5"
export KUZU_STORE_TIMEOUT="10"
EOF

# Reload shell
source ~/.zshrc

# Verify
echo $KUZU_HOOK_LOG_DIR
```

---

## Development Workflow

### Before Committing Changes

1. **Run type checks**:
   ```bash
   mypy .claude/hooks/*.py
   ```

2. **Run tests**:
   ```bash
   pytest tests/test_hooks.py -v
   ```

3. **Check test coverage**:
   ```bash
   pytest tests/test_hooks.py --cov=.claude/hooks --cov-report=term-missing
   ```

4. **Format code** (if using black):
   ```bash
   black .claude/hooks/*.py tests/test_hooks.py
   ```

5. **Lint** (if using flake8):
   ```bash
   flake8 .claude/hooks/*.py tests/test_hooks.py
   ```

### CI/CD Integration

**Example GitHub Actions workflow**:
```yaml
name: Hook Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install pytest mypy
      - run: mypy .claude/hooks/*.py
      - run: pytest tests/test_hooks.py -v
```

---

## Troubleshooting

### Tests Failing

**Import errors**:
```bash
# Ensure hooks can be imported
export PYTHONPATH=".claude/hooks:$PYTHONPATH"
pytest tests/test_hooks.py -v
```

**Missing dependencies**:
```bash
pip install pytest pytest-mock
```

### Type Check Issues

**Import errors with mypy**:
- Check that `mypy.ini` has correct paths
- Ensure Python version matches (3.11+)
- Install type stubs: `pip install types-*`

### Log Rotation Not Working

**Check crontab**:
```bash
crontab -l  # List current cron jobs
```

**Test manually**:
```bash
.claude/hooks/rotate_logs.sh
```

**Check permissions**:
```bash
ls -l .claude/hooks/rotate_logs.sh  # Should be executable
chmod +x .claude/hooks/rotate_logs.sh  # Fix if needed
```

---

## Performance Monitoring

### Hook Execution Times

```bash
# Extract execution times from logs
grep "Hook completed" /tmp/kuzu_learn.log | \
  awk '{print $(NF-3), $(NF-2)}' | \
  tail -20

# Average memory size stored
grep "Storing memory" /tmp/kuzu_learn.log | \
  grep -oP '\d+ chars' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "chars"}'
```

### Memory Database Growth

```bash
# Check memory count over time
kuzu-memory status

# See recent additions
kuzu-memory memory recall "claude-code-hook" | head -20
```

---

## Best Practices

### Testing
- ✅ Run tests before committing changes
- ✅ Maintain >80% code coverage
- ✅ Add tests for new features
- ✅ Test edge cases and error conditions

### Type Checking
- ✅ Use type hints for all functions
- ✅ Run mypy before committing
- ✅ Fix type errors, don't ignore them
- ✅ Use `Optional[]` for nullable values

### Logging
- ✅ Use appropriate log levels (INFO, WARNING, ERROR)
- ✅ Log function entry/exit for debugging
- ✅ Include context in error messages
- ✅ Rotate logs regularly to manage disk space

### Security
- ✅ Validate all inputs
- ✅ Set reasonable timeouts
- ✅ Handle errors gracefully
- ✅ Don't log sensitive data

---

## Resources

- **pytest docs**: https://docs.pytest.org/
- **mypy docs**: https://mypy.readthedocs.io/
- **logrotate**: https://linux.die.net/man/8/logrotate
- **Python logging**: https://docs.python.org/3/library/logging.html

---

**Last Updated**: 2025-10-25
**Status**: Production-ready ✅
