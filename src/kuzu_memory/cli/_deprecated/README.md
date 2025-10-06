# Deprecated CLI Commands

This directory contains CLI command files that have been deprecated as part of the CLI reorganization.

## Why Deprecated

These files were part of the old CLI structure that had too many top-level commands and lacked proper organization. They have been replaced with a cleaner, more hierarchical structure.

## Migration Path

### Old Commands → New Commands

**Auggie Commands** (`auggie_commands.py`):
- Merged into `install` group
- Use `kuzu-memory install add auggie` instead

**Claude Commands** (`claude_commands.py`):
- Merged into `install` group
- Use `kuzu-memory install add claude-code` or `kuzu-memory install add claude-desktop` instead

**Install Commands** (`install_commands.py`):
- Replaced by `install_commands_simple.py` with group structure
- Use `kuzu-memory install <subcommand>` instead

**MCP Commands** (`mcp_commands.py`):
- Merged into `doctor` group
- Use `kuzu-memory doctor mcp` for MCP diagnostics instead

**Diagnostic Commands** (`diagnostic_commands.py`):
- Merged into `doctor` group
- Use `kuzu-memory doctor` for all diagnostics instead

**Utility Commands** (`utility_commands.py`):
- Merged into `help` group
- Use `kuzu-memory help examples` and `kuzu-memory help tips` instead

## New CLI Structure

The new CLI has only **6 top-level commands**:

1. `init` - Initialize project
2. `install` - Manage integrations (add, remove, list, status)
3. `memory` - Memory operations (store, learn, recall, enhance, recent)
4. `status` - System status and info
5. `doctor` - Diagnostics and health checks
6. `help` - Help and examples

Plus `quickstart` and `demo` for onboarding.

## Removal Timeline

These files will be completely removed in v2.0.0. They are kept here temporarily for reference.
