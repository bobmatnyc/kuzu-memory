# KuzuMemory Installation Methods Comparison

This guide compares the different installation methods available for KuzuMemory and helps you choose the best one for your use case.

## Available Installation Methods

### 1. PyPI Installation (Standard)

**Install from Python Package Index:**

```bash
pip install kuzu-memory
# or
pipx install kuzu-memory
```

**Best for:**
- Standard Python package usage
- CLI tool usage
- Integration into Python projects
- System-wide availability

**Pros:**
- ✅ Simple one-command installation
- ✅ Easy updates via pip/pipx
- ✅ Standard Python package management
- ✅ Automatic dependency resolution

**Cons:**
- ❌ Requires pip/pipx knowledge
- ❌ May conflict with other packages (pip)
- ❌ Requires manual Claude Desktop configuration

### 2. pipx + Claude Desktop Installer (Recommended for Claude)

**Install via pipx with automatic Claude Desktop setup:**

```bash
pipx install kuzu-memory
python scripts/install-claude-desktop.py
```

**Best for:**
- Claude Desktop integration
- Development work
- Isolated Python environment
- Users comfortable with pipx

**Pros:**
- ✅ Isolated virtual environment
- ✅ No package conflicts
- ✅ Automatic Claude Desktop configuration
- ✅ Easy updates with `pipx upgrade`
- ✅ Clean uninstall with `pipx uninstall`

**Cons:**
- ❌ Requires pipx installation
- ❌ Two-step process
- ❌ Larger disk space (~10-20MB)

### 3. Home Installation - Wrapper Mode (NEW)

**Install to ~/.kuzu-memory/ using system package:**

```bash
# Install kuzu-memory first
pip install kuzu-memory
# or
pipx install kuzu-memory

# Then install home wrapper
python scripts/install-claude-desktop-home.py --mode wrapper
```

**Best for:**
- Users who already have kuzu-memory installed
- Minimal disk space usage
- Development with frequent updates
- Custom Claude Desktop setup

**Pros:**
- ✅ Minimal disk space (~1KB for scripts)
- ✅ Uses existing system installation
- ✅ Automatic Claude Desktop configuration
- ✅ Auto-updates with system package
- ✅ Simple launcher scripts
- ✅ Easy to update/maintain

**Cons:**
- ❌ Requires system installation of kuzu-memory
- ❌ Depends on system Python environment
- ❌ May break if system installation removed

### 4. Home Installation - Standalone Mode (NEW)

**Install complete package to ~/.kuzu-memory/:**

```bash
python scripts/install-claude-desktop-home.py --mode standalone
```

**Best for:**
- Self-contained installation
- No system dependencies
- Fixed version pinning
- Isolated testing environments

**Pros:**
- ✅ Fully self-contained
- ✅ No system package dependencies
- ✅ Automatic Claude Desktop configuration
- ✅ Version pinning capability
- ✅ Complete isolation
- ✅ Works without pip/pipx

**Cons:**
- ❌ Larger disk space (~5MB)
- ❌ Manual updates required
- ❌ Must rebuild for updates
- ❌ Duplicate package code

### 5. Home Installation - Auto Mode (NEW - Recommended)

**Automatically detects best mode:**

```bash
python scripts/install-claude-desktop-home.py
```

**Best for:**
- First-time users
- Quick setup
- Users unsure which mode to use
- Automatic optimization

**Pros:**
- ✅ Intelligent mode detection
- ✅ Uses wrapper if system package exists
- ✅ Falls back to standalone if needed
- ✅ Best performance for environment
- ✅ Automatic Claude Desktop configuration

**Cons:**
- ❌ Less control over installation type
- ❌ May change behavior if system changes

## Comparison Table

| Feature | PyPI | pipx + Claude | Home Wrapper | Home Standalone | Home Auto |
|---------|------|---------------|--------------|-----------------|-----------|
| **Installation Command** | `pip install` | `pipx install` + script | Script wrapper | Script standalone | Script auto |
| **Disk Space** | ~10MB | ~10-20MB | ~1KB + system | ~5MB | Varies |
| **Claude Desktop Setup** | Manual | Automatic | Automatic | Automatic | Automatic |
| **Isolated Environment** | ❌ No | ✅ Yes | ❌ No | ✅ Yes | Varies |
| **Update Command** | `pip upgrade` | `pipx upgrade` | `--update` | `--force` | `--update` |
| **Requires pipx** | ❌ No | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **System Dependencies** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | Varies |
| **Auto-detect Mode** | ❌ No | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Database Location** | Configurable | `~/.kuzu-memory/` | `~/.kuzu-memory/` | `~/.kuzu-memory/` | `~/.kuzu-memory/` |
| **Uninstall** | `pip uninstall` | `pipx uninstall` + manual | `--uninstall` | `--uninstall` | `--uninstall` |
| **Best For** | General use | Development | Light + Updates | Isolation | Easiest |

## Decision Tree

```
┌─────────────────────────────────────┐
│   What is your primary use case?   │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
   Python CLI      Claude Desktop
       │                │
       │         ┌──────┴───────┐
       │         │              │
       │    Already have    First time
       │    kuzu-memory?        │
       │         │              │
   pip install   │              │
       │     ┌───┴───┐          │
       │     │       │          │
       │    Yes     No          │
       │     │       │          │
       │  Wrapper  Auto       Auto
       │  or Auto  Mode       Mode
       │           │           │
       └───────────┴───────────┘
```

## Use Case Recommendations

### For Python Developers

```bash
# Standard installation
pip install kuzu-memory

# Development installation
pip install -e ".[dev]"
```

### For Claude Desktop Users (First Time)

```bash
# Easiest - auto-detect mode
python scripts/install-claude-desktop-home.py

# Alternative - pipx method
pipx install kuzu-memory
python scripts/install-claude-desktop.py
```

### For Claude Desktop Users (Have kuzu-memory)

```bash
# Lightweight wrapper mode
python scripts/install-claude-desktop-home.py --mode wrapper
```

### For Testing/Isolation

```bash
# Standalone mode - complete isolation
python scripts/install-claude-desktop-home.py --mode standalone
```

### For Production Deployment

```bash
# Pin version via pipx
pipx install kuzu-memory==1.1.11
python scripts/install-claude-desktop.py

# Or standalone for fixed version
git checkout v1.1.11
python scripts/install-claude-desktop-home.py --mode standalone
```

## Migration Paths

### From pip to Home Installation

```bash
# Current: pip installation
pip list | grep kuzu-memory

# Option 1: Keep pip, add wrapper
python scripts/install-claude-desktop-home.py --mode wrapper

# Option 2: Remove pip, use standalone
pip uninstall kuzu-memory
python scripts/install-claude-desktop-home.py --mode standalone
```

### From pipx to Home Installation

```bash
# Current: pipx installation
pipx list | grep kuzu-memory

# Option 1: Keep pipx, add wrapper
python scripts/install-claude-desktop-home.py --mode wrapper

# Option 2: Remove pipx, use standalone
pipx uninstall kuzu-memory
python scripts/install-claude-desktop-home.py --mode standalone
```

### From Home Wrapper to Standalone

```bash
# Switch to standalone mode
python scripts/install-claude-desktop-home.py --mode standalone --force
```

### From Home Standalone to Wrapper

```bash
# First install system package
pip install kuzu-memory

# Switch to wrapper mode
python scripts/install-claude-desktop-home.py --mode wrapper --force
```

## Update Strategies

### PyPI Installation

```bash
# Update via pip
pip install --upgrade kuzu-memory

# Update via pipx
pipx upgrade kuzu-memory
```

### Home Wrapper Installation

```bash
# Update system package
pip install --upgrade kuzu-memory
# or
pipx upgrade kuzu-memory

# Update launcher scripts
python scripts/install-claude-desktop-home.py --update
```

### Home Standalone Installation

```bash
# Pull latest code
git pull origin main

# Reinstall
python scripts/install-claude-desktop-home.py --mode standalone --force
```

### Home Auto Installation

```bash
# Simple update command
python scripts/install-claude-desktop-home.py --update
```

## Troubleshooting by Installation Type

### PyPI Installation Issues

```bash
# Verify installation
pip list | grep kuzu-memory

# Reinstall
pip install --force-reinstall kuzu-memory

# Check CLI
kuzu-memory --version
```

### pipx Installation Issues

```bash
# List pipx packages
pipx list

# Reinstall
pipx reinstall kuzu-memory

# Check paths
which kuzu-memory
```

### Home Installation Issues

```bash
# Validate installation
python scripts/install-claude-desktop-home.py --validate --verbose

# Check installation type
cat ~/.kuzu-memory/.installation_type

# Check version
cat ~/.kuzu-memory/.version

# Test launcher
~/.kuzu-memory/bin/kuzu-memory-mcp-server --help
```

## Performance Considerations

| Installation Type | Startup Time | Memory Usage | Disk Space |
|------------------|--------------|--------------|------------|
| PyPI (pip) | ~50ms | ~20MB | ~10MB |
| pipx | ~50ms | ~25MB | ~15-20MB |
| Home Wrapper | ~60ms | ~20MB | ~1KB + system |
| Home Standalone | ~60ms | ~20MB | ~5MB |
| Home Auto | Varies | Varies | Varies |

## Security Considerations

### PyPI/pipx Installation

- ✅ Official Python packaging
- ✅ Checksum verification
- ✅ PyPI trust chain
- ⚠️ System-wide or user PATH

### Home Installation

- ✅ User-only installation
- ✅ No sudo required
- ✅ Isolated in ~/.kuzu-memory/
- ⚠️ Manual script verification
- ⚠️ Check script source before running

## Quick Reference

### Installation Commands

```bash
# PyPI
pip install kuzu-memory

# pipx + Claude
pipx install kuzu-memory && python scripts/install-claude-desktop.py

# Home Auto
python scripts/install-claude-desktop-home.py

# Home Wrapper
python scripts/install-claude-desktop-home.py --mode wrapper

# Home Standalone
python scripts/install-claude-desktop-home.py --mode standalone
```

### Validation Commands

```bash
# PyPI
kuzu-memory --version

# pipx
pipx list | grep kuzu-memory

# Home
python scripts/install-claude-desktop-home.py --validate
```

### Uninstall Commands

```bash
# PyPI
pip uninstall kuzu-memory

# pipx
pipx uninstall kuzu-memory
python scripts/install-claude-desktop.py --uninstall

# Home
python scripts/install-claude-desktop-home.py --uninstall
```

## See Also

- [Getting Started Guide](GETTING_STARTED.md) - Quick start for all methods
- [Home Installation Guide](HOME_INSTALLATION.md) - Detailed home installation docs
- [Claude Desktop Setup](CLAUDE_SETUP.md) - Original pipx-based setup
- [MCP Testing Guide](MCP_TESTING_GUIDE.md) - Testing MCP integration
