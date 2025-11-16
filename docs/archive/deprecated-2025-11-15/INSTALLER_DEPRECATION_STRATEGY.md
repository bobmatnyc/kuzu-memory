# Installer Scripts Deprecation Strategy

**Status**: Active Deprecation (as of v1.1.11)
**Removal Target**: v2.0.0 (planned: 2026 Q1)

## Summary

The standalone installer scripts in `scripts/` directory have been deprecated in favor of integrated CLI commands. This document outlines the deprecation strategy, migration path, and timeline.

## Deprecated Scripts

### Primary Scripts
1. **scripts/install-claude-desktop.py** - Claude Desktop MCP installer (pipx-based)
2. **scripts/install-claude-desktop-home.py** - Claude Desktop home directory installer

### Status
- ✅ **Still Functional**: Scripts work and are maintained for backward compatibility
- ⚠️ **Deprecated**: Not recommended for new installations
- 🗓️ **Removal Planned**: Will be removed in v2.0.0 (2026 Q1)

## Migration Path

### Old Scripts → New CLI Commands

| Old Script Command | New CLI Command |
|-------------------|-----------------|
| `python scripts/install-claude-desktop.py` | `kuzu-memory install claude-desktop` |
| `python scripts/install-claude-desktop.py --dry-run` | `kuzu-memory install claude-desktop --dry-run` |
| `python scripts/install-claude-desktop.py --force` | `kuzu-memory install claude-desktop --force` |
| `python scripts/install-claude-desktop.py --uninstall` | `kuzu-memory uninstall claude-desktop` |
| `python scripts/install-claude-desktop.py --validate` | `kuzu-memory install-status` |
| | |
| `python scripts/install-claude-desktop-home.py` | `kuzu-memory install claude-desktop-home` |
| `python scripts/install-claude-desktop-home.py --mode wrapper` | `kuzu-memory install claude-desktop-home --mode wrapper` |
| `python scripts/install-claude-desktop-home.py --mode standalone` | `kuzu-memory install claude-desktop-home --mode standalone` |
| `python scripts/install-claude-desktop-home.py --update` | `kuzu-memory install claude-desktop-home --force` |
| `python scripts/install-claude-desktop-home.py --validate` | `kuzu-memory install-status` |
| `python scripts/install-claude-desktop-home.py --uninstall` | `kuzu-memory uninstall claude-desktop-home` |

### Common Options

All new installer commands support:
- `--force` - Force reinstall even if already installed
- `--dry-run` - Preview changes without modifying files
- `--verbose` - Show detailed installation steps
- `--mode [auto|wrapper|standalone]` - Installation mode (for home installer)
- `--backup-dir PATH` - Custom backup directory
- `--memory-db PATH` - Custom memory database location

## Deprecation Implementation

### 1. Script-Level Warnings

Both deprecated scripts include:
- **Header documentation**: Clear deprecation notice at top of file
- **Runtime warnings**: Printed when script executes
- **Migration examples**: Exact command equivalents
- **Removal timeline**: Specific version number (v2.0.0)

Example runtime warning:
```
⚠️  DEPRECATION WARNING ⚠️
This standalone script is deprecated. Please use:
    kuzu-memory install claude-desktop
For more options: kuzu-memory install --help
Continuing with legacy installation...
```

### 2. Documentation Updates

All documentation updated with:
- **Deprecation banners**: Prominent notices in affected docs
- **Migration guides**: Complete command mapping tables
- **Timeline information**: Clear removal date
- **Benefits explanation**: Why to migrate

Updated documents:
- ✅ `scripts/README.md` - Added deprecation notice and timeline
- ✅ `docs/HOME_INSTALLATION.md` - Added deprecation banner and migration guide
- ✅ `docs/CLAUDE_SETUP.md` - Added migration note
- ✅ `CLAUDE.md` - Updated setup guides and documentation links

### 3. README Updates

Main README.md updated to:
- ✅ Promote new CLI commands
- ✅ Show integrated installer workflow
- ✅ Mention deprecated scripts only in migration context

## Benefits of New CLI Commands

### For Users
- ✅ **Unified Interface**: Consistent with other `kuzu-memory` commands
- ✅ **Better Discoverability**: `kuzu-memory list-installers` shows all options
- ✅ **Improved Error Handling**: Better validation and error messages
- ✅ **Installation Tracking**: `kuzu-memory install-status` shows what's installed
- ✅ **Easier Uninstall**: Dedicated uninstall commands
- ✅ **No Script Path Required**: Works from anywhere in system

### For Developers
- ✅ **Single Codebase**: All installer logic in `src/kuzu_memory/installers/`
- ✅ **Centralized Testing**: Unified test suite for all installers
- ✅ **Easier Maintenance**: One place to fix bugs
- ✅ **Consistent API**: Same options across all installers
- ✅ **Better Extensibility**: Easy to add new installers

## Timeline

### Phase 1: Deprecation (CURRENT - v1.1.11+)
- ✅ Add deprecation notices to scripts
- ✅ Update all documentation
- ✅ Promote new CLI commands in README
- ✅ Maintain backward compatibility
- ✅ Runtime warnings when scripts execute

### Phase 2: Active Deprecation (v1.2.x - v1.9.x)
- ⏳ Continue showing warnings
- ⏳ Monitor usage metrics
- ⏳ Help users migrate
- ⏳ Keep scripts functional but frozen (no new features)
- ⏳ Update deprecation warnings with countdown

### Phase 3: Removal (v2.0.0 - 2026 Q1)
- ⏳ Remove standalone scripts
- ⏳ Archive documentation to `docs/archive/`
- ⏳ Update CHANGELOG with removal notice
- ⏳ Provide migration guide for stragglers
- ⏳ Breaking change announcement

## Backward Compatibility Commitment

### During Deprecation Period (v1.x)
- ✅ Scripts remain fully functional
- ✅ No breaking changes to script APIs
- ✅ Continued bug fixes for critical issues
- ✅ Security updates if needed
- ⚠️ No new features added to scripts

### After Removal (v2.0.0+)
- ❌ Scripts removed from repository
- ✅ Archived documentation available
- ✅ Migration guide maintained
- ✅ CLI commands fully cover all use cases

## User Communication

### Channels
1. **Runtime Warnings**: When executing deprecated scripts
2. **Documentation**: All guides and README files
3. **CHANGELOG.md**: Documented in each release
4. **Release Notes**: Mentioned in GitHub releases
5. **Migration Guide**: Dedicated section in docs

### Messaging
- Clear, non-alarming tone
- Specific migration commands
- Benefits of new approach
- Timeline transparency
- Help/support information

## Monitoring & Metrics

### Usage Tracking (Optional)
- Monitor script execution vs CLI usage
- Track migration adoption rate
- Identify blockers or issues
- Adjust timeline if needed

### Success Criteria
- 90%+ users migrated before v2.0.0
- No critical issues blocking migration
- Positive user feedback on new CLI
- Documentation comprehensive and clear

## Migration Support

### For Users Who Need Help
1. Check migration table in this document
2. Run `kuzu-memory install --help` for options
3. Use `kuzu-memory list-installers` to see all methods
4. Review updated documentation
5. File issue if stuck: Include current command and desired outcome

### For Automated Systems
- Update CI/CD pipelines to use new commands
- Test dry-run mode first
- Update documentation/runbooks
- Plan rollout with testing period

## Rollback Plan

If issues arise with new CLI commands:
1. Keep old scripts functional during v1.x
2. Fix critical bugs in both old and new systems
3. Extend timeline if needed
4. Communicate changes clearly

## Testing

### Before v2.0.0 Release
- ✅ Verify all old script functionality in new CLI
- ✅ Test all migration paths
- ✅ Validate documentation accuracy
- ✅ Ensure error messages are helpful
- ✅ Confirm installation/uninstallation works
- ✅ Test on all supported platforms (macOS, Linux, Windows)

### Verification Checklist
- [ ] All script options mapped to CLI equivalents
- [ ] Documentation updated and accurate
- [ ] Migration guide tested with real users
- [ ] No regressions in functionality
- [ ] Error handling comprehensive
- [ ] All platforms tested

## Frequently Asked Questions

### Why deprecate the standalone scripts?

The integrated CLI commands provide:
- Better user experience with consistent interface
- Easier maintenance with single codebase
- Improved discoverability and help system
- Better error handling and validation
- Installation status tracking
- Easier to add new installers

### Will my existing installation break?

No. The deprecation only affects **how you install**, not existing installations. Your current setup will continue working. When you need to reinstall or update, use the new CLI commands.

### Can I still use the old scripts?

Yes, during the v1.x series. They work exactly as before but show deprecation warnings. They will be removed in v2.0.0 (2026 Q1).

### What if I have automation using the old scripts?

Update your automation to use the new CLI commands. The migration table shows exact equivalents. Test with `--dry-run` first.

### What happens if I don't migrate before v2.0.0?

The scripts will be removed. You'll need to use the CLI commands to manage installations. Existing installations won't break, but you'll need the new commands to modify them.

### How do I know which command to use?

Run:
```bash
kuzu-memory list-installers    # See all available installers
kuzu-memory install --help     # Get detailed help
kuzu-memory install-status     # Check what's installed
```

### Is there a way to test the migration?

Yes:
```bash
# Test dry-run mode (shows what would happen)
kuzu-memory install claude-desktop --dry-run --verbose

# Validate installation afterward
kuzu-memory install-status
```

## Conclusion

The deprecation strategy provides:
- ✅ Clear migration path for all users
- ✅ Reasonable timeline (v1.x through v2.0.0)
- ✅ Backward compatibility during transition
- ✅ Comprehensive documentation
- ✅ Better user experience long-term

The removal of standalone scripts in v2.0.0 will simplify maintenance, improve user experience, and enable faster development of new features.

---

**Last Updated**: 2025-10-01
**Status**: Active Deprecation
**Target Removal**: v2.0.0 (2026 Q1)
**Contact**: File issue if you need help migrating
