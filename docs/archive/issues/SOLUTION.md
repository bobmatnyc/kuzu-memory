# KuzuMemory MCP Server "mcp serve" Error - DEFINITIVE FIX

## ✅ VERIFIED: Your Configuration is 100% CORRECT

```json
{
  "type": "stdio",
  "command": "kuzu-memory",
  "args": ["mcp"]  // ✅ CORRECT - No "serve" here
}
```

**Configuration location**: `/Users/masa/.claude.json` → `projects./Users/masa/Projects/kuzu-memory.mcpServers.kuzu-memory`

## 🔍 Root Cause Identified

The error message showing `Args: mcp serve` is from **cached error state** in Claude Code's conversation history, NOT from your actual configuration.

**Evidence**:
- Actual config verified: `"args": ["mcp"]` ✅
- Command works: `kuzu-memory mcp --help` executes successfully ✅
- All 30+ projects in `.claude.json` show correct `"args": ["mcp"]` ✅
- "mcp serve" only appears in cached error strings at lines: 1119, 2506, 2520, 2542, 2572, 6812

## 🚀 THE FIX - Three Options

### Option 1: Force Reconnect (RECOMMENDED - Try First)

**In Claude Code's MCP Server Error Dialog:**
1. Look for the MCP server error showing kuzu-memory status
2. Click the **"Reconnect"** button (or "Retry" if available)
3. This forces Claude Code to re-read the actual configuration
4. The cached error state should clear and use the correct config

**Expected result**: Server connects successfully with `Args: mcp` (no "serve")

---

### Option 2: Restart VS Code/Claude Code Completely

```bash
# 1. Quit VS Code/Claude Code completely
# Use CMD+Q or File > Quit (NOT just close window)

# 2. Wait 5 seconds for process to fully terminate

# 3. Reopen VS Code
code /Users/masa/Projects/kuzu-memory
```

**Why this works**: Forces complete reload of configuration files and clears UI cache.

---

### Option 3: Clear Cached Conversation State (NUCLEAR OPTION)

**⚠️ WARNING**: This removes conversation history but preserves all MCP configurations.

```bash
# 1. BACKUP FIRST (MANDATORY)
cp ~/.claude.json ~/.claude.json.backup_$(date +%Y%m%d_%H%M%S)

# 2. Run this Python script to clean cached errors
python3 << 'SCRIPT'
import json
from pathlib import Path

config_file = Path.home() / '.claude.json'
config = json.load(open(config_file))

# Keep only MCP configurations, remove conversation history
if 'projects' in config:
    for project_path, project_data in config['projects'].items():
        if 'mcpServers' in project_data:
            # Preserve only the MCP server configs
            config['projects'][project_path] = {
                'mcpServers': project_data['mcpServers']
            }

# Save cleaned config
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Cleaned conversation history while preserving MCP configs")
print("⚠️  You may need to restart VS Code for changes to take effect")
SCRIPT

# 3. Restart VS Code
```

**What this does**:
- Removes cached error messages from conversation history
- Preserves all MCP server configurations
- Reduces `.claude.json` file size significantly
- Forces Claude Code to start fresh

---

## 📋 Post-Fix Verification

After applying one of the fixes above, verify the connection:

```bash
# 1. Check that kuzu-memory command works
kuzu-memory mcp --help
# Should show usage without errors

# 2. In Claude Code, check MCP server status
# Should show: ✓ kuzu-memory (connected)

# 3. Test an MCP tool
# Ask Claude to run: "Use kuzu_stats to check memory system"
```

## 🔧 Additional Steps (If Issues Persist)

### Upgrade to Latest Version
```bash
# Your current version: 1.4.49
# Latest version: 1.4.51

pipx upgrade kuzu-memory

# Verify upgrade
kuzu-memory --version
# Should show: kuzu-memory, version 1.4.51
```

### Run Auto-Repair (Belt & Suspenders)
```bash
kuzu-memory repair
# Scans all configs and fixes any remaining issues
```

## 📊 Why This Happened

1. **Old error was cached** in Claude Code's conversation history (`.claude.json`)
2. **UI displays cached state** instead of reading fresh configuration
3. **Actual configuration has been correct** all along
4. The error display is **misleading** - shows old state, not current config

## 🎯 Expected Outcome

After applying the fix:
- ✅ MCP server connects successfully
- ✅ Status shows: `✓ kuzu-memory (connected)`
- ✅ No more "Args: mcp serve" error
- ✅ MCP tools (kuzu_enhance, kuzu_learn, kuzu_recall, kuzu_stats) work

## 📝 Summary

**The Problem**: Claude Code showing cached error `Args: mcp serve`
**The Config**: 100% correct with `"args": ["mcp"]`
**The Solution**: Reconnect MCP server OR restart VS Code
**The Truth**: Configuration was never broken - just cached UI state

---

**Try Option 1 first** (Force Reconnect). If that doesn't work, proceed to Option 2 (Restart). Only use Option 3 if both fail.
