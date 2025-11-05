# MCP Configuration Migration Strategy

## Executive Summary

**Problem**: kuzu-memory installer creates MCP server configurations in `~/.claude.json` under `projects[path].mcpServers`, but Claude Code **does NOT support** this location. Claude Code only supports:
- Global MCP servers at `~/.claude.json` root level `mcpServers`
- Project-local MCP servers in `.mcp.json` in project directory

**Impact**: All project-specific kuzu-memory MCP servers show "✘ failed" status in Claude Code because they are in an unsupported location.

**Solution**: Migrate from `~/.claude.json → projects[path].mcpServers` to `.mcp.json` in each project directory.

---

## Current Installation Analysis

### What the Installer Does (BROKEN)

File: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_hooks.py`

**Lines 59-118**: `_update_global_mcp_config()` method writes to:
```json
~/.claude.json
{
  "projects": {
    "/absolute/path/to/project": {
      "mcpServers": {
        "kuzu-memory": {
          "type": "stdio",
          "command": "kuzu-memory",
          "args": ["mcp"],
          "env": {...}
        }
      }
    }
  }
}
```

**Problem**: This location is **NOT supported by Claude Code**. It's ignored completely.

### Supported Locations

Claude Code MCP server support:

1. **Global MCP servers** (for all projects):
   ```
   ~/.claude.json
   {
     "mcpServers": {
       "server-name": {...}
     }
   }
   ```

2. **Project-local MCP servers** (recommended):
   ```
   /project/root/.mcp.json
   {
     "mcpServers": {
       "server-name": {...}
     }
   }
   ```

### Current State in Production

Based on analysis of `~/.claude.json`:
- **23 projects** have kuzu-memory in broken `projects[path].mcpServers` location
- All show "✘ failed" status in Claude Code
- `.mcp.json` files may or may not exist in project directories
- Some have different command formats (python -m vs kuzu-memory CLI)

---

## Migration Strategy

### Option A: Migrate to .mcp.json (RECOMMENDED)

**Benefits**:
- Project-specific configuration (proper isolation)
- Works correctly with Claude Code
- Version control friendly (can commit to repo)
- Clean separation from global config

**Drawbacks**:
- Need to create `.mcp.json` in each project
- Must handle existing `.mcp.json` files with other servers
- Requires file I/O in each project directory

### Option B: Migrate to Global mcpServers

**Benefits**:
- Single configuration location
- Easier to migrate (all in one file)

**Drawbacks**:
- All projects share same MCP server (no per-project customization)
- Cannot override DB path per project
- Not recommended by Claude Code docs for project-specific tools

**Recommendation**: **Option A** - Migrate to project-local `.mcp.json`

---

## Implementation Design

### 1. Detection Logic

**Where to detect**:
- On `kuzu-memory install claude-code` (always check and migrate)
- On `kuzu-memory init` (check if broken config exists)
- **NOT** on every CLI invocation (too heavy for file I/O)

**Detection algorithm**:
```python
def detect_broken_installations() -> list[dict]:
    """
    Detect kuzu-memory MCP servers in broken location.

    Returns:
        List of broken installations: [
            {
                "project_path": "/absolute/path",
                "config": {"type": "stdio", ...},
                "has_local_mcp_json": bool,
                "project_exists": bool
            }
        ]
    """
    claude_json = Path.home() / ".claude.json"
    if not claude_json.exists():
        return []

    config = load_json_config(claude_json)
    broken_installs = []

    for project_path, project_config in config.get("projects", {}).items():
        if "mcpServers" not in project_config:
            continue

        kuzu_config = project_config["mcpServers"].get("kuzu-memory")
        if not kuzu_config:
            continue

        project_dir = Path(project_path)
        mcp_json = project_dir / ".mcp.json"

        broken_installs.append({
            "project_path": project_path,
            "config": kuzu_config,
            "has_local_mcp_json": mcp_json.exists(),
            "project_exists": project_dir.exists()
        })

    return broken_installs
```

### 2. Migration Logic

**Core migration function**:
```python
def migrate_mcp_to_local(
    project_path: Path,
    kuzu_config: dict,
    force: bool = False
) -> tuple[bool, str]:
    """
    Migrate MCP config from ~/.claude.json to .mcp.json

    Args:
        project_path: Absolute path to project directory
        kuzu_config: MCP server configuration to migrate
        force: If True, overwrite existing kuzu-memory in .mcp.json

    Returns:
        (success: bool, message: str)
    """
    mcp_json = project_path / ".mcp.json"

    # Load or create .mcp.json
    if mcp_json.exists():
        try:
            existing = load_json_config(mcp_json)
        except JSONConfigError as e:
            return False, f"Cannot read existing .mcp.json: {e}"

        # Check if kuzu-memory already exists
        if "kuzu-memory" in existing.get("mcpServers", {}):
            if not force:
                return False, "kuzu-memory already in .mcp.json (use --force to overwrite)"
    else:
        existing = {"mcpServers": {}}

    # Add/update kuzu-memory
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}
    existing["mcpServers"]["kuzu-memory"] = kuzu_config

    # Write to .mcp.json
    try:
        save_json_config(mcp_json, existing, indent=2)
        return True, f"Migrated to {mcp_json}"
    except JSONConfigError as e:
        return False, f"Failed to write .mcp.json: {e}"
```

### 3. Cleanup Logic

**Remove from broken location**:
```python
def cleanup_broken_location(project_path: str) -> tuple[bool, str]:
    """
    Remove kuzu-memory from projects[path].mcpServers in ~/.claude.json

    Args:
        project_path: Absolute path as string (key in projects dict)

    Returns:
        (success: bool, message: str)
    """
    claude_json = Path.home() / ".claude.json"
    config = load_json_config(claude_json)

    if "projects" not in config or project_path not in config["projects"]:
        return True, "Already cleaned up"

    project_config = config["projects"][project_path]
    if "mcpServers" not in project_config:
        return True, "Already cleaned up"

    if "kuzu-memory" not in project_config["mcpServers"]:
        return True, "Already cleaned up"

    # Backup before modifying
    backup_path = claude_json.with_suffix(".json.backup")
    shutil.copy(claude_json, backup_path)

    # Remove kuzu-memory
    del project_config["mcpServers"]["kuzu-memory"]

    # Clean up empty structures
    if not project_config["mcpServers"]:
        del project_config["mcpServers"]
    if not config["projects"][project_path]:
        del config["projects"][project_path]
    if not config["projects"]:
        del config["projects"]

    # Write updated config
    save_json_config(claude_json, config, indent=2)
    return True, "Removed from ~/.claude.json"
```

### 4. Orchestration

**Full migration workflow**:
```python
def migrate_all_broken_installations(
    force: bool = False,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Migrate all broken MCP installations to .mcp.json

    Returns:
        {
            "detected": int,
            "migrated": int,
            "failed": int,
            "skipped": int,
            "details": [...]
        }
    """
    broken = detect_broken_installations()
    results = {
        "detected": len(broken),
        "migrated": 0,
        "failed": 0,
        "skipped": 0,
        "details": []
    }

    for install in broken:
        project_path = Path(install["project_path"])

        # Skip if project directory doesn't exist
        if not install["project_exists"]:
            results["skipped"] += 1
            results["details"].append({
                "project": str(project_path),
                "status": "skipped",
                "reason": "Project directory does not exist"
            })
            continue

        if dry_run:
            results["details"].append({
                "project": str(project_path),
                "status": "dry_run",
                "message": f"Would migrate to {project_path}/.mcp.json"
            })
            continue

        # Migrate to .mcp.json
        success, message = migrate_mcp_to_local(
            project_path,
            install["config"],
            force=force
        )

        if success:
            # Clean up broken location
            cleanup_success, cleanup_msg = cleanup_broken_location(
                install["project_path"]
            )

            results["migrated"] += 1
            results["details"].append({
                "project": str(project_path),
                "status": "success",
                "message": message,
                "cleanup": cleanup_msg
            })
        else:
            results["failed"] += 1
            results["details"].append({
                "project": str(project_path),
                "status": "failed",
                "reason": message
            })

    return results
```

---

## Edge Cases and Handling

### Edge Case 1: Project Directory Doesn't Exist

**Scenario**: Entry in `~/.claude.json` for `/tmp/test-project` but directory was deleted.

**Handling**:
- Skip migration for this project
- Remove from `~/.claude.json` during cleanup
- Log as "skipped - project not found"

**Implementation**:
```python
if not project_path.exists():
    cleanup_broken_location(project_path)  # Remove from ~/.claude.json
    return "skipped", "Project directory not found"
```

### Edge Case 2: .mcp.json Already Exists with Other Servers

**Scenario**: Project has `.mcp.json` with mcp-ticketer, mcp-browser, etc.

**Handling**:
- Load existing `.mcp.json`
- Merge kuzu-memory into `mcpServers` dict
- Preserve all other servers
- Check if kuzu-memory already exists (require --force to overwrite)

**Implementation**:
```python
existing = load_json_config(mcp_json)
if "kuzu-memory" in existing.get("mcpServers", {}) and not force:
    return False, "kuzu-memory already exists (use --force)"

existing["mcpServers"]["kuzu-memory"] = kuzu_config
save_json_config(mcp_json, existing)
```

### Edge Case 3: .mcp.json Already Has kuzu-memory

**Scenario**: User manually created `.mcp.json` or ran migration already.

**Handling**:
- Default: Skip migration, warn user
- With `--force`: Overwrite existing config
- Show diff of what would change

**Implementation**:
```python
if "kuzu-memory" in existing["mcpServers"]:
    if force:
        logger.warning(f"Overwriting existing kuzu-memory config in {mcp_json}")
    else:
        return False, "Already exists - use --force to overwrite"
```

### Edge Case 4: .mcp.json Has Syntax Errors

**Scenario**: Corrupted or invalid JSON in existing `.mcp.json`

**Handling**:
- Create backup: `.mcp.json.backup`
- Attempt to parse and recover
- If recovery fails, ask user to fix manually
- Do NOT overwrite corrupted file

**Implementation**:
```python
try:
    existing = load_json_config(mcp_json)
except JSONConfigError as e:
    backup = mcp_json.with_suffix(".json.backup")
    shutil.copy(mcp_json, backup)
    return False, f"Corrupted .mcp.json (backed up to {backup}): {e}"
```

### Edge Case 5: Permission Errors

**Scenario**: Cannot write to project directory or `~/.claude.json`

**Handling**:
- Catch PermissionError
- Provide clear error message
- Suggest running with appropriate permissions
- Do NOT partially migrate (all-or-nothing)

**Implementation**:
```python
try:
    save_json_config(mcp_json, existing)
except PermissionError:
    return False, f"Permission denied writing to {mcp_json}"
```

### Edge Case 6: Multiple Projects with Same Name

**Scenario**: `/tmp/project` and `/home/user/project` both have kuzu-memory

**Handling**:
- Each project is independent (absolute paths)
- Migrate each separately
- No conflict possible (different directories)

### Edge Case 7: Symlinks in Project Path

**Scenario**: Project path contains symlinks

**Handling**:
- Use `Path.resolve()` to get canonical path
- Match against resolved paths in `~/.claude.json`
- Handle both resolved and unresolved paths

**Implementation**:
```python
project_path = Path(project_path).resolve()
# Also check unresolved path as key in config
```

---

## Backup and Rollback Strategy

### Backup Strategy

**What to backup**:
1. `~/.claude.json` → `~/.claude.json.backup` (before any modification)
2. `.mcp.json` → `.mcp.json.backup` (if exists, before overwrite)

**When to backup**:
- Before ANY modification to either file
- Keep timestamped backups: `.json.backup.2025-11-05-143022`

**Backup implementation**:
```python
def create_timestamped_backup(file_path: Path) -> Path:
    """Create timestamped backup of file."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup_path = file_path.with_suffix(f".json.backup.{timestamp}")
    shutil.copy(file_path, backup_path)
    logger.info(f"Created backup: {backup_path}")
    return backup_path
```

### Rollback Strategy

**Automatic rollback triggers**:
- Migration fails mid-process
- JSON write fails
- Permission errors

**Rollback implementation**:
```python
def rollback_migration(backup_files: list[Path]) -> None:
    """Restore from backups on migration failure."""
    for backup in backup_files:
        original = backup.with_suffix("")  # Remove .backup
        if backup.exists():
            shutil.copy(backup, original)
            logger.info(f"Rolled back: {original}")
```

**Manual rollback**:
```bash
# User can manually restore from backup
cp ~/.claude.json.backup ~/.claude.json
cp .mcp.json.backup .mcp.json
```

---

## When to Run Migration

### Option 1: On `kuzu-memory install claude-code` (RECOMMENDED)

**Benefits**:
- Users expect changes during install
- Natural place for migration
- Can show migration progress
- Can prompt user if needed

**Implementation**:
```python
class ClaudeHooksInstaller:
    def install(self, ...):
        # ... existing install logic ...

        # AFTER successful installation, migrate broken configs
        self._migrate_if_needed()

    def _migrate_if_needed(self):
        """Migrate MCP configs from broken location."""
        broken = detect_broken_installations()
        if not broken:
            return

        logger.info(f"Detected {len(broken)} broken MCP installation(s)")
        logger.info("Migrating to project-local .mcp.json...")

        results = migrate_all_broken_installations()

        if results["migrated"] > 0:
            print(f"✓ Migrated {results['migrated']} project(s) to .mcp.json")
        if results["failed"] > 0:
            print(f"✘ Failed to migrate {results['failed']} project(s)")
```

### Option 2: On `kuzu-memory init`

**Benefits**:
- Runs for each project
- Can fix project-specific issues

**Drawbacks**:
- Runs on every project init (repetitive)
- Might surprise users

### Option 3: Separate `kuzu-memory migrate` Command

**Benefits**:
- Explicit user intent
- Can be run independently
- Good for batch migration

**Drawbacks**:
- Users might not know to run it
- Extra step

### Option 4: Automatic on CLI Startup (NOT RECOMMENDED)

**Drawbacks**:
- Too heavy (file I/O on every command)
- Slows down all CLI commands
- Already have `_silent_repair_mcp_configs()` for args fix

---

## User Communication

### Success Message
```
✓ Claude Code hooks installed successfully

Migration Report:
  • Migrated 3 project(s) to .mcp.json
  • Cleaned up 3 broken configuration(s) from ~/.claude.json

Projects migrated:
  • /Users/masa/Projects/kuzu-memory
  • /Users/masa/Projects/another-project
  • /Users/masa/Clients/client-project

Restart Claude Code to apply changes.
```

### Failure Message
```
✘ Migration failed for 1 project(s):
  • /tmp/test-project: Project directory not found (skipped)

Migrated successfully: 2 project(s)

Some projects could not be migrated automatically.
Run 'kuzu-memory install claude-code --force' to retry.
```

### Warning Message
```
⚠ Found kuzu-memory MCP servers in unsupported location:
  ~/.claude.json → projects[path].mcpServers

This location is NOT supported by Claude Code.
Running migration to .mcp.json...
```

---

## Testing Strategy

### Unit Tests

1. **Test detection**:
   - Empty `~/.claude.json`
   - No projects section
   - Projects with no mcpServers
   - Projects with kuzu-memory
   - Projects with other servers only

2. **Test migration**:
   - Fresh `.mcp.json` creation
   - Merge with existing `.mcp.json`
   - Overwrite with --force
   - Handle corrupted `.mcp.json`
   - Handle permission errors

3. **Test cleanup**:
   - Remove from broken location
   - Clean up empty structures
   - Preserve other projects
   - Handle missing keys

### Integration Tests

1. **End-to-end migration**:
   - Create broken config
   - Run migration
   - Verify `.mcp.json` created
   - Verify `~/.claude.json` cleaned up
   - Test Claude Code can read `.mcp.json`

2. **Multi-project migration**:
   - 10+ projects with kuzu-memory
   - Some with existing `.mcp.json`
   - Some with missing directories
   - Verify all handled correctly

3. **Rollback testing**:
   - Simulate migration failure
   - Verify rollback restores state
   - Verify no partial migrations

---

## Migration Command CLI

### New Command: `kuzu-memory migrate mcp`

```bash
kuzu-memory migrate mcp [OPTIONS]

Options:
  --dry-run        Show what would be migrated without making changes
  --force          Overwrite existing kuzu-memory in .mcp.json
  --project PATH   Migrate specific project only (default: all)
  --skip-cleanup   Don't remove from ~/.claude.json after migration

Examples:
  # Detect and migrate all broken installations
  kuzu-memory migrate mcp

  # Preview migration without making changes
  kuzu-memory migrate mcp --dry-run

  # Force overwrite existing .mcp.json configs
  kuzu-memory migrate mcp --force

  # Migrate specific project only
  kuzu-memory migrate mcp --project /Users/masa/Projects/my-project
```

### Integration with Install Command

```bash
# Automatically runs migration during install
kuzu-memory install claude-code

# Skip automatic migration
kuzu-memory install claude-code --skip-migration

# Force reinstall + migration
kuzu-memory install claude-code --force
```

---

## Implementation Priority

### Phase 1: Core Migration (HIGH PRIORITY)
1. ✅ Implement detection logic
2. ✅ Implement migration to .mcp.json
3. ✅ Implement cleanup from broken location
4. ✅ Add backup/rollback
5. ✅ Integrate into install command

### Phase 2: CLI Command (MEDIUM PRIORITY)
6. ⬜ Add `kuzu-memory migrate mcp` command
7. ⬜ Add --dry-run support
8. ⬜ Add --force support
9. ⬜ Add progress reporting

### Phase 3: Testing (HIGH PRIORITY)
10. ⬜ Unit tests for detection
11. ⬜ Unit tests for migration
12. ⬜ Integration tests
13. ⬜ Test with real Claude Code

### Phase 4: Documentation (MEDIUM PRIORITY)
14. ⬜ Update installation docs
15. ⬜ Add migration guide
16. ⬜ Update troubleshooting guide

---

## Risk Assessment

### High Risk
- **Corrupting `~/.claude.json`**: Mitigated by backups
- **Losing MCP configs**: Mitigated by backup strategy
- **Permission errors**: Handled gracefully with clear errors

### Medium Risk
- **Partial migration**: Mitigated by all-or-nothing approach
- **Symlink confusion**: Handled by path resolution
- **Multiple runs**: Idempotent (can run multiple times safely)

### Low Risk
- **Performance**: One-time operation, acceptable overhead
- **User confusion**: Clear messages and documentation

---

## Success Criteria

✅ **Migration successful if**:
1. All kuzu-memory MCP servers moved to `.mcp.json`
2. All entries removed from `~/.claude.json → projects[path].mcpServers`
3. Claude Code shows "✓ ready" status for kuzu-memory MCP
4. Backups created before any modifications
5. No data loss or corruption
6. Clear user feedback on what happened

---

## Appendix: File Locations Reference

### Claude Code MCP Configuration Locations

**Supported locations**:
```
~/.claude.json
{
  "mcpServers": {          ← GLOBAL (works)
    "server-name": {...}
  }
}

/project/root/.mcp.json    ← PROJECT-LOCAL (works, RECOMMENDED)
{
  "mcpServers": {
    "server-name": {...}
  }
}
```

**Unsupported location (current bug)**:
```
~/.claude.json
{
  "projects": {
    "/project/path": {
      "mcpServers": {      ← NOT SUPPORTED (ignored by Claude Code)
        "server-name": {...}
      }
    }
  }
}
```

### Installer File References

**Main installer**: `src/kuzu_memory/installers/claude_hooks.py`
- Line 59-118: `_update_global_mcp_config()` - writes to broken location
- Line 120-169: `_clean_legacy_mcp_locations()` - cleanup helper
- Line 1181-1231: `_validate_hooks_config()` - validation logic

**JSON utilities**: `src/kuzu_memory/installers/json_utils.py`
- Line 53-92: `merge_json_configs()` - config merging
- Line 95-118: `load_json_config()` - JSON loading
- Line 120-144: `save_json_config()` - JSON saving
- Line 275-337: `fix_broken_mcp_args()` - args repair (existing pattern)

**Auto-repair**: `src/kuzu_memory/cli/commands.py`
- Line 40-76: `_silent_repair_mcp_configs()` - auto-fix on CLI startup
- Line 137: Called on every CLI invocation (except help/version)

---

## Next Steps for Engineer

1. **Review this document** with PM and get approval
2. **Create implementation branch**: `feature/migrate-mcp-to-local`
3. **Implement Phase 1** (Core Migration):
   - Add detection logic to `claude_hooks.py`
   - Add migration logic to `claude_hooks.py`
   - Add cleanup logic to `claude_hooks.py`
   - Integrate into `install()` method
4. **Write unit tests** in `tests/unit/test_mcp_migration.py`
5. **Write integration tests** in `tests/integration/test_mcp_migration_e2e.py`
6. **Test manually** with real Claude Code
7. **Update documentation** in `docs/MCP_INSTALLATION.md`
8. **Create PR** with comprehensive testing

**Estimated effort**: 6-8 hours for Phase 1 + testing
