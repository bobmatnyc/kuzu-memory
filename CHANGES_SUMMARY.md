# KuzuMemory: Coding Tools Only - Changes Summary

## Date: 2025-01-25

## What Was Changed

### 1. Claude Desktop Support Removed
**Status**: ✅ Complete in source code, will take effect in next release

**Code Changes**:
- Removed `"claude-desktop"` from `AVAILABLE_INTEGRATIONS` in `install_unified.py`
- Commented out `SmartClaudeDesktopInstaller` registration in `registry.py`
- Updated install command help text to remove Claude Desktop references
- Added note: "claude-desktop is no longer supported. Use claude-code instead"

**Files Modified**:
- `src/kuzu_memory/cli/install_unified.py`
- `src/kuzu_memory/installers/registry.py`

**Git Commits**:
```
7f719e6 refactor: remove Claude Desktop support, focus on coding tools only
7b0f735 docs: add troubleshooting guides for MCP server cached error state
```

### 2. Configuration Cleanup
**Status**: ✅ Complete

**Configuration Changes**:
- Removed `kuzu-memory` entry from `~/Library/Application Support/Claude/claude_desktop_config.json`
- Kept other MCP servers intact (mcp-ticketer, mcp-skillkit, mcp-vector-search)

**Before**:
```json
{
  "mcpServers": {
    "mcp-ticketer": {...},
    "kuzu-memory": {...},  // ← REMOVED
    "mcp-skillkit": {...},
    "mcp-vector-search": {...}
  }
}
```

**After**:
```json
{
  "mcpServers": {
    "mcp-ticketer": {...},
    "mcp-skillkit": {...},
    "mcp-vector-search": {...}
  }
}
```

### 3. Documentation Created
**Status**: ✅ Complete

**New Documentation Files**:
1. **CODING_TOOLS_ONLY.md** (196 lines)
   - Explains rationale for removing Claude Desktop support
   - Lists supported platforms (coding tools only)
   - Provides migration guide
   - Documents technical changes

2. **SOLUTION.md** (147 lines)
   - Definitive fix for "mcp serve" cached error issue
   - Three options: reconnect, restart, nuclear
   - Verification steps

3. **REAL_FIX.md** (128 lines)
   - Explains that configs are correct
   - Error is from cached UI state
   - Evidence and proof

4. **MCP_SERVE_FIX_SOLUTION.md** (250 lines)
   - Comprehensive troubleshooting guide
   - Root cause analysis
   - Configuration reference

## Current State

### Source Code
✅ Changes committed and ready for next release:
- Claude Desktop removed from available integrations
- Registry no longer registers Claude Desktop installers
- Install command help text updated

### Installed Package
⚠️ Currently installed version (1.4.49) still includes Claude Desktop:
- The changes above are in source code only
- Will take effect when package is rebuilt and installed
- Current installation still has old code at `/Users/masa/.local/pipx/venvs/kuzu-memory/`

### Configuration Files
✅ Claude Desktop config cleaned:
- `kuzu-memory` entry removed from `claude_desktop_config.json`
- Other MCP servers preserved

## Next Steps

### For Development
1. **Test the changes**:
   ```bash
   # Install from source to test
   cd /Users/masa/Projects/kuzu-memory
   pip install -e .

   # Verify claude-desktop is not available
   kuzu-memory install claude-desktop
   # Should show error: "No installer found for: claude-desktop"
   ```

2. **Increment version** (for release):
   ```bash
   # Update version in pyproject.toml
   # Currently: version = "1.4.51"
   # Next: version = "1.5.0" (minor bump for feature removal)
   ```

3. **Build and publish** (when ready):
   ```bash
   # Build package
   python -m build

   # Publish to PyPI
   twine upload dist/*

   # Update pipx installation
   pipx upgrade kuzu-memory
   ```

### For Users
1. **Migration from Claude Desktop to Claude Code**:
   - Install Claude Code extension for VS Code
   - Run: `kuzu-memory install claude-code`
   - Restart VS Code

2. **Verify Claude Desktop removal**:
   - Restart Claude Desktop
   - Verify kuzu-memory tools are no longer available
   - This is expected behavior - coding tools only now

## Why This Change

### Rationale
1. **Better Focus**: KuzuMemory excels in project-scoped development environments
2. **Simpler Architecture**: Fewer configurations to maintain
3. **Clearer Purpose**: Coding tools, not general chat
4. **User Clarity**: Less confusion about where KuzuMemory is active

### Supported Platforms Now
✅ **Coding Tools** (Fully Supported):
- claude-code (VS Code + Claude extension)
- cursor (Cursor IDE)
- vscode (VS Code)
- windsurf (Windsurf IDE)
- codex (Codex MCP server)
- auggie (Auggie AI editor)
- auggie-mcp (Auggie MCP integration)

❌ **No Longer Supported**:
- claude-desktop (general chat application)

### User Impact
**Low impact**:
- Most users use KuzuMemory in coding environments already
- Claude Desktop users can easily migrate to Claude Code
- Manual MCP configuration still possible (unsupported)

## Troubleshooting

### If "mcp serve" Error Still Appears
See `SOLUTION.md` for three fix options:
1. Force reconnect in Claude Code
2. Restart VS Code completely
3. Clear cached conversation state

### If Installation Still Shows claude-desktop
**Expected**: Current installed version (1.4.49) still includes it.
**Solution**: Wait for next release (1.5.0) or install from source for testing.

### If You Need Claude Desktop Support
**Option 1**: Stay on version 1.4.49 (unsupported)
**Option 2**: Switch to Claude Code (recommended)
**Option 3**: Manually configure MCP in Claude Desktop (unsupported)

## Summary

✅ **Completed**:
- Source code changes committed
- Configuration cleaned
- Documentation created
- Git commits with proper messages

⏳ **Pending**:
- Version bump for release
- Build and publish to PyPI
- Test from clean installation

🎯 **Goal Achieved**:
KuzuMemory now focuses exclusively on coding tools where it provides the most value, with clearer purpose and simpler architecture.
