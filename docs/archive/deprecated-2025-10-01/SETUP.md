# 🚀 KuzuMemory Setup Guide

This guide covers all installation and setup options for KuzuMemory.

## 📋 Installation Options

### 🔧 **Development (This Project)**
For working on KuzuMemory source code:

```bash
# Use the development shell script
./kuzu-memory.sh --setup    # One-time setup
./kuzu-memory.sh demo       # Run commands from source
./kuzu-memory.sh --help-dev # Development help
```

### 📦 **Production (pipx - Recommended)**
For using KuzuMemory as a CLI tool:

```bash
# Install via pipx (isolated environment)
pipx install kuzu-memory

# Or use our installer script
python scripts/install-pipx.py
```

### 🐍 **Python Package (pip)**
For using KuzuMemory in Python projects:

```bash
pip install kuzu-memory
```

---

## 🔧 Development Setup

### **Using the Shell Script (Recommended)**

The `kuzu-memory.sh` script handles everything automatically:

```bash
# First time setup
./kuzu-memory.sh --setup

# Run any command
./kuzu-memory.sh demo
./kuzu-memory.sh remember "I love Python" --user-id dev
./kuzu-memory.sh optimize --enable-cli

# Check environment
./kuzu-memory.sh --venv-info
```

**Features:**
- ✅ Automatic virtual environment creation
- ✅ Dependency installation and updates
- ✅ Proper Python path configuration
- ✅ Colored output and error handling
- ✅ Works with existing venvs (venv, .venv, conda)

### **Manual Development Setup**

If you prefer manual setup:

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install in development mode
pip install -e .

# 4. Run from source
python -m kuzu_memory.cli.commands demo
```

---

## 📦 Production Installation

### **pipx Installation (Recommended)**

pipx installs KuzuMemory in an isolated environment:

```bash
# Install pipx if needed
pip install pipx
pipx ensurepath

# Install KuzuMemory
pipx install kuzu-memory

# Use anywhere
kuzu-memory demo
kuzu-memory --help
```

**Benefits:**
- ✅ Isolated from other Python packages
- ✅ Available system-wide as `kuzu-memory` command
- ✅ Easy updates: `pipx upgrade kuzu-memory`
- ✅ Clean uninstall: `pipx uninstall kuzu-memory`

### **Using Our Installer Script**

```bash
# Automatic installation
python scripts/install-pipx.py

# Options
python scripts/install-pipx.py --local      # Install from local source
python scripts/install-pipx.py --test-pypi  # Install from Test PyPI
python scripts/install-pipx.py --force      # Force reinstall
```

### **Regular pip Installation**

For use in Python projects:

```bash
pip install kuzu-memory

# Then use in Python
from kuzu_memory import KuzuMemory
```

---

## 🚀 Publishing to PyPI

### **Using the Publishing Script**

```bash
# Test publication (Test PyPI only)
python scripts/publish.py --test

# Full publication (Test PyPI then PyPI)
python scripts/publish.py

# Skip tests
python scripts/publish.py --skip-tests
```

### **Manual Publishing**

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Upload to Test PyPI
python -m twine upload --repository testpypi dist/*

# Upload to PyPI
python -m twine upload dist/*
```

---

## 🎯 Quick Start Examples

### **Development Workflow**
```bash
# Setup once
./kuzu-memory.sh --setup

# Daily development
./kuzu-memory.sh demo                    # Test functionality
./kuzu-memory.sh remember "test data"    # Test features
./kuzu-memory.sh examples workflow       # See examples
```

### **Production Usage**
```bash
# Install once
pipx install kuzu-memory

# Daily usage
kuzu-memory demo                         # Try it out
kuzu-memory quickstart                   # Full setup
kuzu-memory remember "I love Python"     # Store memories
kuzu-memory recall "What do I like?"     # Recall context
```

---

## 🔧 Configuration

### **Development Configuration**
The shell script automatically:
- Creates/finds virtual environment
- Installs/updates dependencies
- Sets up Python path
- Handles activation/deactivation

### **Production Configuration**
After installation:
```bash
kuzu-memory setup          # Interactive configuration
kuzu-memory optimize       # Performance tuning
kuzu-memory config show    # View current settings
```

---

## 🆘 Troubleshooting

### **Development Issues**

**Virtual environment not found:**
```bash
./kuzu-memory.sh --venv-info  # Check status
./kuzu-memory.sh --setup      # Recreate environment
```

**Import errors:**
```bash
# Reinstall dependencies
./kuzu-memory.sh --setup
```

**Permission errors:**
```bash
chmod +x kuzu-memory.sh
```

### **Production Issues**

**Command not found:**
```bash
pipx ensurepath              # Add to PATH
pipx list                    # Check installation
pipx reinstall kuzu-memory   # Reinstall
```

**Version conflicts:**
```bash
pipx uninstall kuzu-memory   # Clean uninstall
pipx install kuzu-memory     # Fresh install
```

---

## 📊 Verification

### **Test Development Setup**
```bash
./kuzu-memory.sh --venv-info     # Check environment
./kuzu-memory.sh demo            # Test functionality
./kuzu-memory.sh --help          # Verify CLI
```

### **Test Production Installation**
```bash
kuzu-memory --version            # Check version
kuzu-memory demo                 # Test functionality
pipx list                        # Verify installation
```

---

## 🎉 Success Criteria

### **Development Setup Complete When:**
- ✅ `./kuzu-memory.sh --venv-info` shows active environment
- ✅ `./kuzu-memory.sh demo` runs successfully
- ✅ `./kuzu-memory.sh --help` shows rich CLI help

### **Production Installation Complete When:**
- ✅ `kuzu-memory --version` shows version number
- ✅ `kuzu-memory demo` runs successfully
- ✅ `pipx list` shows kuzu-memory installed

---

## 🔗 Next Steps

After successful setup:

1. **Try the demo:** `kuzu-memory demo`
2. **Run quickstart:** `kuzu-memory quickstart`
3. **Explore examples:** `kuzu-memory examples`
4. **Read help:** `kuzu-memory --help`

**Happy coding with KuzuMemory!** 🧠✨
