# KuzuMemory Installation Summary

Quick reference for all installation methods.

## 🚀 Quick Install (Recommended)

### For Claude Desktop Users

```bash
# Easiest - auto-detects best mode
python scripts/install-claude-desktop-home.py

# Restart Claude Desktop
```

### For Python CLI Users

```bash
# Standard Python package
pip install kuzu-memory

# Or isolated with pipx
pipx install kuzu-memory
```

## 📋 Installation Methods Comparison

| Method | Command | Disk Space | Auto Config | Best For |
|--------|---------|------------|-------------|----------|
| **Home Auto** | `python scripts/install-claude-desktop-home.py` | Varies | ✅ Yes | Claude Desktop (easiest) |
| **Home Wrapper** | `--mode wrapper` | ~1KB | ✅ Yes | Minimal + has kuzu-memory |
| **Home Standalone** | `--mode standalone` | ~5MB | ✅ Yes | Isolation + no dependencies |
| **pipx + Script** | `pipx install` + script | ~15MB | ✅ Yes | Development + isolation |
| **pip** | `pip install kuzu-memory` | ~10MB | ❌ No | Python projects |

## 🏠 Home Installation Details

### Auto Mode (Recommended)

Automatically selects the best installation mode:

```bash
python scripts/install-claude-desktop-home.py
```

**Installs to**: `~/.kuzu-memory/`
**Configuration**: Automatic Claude Desktop setup
**Update**: `python scripts/install-claude-desktop-home.py --update`

### Wrapper Mode

Uses existing system installation (requires kuzu-memory via pip/pipx):

```bash
# First ensure kuzu-memory is installed
pip install kuzu-memory
# or
pipx install kuzu-memory

# Then install wrapper
python scripts/install-claude-desktop-home.py --mode wrapper
```

**Advantages**:
- Minimal disk space (~1KB)
- Auto-updates with system package
- Single source of truth

### Standalone Mode

Complete self-contained installation:

```bash
python scripts/install-claude-desktop-home.py --mode standalone
```

**Advantages**:
- No system dependencies
- Fully isolated
- Version pinning

## 🔧 Management Commands

### Via Makefile

```bash
make install-home              # Install (auto mode)
make install-home-wrapper      # Install wrapper mode
make install-home-standalone   # Install standalone mode
make update-home               # Update installation
make validate-home             # Check health
make uninstall-home            # Remove installation
make test-home-installer       # Run tests
```

### Via Script

```bash
# Installation
python scripts/install-claude-desktop-home.py [--mode MODE]

# Update
python scripts/install-claude-desktop-home.py --update

# Validation
python scripts/install-claude-desktop-home.py --validate --verbose

# Uninstall
python scripts/install-claude-desktop-home.py --uninstall

# Dry-run (preview)
python scripts/install-claude-desktop-home.py --dry-run --verbose
```

## 📖 Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** - Quick start guide
- **[Home Installation](docs/HOME_INSTALLATION.md)** - Complete home installation guide
- **[Installation Comparison](docs/INSTALLATION_COMPARISON.md)** - All methods compared
- **[Claude Desktop Setup](docs/CLAUDE_SETUP.md)** - Original pipx setup
- **[Implementation Details](docs/HOME_INSTALLER_IMPLEMENTATION.md)** - Technical details

## ❓ Which Should I Use?

### Choose Home Auto If:
- ✅ You use Claude Desktop
- ✅ You want the easiest setup
- ✅ You're not sure which mode to use

### Choose Home Wrapper If:
- ✅ You already have kuzu-memory installed
- ✅ You want minimal disk usage
- ✅ You want automatic updates

### Choose Home Standalone If:
- ✅ You want complete isolation
- ✅ You don't have kuzu-memory installed
- ✅ You want version pinning

### Choose pipx + Script If:
- ✅ You're doing development work
- ✅ You prefer pipx for package management
- ✅ You want isolation + easy updates

### Choose pip If:
- ✅ You're using as a Python library
- ✅ You don't need Claude Desktop integration
- ✅ You want standard Python package

## 🚨 Troubleshooting

### Installation Issues

```bash
# Check what would happen
python scripts/install-claude-desktop-home.py --dry-run --verbose

# Validate existing installation
python scripts/install-claude-desktop-home.py --validate --verbose

# Force reinstall
python scripts/install-claude-desktop-home.py --force
```

### Mode Selection Issues

```bash
# See system installation status
python3 -c "import kuzu_memory; print(kuzu_memory.__file__)"

# Force specific mode
python scripts/install-claude-desktop-home.py --mode standalone --force
```

### Claude Desktop Issues

```bash
# Validate configuration
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Test launcher directly
~/.kuzu-memory/bin/kuzu-memory-mcp-server --help
```

## 📊 Directory Structure

After home installation:

```
~/.kuzu-memory/
├── bin/
│   ├── kuzu-memory-mcp-server    # Main launcher
│   └── run-mcp-server.sh         # Shell wrapper
├── lib/                           # Package (standalone only)
│   └── kuzu_memory/
├── memorydb/                      # Database
├── config.yaml                    # Configuration
├── .version                       # Installation version
└── .installation_type             # Mode (wrapper/standalone)
```

## 🔄 Migration Paths

### From pipx to Home

```bash
# Keep pipx, add wrapper
python scripts/install-claude-desktop-home.py --mode wrapper

# Or switch to standalone
pipx uninstall kuzu-memory
python scripts/install-claude-desktop-home.py --mode standalone
```

### From pip to Home

```bash
# Keep pip, add wrapper
python scripts/install-claude-desktop-home.py --mode wrapper

# Or switch to standalone
pip uninstall kuzu-memory
python scripts/install-claude-desktop-home.py --mode standalone
```

### Between Home Modes

```bash
# Wrapper to standalone
python scripts/install-claude-desktop-home.py --mode standalone --force

# Standalone to wrapper (need system package first)
pip install kuzu-memory
python scripts/install-claude-desktop-home.py --mode wrapper --force
```

## ✅ Verification

After installation, verify:

```bash
# 1. Check installation
python scripts/install-claude-desktop-home.py --validate --verbose

# 2. Check launcher
~/.kuzu-memory/bin/kuzu-memory-mcp-server --help

# 3. Check Claude Desktop config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 4. Test with Claude Desktop
# Restart Claude Desktop and check for kuzu-memory tools
```

## 📞 Support

For issues:

1. Run validation: `python scripts/install-claude-desktop-home.py --validate --verbose`
2. Check documentation in `docs/`
3. Run tests: `make test-home-installer`
4. File issue with validation output

## 🎯 Next Steps After Installation

1. **Restart Claude Desktop** to load MCP configuration
2. **Test MCP tools** are available in conversations
3. **Initialize database** (done automatically)
4. **Start using** memory features

Available MCP tools after installation:
- `kuzu_enhance` - Enhance prompts with context
- `kuzu_learn` - Store learnings asynchronously
- `kuzu_recall` - Query specific memories
- `kuzu_remember` - Store important information
- `kuzu_stats` - Get memory system statistics

---

**Need Help?** See detailed documentation in `docs/` directory.
