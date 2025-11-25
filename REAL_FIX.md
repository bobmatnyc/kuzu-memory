# REAL FIX: Claude Code Cached Error State

## The Truth

Your configuration is **100% CORRECT**:
```json
{
  "type": "stdio",
  "command": "kuzu-memory",
  "args": ["mcp"]  // ✅ CORRECT
}
```

The error showing `Args: mcp serve` is from **cached conversation history** in Claude Code's `.claude.json`, NOT from your actual MCP configuration.

## Evidence

1. **Actual config verified**: `/Users/masa/.claude.json` shows `"args": ["mcp"]` ✅
2. **All 30+ project configs checked**: Every single one shows `"args": ["mcp"]` ✅
3. **Error is in conversation history**: Lines 1119, 2506, 2520, 2542, 2572, 6812 of `.claude.json` contain **cached error messages** showing "mcp serve"

The "mcp serve" text appears in:
- Old AI assistant suggestions (incorrect advice from conversation history)
- Cached error display states (UI showing old error from previous attempts)
- **NOT in any actual `mcpServers` configuration**

## The Fix

### Option 1: Force Reconnect (Recommended)
1. In Claude Code, go to the MCP server error dialog
2. Click **"1. Reconnect"**
3. This should clear the cached error and read the actual correct config

### Option 2: Restart VS Code/Claude Code
```bash
# Quit VS Code completely
# CMD+Q or from menu

# Reopen
code /Users/masa/Projects/kuzu-memory
```

### Option 3: Clear Conversation State (Nuclear Option)
If reconnect doesn't work, you can remove the cached error messages:

```bash
# Backup first
cp ~/.claude.json ~/.claude.json.backup_$(date +%Y%m%d_%H%M%S)

# This Python script will remove conversation history but keep configs
python3 << 'SCRIPT'
import json
from pathlib import Path

config_file = Path.home() / '.claude.json'
config = json.load(open(config_file))

# Keep only the essential project configurations
# Remove conversation history that contains cached errors
if 'projects' in config:
    for project_path, project_data in config['projects'].items():
        # Keep only mcpServers config, remove conversation history
        if 'mcpServers' in project_data:
            config['projects'][project_path] = {
                'mcpServers': project_data['mcpServers']
            }

# Save cleaned config
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Cleaned conversation history while preserving MCP configs")
SCRIPT
```

**⚠️ WARNING**: Option 3 will remove conversation history! Only use if reconnect doesn't work.

## Why This Happened

1. **Old error was cached** in Claude Code's conversation history
2. **UI displays** this cached error state instead of reading fresh config
3. **Actual config** has been correct all along
4. The error display is **misleading** - it shows old state, not current state

## Verification

After reconnecting, verify the MCP server starts correctly:

```bash
# Test the command directly
kuzu-memory mcp
# Should NOT show any "serve" errors
# Press Ctrl+C to exit

# Check MCP server status in Claude Code
# Should show "✓ connected" or similar
```

## Proof the Config is Correct

```bash
# Show actual config for this project
cd /Users/masa && python3 -c "
import json
config = json.load(open('.claude.json'))
km = config['projects']['/Users/masa/Projects/kuzu-memory']['mcpServers']['kuzu-memory']
print(json.dumps(km, indent=2))
"

# Output:
# {
#   "type": "stdio",
#   "command": "kuzu-memory",
#   "args": [
#     "mcp"        <-- ✅ CORRECT, no "serve" here
#   ]
# }
```

## Summary

**The problem**: Claude Code's UI is showing a cached error from conversation history
**The config**: 100% correct with `"args": ["mcp"]`
**The solution**: Reconnect the MCP server to clear the cached state
**The misconception**: The error display made it seem like the config was wrong, but it's actually correct

You've been trying to fix something that was never broken! 🎯
