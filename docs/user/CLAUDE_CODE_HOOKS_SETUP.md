# Claude Code Hooks Setup Guide

## Overview

Claude Code hooks allow KuzuMemory to automatically enhance your prompts and learn from conversations **in the background**, without you having to manually run commands. This guide will help you set up hooks properly.

## What Are Claude Code Hooks?

Claude Code hooks are **event-driven triggers** that execute Python scripts automatically when certain events occur:

- **`UserPromptSubmit`**: Fires when you submit a prompt to Claude
- **`PostToolUse`**: Fires after Claude uses a tool (like editing a file)
- **`Stop`**: Fires when you stop Claude's response

## Quick Setup (2 Minutes)

### 1. Install the Hooks

```bash
# From your project directory
kuzu-memory install add claude-code

# Or to reinstall/update
kuzu-memory install add claude-code --force
```

This creates:
- `.claude/hooks/user_prompt_submit.py` - Enhances prompts before sending
- `.claude/hooks/post_tool_use.py` - Learns from tool usage
- `.claude/CLAUDE.md` - Instructions for Claude Code

### 2. Verify Installation

```bash
# Check if hooks exist
ls -la .claude/hooks/

# You should see:
# user_prompt_submit.py
# post_tool_use.py
```

### 3. Test the Hooks

Open Claude Code in your project and ask a technical question:

```
You: "How do I implement authentication in this project?"
```

**What happens automatically**:
1. `UserPromptSubmit` hook fires
2. KuzuMemory enhances your prompt with project context
3. Claude receives enhanced prompt with memories
4. You get better, project-specific answers

## How It Works

### Event Flow Diagram

```
User types prompt
        ↓
[UserPromptSubmit Hook]
        ↓
KuzuMemory enhances with context (<100ms)
        ↓
Enhanced prompt → Claude
        ↓
Claude responds
        ↓
[PostToolUse Hook]
        ↓
KuzuMemory learns from changes (async)
        ↓
Done
```

### Key Features

✅ **Automatic**: No manual commands needed
✅ **Fast**: <100ms enhancement overhead
✅ **Smart Deduplication**: No duplicate memories
✅ **Async Learning**: Non-blocking background storage
✅ **Type Safe**: Full Python type hints

## Hook Details

### UserPromptSubmit Hook

**Purpose**: Enhance prompts with project context before sending to Claude

**File**: `.claude/hooks/user_prompt_submit.py`

**What it does**:
1. Receives your original prompt
2. Calls `kuzu-memory enhance` to add context
3. Returns enhanced prompt to Claude
4. Uses SHA256 deduplication (5-minute TTL)

**Example**:

```python
# Original prompt
"How do I add logging?"

# Enhanced prompt (automatic)
"How do I add logging?

[Relevant context from project memories:
- Project uses Python logging with rotating file handlers
- Logs stored in .kuzu-memory/logs/
- Standard format: timestamp, level, message
]"
```

**Performance**: ~50-100ms per prompt

### PostToolUse Hook

**Purpose**: Learn from file changes and tool usage

**File**: `.claude/hooks/post_tool_use.py`

**What it does**:
1. Detects when Claude edits/creates files
2. Extracts meaningful changes
3. Stores as memories asynchronously
4. Fires in background (non-blocking)

**Example**:

When Claude edits `auth.py` to add OAuth:
```python
# Automatically learned
"Implemented OAuth2 authentication in auth.py with Google provider support"
```

**Performance**: Non-blocking (fires and forgets)

## Configuration

### Default Settings

Hooks use these defaults:
- **Max memories per enhancement**: 10
- **Deduplication TTL**: 5 minutes
- **Format**: Plain text (for Claude)
- **Learning**: Async with `--quiet` flag

### Customization

Edit the hook files directly:

```python
# .claude/hooks/user_prompt_submit.py

# Change max memories
max_memories = 15  # Default: 10

# Disable deduplication
use_deduplication = False  # Default: True

# Change TTL
dedup_ttl_seconds = 300  # Default: 300 (5 minutes)
```

### Project-Specific Settings

Create `.kuzu-memory/config.yaml`:

```yaml
hooks:
  user_prompt_submit:
    enabled: true
    max_memories: 10
    deduplication_ttl: 300

  post_tool_use:
    enabled: true
    async_learning: true
```

## Troubleshooting

### Issue: Hooks Not Firing

**Check 1: File Permissions**
```bash
# Hooks must be executable
chmod +x .claude/hooks/*.py
```

**Check 2: Python Path**
```bash
# Hooks use system Python
which python3
# Should be /usr/bin/python3 or similar
```

**Check 3: Hook Script Syntax**
```bash
# Test hook directly
python3 .claude/hooks/user_prompt_submit.py
```

### Issue: Slow Enhancement

**Symptom**: Claude takes >1 second to respond

**Solution**: Reduce max_memories
```python
# In user_prompt_submit.py
max_memories = 5  # Reduce from 10
```

**Check Database Size**:
```bash
kuzu-memory stats
# If >10k memories, consider cleanup
```

### Issue: Duplicate Memories

**Symptom**: Same memory stored multiple times

**Solution**: Verify deduplication is enabled
```python
# In user_prompt_submit.py
use_deduplication = True  # Should be True

# Check dedup cache
ls -la /tmp/kuzu-memory-dedup-*.json
```

### Issue: No Learning from Tool Use

**Check Hook File**:
```bash
# Verify post_tool_use.py exists
ls -la .claude/hooks/post_tool_use.py

# Test manually
echo '{"tool": "Edit", "path": "/test.py"}' | \
  python3 .claude/hooks/post_tool_use.py
```

## Advanced Usage

### Disable Hooks Temporarily

```bash
# Rename hooks to disable
mv .claude/hooks/user_prompt_submit.py \
   .claude/hooks/user_prompt_submit.py.disabled

# Re-enable
mv .claude/hooks/user_prompt_submit.py.disabled \
   .claude/hooks/user_prompt_submit.py
```

### Custom Hook Logic

You can modify hooks to add custom behavior:

```python
# .claude/hooks/user_prompt_submit.py

# Add custom filtering
if "skip-enhancement" in original_prompt.lower():
    return original_prompt  # Don't enhance

# Add project-specific context
if is_backend_question(original_prompt):
    extra_context = "Project uses FastAPI + PostgreSQL"
    return f"{enhanced_prompt}\n\n{extra_context}"
```

### Hook Logs

Hooks write to stderr (visible in Claude Code logs):

```python
import sys
print(f"Enhanced prompt with {memory_count} memories", file=sys.stderr)
```

View logs:
```bash
# macOS
~/Library/Application Support/Claude/logs/

# Linux
~/.config/Claude/logs/
```

## Best Practices

### 1. Keep Hooks Simple

❌ **Don't**:
```python
# Complex logic that could fail
result = call_external_api()
process_with_ml_model(result)
store_in_database(result)
```

✅ **Do**:
```python
# Simple, fast enhancement
enhanced = subprocess.run(['kuzu-memory', 'enhance', prompt])
return enhanced.stdout
```

### 2. Handle Errors Gracefully

❌ **Don't**:
```python
enhanced = enhance_prompt(prompt)  # Crashes if fails
return enhanced
```

✅ **Do**:
```python
try:
    enhanced = enhance_prompt(prompt)
    return enhanced
except Exception as e:
    print(f"Enhancement failed: {e}", file=sys.stderr)
    return original_prompt  # Fallback
```

### 3. Performance First

- Keep enhancement <100ms
- Use async for learning
- Cache when possible
- Deduplicate aggressively

### 4. Test Before Deploying

```bash
# Test enhancement
echo "test prompt" | python3 .claude/hooks/user_prompt_submit.py

# Time performance
time echo "test" | python3 .claude/hooks/user_prompt_submit.py
```

## Monitoring

### Check Hook Performance

```bash
# View enhancement stats
kuzu-memory stats

# Check recent enhancements
kuzu-memory query "enhanced prompt" --limit 10
```

### Verify Deduplication

```bash
# Check dedup cache files
ls -la /tmp/kuzu-memory-dedup-*.json

# Count entries
cat /tmp/kuzu-memory-dedup-*.json | jq 'length'
```

### Monitor Memory Growth

```bash
# Track database size over time
watch -n 60 'kuzu-memory stats | grep "Total memories"'
```

## Migration from Manual Commands

### Before (Manual)
```bash
# You had to run these manually
kuzu-memory enhance "How do I deploy?"
kuzu-memory learn "We use Docker for deployment" --quiet
```

### After (Automatic with Hooks)
```bash
# Just talk to Claude - hooks handle everything
# No manual commands needed!
```

## FAQ

### Q: Do hooks work with all Claude Code versions?

A: Yes, hooks work with Claude Code v0.1.0+

### Q: Can I use hooks with other AI editors?

A: Hooks are Claude Code-specific. For other editors:
- **Cursor**: Use Cursor-specific integration
- **VS Code**: Use MCP integration
- **Windsurf**: Use Windsurf-specific integration

### Q: How much does enhancement slow down responses?

A: Typically 50-100ms. Imperceptible in normal use.

### Q: Can hooks access the internet?

A: Yes, but avoid it. Keep hooks fast and local.

### Q: What if I have multiple projects?

A: Each project has its own `.claude/hooks/` directory. Hooks are project-specific.

### Q: Can I share hooks across projects?

A: Not recommended. Each project should have its own hooks with project-specific logic.

## Example: Complete Setup Workflow

```bash
# 1. Navigate to your project
cd ~/Projects/my-app

# 2. Install KuzuMemory
pip install kuzu-memory

# 3. Initialize project
kuzu-memory init

# 4. Install Claude Code hooks
kuzu-memory install add claude-code

# 5. Verify installation
ls -la .claude/hooks/
# Should see: user_prompt_submit.py, post_tool_use.py

# 6. Test with Claude Code
# Open Claude Code and ask a question
# Hooks will automatically enhance your prompts!

# 7. Monitor performance
kuzu-memory stats
```

## Next Steps

- **Customize hooks**: Edit `.claude/hooks/*.py` for your needs
- **Monitor performance**: Run `kuzu-memory stats` regularly
- **Learn more**: See [CLAUDE.md](../CLAUDE.md) for detailed usage
- **Troubleshoot**: Check logs in Claude Code if issues arise

## Resources

- **Main Docs**: [README.md](../README.md)
- **Claude Code Docs**: https://docs.claude.com/claude-code
- **Hook Examples**: `.claude/hooks/` in this project
- **Issue Tracker**: https://github.com/bobmatnyc/kuzu-memory/issues

---

**Generated by KuzuMemory Claude Code Hooks Installer v1.4.0+**
