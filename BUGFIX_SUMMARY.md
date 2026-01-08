# Auto-Update Infinite Loop Bug Fix

## Summary

Fixed three critical issues in the auto-update system that could cause infinite upgrade loops and poor user experience.

## Issues Fixed

### Issue 1: Version Mismatch (Root Cause)

**Problem**: `src/kuzu_memory/__version__.py` contained version `1.6.10` while the actual version was `1.6.13` (from VERSION file and pyproject.toml).

**Impact**: Version checker would always detect an "update available" because the running code reported 1.6.10, even after upgrading to 1.6.13.

**Solution**:
1. Updated `src/kuzu_memory/__version__.py` to `1.6.13` to match VERSION file
2. Added `update_version_py()` method to `scripts/version.py` to automatically sync `__version__.py` when bumping versions
3. Integrated `update_version_py()` into the `bump_version()` method

**Files Changed**:
- `src/kuzu_memory/__version__.py`: Updated version from 1.6.10 → 1.6.13
- `scripts/version.py`:
  - Added `update_version_py()` method (lines 72-87)
  - Updated `bump_version()` to call `update_version_py()` (line 109)
  - Updated console output to mention `__version__.py` update (line 353)

### Issue 2: Missing User Confirmation

**Problem**: Auto-upgrade started immediately without asking user permission, which is poor UX and doesn't give users control.

**Impact**: Users couldn't opt out of auto-upgrade during setup.

**Solution**: Added `click.confirm()` prompt before running auto-upgrade in `_check_and_upgrade_if_needed()`.

**Files Changed**:
- `src/kuzu_memory/cli/setup_commands.py` (lines 77-83):
  ```python
  # Ask user for confirmation before upgrading
  if not click.confirm(
      "   Upgrade now?",
      default=True,
  ):
      rich_print("   Skipping upgrade - continuing with current version", style="dim")
      return False
  ```

### Issue 3: No Loop Prevention (Defensive Measure)

**Problem**: Even with version sync fixed, there was no defensive mechanism to prevent restart loops if version detection failed.

**Impact**: If version detection logic had any bugs, the system could enter an infinite restart loop.

**Solution**: Added environment variable check (`KUZU_MEMORY_UPGRADE_ATTEMPTED=1`) to prevent re-entry.

**Files Changed**:
- `src/kuzu_memory/cli/setup_commands.py`:
  - Added environment variable check at start of `_check_and_upgrade_if_needed()` (lines 38-41)
  - Set environment variable before running upgrade (line 88)

## Code Changes

### Modified Files
1. **src/kuzu_memory/__version__.py** (1 line)
   - Updated version string to match VERSION file

2. **scripts/version.py** (+18 lines)
   - New method: `update_version_py()` to sync `__version__.py`
   - Modified: `bump_version()` to call new method
   - Modified: Console output to mention `__version__.py` update

3. **src/kuzu_memory/cli/setup_commands.py** (+18 lines)
   - Added environment variable check for loop prevention
   - Added user confirmation prompt before upgrade
   - Set environment variable before restart

### Git Diff Summary
```
 scripts/version.py                    | 20 +++++++++++++++++++-
 src/kuzu_memory/__version__.py        |  2 +-
 src/kuzu_memory/cli/setup_commands.py | 19 ++++++++++++++++++-
 4 files changed, 39 insertions(+), 4 deletions(-)
```

## Testing

### Manual Verification
✅ All version files synchronized (VERSION, pyproject.toml, __version__.py)
✅ CLI reports correct version: `kuzu-memory, version 1.6.13`
✅ Loop prevention environment variable works as expected

### Automated Tests
✅ Version-related tests pass (29/32 passing, 3 pre-existing failures unrelated to changes)
✅ No mypy type errors introduced
✅ Code follows existing patterns and conventions

## Behavior After Fix

### Before Fix:
1. User runs `kuzu-memory setup`
2. Version checker detects "1.6.10 → 1.6.13" update
3. Auto-upgrade runs without asking
4. System restarts
5. Version checker **still** sees "1.6.10 → 1.6.13" (because `__version__.py` not updated)
6. **INFINITE LOOP** 🔄

### After Fix:
1. User runs `kuzu-memory setup`
2. Version checker detects update (if any)
3. **User is prompted**: "Upgrade now? [Y/n]"
4. If user confirms:
   - Environment variable set: `KUZU_MEMORY_UPGRADE_ATTEMPTED=1`
   - Upgrade runs
   - System restarts
   - **Loop prevention** kicks in: Detects env var, skips version check
5. Setup continues normally ✅

## Future Version Bumps

When running `./scripts/version.py bump patch`:
- ✅ Updates `VERSION`
- ✅ Updates `pyproject.toml`
- ✅ Updates `src/kuzu_memory/__version__.py` (NEW!)
- ✅ Updates `CHANGELOG.md`
- ✅ Creates git tag

All three version files stay synchronized automatically.

## Related Documentation

- **CLAUDE.md**: Development guide for AI assistants
- **scripts/version.py**: Version management utility
- **Makefile**: Build and release automation (calls `version.py`)

## Rollback Plan (if needed)

If this fix causes issues, revert with:
```bash
git revert <commit-hash>
# Then manually set __version__.py back to 1.6.13
```

## Notes

- Loop prevention uses environment variable instead of file marker for simplicity
- Environment variable is session-scoped (doesn't persist across shell sessions)
- User confirmation defaults to "Yes" for convenience but gives users control
- This is a defensive fix - addresses root cause (version sync) AND adds safeguards (confirmation + loop prevention)
