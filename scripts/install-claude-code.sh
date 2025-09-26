#!/usr/bin/env bash
#
# KuzuMemory Claude Code Installation Script
# One-line installation: curl -sSL https://raw.../install-claude-code.sh | bash
#

set -e

# Configuration
REPO_URL="https://github.com/yourusername/kuzu-memory"
INSTALL_DIR="${HOME}/.local/kuzu-memory"
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${HOME}/.config/kuzu-memory"
TEMP_DIR="/tmp/kuzu-memory-install-$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_header() {
    echo -e "\n${CYAN}==============================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}==============================================================${NC}\n"
}

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

# Cleanup function
cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Detect Python
detect_python() {
    for py in python3.12 python3.11 python3.10 python3.9 python3 python; do
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

    return 1
}

# Detect Claude Code installation
detect_claude_code() {
    local os_type=$(detect_os)
    local claude_config=""

    case "$os_type" in
        macos)
            claude_config="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
            ;;
        linux)
            claude_config="${HOME}/.config/Claude/claude_desktop_config.json"
            ;;
        windows)
            claude_config="${APPDATA}/Claude/claude_desktop_config.json"
            ;;
    esac

    if [ -f "$claude_config" ]; then
        echo "$claude_config"
        return 0
    fi

    return 1
}

# Download and install KuzuMemory
install_kuzu_memory() {
    log_header "Installing KuzuMemory"

    # Create temp directory
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"

    # Check if we should install from PyPI or from source
    log_info "Downloading KuzuMemory..."

    # Try to install from PyPI first
    if pip show kuzu-memory &> /dev/null; then
        log_info "KuzuMemory already installed via pip, upgrading..."
        pip install --upgrade kuzu-memory
    else
        # Try to clone from git or download release
        if command -v git &> /dev/null; then
            log_info "Cloning KuzuMemory repository..."
            git clone "$REPO_URL" kuzu-memory
            cd kuzu-memory

            # Install in development mode
            pip install -e .
        else
            # Install from PyPI
            log_info "Installing from PyPI..."
            pip install kuzu-memory
        fi
    fi

    log_success "KuzuMemory package installed"
}

# Create wrapper scripts
create_wrappers() {
    log_header "Creating Wrapper Scripts"

    mkdir -p "$BIN_DIR"

    # Create main wrapper
    cat > "$BIN_DIR/kuzu-memory" << 'EOF'
#!/bin/bash
# KuzuMemory CLI wrapper
exec python -m kuzu_memory.cli.commands "$@"
EOF
    chmod +x "$BIN_DIR/kuzu-memory"

    # Create MCP server wrapper
    cat > "$BIN_DIR/kuzu-memory-mcp" << 'EOF'
#!/bin/bash
# KuzuMemory MCP Server wrapper
exec python -m kuzu_memory.mcp.run_server "$@"
EOF
    chmod +x "$BIN_DIR/kuzu-memory-mcp"

    log_success "Wrapper scripts created in $BIN_DIR"
}

# Setup Claude Code integration
setup_claude_code() {
    log_header "Setting Up Claude Code Integration"

    local claude_config=$(detect_claude_code || echo "")

    if [ -z "$claude_config" ]; then
        log_warning "Claude Code not detected. Skipping integration setup."
        log_info "You can manually configure Claude Code later."
        return
    fi

    log_info "Found Claude Code configuration at: $claude_config"

    # Create MCP configuration
    mkdir -p "$CONFIG_DIR"

    cat > "$CONFIG_DIR/mcp_server_config.json" << EOF
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "$BIN_DIR/kuzu-memory-mcp",
      "args": [],
      "env": {
        "KUZU_MEMORY_HOME": "$INSTALL_DIR"
      }
    }
  }
}
EOF

    # Try to merge with existing Claude config
    if [ -f "$claude_config" ]; then
        log_info "Backing up existing Claude configuration..."
        cp "$claude_config" "${claude_config}.backup-$(date +%Y%m%d-%H%M%S)"

        # Check if jq is available for JSON merging
        if command -v jq &> /dev/null; then
            log_info "Updating Claude configuration..."

            # Merge configurations
            jq -s '.[0] * .[1]' "$claude_config" "$CONFIG_DIR/mcp_server_config.json" > "${claude_config}.tmp"
            mv "${claude_config}.tmp" "$claude_config"

            log_success "Claude Code configuration updated"
        else
            log_warning "jq not found. Please manually add the MCP configuration to Claude Code."
            log_info "Configuration saved to: $CONFIG_DIR/mcp_server_config.json"
        fi
    else
        log_info "Creating new Claude configuration..."
        cp "$CONFIG_DIR/mcp_server_config.json" "$claude_config"
        log_success "Claude Code configuration created"
    fi
}

# Setup shell integration
setup_shell() {
    log_header "Setting Up Shell Integration"

    local shell_name=$(basename "$SHELL")
    local shell_config=""

    case "$shell_name" in
        bash)
            shell_config="${HOME}/.bashrc"
            ;;
        zsh)
            shell_config="${HOME}/.zshrc"
            ;;
        fish)
            shell_config="${HOME}/.config/fish/config.fish"
            ;;
        *)
            shell_config="${HOME}/.profile"
            ;;
    esac

    if [ -f "$shell_config" ]; then
        # Check if PATH already contains our bin directory
        if ! grep -q "$BIN_DIR" "$shell_config" 2>/dev/null; then
            echo "" >> "$shell_config"
            echo "# KuzuMemory PATH" >> "$shell_config"

            if [ "$shell_name" = "fish" ]; then
                echo "set -gx PATH \$PATH $BIN_DIR" >> "$shell_config"
            else
                echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$shell_config"
            fi

            log_success "Added $BIN_DIR to PATH in $shell_config"
        else
            log_info "PATH already configured"
        fi

        # Add aliases
        if ! grep -q "alias km=" "$shell_config" 2>/dev/null; then
            echo "" >> "$shell_config"
            echo "# KuzuMemory aliases" >> "$shell_config"
            echo "alias km='kuzu-memory'" >> "$shell_config"
            echo "alias kme='kuzu-memory enhance'" >> "$shell_config"
            echo "alias kml='kuzu-memory learn'" >> "$shell_config"
            echo "alias kmr='kuzu-memory recall'" >> "$shell_config"

            log_success "Added KuzuMemory aliases"
        else
            log_info "Aliases already configured"
        fi
    fi
}

# Main installation
main() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║            🧠 KuzuMemory Claude Code Installer 🧠           ║"
    echo "║                                                              ║"
    echo "║      Intelligent Memory System for AI Applications          ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # Check prerequisites
    log_header "Checking Prerequisites"

    # Check OS
    OS_TYPE=$(detect_os)
    log_info "Operating System: $OS_TYPE"

    # Check Python
    if ! PYTHON=$(detect_python); then
        log_error "Python 3.9+ is required but not found"
        log_info "Please install Python 3.9 or higher and try again"
        exit 1
    fi
    log_success "Found Python: $PYTHON"

    # Check pip
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        log_error "pip is required but not found"
        log_info "Please install pip and try again"
        exit 1
    fi
    log_success "Found pip"

    # Install KuzuMemory
    install_kuzu_memory

    # Create wrappers
    create_wrappers

    # Setup Claude Code
    setup_claude_code

    # Setup shell
    setup_shell

    # Final instructions
    log_header "Installation Complete! 🎉"

    echo -e "${GREEN}KuzuMemory has been successfully installed!${NC}\n"

    echo "Next steps:"
    echo "1. Restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
    echo "2. Initialize a project: kuzu-memory init"
    echo "3. Test the installation: kuzu-memory --help"
    echo ""
    echo "Quick commands:"
    echo "  km remember \"Project uses FastAPI\""
    echo "  km enhance \"How do I create an endpoint?\""
    echo "  km learn \"User prefers async patterns\""
    echo "  km recall \"database configuration\""
    echo ""

    if detect_claude_code &> /dev/null; then
        echo "Claude Code Integration:"
        echo "  ✓ MCP server configured and ready"
        echo "  ✓ Restart Claude Code to load the new MCP server"
    else
        echo "Claude Code Integration:"
        echo "  ⚠ Claude Code not detected"
        echo "  ⚠ Install Claude Code and run this installer again"
    fi

    echo ""
    log_success "Happy coding with KuzuMemory! 🧠✨"
}

# Run main installation
main "$@"