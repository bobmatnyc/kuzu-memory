# KuzuMemory Hooks Troubleshooting Guide

**Quick diagnostic guide for Claude Code hooks issues**

---

## 🎯 Quick Diagnosis Checklist

Run these commands in your project directory to diagnose hooks status:

```bash
# 1. Check if database exists
ls -la .kuzu-memory/memorydb/

# 2. Check if hooks are installed
ls -la .claude/hooks/

# 3. Check if settings.local.json exists
ls -la .claude/settings.local.json

# 4. Check memory count
kuzu-memory stats | grep "Total memories"

# 5. Check hook logs (last 10 entries)
tail -10 /tmp/kuzu_enhance.log /tmp/kuzu_learn.log
```

### ✅ Healthy Project Should Show:
- `.kuzu-memory/memorydb/` exists with database files
- `.claude/hooks/` contains `user_prompt_submit.py` and `post_tool_use.py`
- `.claude/settings.local.json` exists with hook configuration
- `kuzu-memory stats` returns memory count
- Hook logs show recent activity

### ❌ Problem Indicators:
- Missing `.claude/settings.local.json` = **Hooks not installed**
- Empty `/tmp/kuzu_*` logs = **Hooks not firing**
- Database exists but no memories from conversations = **Hooks not configured**

---

## 🔍 Understanding: `init` vs `install claude-code`

### Confusion Point

Many users run `kuzu-memory init` and assume hooks are installed. **They are not.**

### What Each Command Does

#### `kuzu-memory init`
**Purpose**: Initialize the memory database only

**Creates**:
- `.kuzu-memory/memorydb/` - Database directory
- `.kuzu-memory/config.yaml` - Configuration file
- `CLAUDE.md` - Instructions for Claude

**Does NOT Create**:
- ❌ `.claude/hooks/` directory
- ❌ `.claude/settings.local.json` (critical for hooks)
- ❌ Hook scripts

**Use Case**: Manual workflow without automatic enhancement

```bash
# What you can do after init only:
kuzu-memory enhance "my prompt"  # Manual command
kuzu-memory learn "some context" # Manual command
kuzu-memory recall "query"       # Manual command
```

---

#### `kuzu-memory install add claude-code`
**Purpose**: Install **both** database **and** Claude Code hooks

**Creates**:
- Everything from `init` (database, config, CLAUDE.md)
- ✅ `.claude/hooks/user_prompt_submit.py` - Enhancement hook
- ✅ `.claude/hooks/post_tool_use.py` - Learning hook
- ✅ `.claude/settings.local.json` - Hook configuration (critical!)

**Use Case**: Automatic workflow with hooks

```bash
# What happens automatically after install:
# - Prompts enhanced without manual commands
# - Learning happens in background
# - No manual kuzu-memory commands needed
```

---

### Quick Reference Table

| Feature | `init` Only | `install add claude-code` |
|---------|-------------|---------------------------|
| Database created | ✅ | ✅ |
| Manual commands work | ✅ | ✅ |
| Automatic prompt enhancement | ❌ | ✅ |
| Automatic learning from conversations | ❌ | ✅ |
| `.claude/settings.local.json` | ❌ | ✅ |
| Hook scripts | ❌ | ✅ |

---

## 🚨 Common Issue: "Hooks Not Working"

### Symptom
- Database exists with memories (usually from git_sync)
- `CLAUDE.md` exists
- Conversations with Claude Code are NOT stored as memories
- No entries in `/tmp/kuzu_learn.log` for this project

### Root Cause
Project was initialized with `kuzu-memory init` but hooks were never installed with `kuzu-memory install add claude-code`.

### The Missing Piece: `.claude/settings.local.json`

This file is **critical** for hooks to work. It tells Claude Code:
1. Where to find the hook scripts
2. What events should trigger hooks
3. How to execute the hooks

**Without this file, hooks will never fire.**

### Diagnosis

```bash
# Check if settings.local.json exists
ls -la .claude/settings.local.json

# If file is missing, hooks are NOT installed
# If file exists, check its contents:
cat .claude/settings.local.json
```

**Expected content**:
```json
{
  "hooks": {
    "UserPromptSubmit": ".claude/hooks/user_prompt_submit.py",
    "PostToolUse": ".claude/hooks/post_tool_use.py"
  }
}
```

### Solution

```bash
# Install Claude Code hooks
cd your-project
kuzu-memory install add claude-code

# Verify installation
ls -la .claude/hooks/
ls -la .claude/settings.local.json

# Test by having a conversation with Claude Code
# Then check logs:
tail -5 /tmp/kuzu_enhance.log
```

---

## 🔧 Installation Scenarios

### Scenario 1: Fresh Project (Recommended Path)

```bash
cd your-project

# ONE COMMAND - does everything
kuzu-memory install add claude-code

# Verifies:
✅ Database created
✅ Hooks installed
✅ Settings configured
✅ CLAUDE.md created
```

---

### Scenario 2: Already Ran `init` (Need to Add Hooks)

```bash
cd your-project

# Database exists but hooks missing
# Run install to add hooks
kuzu-memory install add claude-code

# The installer will:
# - Preserve existing database
# - Add missing hooks
# - Create settings.local.json
# - Not overwrite existing config
```

---

### Scenario 3: Force Reinstall (Hooks Corrupted)

```bash
cd your-project

# Force reinstall everything
kuzu-memory install add claude-code --force

# Creates backup before overwriting
# Backup location: ~/.kuzu-memory-backups/
```

---

### Scenario 4: Multiple Projects

```bash
# Each project needs separate installation
cd project-1
kuzu-memory install add claude-code

cd ../project-2
kuzu-memory install add claude-code

# Each has isolated:
# - Database (.kuzu-memory/memorydb/)
# - Hooks (.claude/hooks/)
# - Configuration (.claude/settings.local.json)
```

---

## 📋 Verification Protocol

After installation, verify hooks are working:

### Step 1: Check Files

```bash
# All these should exist:
ls -la .kuzu-memory/memorydb/      # Database
ls -la .claude/hooks/              # Hook scripts
ls -la .claude/settings.local.json # Hook config
ls -la CLAUDE.md                   # Instructions
```

### Step 2: Check Hook Scripts

```bash
# Hooks should be executable
ls -la .claude/hooks/*.py

# Should show:
# -rwxr-xr-x user_prompt_submit.py
# -rwxr-xr-x post_tool_use.py
```

### Step 3: Test Enhancement Hook

```bash
# Test manually
echo "test prompt" | python3 .claude/hooks/user_prompt_submit.py

# Should output enhanced prompt with context
# If error, hook is broken
```

### Step 4: Test with Claude Code

```bash
# Clear old logs
> /tmp/kuzu_enhance.log
> /tmp/kuzu_learn.log

# Have a conversation with Claude Code
# Ask a technical question about your project

# Check logs immediately after
tail -10 /tmp/kuzu_enhance.log

# Should see:
# === Hook called ===
# Enhancing prompt...
# Enhancement generated...
```

### Step 5: Verify Learning

```bash
# After Claude edits a file, check learn log
tail -10 /tmp/kuzu_learn.log

# Should see learning entries for tool usage
```

---

## 🐛 Troubleshooting Common Issues

### Issue 1: Settings File Exists but Hooks Don't Fire

**Check hook paths in settings.local.json**:
```bash
cat .claude/settings.local.json | jq .hooks
```

**Paths must be relative to project root**:
```json
{
  "hooks": {
    "UserPromptSubmit": ".claude/hooks/user_prompt_submit.py",
    "PostToolUse": ".claude/hooks/post_tool_use.py"
  }
}
```

**Fix wrong paths**:
```bash
kuzu-memory install add claude-code --force
```

---

### Issue 2: Hooks Fire but No Memories Created

**Check if kuzu-memory command is accessible**:
```bash
# Test from hook directory
cd .claude/hooks
which kuzu-memory

# Should return path like:
# /Users/you/.local/bin/kuzu-memory
```

**If not found, install kuzu-memory globally**:
```bash
pipx install kuzu-memory
# Or
pip install kuzu-memory
```

---

### Issue 3: Hook Logs Show Errors

**View full error**:
```bash
tail -50 /tmp/kuzu_enhance.log | grep -A 10 ERROR
```

**Common errors and solutions**:

| Error | Cause | Solution |
|-------|-------|----------|
| `kuzu-memory: command not found` | Not in PATH | Install with pipx |
| `Permission denied` | Hook not executable | `chmod +x .claude/hooks/*.py` |
| `Database not found` | Wrong database path | Check config.yaml |
| `Import error` | Python dependencies missing | `pip install -r requirements.txt` |

---

### Issue 4: Only Git Memories, No Conversation Memories

**Symptom**:
```bash
kuzu-memory stats
# Shows: 7 memories (all from git_sync)
# No memories from actual conversations
```

**Diagnosis**:
```bash
# Check learn log for your project path
grep "/path/to/your/project" /tmp/kuzu_learn.log

# If empty, hooks aren't firing
```

**Solution**:
```bash
# Verify settings.local.json exists
ls -la .claude/settings.local.json

# If missing, install hooks
kuzu-memory install add claude-code

# If exists, check Claude Code is actually using it
# Restart Claude Code application
```

---

## 🎓 Best Practices

### 1. Always Use `install add claude-code` for New Projects

❌ **Don't**:
```bash
kuzu-memory init  # Then manually try to set up hooks
```

✅ **Do**:
```bash
kuzu-memory install add claude-code  # Everything in one command
```

### 2. Verify Installation Immediately

```bash
# Right after installation:
kuzu-memory install status

# Should show:
# ✅ Claude Code: Installed
# ✅ Hooks: Configured
# ✅ Database: Ready
```

### 3. Test Hooks Before Committing

```bash
# Test locally before committing to git
echo "test" | python3 .claude/hooks/user_prompt_submit.py

# Verify output shows enhancement
```

### 4. Document in README

Add to your project README:
```markdown
## AI Assistant Setup

This project uses KuzuMemory for intelligent context:

```bash
# Install KuzuMemory hooks
kuzu-memory install add claude-code
```
```

---

## 🔍 Deep Diagnosis: Why Aren't Hooks Working?

Use this decision tree to diagnose:

```
Is .claude/settings.local.json present?
├─ NO → Run: kuzu-memory install add claude-code
└─ YES
   │
   Does it contain "UserPromptSubmit" and "PostToolUse"?
   ├─ NO → Reinstall: kuzu-memory install add claude-code --force
   └─ YES
      │
      Do hook files exist at specified paths?
      ├─ NO → Reinstall: kuzu-memory install add claude-code --force
      └─ YES
         │
         Are hooks executable (ls -la shows 'x' permission)?
         ├─ NO → Fix: chmod +x .claude/hooks/*.py
         └─ YES
            │
            Does 'which kuzu-memory' return a path?
            ├─ NO → Install: pipx install kuzu-memory
            └─ YES
               │
               Do logs show hook execution?
               ├─ NO → Restart Claude Code application
               └─ YES
                  │
                  Do logs show successful enhancement?
                  ├─ NO → Check logs for errors
                  └─ YES
                     │
                     Are memories being created?
                     ├─ NO → Check database path in config.yaml
                     └─ YES → ✅ Hooks working correctly!
```

---

## 📊 Comparison: Working vs Broken Setup

### ✅ Working Setup

```bash
$ ls -la .claude/
drwxr-xr-x  hooks/
-rw-r--r--  settings.local.json  # ← CRITICAL
-rw-r--r--  CLAUDE.md

$ cat .claude/settings.local.json
{
  "hooks": {
    "UserPromptSubmit": ".claude/hooks/user_prompt_submit.py",
    "PostToolUse": ".claude/hooks/post_tool_use.py"
  }
}

$ tail -5 /tmp/kuzu_enhance.log
2025-10-31 10:15:32 [INFO] === Hook called ===
2025-10-31 10:15:32 [INFO] Enhancing prompt (45 chars)
2025-10-31 10:15:33 [INFO] Enhancement generated (512 chars)
```

### ❌ Broken Setup

```bash
$ ls -la .claude/
-rw-r--r--  CLAUDE.md
# ← Missing settings.local.json!
# ← Missing hooks/ directory!

$ tail -5 /tmp/kuzu_enhance.log
# Empty or no entries for this project

$ kuzu-memory stats
Total memories: 7
# All from git_sync, none from conversations
```

---

## 🚀 Quick Fix Command

If you're unsure of the current state, run this one-liner to fix everything:

```bash
cd your-project && \
kuzu-memory install add claude-code --force && \
kuzu-memory install status && \
echo "Test" | python3 .claude/hooks/user_prompt_submit.py
```

This will:
1. Force reinstall hooks (with backup)
2. Show installation status
3. Test enhancement hook immediately

---

## 📝 Summary

### Key Takeaways

1. **`init` ≠ hooks installed** - You need `install add claude-code`
2. **`.claude/settings.local.json` is critical** - Without it, hooks never fire
3. **Each project needs separate installation** - Hooks are not global
4. **Verify after installation** - Don't assume it worked, test it
5. **Check logs for debugging** - `/tmp/kuzu_*.log` shows what's happening

### Installation Command Reference

```bash
# Fresh project - recommended
kuzu-memory install add claude-code

# Already ran init - add hooks
kuzu-memory install add claude-code

# Hooks corrupted - reinstall
kuzu-memory install add claude-code --force

# Check status
kuzu-memory install status

# View available installers
kuzu-memory install list
```

---

## 📚 Related Documentation

- **[Claude Code Hooks Setup](CLAUDE_CODE_HOOKS_SETUP.md)** - Detailed hook guide
- **[Claude Setup Guide](CLAUDE_SETUP.md)** - Complete integration guide
- **[Hooks Verification Report](hooks-verification-report.md)** - Technical verification details
- **[Installation Comparison](INSTALLATION_COMPARISON.md)** - Installation method comparison

---

**Last Updated**: 2025-10-31
**KuzuMemory Version**: 1.4.36+
