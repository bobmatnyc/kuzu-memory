# MCP Migration Strategy - Executive Summary

## Problem Statement

**Current State**: kuzu-memory installer creates MCP server configurations in an **unsupported location** that Claude Code ignores:
```
~/.claude.json → projects["/project/path"].mcpServers["kuzu-memory"]
```

**Expected State**: Claude Code only supports two locations:
1. Global: `~/.claude.json → mcpServers["kuzu-memory"]` (all projects)
2. **Local**: `/project/root/.mcp.json → mcpServers["kuzu-memory"]` (per-project) ✅

**Impact**:
- All 23 projects in production show "✘ failed" MCP status
- Users cannot use kuzu-memory MCP tools in Claude Code
- Silent failure (no error messages, just doesn't work)

## Solution Overview

**Migrate from**: `~/.claude.json → projects[path].mcpServers`
**Migrate to**: `/project/root/.mcp.json`

This is a **one-time migration** that will:
1. Detect all broken installations in `~/.claude.json`
2. Create/update `.mcp.json` in each project directory
3. Remove broken entries from `~/.claude.json`
4. Backup everything before making changes

## Migration Trigger

**When**: Automatically during `kuzu-memory install claude-code`

**Why**:
- Natural place for migration (users expect changes during install)
- Can show progress and results
- Fixes both new and existing installations
- One-time operation per project

## Key Design Decisions

### Decision 1: Local .mcp.json vs Global mcpServers

**Choice**: Migrate to project-local `.mcp.json` ✅

**Rationale**:
- Each project has its own database path (project-specific)
- Version control friendly (can commit to repo)
- Proper isolation between projects
- Recommended by Claude Code documentation

### Decision 2: When to Run Migration

**Choice**: During `kuzu-memory install claude-code` ✅

**Rationale**:
- Users expect changes during install
- Natural place for one-time migration
- Can show progress and handle errors
- Not on every CLI invocation (too heavy)

### Decision 3: Handling Existing .mcp.json

**Choice**: Merge, don't overwrite ✅

**Rationale**:
- Projects may have other MCP servers (mcp-ticketer, mcp-browser, etc.)
- Must preserve existing servers
- Only add/update kuzu-memory entry
- Require `--force` to overwrite existing kuzu-memory

## Edge Cases Covered

1. ✅ **Project directory doesn't exist** → Skip, cleanup broken config
2. ✅ **`.mcp.json` already exists** → Merge, preserve other servers
3. ✅ **`.mcp.json` has kuzu-memory** → Skip (or overwrite with --force)
4. ✅ **`.mcp.json` is corrupted** → Backup, fail with clear error
5. ✅ **Permission errors** → Fail gracefully with clear message
6. ✅ **Multiple projects** → Migrate each independently
7. ✅ **Symlinks in path** → Resolve to canonical path

## Backup Strategy

**Before ANY modification**:
- `~/.claude.json` → `~/.claude.json.backup.{timestamp}`
- `.mcp.json` → `.mcp.json.backup.{timestamp}`

**Rollback**: Automatic on failure, manual via backup files

## Implementation Phases

### Phase 1: Core Migration (HIGH PRIORITY) - 6-8 hours
- ✅ Detection logic
- ✅ Migration logic
- ✅ Cleanup logic
- ✅ Backup/rollback
- ✅ Integration with install command

### Phase 2: Testing (HIGH PRIORITY) - 4 hours
- Unit tests for detection
- Unit tests for migration
- Integration tests
- Manual testing with Claude Code

### Phase 3: Documentation (MEDIUM PRIORITY) - 2 hours
- Update installation docs
- Add migration guide
- Update troubleshooting

### Phase 4: CLI Command (OPTIONAL) - 3 hours
- Add `kuzu-memory migrate mcp` command
- Add --dry-run and --force flags

**Total Estimate**: 12-17 hours for complete implementation

## Success Criteria

✅ Migration successful when:
1. All kuzu-memory MCP configs moved to `.mcp.json`
2. `~/.claude.json → projects[path].mcpServers` cleaned up
3. Claude Code shows "✓ ready" status
4. No data loss or corruption
5. Clear user feedback

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Corrupt `~/.claude.json` | High | Timestamped backups before changes |
| Lose MCP configs | High | Backup strategy + rollback |
| Partial migration | Medium | All-or-nothing approach |
| Permission errors | Medium | Graceful failure + clear errors |
| User confusion | Low | Clear messages + documentation |

## Next Steps

**For Engineer**:
1. Review full strategy document: `MCP_MIGRATION_STRATEGY.md`
2. Create implementation branch: `feature/migrate-mcp-to-local`
3. Implement Phase 1 (Core Migration)
4. Write comprehensive tests
5. Test with real Claude Code
6. Create PR for review

**For PM**:
1. Review and approve strategy
2. Prioritize against other work
3. Decide on Phase 4 (CLI command) necessity
4. Approve for implementation

## Files to Review

- **Full strategy**: `/Users/masa/Projects/kuzu-memory/MCP_MIGRATION_STRATEGY.md`
- **Current installer**: `src/kuzu_memory/installers/claude_hooks.py` (line 59-118)
- **JSON utils**: `src/kuzu_memory/installers/json_utils.py`
- **Auto-repair pattern**: `src/kuzu_memory/cli/commands.py` (line 40-76)

## Production Impact

**Current production state** (from `~/.claude.json`):
- 23 projects have kuzu-memory in broken location
- All show "✘ failed" status
- Manual `.mcp.json` exists in some projects (e.g., this one)

**After migration**:
- All projects will have working `.mcp.json`
- Claude Code will show "✓ ready" status
- Users can use kuzu-memory MCP tools
- Clean `~/.claude.json` (no broken entries)
