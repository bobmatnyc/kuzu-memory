# KuzuMemory Home Installation Guide

> **⚠️ DEPRECATION NOTICE - Standalone Scripts Deprecated ⚠️**
>
> The standalone script `python scripts/install-claude-desktop-home.py` referenced throughout
> this document is **DEPRECATED** and will be removed in v2.0.0.
>
> **Please use the integrated CLI command instead:**
> ```bash
> kuzu-memory install claude-desktop-home [options]
> ```
>
> All script examples in this document work with the new CLI by replacing:
> - `python scripts/install-claude-desktop-home.py` → `kuzu-memory install claude-desktop-home`
>
> See the **Migration Guide** section below for complete details.

---

This guide covers the **home-based installation** of KuzuMemory that installs everything in `~/.kuzu-memory/` without requiring pipx or system-wide installations.

## Overview

The home-based installer provides a self-contained installation that:

- ✅ Installs entirely within `~/.kuzu-memory/` directory
- ✅ No pipx dependency required
- ✅ Supports both wrapper mode (uses system package) and standalone mode (local copy)
- ✅ Automatically configures Claude Desktop MCP integration
- ✅ Idempotent and safe to run multiple times
- ✅ Easy to update and uninstall

## Installation Modes

### Auto Mode (Recommended)

Automatically detects the best installation mode:

- **Wrapper Mode**: If kuzu-memory is installed via pip/pipx, uses the system installation
- **Standalone Mode**: If no system installation found, copies package to `~/.kuzu-memory/lib/`

```bash
python scripts/install-claude-desktop-home.py
```

### Wrapper Mode (Lightweight)

Uses existing system installation (requires kuzu-memory installed via pip/pipx):

```bash
# First install kuzu-memory system-wide
pip install kuzu-memory
# or
pipx install kuzu-memory

# Then install as wrapper
python scripts/install-claude-desktop-home.py --mode wrapper
```

**Advantages:**
- Minimal disk space (~1KB for scripts)
- Automatic updates when system package updates
- Single source of truth for package code

**Requirements:**
- kuzu-memory must be installed via pip/pipx
- Python environment must be accessible

### Standalone Mode (Self-Contained)

Copies entire package to `~/.kuzu-memory/lib/`:

```bash
python scripts/install-claude-desktop-home.py --mode standalone
```

**Advantages:**
- No external dependencies on system Python packages
- Fully isolated installation
- Works even if system installation changes

**Disadvantages:**
- Larger disk space (~2-5MB for package)
- Must manually update when new versions released

## Directory Structure

After installation, `~/.kuzu-memory/` contains:

```
~/.kuzu-memory/
├── bin/
│   ├── kuzu-memory-mcp-server    # Main Python launcher (executable)
│   └── run-mcp-server.sh         # Shell wrapper fallback (executable)
├── lib/
│   └── kuzu_memory/              # Package files (standalone mode only)
├── memorydb/                      # Database storage directory
├── config.yaml                    # Configuration file
├── .version                       # Installed version
└── .installation_type             # "wrapper" or "standalone"
```

## Quick Start

### Install (Auto Mode)

```bash
# Clone repository or download script
cd kuzu-memory

# Run installer (auto-detects best mode)
python scripts/install-claude-desktop-home.py

# Restart Claude Desktop
```

### Install with Specific Mode

```bash
# Force wrapper mode
python scripts/install-claude-desktop-home.py --mode wrapper

# Force standalone mode
python scripts/install-claude-desktop-home.py --mode standalone
```

### Update Installation

```bash
# Update existing installation (preserves database)
python scripts/install-claude-desktop-home.py --update
```

### Validate Installation

```bash
# Check installation health
python scripts/install-claude-desktop-home.py --validate
```

### Uninstall

```bash
# Remove installation (backs up Claude config)
python scripts/install-claude-desktop-home.py --uninstall
```

## Command Reference

### Installation Commands

| Command | Description |
|---------|-------------|
| `--mode {auto\|wrapper\|standalone}` | Installation mode (default: auto) |
| `--force` | Force installation even if exists |
| `--update` | Update existing installation |
| `--uninstall` | Remove installation completely |
| `--validate` | Validate installation health |
| `--dry-run` | Show what would be done without changes |
| `--verbose` | Enable detailed output |
| `--backup-dir PATH` | Custom backup directory |

### Examples

```bash
# Dry run to see what would happen
python scripts/install-claude-desktop-home.py --dry-run --verbose

# Force reinstall
python scripts/install-claude-desktop-home.py --force

# Install with custom backup location
python scripts/install-claude-desktop-home.py --backup-dir ~/my-backups

# Validate and show details
python scripts/install-claude-desktop-home.py --validate --verbose
```

## How It Works

### Wrapper Mode Flow

1. Detects system Python with kuzu-memory installed
2. Creates launcher scripts in `~/.kuzu-memory/bin/`
3. Launcher scripts use system Python and package
4. Configures Claude Desktop to use launcher
5. Database stored in `~/.kuzu-memory/memorydb/`

### Standalone Mode Flow

1. Copies package from `src/kuzu_memory/` to `~/.kuzu-memory/lib/`
2. Creates launcher scripts that add lib to Python path
3. Launcher scripts use local package copy
4. Configures Claude Desktop to use launcher
5. Database stored in `~/.kuzu-memory/memorydb/`

### Launcher Scripts

The installer creates two launcher scripts:

#### kuzu-memory-mcp-server (Python)

```python
#!/usr/bin/env python3
"""
KuzuMemory MCP Server Launcher
"""
import os
import sys

# Set database path
os.environ.setdefault('KUZU_MEMORY_DB', '~/.kuzu-memory/memorydb')
os.environ['KUZU_MEMORY_MODE'] = 'mcp'

# Import and run (wrapper or standalone)
from kuzu_memory.mcp.run_server import main

if __name__ == '__main__':
    main()
```

#### run-mcp-server.sh (Shell)

```bash
#!/bin/bash
# Fallback shell wrapper
export KUZU_MEMORY_DB="~/.kuzu-memory/memorydb"
export KUZU_MEMORY_MODE="mcp"

exec python3 "~/.kuzu-memory/bin/kuzu-memory-mcp-server" "$@"
```

## Claude Desktop Configuration

The installer automatically updates `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "/Users/username/.kuzu-memory/bin/kuzu-memory-mcp-server",
      "args": [],
      "env": {
        "KUZU_MEMORY_DB": "/Users/username/.kuzu-memory/memorydb",
        "KUZU_MEMORY_MODE": "mcp"
      }
    }
  }
}
```

### Configuration Paths by OS

| OS | Configuration Path |
|----|-------------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

## Updating Installations

### Update Wrapper Installation

```bash
# Update system package first
pip install --upgrade kuzu-memory
# or
pipx upgrade kuzu-memory

# Then update home installation
python scripts/install-claude-desktop-home.py --update
```

### Update Standalone Installation

```bash
# Pull latest code
git pull

# Update installation (copies new package)
python scripts/install-claude-desktop-home.py --mode standalone --force
```

## Troubleshooting

### Installation Issues

**Problem**: "System installation not found for wrapper mode"

```bash
# Solution: Install kuzu-memory first or use standalone mode
pip install kuzu-memory
# or
python scripts/install-claude-desktop-home.py --mode standalone
```

**Problem**: "Installation already exists"

```bash
# Solution: Use --force or --update
python scripts/install-claude-desktop-home.py --force
```

### Runtime Issues

**Problem**: Claude Desktop can't find MCP tools

```bash
# Check installation
python scripts/install-claude-desktop-home.py --validate

# Verify launcher is executable
ls -l ~/.kuzu-memory/bin/kuzu-memory-mcp-server

# Check Claude Desktop config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Problem**: Database errors

```bash
# Verify database directory
ls -la ~/.kuzu-memory/memorydb/

# Reinitialize if needed
~/.kuzu-memory/bin/kuzu-memory-mcp-server init --force
```

### Validation Checks

```bash
# Full validation with details
python scripts/install-claude-desktop-home.py --validate --verbose

# Test launcher directly
~/.kuzu-memory/bin/kuzu-memory-mcp-server stats

# Check installation type
cat ~/.kuzu-memory/.installation_type

# Check installed version
cat ~/.kuzu-memory/.version
```

## 🔄 Migration from Standalone Scripts

**All standalone script commands have CLI equivalents:**

| Standalone Script (DEPRECATED) | New CLI Command (RECOMMENDED) |
|-------------------------------|------------------------------|
| `python scripts/install-claude-desktop-home.py` | `kuzu-memory install claude-desktop-home` |
| `python scripts/install-claude-desktop-home.py --mode wrapper` | `kuzu-memory install claude-desktop-home --mode wrapper` |
| `python scripts/install-claude-desktop-home.py --mode standalone` | `kuzu-memory install claude-desktop-home --mode standalone` |
| `python scripts/install-claude-desktop-home.py --update` | `kuzu-memory install claude-desktop-home --force` |
| `python scripts/install-claude-desktop-home.py --validate` | `kuzu-memory install-status` |
| `python scripts/install-claude-desktop-home.py --uninstall` | `kuzu-memory uninstall claude-desktop-home` |
| `python scripts/install-claude-desktop-home.py --dry-run` | `kuzu-memory install claude-desktop-home --dry-run` |

**Benefits of new CLI commands:**
- ✅ Unified interface across all installers
- ✅ Better error handling and validation
- ✅ Consistent with other KuzuMemory commands
- ✅ No need to locate script files
- ✅ Works from anywhere in your system

**Removal Timeline:** Standalone scripts will be removed in **v2.0.0** (planned for 2026 Q1)

---

## Migration Guide

### From pipx Installation

```bash
# Current: Using pipx
pipx list  # Shows kuzu-memory

# Install home version as wrapper
python scripts/install-claude-desktop-home.py --mode wrapper

# Restart Claude Desktop
# (pipx installation remains, used by wrapper)

# Optional: Remove pipx after confirming it works
# pipx uninstall kuzu-memory
```

### From System pip Installation

```bash
# Current: Using system pip
pip list | grep kuzu-memory

# Install home version as wrapper
python scripts/install-claude-desktop-home.py --mode wrapper

# Restart Claude Desktop
# (pip installation remains, used by wrapper)
```

### To Standalone Installation

```bash
# If you want full isolation, use standalone
python scripts/install-claude-desktop-home.py --mode standalone --force

# Now you can remove system installation if desired
pip uninstall kuzu-memory
# or
pipx uninstall kuzu-memory
```

## Comparison: Home vs pipx Installation

| Feature | Home Installation | pipx Installation |
|---------|------------------|------------------|
| **Installation Location** | `~/.kuzu-memory/` | `~/.local/pipx/venvs/` |
| **Requires pipx** | ❌ No | ✅ Yes |
| **Isolated Environment** | ✅ Yes | ✅ Yes |
| **Database Location** | `~/.kuzu-memory/memorydb/` | `~/.kuzu-memory/memorydb/` |
| **Configuration** | `~/.kuzu-memory/config.yaml` | System-wide |
| **Update Command** | `--update` flag | `pipx upgrade` |
| **Uninstall Command** | `--uninstall` flag | `pipx uninstall` |
| **Disk Space (wrapper)** | ~1KB | ~10-20MB |
| **Disk Space (standalone)** | ~5MB | ~10-20MB |
| **Claude Desktop Setup** | ✅ Automatic | ✅ Automatic |

## Best Practices

### For Development

```bash
# Use wrapper mode during development
pip install -e .  # Editable install
python scripts/install-claude-desktop-home.py --mode wrapper

# Changes to code are immediately reflected
# Update launcher scripts after major changes
python scripts/install-claude-desktop-home.py --update
```

### For Production

```bash
# Use standalone mode for stability
python scripts/install-claude-desktop-home.py --mode standalone

# Pin to specific version
git checkout v1.1.11
python scripts/install-claude-desktop-home.py --mode standalone --force
```

### For Testing

```bash
# Use dry-run to preview changes
python scripts/install-claude-desktop-home.py --dry-run --verbose

# Validate after installation
python scripts/install-claude-desktop-home.py --validate --verbose

# Test with different modes
python scripts/install-claude-desktop-home.py --mode wrapper --dry-run
python scripts/install-claude-desktop-home.py --mode standalone --dry-run
```

## Advanced Usage

### Custom Database Location

Edit `~/.kuzu-memory/config.yaml`:

```yaml
database:
  path: /custom/path/to/memorydb
```

Then update environment in Claude Desktop config:

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "env": {
        "KUZU_MEMORY_DB": "/custom/path/to/memorydb"
      }
    }
  }
}
```

### Multiple Installations

You can have both pipx and home installations:

```bash
# System-wide via pipx (for CLI usage)
pipx install kuzu-memory

# Home installation (for Claude Desktop)
python scripts/install-claude-desktop-home.py --mode wrapper

# CLI commands use pipx version
kuzu-memory stats

# Claude Desktop uses home version
# (configured in claude_desktop_config.json)
```

## Security Considerations

- ✅ Scripts are installed with 755 permissions (executable)
- ✅ Configuration files are user-readable only
- ✅ Backups created before any modifications
- ✅ No sudo/elevated permissions required
- ✅ Database stored in user home directory
- ⚠️ Ensure `~/.kuzu-memory/` has appropriate permissions

## Uninstallation

### Clean Uninstall

```bash
# Remove installation (preserves backups)
python scripts/install-claude-desktop-home.py --uninstall

# Remove backups (optional)
rm -rf ~/.kuzu-memory-backups/

# Restart Claude Desktop
```

### Manual Cleanup

If installer is not available:

```bash
# Remove installation directory
rm -rf ~/.kuzu-memory/

# Edit Claude Desktop config
# Remove "kuzu-memory" from mcpServers section
vi ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
```

## Support

For issues specific to home installation:

1. Run validation: `python scripts/install-claude-desktop-home.py --validate --verbose`
2. Check logs in `~/.kuzu-memory/`
3. Review Claude Desktop logs
4. File issue with installation details

## See Also

- [Claude Desktop MCP Setup](CLAUDE_SETUP.md) - Original pipx-based installation
- [Getting Started Guide](GETTING_STARTED.md) - Quick start for all installation methods
- [MCP Testing Guide](MCP_TESTING_GUIDE.md) - Testing MCP integration
