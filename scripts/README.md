# Scripts Directory

This directory contains utility scripts for KuzuMemory.

## ⚠️ Deprecation Notice

**The standalone installer scripts in this directory are DEPRECATED and will be REMOVED in v2.0.0 (planned: 2026 Q1).**

Please use the integrated CLI commands instead:

```bash
# List available installers
kuzu-memory list-installers

# Install Claude Desktop integration (pipx)
kuzu-memory install claude-desktop

# Install Claude Desktop (home directory)
kuzu-memory install claude-desktop-home --mode standalone

# Install Auggie/Claude integration
kuzu-memory install auggie

# Install universal integration
kuzu-memory install universal

# Check installation status
kuzu-memory install-status

# Get help
kuzu-memory install --help
```

## Migration Guide

### Old Scripts → New Commands

| Old Script | New Command |
|-----------|-------------|
| `python scripts/install-claude-desktop.py` | `kuzu-memory install claude-desktop` |
| `python scripts/install-claude-desktop-home.py` | `kuzu-memory install claude-desktop-home` |
| `python scripts/install-claude-desktop.py --dry-run` | `kuzu-memory install claude-desktop --dry-run` |
| `python scripts/install-claude-desktop-home.py --mode standalone` | `kuzu-memory install claude-desktop-home --mode standalone` |

### Installation Options

All new installer commands support:
- `--force` - Force reinstall even if already installed
- `--dry-run` - Preview changes without modifying files
- `--verbose` - Show detailed installation steps
- `--mode [auto|wrapper|standalone]` - Installation mode (for home installer)
- `--backup-dir PATH` - Custom backup directory
- `--memory-db PATH` - Custom memory database location

## Available Scripts

### Deprecated (Use CLI commands instead)

- ⚠️ `install-claude-desktop.py` - **DEPRECATED** - Use `kuzu-memory install claude-desktop`
- ⚠️ `install-claude-desktop-home.py` - **DEPRECATED** - Use `kuzu-memory install claude-desktop-home`

### Utility Scripts

- `install.py` - Legacy installer (use `kuzu-memory install` instead)
- `install-pipx.py` - Utility to install KuzuMemory via pipx

## Why the Change?

The integrated CLI commands provide:
- ✅ Unified interface for all installation methods
- ✅ Better error handling and validation
- ✅ Consistent options across all installers
- ✅ Built-in help and documentation
- ✅ Installation status tracking
- ✅ Easy uninstallation
- ✅ Dry-run mode for all operations

## Need Help?

```bash
# Get comprehensive help
kuzu-memory install --help

# List all available installers with descriptions
kuzu-memory list-installers

# Check what's currently installed
kuzu-memory install-status
```

For more information, see:
- [CLAUDE_SETUP.md](../docs/CLAUDE_SETUP.md) - Complete Claude integration guide
- [GETTING_STARTED.md](../docs/GETTING_STARTED.md) - Quick start guide
- [CLAUDE.md](../CLAUDE.md) - Project instructions
