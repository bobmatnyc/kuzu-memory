# MCP Installation Guide

**Unified MCP Server Installation for Multiple AI Coding Assistants**

## Overview

KuzuMemory provides a unified MCP (Model Context Protocol) installation system that auto-detects and configures MCP servers for multiple AI coding assistants with a single command.

### Key Features

✅ **Auto-Detection**: Automatically detects installed AI systems in your project
✅ **Configuration Preservation**: Merges with existing MCP servers without overwriting
✅ **Backup Creation**: Automatically backs up existing configurations
✅ **Dry-Run Mode**: Preview changes before applying them
✅ **Multi-System Support**: Install for multiple AI assistants simultaneously

## Supported AI Systems

### Priority 1 (Implemented)

| AI System | Config Type | Config Path | Status |
|-----------|-------------|-------------|--------|
| **Cursor IDE** | Project-specific | `.cursor/mcp.json` | ✅ Implemented |
| **VS Code** (Claude Extension) | Project-specific | `.vscode/mcp.json` | ✅ Implemented |
| **Windsurf IDE** | Global (user-wide) | `~/.codeium/windsurf/mcp_config.json` | ✅ Implemented |

### Coming Soon

| AI System | Config Type | Config Path | Status |
|-----------|-------------|-------------|--------|
| **Roo Code** | Project-specific | `.roo/mcp.json` | 🚧 Planned |
| **Zed Editor** | Project-specific | `.zed/settings.json` | 🚧 Planned |
| **Continue** | Project-specific | `.continue/config.yaml` | 🚧 Planned |
| **JetBrains Junie** | Project-specific | `.junie/mcp/mcp.json` | 🚧 Planned |

## Quick Start

### 1. Detect AI Systems

Check which AI coding assistants are available in your project:

```bash
# Detect all systems
kuzu-memory mcp detect

# Show only installed systems (existing configs)
kuzu-memory mcp detect --installed

# Show only available systems (can be installed)
kuzu-memory mcp detect --available

# Show detailed information
kuzu-memory mcp detect --verbose
```

### 2. Install MCP Configurations

#### Auto-Install All Detected Systems

```bash
# Install MCP configs for all detected AI systems
kuzu-memory mcp install --all

# Preview what would be installed (dry-run)
kuzu-memory mcp install --all --dry-run

# Install with verbose output
kuzu-memory mcp install --all --verbose
```

#### Install Specific System

```bash
# Install for Cursor IDE only
kuzu-memory mcp install --system cursor

# Install for VS Code only
kuzu-memory mcp install --system vscode

# Install for Windsurf IDE only
kuzu-memory mcp install --system windsurf
```

#### Force Reinstall

```bash
# Force reinstall (overwrites existing, creates backup)
kuzu-memory mcp install --system cursor --force

# Force reinstall all systems
kuzu-memory mcp install --all --force
```

### 3. List Available Installers

```bash
# List all available MCP installers
kuzu-memory mcp list

# Show detailed information
kuzu-memory mcp list --verbose
```

## Installation Modes

### Project-Specific Installation (Cursor, VS Code)

Project-specific installers create MCP configurations in your project directory:

```
my-project/
├── .cursor/
│   └── mcp.json          # Cursor IDE configuration
├── .vscode/
│   └── mcp.json          # VS Code configuration
└── .kuzu-memory-backups/ # Automatic backups
```

**Advantages**:
- Isolated per-project memory
- Can be version-controlled and shared with team
- Different projects can have different configurations

**Example**:
```bash
cd /path/to/my-project
kuzu-memory mcp install --system cursor
```

### Global Installation (Windsurf)

Global installers create MCP configurations in your home directory:

```
~/.codeium/windsurf/
└── mcp_config.json       # Windsurf global configuration

~/.kuzu-memory-backups/   # Automatic backups
```

**Advantages**:
- Shared across all projects
- Single configuration to maintain
- Works globally in Windsurf IDE

**Example**:
```bash
kuzu-memory mcp install --system windsurf
```

## Configuration Preservation

KuzuMemory intelligently merges with existing MCP server configurations:

### Example: Existing Configuration

```json
{
  "mcpServers": {
    "github-mcp": {
      "command": "github-mcp-server",
      "args": ["--token", "xxx"]
    }
  }
}
```

### After KuzuMemory Installation

```json
{
  "mcpServers": {
    "github-mcp": {
      "command": "github-mcp-server",
      "args": ["--token", "xxx"]
    },
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp", "serve"],
      "env": {
        "KUZU_MEMORY_PROJECT": "/path/to/project"
      }
    }
  }
}
```

**✅ Existing servers preserved**
**✅ New server added**
**✅ Configuration validated**
**✅ Backup created automatically**

## Advanced Usage

### Dry-Run Mode

Preview changes without modifying any files:

```bash
# See what would be installed for Cursor
kuzu-memory mcp install --system cursor --dry-run

# See what would be installed for all systems
kuzu-memory mcp install --all --dry-run --verbose
```

**Output**:
```
[DRY RUN] Would install MCP configuration to /project/.cursor/mcp.json
Would preserve 1 existing server(s)

MCP servers that would be configured: 2
  • existing-server (preserved)
  • kuzu-memory (new)
```

### Verbose Mode

Get detailed information about the installation process:

```bash
kuzu-memory mcp install --system cursor --verbose
```

**Output**:
```
Installing MCP configuration for Cursor IDE...
Merging with existing configuration
Existing servers: ['github-mcp', 'filesystem-mcp']
Created backup: .kuzu-memory-backups/mcp.json.backup_20250109_143022

Files:
  ✨ Created: .cursor/mcp.json
  💾 Backup: .kuzu-memory-backups/mcp.json.backup_20250109_143022

Successfully installed MCP configuration for Cursor IDE
Configuration file: /project/.cursor/mcp.json
MCP servers configured: 3
Preserved 2 existing server(s)
```

### Force Mode

Overwrite existing configuration (creates backup):

```bash
kuzu-memory mcp install --system cursor --force
```

**⚠️ Warning**: This will overwrite the existing configuration file. A backup will be created automatically.

## Troubleshooting

### AI System Not Detected

**Problem**: System not showing up in detection

**Solutions**:
1. Create the appropriate directory for your AI system:
   ```bash
   # For Cursor
   mkdir -p .cursor

   # For VS Code
   mkdir -p .vscode
   ```

2. Verify system is supported:
   ```bash
   kuzu-memory mcp list
   ```

### Installation Fails

**Problem**: Installation returns error

**Solutions**:
1. Check prerequisites:
   ```bash
   kuzu-memory mcp detect --verbose
   ```

2. Use dry-run to diagnose:
   ```bash
   kuzu-memory mcp install --system cursor --dry-run --verbose
   ```

3. Check existing configuration is valid JSON:
   ```bash
   # For Cursor
   cat .cursor/mcp.json | jq .

   # For VS Code
   cat .vscode/mcp.json | jq .
   ```

### Configuration Not Working

**Problem**: AI system doesn't recognize KuzuMemory

**Solutions**:
1. Verify configuration file exists:
   ```bash
   kuzu-memory mcp detect --installed
   ```

2. Validate configuration format:
   ```bash
   cat .cursor/mcp.json | jq .mcpServers
   ```

3. Restart your AI coding assistant after installation

4. Check server is in list:
   ```bash
   cat .cursor/mcp.json | jq '.mcpServers | keys'
   ```

### Restore from Backup

**Problem**: Need to restore previous configuration

**Solution**:
```bash
# List backups
ls -lh .kuzu-memory-backups/

# Restore from backup
cp .kuzu-memory-backups/mcp.json.backup_TIMESTAMP .cursor/mcp.json
```

## Best Practices

### 1. Use Dry-Run First

Always preview changes before applying:

```bash
kuzu-memory mcp install --all --dry-run --verbose
```

### 2. Version Control Project Configurations

For project-specific installations, consider committing configs:

```bash
# .gitignore
# Don't ignore project MCP configs
!.cursor/mcp.json
!.vscode/mcp.json

# Do ignore backups
.kuzu-memory-backups/
```

### 3. Install for Team

Share MCP configurations with your team:

```bash
# Install and commit
kuzu-memory mcp install --system cursor
git add .cursor/mcp.json
git commit -m "Add KuzuMemory MCP configuration"
```

### 4. Regular Updates

After updating KuzuMemory, reinstall configs:

```bash
pip install --upgrade kuzu-memory
kuzu-memory mcp install --all --force
```

## Configuration Reference

### Standard MCP Configuration Format

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp", "serve"],
      "env": {
        "KUZU_MEMORY_PROJECT": "${PROJECT_ROOT}"
      }
    }
  }
}
```

**Fields**:
- `command`: Command to run the MCP server
- `args`: Command-line arguments
- `env`: Environment variables (supports `${VARIABLE}` expansion)

### Variable Expansion

Available variables:
- `${PROJECT_ROOT}`: Absolute path to project root
- `${HOME}`: User home directory
- `${USER}`: Current username

## Integration with Existing Commands

The MCP installation system integrates with existing KuzuMemory commands:

```bash
# Traditional installation commands still work
kuzu-memory install add claude-code    # Claude Code integration
kuzu-memory install add claude-desktop # Claude Desktop integration

# New unified MCP installation
kuzu-memory mcp install --system cursor   # Cursor IDE
kuzu-memory mcp install --system vscode   # VS Code
kuzu-memory mcp install --system windsurf # Windsurf IDE
```

## FAQ

### Q: Can I install for multiple systems at once?

**A**: Yes! Use `--all` flag:
```bash
kuzu-memory mcp install --all
```

### Q: Will this overwrite my existing MCP servers?

**A**: No. KuzuMemory intelligently merges configurations, preserving existing servers. Backups are created automatically.

### Q: How do I uninstall?

**A**: Use the traditional install command:
```bash
kuzu-memory install remove cursor
kuzu-memory install remove vscode
```

### Q: Can I customize the configuration?

**A**: Yes. After installation, you can manually edit the configuration files. KuzuMemory will respect your changes on subsequent installations (unless using `--force`).

### Q: What's the difference between `kuzu-memory install` and `kuzu-memory mcp install`?

**A**:
- `kuzu-memory install`: Traditional installation for Claude Code/Desktop
- `kuzu-memory mcp install`: New unified system for multiple AI assistants

Both work, but `mcp install` provides auto-detection and multi-system support.

## Support

For issues or questions:

1. Check [Known Issues](KNOWN_ISSUES.md)
2. Run diagnostics: `kuzu-memory doctor mcp`
3. Open an issue on GitHub with:
   - Output of `kuzu-memory mcp detect --verbose`
   - Your AI system and version
   - Configuration file contents (sanitized)

## Changelog

- **v1.3.0** (2025-10-09): Initial unified MCP installation system
  - Added Cursor IDE installer
  - Added VS Code installer
  - Added Windsurf IDE installer
  - Added auto-detection system
  - Added configuration preservation
  - Added backup system
