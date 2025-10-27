# CLI Refactoring: Unified Installation Path v1.3.5

## Summary

Successfully refactored the kuzu-memory CLI to follow **Agentic Coder Optimizer** principles: **ONE way to do ANYTHING**.

## Changes Made

### 1. New Unified Commands

Created `/src/kuzu_memory/cli/install_unified.py` with three commands:

- **`kuzu-memory install <integration>`** - Install integration (ONE command)
- **`kuzu-memory uninstall <integration>`** - Uninstall integration
- **`kuzu-memory remove <integration>`** - Alias for uninstall (hidden)

### 2. Available Integrations

Simplified integration names:
- `claude-code` - Claude Code (MCP + hooks)
- `claude-desktop` - Claude Desktop (MCP only)
- `cursor` - Cursor IDE (MCP only)
- `vscode` - VS Code (MCP only)
- `windsurf` - Windsurf IDE (MCP only)
- `auggie` - Auggie (rules)

### 3. Deprecated Commands

Old commands still work but show deprecation warnings:

**Old Pattern (DEPRECATED):**
```bash
# These still work but show warnings
kuzu-memory install add claude-code
kuzu-memory hooks install claude-code
kuzu-memory mcp install cursor
```

**New Pattern (RECOMMENDED):**
```bash
# ONE way to do anything
kuzu-memory install claude-code
kuzu-memory install cursor
kuzu-memory uninstall claude-code
```

### 4. Updated Files

#### Core CLI Files:
- `src/kuzu_memory/cli/commands.py` - Main CLI with new commands
- `src/kuzu_memory/cli/install_unified.py` - New unified install commands
- `src/kuzu_memory/cli/hooks_commands.py` - Added deprecation warnings
- `src/kuzu_memory/cli/mcp_install_commands.py` - Added deprecation warnings

#### Documentation:
- `CLAUDE.md` - Updated with new command examples
- `README.md` - Updated installation section with unified commands

### 5. Deprecation Strategy

All old commands preserved for backward compatibility:
- Show clear deprecation warnings
- Suggest new unified commands
- Still fully functional

Example deprecation warning:
```
⚠️  WARNING: 'kuzu-memory hooks' is deprecated.
⚠️  Use 'kuzu-memory install <integration>' instead.

Examples:
  kuzu-memory install claude-code
  kuzu-memory uninstall claude-code
```

## Benefits

### Before (3 overlapping paths):
```bash
kuzu-memory install add claude-code      # Path 1
kuzu-memory hooks install claude-code    # Path 2
kuzu-memory mcp install claude-code      # Path 3 (for MCP part)
```

### After (ONE path):
```bash
kuzu-memory install claude-code          # ONE way
```

### Advantages:
1. **Cognitive Load Reduction** - Users learn ONE command pattern
2. **Consistency** - Same command structure for all integrations
3. **Simplicity** - No need to understand hooks vs MCP distinction
4. **Automatic** - Command knows what components to install per platform
5. **Backward Compatible** - Old commands still work during transition

## Implementation Details

### Command Registration

```python
# New unified commands (primary)
cli.add_command(install_command)    # kuzu-memory install
cli.add_command(uninstall_command)  # kuzu-memory uninstall
cli.add_command(remove_command)     # kuzu-memory remove (alias)

# Old commands (deprecated but functional)
cli.add_command(hooks_group, name="hooks")     # Shows warning
cli.add_command(mcp_install_group, name="mcp") # Shows warning
```

### Registry Integration

Uses existing `InstallerRegistry` - no duplication:
```python
installer = get_installer(integration, root)
result = installer.install(dry_run=dry_run, verbose=verbose)
```

### Automatic Component Selection

Each platform gets the right components automatically:
- **claude-code**: MCP server + hooks (complete integration)
- **claude-desktop**: MCP server only
- **cursor/vscode/windsurf**: MCP server only
- **auggie**: Rules integration

## Testing Results

All commands tested and working:

✅ **New Commands:**
```bash
kuzu-memory install claude-code --dry-run
kuzu-memory uninstall cursor
kuzu-memory --help  # Shows new installation section
```

✅ **Deprecated Commands (still work):**
```bash
kuzu-memory hooks install claude-code   # Shows warning + works
kuzu-memory mcp install cursor          # Shows warning + works
```

✅ **Help Text Updated:**
- Main CLI help shows new installation section
- Clear examples of available integrations
- Deprecation notices on old command groups

## Migration Path for Users

### Immediate Actions:
1. Update documentation to show new commands
2. Update examples in tutorials/guides
3. Communicate deprecation in release notes

### Transition Period:
- Old commands continue to work (no breaking changes)
- Users see deprecation warnings guiding them to new commands
- Both paths functional during transition

### Future (v2.0):
- Consider removing old command groups
- Keep only unified `install`/`uninstall` commands

## Success Metrics

✅ **ONE Command Path**: Users only need to learn `install`/`uninstall`
✅ **Backward Compatible**: All old commands still functional
✅ **Clear Messaging**: Deprecation warnings guide users to new path
✅ **Simplified Help**: Main CLI help is cleaner and more focused
✅ **Automatic Selection**: Platform determines components (no user decision needed)

## Code Impact

### Lines of Code:
- **New file**: `install_unified.py` (~240 lines)
- **Modified**: `commands.py` (updated imports, command registration, help text)
- **Modified**: `hooks_commands.py` (added deprecation warnings)
- **Modified**: `mcp_install_commands.py` (added deprecation warnings)
- **Modified**: `CLAUDE.md`, `README.md` (documentation updates)

### Net Impact:
- **Added**: 1 new file
- **Modified**: 6 files
- **Removed**: 0 files (backward compatible)
- **Result**: Cleaner, simpler user experience with ONE command path

## Alignment with Agentic Coder Optimizer Principles

✅ **ONE way to do ANYTHING**: Single install/uninstall command pattern
✅ **Composition over Duplication**: Reuses existing `InstallerRegistry`
✅ **Code Reduction**: Consolidated 3 paths into 1
✅ **User Experience**: Simplified mental model
✅ **Backward Compatible**: No breaking changes

## Next Steps

1. ✅ Test new commands (COMPLETED)
2. ✅ Update documentation (COMPLETED)
3. ⏳ Create release notes for v1.3.5
4. ⏳ Consider updating other documentation files
5. ⏳ Monitor user feedback during transition period

---

**Version**: 1.3.5
**Date**: 2025-10-26
**Status**: ✅ COMPLETE
