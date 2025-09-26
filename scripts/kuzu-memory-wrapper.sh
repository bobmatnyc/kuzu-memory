#!/usr/bin/env bash
#
# KuzuMemory Universal Shell Wrapper
# Provides pipx-style installation and management for KuzuMemory
#
# Usage:
#   ./kuzu-memory-wrapper.sh install    # Install KuzuMemory
#   ./kuzu-memory-wrapper.sh uninstall  # Uninstall KuzuMemory
#   ./kuzu-memory-wrapper.sh upgrade    # Upgrade KuzuMemory
#   ./kuzu-memory-wrapper.sh status     # Check installation status
#   ./kuzu-memory-wrapper.sh dev        # Run in development mode
#   ./kuzu-memory-wrapper.sh [args...]  # Run kuzu-memory commands

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
SCRIPT_NAME="kuzu-memory"
PACKAGE_NAME="kuzu-memory"
VENV_NAME=".kuzu-memory-venv"
INSTALL_DIR="${HOME}/.local/kuzu-memory"
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${HOME}/.config/kuzu-memory"
CLAUDE_CODE_CONFIG="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
CLAUDE_DESKTOP_CONFIG="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

detect_python() {
    # Try to find the best Python installation
    for py in python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$py" &> /dev/null; then
            version=$("$py" --version 2>&1 | cut -d' ' -f2)
            major=$(echo "$version" | cut -d'.' -f1)
            minor=$(echo "$version" | cut -d'.' -f2)
            if [ "$major" -eq 3 ] && [ "$minor" -ge 9 ]; then
                echo "$py"
                return 0
            fi
        fi
    done

    log_error "Python 3.9+ not found"
    return 1
}

detect_shell() {
    # Detect user's shell
    if [ -n "$SHELL" ]; then
        case "$SHELL" in
            */bash)
                echo "bash"
                ;;
            */zsh)
                echo "zsh"
                ;;
            */fish)
                echo "fish"
                ;;
            *)
                echo "bash"  # Default to bash
                ;;
        esac
    else
        echo "bash"
    fi
}

install_kuzu_memory() {
    log_info "Installing KuzuMemory..."

    # Detect Python
    PYTHON=$(detect_python)
    if [ $? -ne 0 ]; then
        exit 1
    fi
    log_success "Found Python: $PYTHON"

    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    mkdir -p "$CONFIG_DIR"

    # Create virtual environment
    log_info "Creating virtual environment..."
    "$PYTHON" -m venv "$INSTALL_DIR/$VENV_NAME"

    # Activate venv
    source "$INSTALL_DIR/$VENV_NAME/bin/activate"

    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel

    # Install package
    log_info "Installing kuzu-memory package..."
    if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
        # Development install from source
        pip install -e "$SCRIPT_DIR"
    else
        # Install from PyPI
        pip install kuzu-memory
    fi

    # Create wrapper script
    log_info "Creating wrapper script..."
    cat > "$BIN_DIR/kuzu-memory" << 'EOF'
#!/bin/bash
INSTALL_DIR="${HOME}/.local/kuzu-memory"
VENV_NAME=".kuzu-memory-venv"

# Activate virtual environment and run command
source "$INSTALL_DIR/$VENV_NAME/bin/activate" 2>/dev/null
exec kuzu-memory "$@"
EOF
    chmod +x "$BIN_DIR/kuzu-memory"

    # Setup shell integration
    setup_shell_integration

    # Setup Claude Code integration
    setup_claude_code

    log_success "KuzuMemory installed successfully!"
    log_info "Run 'kuzu-memory --help' to get started"
}

setup_shell_integration() {
    local shell_type=$(detect_shell)
    local shell_config=""

    case "$shell_type" in
        bash)
            shell_config="${HOME}/.bashrc"
            ;;
        zsh)
            shell_config="${HOME}/.zshrc"
            ;;
        fish)
            shell_config="${HOME}/.config/fish/config.fish"
            ;;
    esac

    if [ -n "$shell_config" ] && [ -f "$shell_config" ]; then
        # Check if PATH already contains our bin directory
        if ! grep -q "$BIN_DIR" "$shell_config" 2>/dev/null; then
            log_info "Adding $BIN_DIR to PATH in $shell_config"
            echo "" >> "$shell_config"
            echo "# KuzuMemory PATH" >> "$shell_config"
            if [ "$shell_type" = "fish" ]; then
                echo "set -gx PATH \$PATH $BIN_DIR" >> "$shell_config"
            else
                echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$shell_config"
            fi
        fi

        # Add useful aliases
        if ! grep -q "alias km=" "$shell_config" 2>/dev/null; then
            echo "" >> "$shell_config"
            echo "# KuzuMemory aliases" >> "$shell_config"
            if [ "$shell_type" = "fish" ]; then
                echo "alias km='kuzu-memory'" >> "$shell_config"
                echo "alias kme='kuzu-memory enhance'" >> "$shell_config"
                echo "alias kml='kuzu-memory learn'" >> "$shell_config"
                echo "alias kmr='kuzu-memory recall'" >> "$shell_config"
            else
                echo "alias km='kuzu-memory'" >> "$shell_config"
                echo "alias kme='kuzu-memory enhance'" >> "$shell_config"
                echo "alias kml='kuzu-memory learn'" >> "$shell_config"
                echo "alias kmr='kuzu-memory recall'" >> "$shell_config"
            fi
        fi

        log_success "Shell integration added to $shell_config"
        log_info "Restart your shell or run: source $shell_config"
    fi
}

setup_claude_code() {
    log_info "Setting up Claude Code integration..."

    # Create MCP server wrapper script
    cat > "$BIN_DIR/kuzu-memory-mcp" << 'EOF'
#!/bin/bash
INSTALL_DIR="${HOME}/.local/kuzu-memory"
VENV_NAME=".kuzu-memory-venv"

# Activate virtual environment
source "$INSTALL_DIR/$VENV_NAME/bin/activate" 2>/dev/null

# Run MCP server
exec python -m kuzu_memory.mcp.run_server "$@"
EOF
    chmod +x "$BIN_DIR/kuzu-memory-mcp"

    # Check if Claude Code is installed
    if [ -f "$CLAUDE_CODE_CONFIG" ] || [ -f "$CLAUDE_DESKTOP_CONFIG" ]; then
        # Create MCP server configuration
        cat > "$CONFIG_DIR/claude_mcp_config.json" << EOF
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "$BIN_DIR/kuzu-memory-mcp",
      "args": [],
      "env": {
        "KUZU_MEMORY_HOME": "$INSTALL_DIR",
        "PYTHONPATH": "$INSTALL_DIR/$VENV_NAME/lib/python*/site-packages"
      }
    }
  }
}
EOF

        log_success "Claude Code configuration created at $CONFIG_DIR/claude_mcp_config.json"
        log_info "To complete setup:"
        log_info "1. Open Claude Code settings"
        log_info "2. Add the MCP server configuration from $CONFIG_DIR/claude_mcp_config.json"
    else
        log_warning "Claude Code/Desktop not detected, skipping MCP setup"
    fi
}

uninstall_kuzu_memory() {
    log_info "Uninstalling KuzuMemory..."

    # Remove virtual environment
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        log_success "Removed installation directory"
    fi

    # Remove wrapper scripts
    if [ -f "$BIN_DIR/kuzu-memory" ]; then
        rm "$BIN_DIR/kuzu-memory"
        log_success "Removed kuzu-memory wrapper"
    fi

    if [ -f "$BIN_DIR/kuzu-memory-mcp" ]; then
        rm "$BIN_DIR/kuzu-memory-mcp"
        log_success "Removed MCP wrapper"
    fi

    # Remove config directory
    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
        log_success "Removed configuration directory"
    fi

    log_warning "Please manually remove KuzuMemory entries from your shell config files"
    log_success "KuzuMemory uninstalled"
}

upgrade_kuzu_memory() {
    log_info "Upgrading KuzuMemory..."

    # Activate venv
    if [ -d "$INSTALL_DIR/$VENV_NAME" ]; then
        source "$INSTALL_DIR/$VENV_NAME/bin/activate"

        # Upgrade package
        if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
            # Development mode - reinstall from source
            pip install --upgrade -e "$SCRIPT_DIR"
        else
            # Production mode - upgrade from PyPI
            pip install --upgrade kuzu-memory
        fi

        log_success "KuzuMemory upgraded to latest version"
    else
        log_error "KuzuMemory not installed. Run '$0 install' first"
        exit 1
    fi
}

check_status() {
    log_info "Checking KuzuMemory status..."

    # Check installation
    if [ -d "$INSTALL_DIR/$VENV_NAME" ]; then
        log_success "Installation found at $INSTALL_DIR"

        # Check version
        if [ -f "$BIN_DIR/kuzu-memory" ]; then
            version=$("$BIN_DIR/kuzu-memory" --version 2>&1 || echo "unknown")
            log_info "Version: $version"
        fi

        # Check PATH
        if command -v kuzu-memory &> /dev/null; then
            log_success "kuzu-memory is in PATH"
        else
            log_warning "kuzu-memory not in PATH. Restart shell or add $BIN_DIR to PATH"
        fi

        # Check Claude Code integration
        if [ -f "$CONFIG_DIR/claude_mcp_config.json" ]; then
            log_success "Claude Code MCP configuration found"
        else
            log_warning "Claude Code MCP not configured"
        fi
    else
        log_error "KuzuMemory not installed"
        exit 1
    fi
}

run_dev_mode() {
    log_info "Running KuzuMemory in development mode..."

    # Check if we're in the right directory
    if [ ! -f "$SCRIPT_DIR/src/kuzu_memory/__init__.py" ]; then
        log_error "This script must be run from the KuzuMemory project root"
        exit 1
    fi

    # Find or create development venv
    DEV_VENV="$SCRIPT_DIR/venv"
    if [ ! -d "$DEV_VENV" ]; then
        DEV_VENV="$SCRIPT_DIR/.venv"
    fi

    if [ ! -d "$DEV_VENV" ]; then
        log_info "Creating development virtual environment..."
        PYTHON=$(detect_python)
        "$PYTHON" -m venv "$DEV_VENV"
    fi

    # Activate and install
    source "$DEV_VENV/bin/activate"
    pip install --upgrade pip setuptools wheel
    pip install -e "$SCRIPT_DIR"

    # Run command
    shift  # Remove 'dev' argument
    exec python -m kuzu_memory.cli.commands "$@"
}

# Main script logic
case "${1:-}" in
    install)
        install_kuzu_memory
        ;;
    uninstall)
        uninstall_kuzu_memory
        ;;
    upgrade)
        upgrade_kuzu_memory
        ;;
    status)
        check_status
        ;;
    dev)
        run_dev_mode "$@"
        ;;
    *)
        # Pass through to kuzu-memory command
        if [ -f "$BIN_DIR/kuzu-memory" ]; then
            exec "$BIN_DIR/kuzu-memory" "$@"
        elif [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
            # Development mode fallback
            log_warning "Running in development mode. Install with: $0 install"
            run_dev_mode "$@"
        else
            log_error "KuzuMemory not installed. Run '$0 install' first"
            exit 1
        fi
        ;;
esac