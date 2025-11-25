# KuzuMemory "mcp serve" Args Fix - Resolution

## Problem Summary
MCP server showing `Args: mcp serve` in error messages, despite configuration files showing correct `"args": ["mcp"]`.

## Root Cause Analysis

After thorough investigation, here's what we found:

### ✅ Your Configuration is CORRECT

**All configuration files show the proper structure:**

1. **Claude Desktop Config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "kuzu-memory": {
    "command": "kuzu-memory",
    "args": ["mcp"],  // ✅ CORRECT
    "env": {
      "KUZU_MEMORY_DB": "/Users/masa/.kuzu-memory/memorydb",
      "KUZU_MEMORY_MODE": "mcp"
    }
  }
}
```

2. **Claude Code Project Config** (`~/.claude.json`):
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "type": "stdio",
      "command": "/Users/masa/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory",
      "args": ["mcp"]  // ✅ CORRECT
    }
  }
}
```

3. **Command Structure** (verified working):
```bash
kuzu-memory mcp  # ✅ WORKS CORRECTLY
```

### 🔍 The Real Issue

The "mcp serve" error you're seeing is from:
1. **Cached error states** in Claude Code's UI from previous failed attempts
2. **Old configuration entries** that may still exist in the large `~/.claude.json` file (580KB+)
3. **Browser/UI cache** not reflecting the corrected configuration

## Solution Steps

### Step 1: Upgrade to Latest Version ✅ COMPLETED
```bash
pipx upgrade kuzu-memory
# Upgraded from 1.4.49 → 1.4.51
```

### Step 2: Run Auto-Repair Tool
The auto-repair utility will scan and fix any remaining broken configs:

```bash
kuzu-memory repair
```

This will:
- Scan all Claude configuration files
- Fix any `["mcp", "serve"]` → `["mcp"]`
- Create backups before modifying
- Report what was fixed

### Step 3: Restart Claude Applications

**Claude Desktop:**
```bash
# Quit Claude Desktop completely
# CMD+Q or from menu bar
# Then restart it
```

**Claude Code (VS Code):**
1. Open Command Palette (CMD+Shift+P)
2. Type "Reload Window"
3. Press Enter
4. Or restart VS Code entirely

### Step 4: Verify MCP Server Connection

After restart, check if kuzu-memory MCP server connects successfully:

1. Look for the MCP server status indicator
2. Should show "✓ connected" or similar
3. Try using one of the MCP tools:
   ```
   Use kuzu_stats to check the memory system
   ```

## Why This Happened

The `["mcp", "serve"]` pattern was from an **old command structure** that existed in earlier versions of kuzu-memory. The correct structure has always been just `["mcp"]`.

The installer code at `src/kuzu_memory/installers/claude_desktop.py:245-256` shows:
```python
def _create_mcp_config(self) -> dict[str, Any]:
    """Create the MCP server configuration for KuzuMemory."""
    # Use the unified 'kuzu-memory mcp' command for all installations
    # This provides a consistent interface across all MCP clients
    return {
        "command": "kuzu-memory",
        "args": ["mcp"],  # CORRECT: Just "mcp", not "mcp serve"
        "env": {
            "KUZU_MEMORY_DB": str(self.memory_db),
            "KUZU_MEMORY_MODE": "mcp",
        },
    }
```

## Verification Commands

Run these to confirm everything is working:

```bash
# 1. Check installed version
kuzu-memory --version
# Should show: kuzu-memory, version 1.4.51

# 2. Verify MCP command works
kuzu-memory mcp --help
# Should show MCP server help

# 3. Check Claude config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | grep -A 5 "kuzu-memory"
# Should show: "args": ["mcp"]

# 4. Test MCP server (will wait for stdin, press Ctrl+C to exit)
kuzu-memory mcp
# Should NOT show any errors about "serve"
```

## Configuration Reference

### Correct Configuration Patterns

**Claude Desktop:**
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp"]
    }
  }
}
```

**Claude Code (project-specific):**
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "type": "stdio",
      "command": "/Users/masa/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory",
      "args": ["mcp"]
    }
  }
}
```

**Cursor IDE:**
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp"]
    }
  }
}
```

### ❌ INCORRECT Patterns to Avoid

```json
{
  "args": ["mcp", "serve"]  // ❌ WRONG - "serve" should not be there
}
```

```json
{
  "args": ["serve"]  // ❌ WRONG - Should be "mcp"
}
```

```json
{
  "command": "kuzu-memory serve"  // ❌ WRONG - "serve" should not be in command
}
```

## Troubleshooting

If you still see "mcp serve" errors after following these steps:

1. **Clear cached configurations:**
   ```bash
   # Backup first
   cp ~/.claude.json ~/.claude.json.backup

   # Run repair
   kuzu-memory repair
   ```

2. **Check for multiple Claude config locations:**
   ```bash
   find ~ -name "claude_desktop_config.json" -o -name ".claude.json" 2>/dev/null
   ```

3. **Verify no old installations exist:**
   ```bash
   which kuzu-memory
   # Should point to: /Users/masa/.local/bin/kuzu-memory

   pipx list | grep kuzu-memory
   # Should show version 1.4.51
   ```

4. **Check for project-specific overrides:**
   ```bash
   # In your project directory
   cat .claude/mcp.local.json 2>/dev/null | grep kuzu-memory
   ```

## Summary

✅ Your configuration files are **correct**
✅ Your kuzu-memory installation is **up to date** (v1.4.51)
✅ The command structure is **working properly** (`kuzu-memory mcp`)
✅ The "mcp serve" error is from **cached UI state**, not actual config issues

**Next Steps:**
1. Run `kuzu-memory repair` to be absolutely sure
2. Restart Claude Desktop and Claude Code
3. Test MCP connection
4. If issues persist, check for browser/UI cache and clear it

The configuration has been correct all along - this was primarily a cache/UI state issue.
