# Deprecation Notice

**Date**: 2025-10-01
**Status**: ARCHIVED - Do Not Use

---

## 🔴 These Documentation Files Have Been Replaced

The files in this directory have been consolidated into new, comprehensive documentation to eliminate redundancy and confusion.

---

## 📋 Migration Guide

### Claude Setup Documentation

**Old Files** (4 files):
- `CLAUDE_CODE_SETUP.md`
- `CLAUDE_DESKTOP_SETUP.md`
- `CLAUDE_HOOKS.md`
- `CLAUDE_INTEGRATION.md`

**New Location**:
- **`docs/CLAUDE_SETUP.md`** - Complete Claude integration guide

**What Changed**:
- Consolidated all Claude setup information into one document
- Organized by integration path (Claude Desktop vs Claude Code)
- Eliminated duplicate content
- Added troubleshooting section with solutions from all sources
- Clear structure with priority markers (🔴🟡🟢⚪)

---

### Getting Started Documentation

**Old Files** (3 files):
- `QUICK_START.md`
- `SETUP.md`
- `README_CLI.md`

**New Location**:
- **`docs/GETTING_STARTED.md`** - Complete getting started guide

**What Changed**:
- Unified installation instructions
- Single 5-minute quick start path
- Combined CLI documentation
- Comprehensive troubleshooting
- AI integration patterns included

---

### Memory System Documentation

**Old Files** (2 files):
- `MEMORY_GUIDE.md`
- `memory-system.md`

**New Location**:
- **`docs/MEMORY_SYSTEM.md`** - Enhanced memory system guide

**What Changed**:
- Consolidated memory type definitions
- Added cognitive memory model explanation
- Unified retention policies
- Comprehensive best practices
- Team collaboration patterns
- Advanced usage examples

---

### AI Integration Documentation

**Old Files** (2 files):
- `auggie_integration.md`
- `SIMPLE_AUGGIE_INTEGRATION.md`

**New Location**:
- **`docs/AI_INTEGRATION.md`** - Universal AI integration guide

**What Changed**:
- Focus on CLI-only integration (simpler approach)
- Universal patterns that work with any AI system
- Complete code examples for multiple AI platforms
- Removed HTTP bridge complexity
- Added troubleshooting and monitoring

---

## 🎯 Quick Reference

| Old File | New Location | Notes |
|----------|-------------|-------|
| CLAUDE_CODE_SETUP.md | docs/CLAUDE_SETUP.md | Section: Claude Code Setup |
| CLAUDE_DESKTOP_SETUP.md | docs/CLAUDE_SETUP.md | Section: Claude Desktop Setup |
| CLAUDE_HOOKS.md | docs/CLAUDE_SETUP.md | Section: Hooks & Integration |
| CLAUDE_INTEGRATION.md | docs/CLAUDE_SETUP.md | Section: Testing Integration |
| QUICK_START.md | docs/GETTING_STARTED.md | Section: 5-Minute Quick Start |
| SETUP.md | docs/GETTING_STARTED.md | Section: Installation Options |
| README_CLI.md | docs/GETTING_STARTED.md | Section: Essential Commands |
| MEMORY_GUIDE.md | docs/MEMORY_SYSTEM.md | Section: Memory Types & Usage |
| memory-system.md | docs/MEMORY_SYSTEM.md | Section: Memory Lifecycle |
| auggie_integration.md | docs/AI_INTEGRATION.md | Section: AI System Examples |
| SIMPLE_AUGGIE_INTEGRATION.md | docs/AI_INTEGRATION.md | Section: CLI Integration |

---

## ✅ Benefits of New Documentation Structure

### Eliminates Confusion
- **Before**: 4 different Claude setup guides with overlapping content
- **After**: 1 comprehensive guide with clear sections

### Reduces Maintenance
- **Before**: Update 11 files when making changes
- **After**: Update 4 consolidated files

### Improves Discoverability
- **Before**: Users had to read multiple files to get complete information
- **After**: Everything in one logical location

### Better Organization
- **Before**: Unclear which file to consult for specific tasks
- **After**: Clear hierarchy with priority markers (🔴🟡🟢⚪)

---

## 🔗 New Documentation Structure

```
docs/
├── CLAUDE_SETUP.md         # 🔴 Complete Claude integration guide
├── GETTING_STARTED.md      # 🔴 Fast-track setup (5 minutes)
├── MEMORY_SYSTEM.md        # 🟡 Memory types and usage
├── AI_INTEGRATION.md       # 🟡 Universal AI integration patterns
├── DEVELOPER.md            # 🟡 Developer documentation
├── ARCHITECTURE.md         # 🟡 Technical architecture
└── archive/
    └── deprecated-2025-10-01/  # Old files (this directory)
```

---

## 📚 Reading the New Documentation

### Start Here:
1. **`docs/GETTING_STARTED.md`** - If you're new to KuzuMemory
2. **`docs/CLAUDE_SETUP.md`** - If you're integrating with Claude
3. **`docs/MEMORY_SYSTEM.md`** - To understand memory types
4. **`docs/AI_INTEGRATION.md`** - To integrate with any AI system

### Priority System:
- 🔴 **Critical** - Read these first
- 🟡 **Important** - Read when you need specific functionality
- 🟢 **Standard** - Reference documentation
- ⚪ **Optional** - Advanced topics

---

## 🚨 Action Required

**If you have bookmarks or links to old documentation**:
1. Update bookmarks to point to new consolidated files
2. Update any scripts or automation referencing old paths
3. Inform team members of the new structure

**If you find missing information**:
1. Check the new consolidated files thoroughly
2. Report any genuinely missing content as an issue
3. All information from old files was preserved in consolidation

---

## 📅 Transition Period

- **Archive Date**: 2025-10-01
- **Transition Period**: 30 days (until 2025-10-31)
- **Deletion Date**: After 2025-10-31 (may be deleted)

**Recommendation**: Update all references to new documentation immediately.

---

## 🆘 Support

If you need help finding information that was in the old files:

1. Search the new consolidated files (Ctrl+F / Cmd+F)
2. Check the Quick Reference table above
3. Open an issue if information appears to be missing
4. Contact maintainers for migration assistance

---

**This consolidation improves documentation quality and eliminates user confusion. All content has been preserved and enhanced in the new files.**
