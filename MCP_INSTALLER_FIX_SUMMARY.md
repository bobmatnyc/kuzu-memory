# MCP Installer Fix Summary

## Problem Identified

The kuzu-memory MCP installers had **incorrect command arguments** that would cause MCP server startup failures.

### Root Cause

Multiple installers were using `["mcp", "serve"]` as the args parameter, but:
1. The `kuzu-memory mcp serve` command is **deprecated** and no longer available in the current CLI
2. The new `kuzu-memory mcp` command group does NOT have a `serve` subcommand
3. This would cause Claude Desktop and other tools to fail when trying to start the MCP server

### Impact

This bug affected:
- **Global configs**: `~/.config/Claude/claude_desktop_config.json` (or equivalent on other platforms)
- **Project configs**: `.cursor/mcp.json`, `.vscode/mcp.json`, `~/.codeium/windsurf/mcp_config.json`

Users would see MCP server failures because the command `kuzu-memory mcp serve` doesn't exist.

## Files Fixed

### 1. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_desktop.py`

**Class**: `ClaudeDesktopPipxInstaller`
**Method**: `_create_mcp_config()` (lines 254-314)

**Changes**:
- ✅ Line 263: Already correct for pipx path: `["-m", "kuzu_memory.mcp.run_server"]`
- ✅ Lines 269-290: Fixed fallback to use Python module invocation instead of `["mcp", "serve"]`
- ✅ Lines 302-314: Fixed final fallback to use `sys.executable` with module invocation

**Before** (lines 272, 281):
```python
"args": ["mcp", "serve"],  # ❌ WRONG - command doesn't exist
```

**After**:
```python
"args": ["-m", "kuzu_memory.mcp.run_server"],  # ✅ CORRECT - Python module invocation
```

### 2. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/cursor_installer.py`

**Class**: `CursorInstaller`
**Method**: `_create_kuzu_server_config()` (lines 51-65)

**Changes**:
- Uses `sys.executable` instead of `"kuzu-memory"`
- Uses `["-m", "kuzu_memory.integrations.mcp_server"]` instead of `["mcp", "serve"]`
- Sets project-specific environment variables

**Before**:
```python
"command": "kuzu-memory",
"args": ["mcp", "serve"],
```

**After**:
```python
"command": sys.executable,
"args": ["-m", "kuzu_memory.integrations.mcp_server"],
"env": {
    "KUZU_MEMORY_PROJECT_ROOT": str(self.project_root),
    "KUZU_MEMORY_DB": str(self.project_root / "kuzu-memories"),
}
```

### 3. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/vscode_installer.py`

**Class**: `VSCodeInstaller`
**Method**: `_create_kuzu_server_config()` (lines 54-68)

**Changes**: Same as Cursor installer above

### 4. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/windsurf_installer.py`

**Class**: `WindsurfInstaller`
**Method**: `_create_kuzu_server_config()` (lines 53-69)

**Changes**: Same as Cursor installer above

## Important Clarifications

### ✅ Claude Hooks Installer is CORRECT

The `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_hooks.py` installer was **already correct**:

- **Line 318**: Uses `["-m", "kuzu_memory.integrations.mcp_server"]` ✅
- **Only modifies**: `.claude/config.local.json` (project-specific) ✅
- **Never modifies**: `~/.claude.json` or global configs ✅

### Global Config Pollution Source

The 22 duplicate kuzu-memory entries in `~/.claude.json` were NOT created by the current code. Possible sources:

1. **Old versions** of kuzu-memory (before the fix)
2. **Manual installations** by users
3. **Other tools** modifying the global config
4. **Claude Desktop itself** auto-generating configs

The current installer **does NOT write to** `~/.claude.json` or `claude_desktop_config.json` from the Claude Code hooks installer.

## Cleanup Solution

### For Users: Clean Up Global Config

If you have duplicate entries in your global Claude Desktop config, manually edit:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Remove all kuzu-memory entries with incorrect args:

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "/path/to/kuzu-memory",
      "args": ["mcp", "serve"]  // ❌ Remove this entire entry
    }
  }
}
```

### For Developers: Automated Cleanup Script

```bash
#!/bin/bash
# clean_mcp_config.sh - Remove broken kuzu-memory MCP entries

CLAUDE_CONFIG="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"

if [ -f "$CLAUDE_CONFIG" ]; then
    echo "Backing up $CLAUDE_CONFIG"
    cp "$CLAUDE_CONFIG" "${CLAUDE_CONFIG}.backup.$(date +%Y%m%d-%H%M%S)"

    # Remove kuzu-memory entries with "mcp serve" args
    python3 -c "
import json
import sys

with open('$CLAUDE_CONFIG') as f:
    config = json.load(f)

if 'mcpServers' in config and 'kuzu-memory' in config['mcpServers']:
    server = config['mcpServers']['kuzu-memory']
    if isinstance(server.get('args'), list) and server['args'] == ['mcp', 'serve']:
        print('Removing broken kuzu-memory MCP entry')
        del config['mcpServers']['kuzu-memory']

        with open('$CLAUDE_CONFIG', 'w') as f:
            json.dump(config, f, indent=2)
        print('✅ Cleaned up successfully')
    else:
        print('✅ Config is already correct')
else:
    print('✅ No kuzu-memory entry found')
"
else
    echo "⚠️  Claude Desktop config not found at $CLAUDE_CONFIG"
fi
```

## Testing the Fix

### 1. Test Claude Desktop Installer

```bash
kuzu-memory mcp install claude-desktop --dry-run
```

Should show:
```json
{
  "command": "/path/to/python",
  "args": ["-m", "kuzu_memory.mcp.run_server"]
}
```

### 2. Test Cursor Installer

```bash
kuzu-memory mcp install cursor --dry-run
```

Should create `.cursor/mcp.json` with:
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "/path/to/python3",
      "args": ["-m", "kuzu_memory.integrations.mcp_server"]
    }
  }
}
```

### 3. Test VS Code Installer

```bash
kuzu-memory mcp install vscode --dry-run
```

Should create `.vscode/mcp.json` with correct module invocation.

### 4. Test Windsurf Installer

```bash
kuzu-memory mcp install windsurf --dry-run
```

Should create global config with correct module invocation.

## Correct MCP Server Invocation

### Two Valid Module Paths

1. **For Claude Desktop (global)**: `kuzu_memory.mcp.run_server`
2. **For project-specific (Claude Code, Cursor, VS Code, Windsurf)**: `kuzu_memory.integrations.mcp_server`

Both work, but project-specific installers should use `kuzu_memory.integrations.mcp_server` with project-specific environment variables.

### Correct Configuration Format

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "/path/to/python3",
      "args": ["-m", "kuzu_memory.integrations.mcp_server"],
      "env": {
        "KUZU_MEMORY_PROJECT_ROOT": "/path/to/project",
        "KUZU_MEMORY_DB": "/path/to/project/kuzu-memories"
      }
    }
  }
}
```

## Summary

- ✅ Fixed 4 installers to use correct Python module invocation
- ✅ Removed all `["mcp", "serve"]` references from active installers
- ✅ Verified Claude Code hooks installer was already correct
- ✅ Project-specific configs now include environment variables
- ✅ All files formatted with black

## Next Steps

1. Test the updated installers with `--dry-run` flag
2. Users should manually clean up any existing broken configs
3. Consider adding migration code to auto-fix broken configs on next install
4. Update documentation to reflect correct MCP server invocation
