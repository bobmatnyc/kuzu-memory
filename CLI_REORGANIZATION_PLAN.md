# KuzuMemory CLI Reorganization Plan

**Date**: 2025-10-06
**Version**: 1.0
**Status**: Planning Phase

---

## Executive Summary

This document provides a comprehensive plan to reorganize the KuzuMemory CLI from its current 20+ command structure to a streamlined 6-command architecture following the "Single Path Principle" (ONE WAY TO DO ANYTHING).

### Current State
- **Total Commands**: 20+ top-level commands
- **Command Groups**: 3 groups (auggie, claude, mcp)
- **Structure**: Flat with some grouping
- **Files**: 14 CLI module files

### Target State
- **Total Commands**: 6 top-level commands
- **Command Groups**: 4 groups (install, memory, status, doctor)
- **Structure**: Hierarchical with clear categorization
- **Files**: Consolidate to 6-8 module files

---

## 1. Command Mapping: OLD → NEW

### 1.1 INIT Command (No Change)
**Purpose**: Initialize system

| OLD Command | NEW Command | Status | Notes |
|-------------|-------------|--------|-------|
| `kuzu-memory init` | `kuzu-memory init` | ✅ Keep | Already following single path |
| Options: `--force`, `--config-path` | Same options | ✅ Keep | Well-defined interface |

**Files Affected**:
- `src/kuzu_memory/cli/project_commands.py` (lines 29-145)

---

### 1.2 INSTALL Command Group (Consolidation)
**Purpose**: Install integrations for AI systems

#### Current Structure (FLAT)
```
kuzu-memory install <ai-system>        # Main install command
kuzu-memory list-installers            # List available
kuzu-memory install-status             # Show status
kuzu-memory uninstall <ai-system>      # Remove integration
kuzu-memory claude install             # DEPRECATED
kuzu-memory auggie install             # DEPRECATED
```

#### New Structure (HIERARCHICAL)
```
kuzu-memory install list               # List available installers
kuzu-memory install <ai-system>        # Install integration (UNCHANGED)
kuzu-memory install status             # Show installation status
kuzu-memory install remove <ai-system> # Remove integration (renamed from uninstall)
```

#### Mapping Table

| OLD Command | NEW Command | Status | Breaking? | Notes |
|-------------|-------------|--------|-----------|-------|
| `install <ai-system>` | `install <ai-system>` | ✅ Keep | No | Core command unchanged |
| `list-installers` | `install list` | ♻️ Move | Yes | Now subcommand |
| `install-status` | `install status` | ♻️ Move | Yes | Now subcommand |
| `uninstall <ai-system>` | `install remove <ai-system>` | ♻️ Rename | Yes | More intuitive name |
| `claude install` | `install claude-code` | 🗑️ Remove | Yes | Already deprecated |
| `auggie install` | `install auggie` | ✅ Keep | No | Maps to new structure |

**Files Affected**:
- `src/kuzu_memory/cli/install_commands_simple.py` (main implementation)
- `src/kuzu_memory/cli/install_commands.py` (may be redundant)
- `src/kuzu_memory/cli/claude_commands.py` (deprecated commands)
- `src/kuzu_memory/cli/auggie_commands.py` (may need refactoring)
- `src/kuzu_memory/cli/commands.py` (lines 319-322 - command registration)

---

### 1.3 MEMORY Command Group (NEW GROUP)
**Purpose**: Memory operations (store, recall, enhance)

#### Current Structure (FLAT)
```
kuzu-memory remember "text"            # Store memory (sync)
kuzu-memory learn "text"               # Store memory (async)
kuzu-memory recall "query"             # Query memories
kuzu-memory enhance "prompt"           # Enhance with context
kuzu-memory recent                     # Show recent memories
```

#### New Structure (HIERARCHICAL)
```
kuzu-memory memory store "text"        # Store memory (sync) - renamed from remember
kuzu-memory memory learn "text"        # Store memory (async) - KEEP
kuzu-memory memory recall "query"      # Query memories
kuzu-memory memory enhance "prompt"    # Enhance with context
kuzu-memory memory recent              # Show recent memories
```

#### Mapping Table

| OLD Command | NEW Command | Status | Breaking? | Notes |
|-------------|-------------|--------|-----------|-------|
| `remember "text"` | `memory store "text"` | ♻️ Rename | Yes | More professional term |
| `learn "text"` | `memory learn "text"` | ♻️ Move | Yes | Now subcommand |
| `recall "query"` | `memory recall "query"` | ♻️ Move | Yes | Now subcommand |
| `enhance "prompt"` | `memory enhance "prompt"` | ♻️ Move | Yes | Now subcommand |
| `recent` | `memory recent` | ♻️ Move | Yes | Now subcommand |

**Files Affected**:
- `src/kuzu_memory/cli/memory_commands.py` (entire file - 500+ lines)
  - `enhance` command (lines 21-123)
  - `learn` command (lines 125-260)
  - `recall` command (lines 262-340)
  - `remember` command (lines 342-494)
  - `recent` command (lines 496-end)
- `src/kuzu_memory/cli/commands.py` (lines 288-293 - command registration)

---

### 1.4 STATUS Command (Consolidation)
**Purpose**: System status and statistics

#### Current Structure (FLAT)
```
kuzu-memory stats                      # System statistics
kuzu-memory project                    # Project information
```

#### New Structure (HIERARCHICAL)
```
kuzu-memory status                     # Default: show basic stats
kuzu-memory status --validate          # Run health validation
kuzu-memory status --project           # Show project info
kuzu-memory status --detailed          # Detailed statistics
```

#### Mapping Table

| OLD Command | NEW Command | Status | Breaking? | Notes |
|-------------|-------------|--------|-----------|-------|
| `stats` | `status` | ♻️ Rename | Yes | Combine stats + project |
| `stats --detailed` | `status --detailed` | ♻️ Rename | Yes | Keep flag |
| `project` | `status --project` | ♻️ Move | Yes | Now a flag |
| N/A | `status --validate` | ✨ New | No | New health check shortcut |

**Files Affected**:
- `src/kuzu_memory/cli/project_commands.py`
  - `stats` command (lines 147-266)
  - `project` command (lines 268-396)
- `src/kuzu_memory/cli/commands.py` (lines 296-298 - command registration)

---

### 1.5 DOCTOR Command Group (NEW - Diagnostics)
**Purpose**: Diagnose and fix issues

#### Current Structure (NESTED IN MCP)
```
kuzu-memory mcp diagnose run           # Full diagnostics
kuzu-memory mcp diagnose config        # Check config
kuzu-memory mcp diagnose connection    # Test connection
kuzu-memory mcp diagnose tools         # Test tools
kuzu-memory mcp health                 # Health check
kuzu-memory mcp test                   # Test functionality
```

#### New Structure (TOP-LEVEL GROUP)
```
kuzu-memory doctor                     # Default: run full diagnostics (interactive)
kuzu-memory doctor --fix               # Auto-fix issues (non-interactive)
kuzu-memory doctor mcp                 # MCP-specific diagnostics
kuzu-memory doctor connection          # Test database connection
kuzu-memory doctor health              # Quick health check
```

#### Mapping Table

| OLD Command | NEW Command | Status | Breaking? | Notes |
|-------------|-------------|--------|-----------|-------|
| `mcp diagnose run` | `doctor` (default) | ♻️ Move | Yes | Top-level now |
| `mcp diagnose run --fix` | `doctor --fix` | ♻️ Move | Yes | Simpler path |
| `mcp diagnose config` | `doctor mcp` | ♻️ Consolidate | Yes | MCP-specific checks |
| `mcp diagnose connection` | `doctor connection` | ♻️ Move | Yes | General connection test |
| `mcp diagnose tools` | `doctor mcp` | ♻️ Consolidate | Yes | Part of MCP diagnostics |
| `mcp health` | `doctor health` | ♻️ Move | Yes | Quick health check |
| `mcp test` | `doctor mcp` | ♻️ Consolidate | Yes | Part of MCP diagnostics |

**Files Affected**:
- `src/kuzu_memory/cli/diagnostic_commands.py` (entire file - 500+ lines)
- `src/kuzu_memory/cli/mcp_commands.py` (lines 261-454 - health command and test)
- `src/kuzu_memory/cli/commands.py` (line 316 - command registration)

---

### 1.6 HELP Command (New)
**Purpose**: Enhanced help system

#### New Structure
```
kuzu-memory help                       # Show general help
kuzu-memory help <command>             # Show command-specific help
kuzu-memory help examples              # Show usage examples
kuzu-memory help tips                  # Show tips and best practices
```

#### Mapping Table

| OLD Command | NEW Command | Status | Breaking? | Notes |
|-------------|-------------|--------|-----------|-------|
| `examples` | `help examples` | ♻️ Move | Yes | Better categorization |
| `tips` | `help tips` | ♻️ Move | Yes | Better categorization |
| `--help` | `--help` | ✅ Keep | No | Standard flag |

**Files Affected**:
- `src/kuzu_memory/cli/utility_commands.py`
  - `examples` command (lines 182-306)
  - `tips` command (lines 308-413)
- New file needed: `src/kuzu_memory/cli/help_commands.py`

---

### 1.7 Commands to REMOVE or DEPRECATE

| Command | Action | Reason | Alternative |
|---------|--------|--------|-------------|
| `quickstart` | Keep (utility) | Useful onboarding | N/A |
| `demo` | Keep (utility) | Useful onboarding | N/A |
| `setup` | 🗑️ Remove | Redundant with init | Use `init` |
| `optimize` | 🗑️ Remove | Rarely used, complex | Document in config guide |
| `temporal-analysis` | 🗑️ Remove | Debug tool, not production | Move to dev tools |
| `cleanup` | 🗑️ Remove | Auto-cleanup is better | Document auto-cleanup |
| `create-config` | 🗑️ Remove | Auto-created by init | Use `init` |
| `mcp serve` | ✅ Keep | Required for MCP server | N/A |
| `mcp start` | 🗑️ Remove | Alias of serve | Use `mcp serve` |
| `mcp info` | ✅ Keep | Useful for debugging | N/A |
| `mcp config` | ✅ Keep | Useful for setup | N/A |
| `claude` (group) | 🗑️ Remove | Already deprecated | Use `install` |
| `auggie` (group) | ♻️ Refactor | Move commands to `install` | N/A |

**Files to Remove/Archive**:
- `src/kuzu_memory/cli/commands_backup.py` (already a backup file)
- `src/kuzu_memory/cli/auggie_cli.py` (old auggie implementation)

---

## 2. File-Level Changes

### 2.1 Files Requiring Major Refactoring

| File | Current LOC | Action | Reason |
|------|-------------|--------|--------|
| `commands.py` | 327 | ♻️ Refactor | Update all command registrations |
| `memory_commands.py` | 500+ | ♻️ Refactor | Convert to command group |
| `project_commands.py` | 500+ | ♻️ Split | Split into status + project |
| `diagnostic_commands.py` | 500+ | ♻️ Refactor | Move to top-level doctor |
| `install_commands_simple.py` | 300+ | ♻️ Refactor | Convert to command group |
| `mcp_commands.py` | 454 | ♻️ Split | Move diagnostics to doctor |
| `utility_commands.py` | 550+ | ♻️ Split | Move examples/tips to help |

### 2.2 New Files Needed

| File | Purpose | Estimated LOC |
|------|---------|---------------|
| `help_commands.py` | Help command group | 200 |
| `doctor_commands.py` | Doctor command group (refactored from diagnostic) | 400 |
| `status_commands.py` | Status command (refactored from project) | 300 |

### 2.3 Files to Archive/Remove

| File | Action | Reason |
|------|--------|--------|
| `commands_backup.py` | 🗑️ Delete | Already a backup |
| `auggie_cli.py` | 🗑️ Delete | Old implementation |
| `install_commands.py` | 🗑️ Delete | Redundant with simple version |
| `claude_commands.py` | 🗑️ Archive | Deprecated commands |

---

## 3. Test Files Requiring Updates

### 3.1 CLI Test Files
```
tests/test_rich_cli.py                 # Update command names
tests/test_cli_adapter.py              # Update command names
tests/mcp/fixtures/mock_clients.py     # Update MCP command paths
```

### 3.2 Integration Test Patterns
```python
# OLD pattern
result = runner.invoke(cli, ['remember', 'test memory'])
result = runner.invoke(cli, ['list-installers'])
result = runner.invoke(cli, ['mcp', 'diagnose', 'run'])

# NEW pattern
result = runner.invoke(cli, ['memory', 'store', 'test memory'])
result = runner.invoke(cli, ['install', 'list'])
result = runner.invoke(cli, ['doctor'])
```

### 3.3 Test Coverage Needed
- [ ] Test backward compatibility warnings
- [ ] Test alias redirects (if implemented)
- [ ] Test new command groupings
- [ ] Test help system
- [ ] Test error messages for deprecated commands

---

## 4. Documentation Updates Required

### 4.1 Primary Documentation Files

| File | Update Required | Priority | Estimated Changes |
|------|-----------------|----------|-------------------|
| `CLAUDE.md` | Complete rewrite of CLI section | 🔴 Critical | 200+ lines |
| `README.md` | Update quick start and examples | 🔴 Critical | 50+ lines |
| `docs/GETTING_STARTED.md` | Update all command examples | 🔴 Critical | 100+ lines |
| `docs/CLAUDE_SETUP.md` | Update installation commands | 🟡 High | 30+ lines |
| `docs/AI_INTEGRATION.md` | Update install commands | 🟡 High | 40+ lines |
| `docs/MCP_DIAGNOSTICS.md` | Update doctor commands | 🟡 High | 60+ lines |
| `docs/MCP_TESTING_GUIDE.md` | Update command paths | 🟡 High | 30+ lines |
| `docs/developer/cli-reference.md` | Complete rewrite | 🟡 High | 300+ lines |
| `docs/MEMORY_SYSTEM.md` | Update memory commands | 🟢 Medium | 20+ lines |
| `docs/ARCHITECTURE.md` | Update CLI architecture section | 🟢 Medium | 40+ lines |

### 4.2 Code Comment Updates
- Update inline help text in all command files
- Update docstrings with new command paths
- Update example code in comments

### 4.3 Configuration Examples
- Update all `.kuzu_memory/config.yaml` examples
- Update MCP configuration examples
- Update Claude Desktop configuration examples

---

## 5. Implementation Order (Phased Approach)

### Phase 1: Foundation (Week 1)
**Goal**: Establish new command structure without breaking existing

1. ✅ **Create new command group files**
   - Create `help_commands.py`
   - Create `doctor_commands.py` (copy from diagnostic_commands.py)
   - Create `status_commands.py` (extract from project_commands.py)

2. ✅ **Implement new commands with OLD commands still working**
   - Register new commands alongside old ones
   - Add deprecation warnings to old commands
   - Test that both work simultaneously

3. ✅ **Add backward compatibility layer**
   - Implement command aliases
   - Add deprecation warnings with migration guidance
   - Log usage of deprecated commands

**Deliverables**:
- All new commands working
- Old commands working with warnings
- Tests passing for both old and new commands

---

### Phase 2: Memory & Install Groups (Week 2)
**Goal**: Migrate high-usage commands to new structure

4. ✅ **Refactor memory commands to group**
   - Update `memory_commands.py` to use `@click.group()`
   - Register subcommands (store, learn, recall, enhance, recent)
   - Add backward compatibility for top-level commands
   - Update tests

5. ✅ **Refactor install commands to group**
   - Update `install_commands_simple.py` to use nested structure
   - Move `list-installers` → `install list`
   - Move `install-status` → `install status`
   - Rename `uninstall` → `install remove`
   - Update tests

**Deliverables**:
- `memory` and `install` groups working
- Backward compatibility maintained
- Tests updated and passing

---

### Phase 3: Status & Doctor Groups (Week 3)
**Goal**: Consolidate diagnostic and status commands

6. ✅ **Implement status command consolidation**
   - Merge `stats` and `project` into unified `status` command
   - Add `--validate`, `--project`, `--detailed` flags
   - Update tests

7. ✅ **Implement doctor command group**
   - Extract diagnostics from MCP commands
   - Create top-level `doctor` command
   - Move `mcp diagnose` → `doctor mcp`
   - Move `mcp health` → `doctor health`
   - Move `mcp test` → `doctor mcp`
   - Update tests

**Deliverables**:
- `status` command working with all options
- `doctor` group fully functional
- MCP commands refactored
- Tests updated and passing

---

### Phase 4: Help System & Cleanup (Week 4)
**Goal**: Finalize new structure and remove deprecated commands

8. ✅ **Implement help command group**
   - Create `help_commands.py`
   - Move `examples` → `help examples`
   - Move `tips` → `help tips`
   - Add `help <command>` for command-specific help
   - Update tests

9. ✅ **Remove deprecated commands and files**
   - Remove `setup`, `optimize`, `temporal-analysis`, `cleanup`
   - Remove `mcp start` (alias)
   - Remove `claude` group
   - Archive old files
   - Clean up imports

10. ✅ **Update main CLI registration**
    - Update `commands.py` with final command structure
    - Remove all deprecated command registrations
    - Add final help text and examples

**Deliverables**:
- Help system fully functional
- All deprecated commands removed
- Clean command structure
- All tests passing

---

### Phase 5: Documentation & Testing (Week 5)
**Goal**: Comprehensive documentation and testing

11. ✅ **Update all documentation**
    - Update `CLAUDE.md` (critical)
    - Update `README.md` (critical)
    - Update all docs/ files
    - Update inline help text
    - Update examples

12. ✅ **Comprehensive testing**
    - Full CLI test suite
    - Integration tests
    - MCP tests
    - Manual testing of all commands
    - Performance benchmarks

13. ✅ **Create migration guide**
    - Document all breaking changes
    - Provide migration scripts if needed
    - Create command translation table
    - Add FAQ for common issues

**Deliverables**:
- All documentation updated
- Full test coverage
- Migration guide published
- Release notes prepared

---

## 6. Backward Compatibility Strategy

### 6.1 Deprecation Warnings

Implement three-tier deprecation system:

```python
# Tier 1: WARNING (v1.2.0) - 3 months notice
@click.command()
def remember(...):
    """
    [DEPRECATED] Use 'kuzu-memory memory store' instead.
    This command will be removed in v1.5.0.
    """
    click.echo("⚠️  WARNING: 'remember' is deprecated. Use 'memory store' instead.", err=True)
    # ... existing implementation ...

# Tier 2: ERROR with redirect (v1.3.0-v1.4.0)
@click.command()
def remember(...):
    """[DEPRECATED - Will be removed soon]"""
    click.echo("⚠️  'remember' has been removed. Use 'memory store' instead.", err=True)
    click.echo("Running 'memory store' for you this time...", err=True)
    # Redirect to new command
    ctx.invoke(memory_store, ...)

# Tier 3: REMOVED (v1.5.0)
# Command completely removed from CLI
```

### 6.2 Alias System

Create command aliases for smooth transition:

```python
# In commands.py
# Add aliases for commonly-used commands
cli.add_command(remember, name='remember')  # Original name
cli.add_command(memory_store, name='remember')  # Alias during transition
```

### 6.3 Migration Helper

Add migration detection and guidance:

```bash
# When old command is used
$ kuzu-memory remember "test"

⚠️  DEPRECATION WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The command 'remember' is deprecated and will be removed in v1.5.0.

Please use instead:
  kuzu-memory memory store "test"

To see all new commands:
  kuzu-memory help

For migration guide:
  https://github.com/kuzu-memory/kuzu-memory/docs/MIGRATION.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💾 Storing memory: test
✅ Memory stored successfully!
```

---

## 7. Risk Assessment

### 7.1 Breaking Changes

| Change | Impact | Risk | Mitigation |
|--------|--------|------|------------|
| `remember` → `memory store` | 🔴 High | High usage command | Alias + 3-month deprecation |
| `recall` → `memory recall` | 🔴 High | High usage command | Alias + 3-month deprecation |
| `enhance` → `memory enhance` | 🔴 High | High usage command | Alias + 3-month deprecation |
| `stats` → `status` | 🟡 Medium | Moderate usage | Alias + clear migration docs |
| `mcp diagnose` → `doctor` | 🟢 Low | Developer-only command | Update docs only |
| `list-installers` → `install list` | 🟢 Low | Low usage | Update docs only |

### 7.2 Testing Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Missing test coverage for new commands | Medium | High | Comprehensive test plan |
| Breaking existing integrations | High | High | Backward compatibility layer |
| Documentation out of sync | High | Medium | Automated doc checks |
| Performance regression | Low | Medium | Benchmark tests |

### 7.3 Adoption Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| User confusion during transition | High | High | Clear migration guide + warnings |
| Scripts breaking in production | High | High | Long deprecation period (3 months) |
| Support burden increase | Medium | Medium | Comprehensive FAQ + examples |

---

## 8. Success Metrics

### 8.1 Code Quality Metrics
- [ ] CLI module count reduced from 14 to 6-8 files
- [ ] Command count reduced from 20+ to 6 top-level
- [ ] Average command nesting: 2 levels (command → subcommand)
- [ ] Test coverage maintained at >90%
- [ ] All linting checks passing

### 8.2 User Experience Metrics
- [ ] Help command usage <100ms response time
- [ ] All commands follow consistent naming pattern
- [ ] Each command has ONE clear path (no aliases in docs)
- [ ] Migration guide covers 100% of breaking changes

### 8.3 Development Metrics
- [ ] Code duplication reduced by >30%
- [ ] New command addition takes <1 hour
- [ ] Documentation auto-generated from code
- [ ] CI/CD pipeline passes in <5 minutes

---

## 9. New CLI Structure (Final)

```bash
kuzu-memory --version
kuzu-memory --help

🔧 INITIALIZATION
  kuzu-memory init [--force] [--config-path PATH]

🚀 INSTALLATION (AI System Integration)
  kuzu-memory install list
  kuzu-memory install <ai-system> [OPTIONS]
  kuzu-memory install status
  kuzu-memory install remove <ai-system>

🧠 MEMORY OPERATIONS
  kuzu-memory memory store "text" [OPTIONS]        # Sync storage (was: remember)
  kuzu-memory memory learn "text" [OPTIONS]        # Async storage
  kuzu-memory memory recall "query" [OPTIONS]      # Query memories
  kuzu-memory memory enhance "prompt" [OPTIONS]    # Enhance prompts
  kuzu-memory memory recent [OPTIONS]              # Show recent

📊 STATUS & INFORMATION
  kuzu-memory status [--validate] [--project] [--detailed]

🩺 DIAGNOSTICS & TROUBLESHOOTING
  kuzu-memory doctor [--fix]                       # Full diagnostics
  kuzu-memory doctor mcp                           # MCP-specific
  kuzu-memory doctor connection                    # Connection test
  kuzu-memory doctor health                        # Quick health check

❓ HELP SYSTEM
  kuzu-memory help [<command>]                     # Command help
  kuzu-memory help examples                        # Usage examples
  kuzu-memory help tips                            # Best practices

🤖 MCP SERVER (Required for Claude Desktop)
  kuzu-memory mcp serve [OPTIONS]                  # Run MCP server
  kuzu-memory mcp info                             # Server information
  kuzu-memory mcp config [--output PATH]           # Generate config

🎯 UTILITIES (Keep for onboarding)
  kuzu-memory quickstart                           # Interactive guide
  kuzu-memory demo                                 # Feature demo
```

---

## 10. Code Patterns

### 10.1 Command Group Template

```python
# src/kuzu_memory/cli/memory_commands.py

import click
from .cli_utils import rich_print, rich_panel

@click.group(name='memory')
@click.pass_context
def memory_group(ctx):
    """
    🧠 Memory operations (store, recall, enhance).

    Manage memory storage, retrieval, and context enhancement
    for AI applications.

    Use 'kuzu-memory memory COMMAND --help' for detailed help.
    """
    pass

@memory_group.command(name='store')
@click.argument('content', required=True)
@click.option('--source', help='Memory source identifier')
@click.pass_context
def store(ctx, content: str, source: str | None):
    """
    💾 Store a memory for future recall (synchronous).

    Stores content immediately in the project memory database.
    Use 'learn' for async background storage.

    \b
    Examples:
      kuzu-memory memory store "We use Python 3.11+"
      kuzu-memory memory store "Alice is the team lead" --source user-profile
    """
    # Implementation
    pass

# Export for main CLI
__all__ = ['memory_group']
```

### 10.2 Command Registration Pattern

```python
# src/kuzu_memory/cli/commands.py

from .memory_commands import memory_group
from .install_commands import install_group
from .doctor_commands import doctor_group
from .help_commands import help_group
from .status_commands import status

# Register command groups
cli.add_command(memory_group, name='memory')
cli.add_command(install_group, name='install')
cli.add_command(doctor_group, name='doctor')
cli.add_command(help_group, name='help')

# Register single commands
cli.add_command(init)
cli.add_command(status)
```

### 10.3 Deprecation Warning Pattern

```python
def _show_deprecation_warning(old_cmd: str, new_cmd: str, removal_version: str):
    """Show consistent deprecation warning."""
    message = f"""
⚠️  DEPRECATION WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The command '{old_cmd}' is deprecated and will be removed in {removal_version}.

Please use instead:
  {new_cmd}

To see all commands:
  kuzu-memory help

For migration guide:
  https://github.com/kuzu-memory/kuzu-memory/docs/MIGRATION.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    rich_print(message, style="yellow")
```

---

## 11. File Structure (After Reorganization)

```
src/kuzu_memory/cli/
├── __init__.py                    # Exports main CLI
├── commands.py                    # Main CLI entry point (300 lines)
├── cli_utils.py                   # Shared utilities (keep as-is)
│
├── memory_commands.py             # Memory group (400 lines)
│   ├── memory_group()
│   ├── store()
│   ├── learn()
│   ├── recall()
│   ├── enhance()
│   └── recent()
│
├── install_commands.py            # Install group (400 lines)
│   ├── install_group()
│   ├── list_installers()
│   ├── install_ai_system()
│   ├── status()
│   └── remove()
│
├── status_commands.py             # Status command (300 lines)
│   └── status()
│
├── doctor_commands.py             # Doctor group (500 lines)
│   ├── doctor_group()
│   ├── diagnose_full()
│   ├── diagnose_mcp()
│   ├── diagnose_connection()
│   └── health()
│
├── help_commands.py               # Help group (200 lines)
│   ├── help_group()
│   ├── show_command_help()
│   ├── examples()
│   └── tips()
│
├── project_commands.py            # Project utilities (200 lines)
│   ├── init()
│   ├── quickstart()
│   └── demo()
│
└── mcp_commands.py                # MCP server (200 lines)
    ├── mcp_group()
    ├── serve()
    ├── info()
    └── config()
```

**Total**: 8 files, ~2,500 LOC (down from 14 files, ~3,500 LOC)

---

## 12. Next Steps

### Immediate Actions (Week 1)
1. ✅ Review and approve this plan
2. ✅ Create feature branch: `feature/cli-reorganization`
3. ✅ Set up tracking issues for each phase
4. ✅ Begin Phase 1 implementation

### Communication Plan
1. **Internal Team**:
   - Share this plan with development team
   - Schedule kick-off meeting
   - Set up daily standups during implementation

2. **External Users**:
   - Publish blog post announcing changes
   - Update GitHub README with migration notice
   - Create migration checklist

3. **Documentation**:
   - Create MIGRATION.md guide
   - Update CHANGELOG.md with breaking changes
   - Add migration scripts if needed

### Review Checkpoints
- [ ] End of Week 1: Review Phase 1 completion
- [ ] End of Week 2: Review Phase 2 completion
- [ ] End of Week 3: Review Phase 3 completion
- [ ] End of Week 4: Review Phase 4 completion
- [ ] End of Week 5: Final review and release preparation

---

## Appendix A: Full Command Comparison

### Before Reorganization (v1.1.x)
```
kuzu-memory [20+ commands]
├── init
├── remember
├── learn
├── recall
├── enhance
├── recent
├── stats
├── project
├── install <ai-system>
├── list-installers
├── install-status
├── uninstall <ai-system>
├── auggie
│   └── install
├── claude
│   └── install
├── mcp
│   ├── serve
│   ├── start
│   ├── test
│   ├── info
│   ├── config
│   ├── health
│   └── diagnose
│       ├── run
│       ├── config
│       ├── connection
│       └── tools
├── examples
├── tips
├── setup
├── optimize
├── temporal-analysis
├── cleanup
├── create-config
├── quickstart
└── demo
```

### After Reorganization (v1.2.0)
```
kuzu-memory [6 top-level + 2 utilities]
├── init
├── install
│   ├── list
│   ├── <ai-system>
│   ├── status
│   └── remove <ai-system>
├── memory
│   ├── store
│   ├── learn
│   ├── recall
│   ├── enhance
│   └── recent
├── status [--validate] [--project] [--detailed]
├── doctor [--fix]
│   ├── (default: full diagnostics)
│   ├── mcp
│   ├── connection
│   └── health
├── help [<command>]
│   ├── (default: general help)
│   ├── examples
│   └── tips
├── mcp
│   ├── serve
│   ├── info
│   └── config
├── quickstart
└── demo
```

---

## Appendix B: Migration Script Template

```bash
#!/bin/bash
# migrate-cli-commands.sh
# Helps users migrate their scripts to new CLI structure

echo "🔍 Scanning for old KuzuMemory CLI commands..."

# Find all shell scripts using old commands
find . -type f \( -name "*.sh" -o -name "*.bash" \) -exec grep -l "kuzu-memory" {} \; | while read file; do
    echo "Checking: $file"

    # Check for deprecated commands
    if grep -q "kuzu-memory remember" "$file"; then
        echo "  ⚠️  Found 'remember' → Suggest: memory store"
    fi

    if grep -q "kuzu-memory recall" "$file"; then
        echo "  ⚠️  Found 'recall' → Suggest: memory recall"
    fi

    if grep -q "kuzu-memory enhance" "$file"; then
        echo "  ⚠️  Found 'enhance' → Suggest: memory enhance"
    fi

    if grep -q "kuzu-memory stats" "$file"; then
        echo "  ⚠️  Found 'stats' → Suggest: status"
    fi

    if grep -q "kuzu-memory mcp diagnose" "$file"; then
        echo "  ⚠️  Found 'mcp diagnose' → Suggest: doctor"
    fi
done

echo ""
echo "✅ Scan complete!"
echo "📖 See migration guide: https://github.com/kuzu-memory/kuzu-memory/docs/MIGRATION.md"
```

---

## Appendix C: References

### Related Documentation
- [CLAUDE.md](/Users/masa/Projects/managed/kuzu-memory/CLAUDE.md) - Primary project instructions
- [README.md](/Users/masa/Projects/managed/kuzu-memory/README.md) - Project overview
- [docs/developer/cli-reference.md](/Users/masa/Projects/managed/kuzu-memory/docs/developer/cli-reference.md) - Current CLI reference
- [docs/MCP_DIAGNOSTICS.md](/Users/masa/Projects/managed/kuzu-memory/docs/MCP_DIAGNOSTICS.md) - MCP diagnostics guide

### Code References
- Main CLI: `src/kuzu_memory/cli/commands.py`
- Memory commands: `src/kuzu_memory/cli/memory_commands.py`
- Install commands: `src/kuzu_memory/cli/install_commands_simple.py`
- Diagnostic commands: `src/kuzu_memory/cli/diagnostic_commands.py`
- MCP commands: `src/kuzu_memory/cli/mcp_commands.py`

---

**End of CLI Reorganization Plan**

*This is a living document and will be updated as implementation progresses.*
