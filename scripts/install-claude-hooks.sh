#!/bin/bash
#
# KuzuMemory Claude Code Hooks Installer
#
# This script installs and configures KuzuMemory integration with Claude Desktop
# using the MCP (Model Context Protocol) server.
#
# Usage:
#   ./install-claude-hooks.sh           # Interactive installation
#   ./install-claude-hooks.sh --help    # Show help
#   ./install-claude-hooks.sh --force   # Force reinstall
#

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT_NAME="$(basename "$0")"
VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
FORCE_INSTALL=false
SKIP_TEST=false
VERBOSE=false
UNINSTALL=false

# Print functions
print_header() {
    echo -e "\n${MAGENTA}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}🧠 KuzuMemory Claude Code Hooks Installer v${VERSION}${NC}  ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_step() {
    echo -e "\n${CYAN}▶${NC} $1"
}

# Show usage
show_usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Install KuzuMemory integration with Claude Desktop using MCP server.

OPTIONS:
    -h, --help          Show this help message
    -f, --force         Force reinstallation even if already installed
    -u, --uninstall     Uninstall Claude hooks
    -t, --skip-test     Skip installation testing
    -v, --verbose       Enable verbose output
    --version           Show version information

EXAMPLES:
    $SCRIPT_NAME                    # Interactive installation
    $SCRIPT_NAME --force            # Force reinstall
    $SCRIPT_NAME --uninstall        # Remove Claude integration

For more information, visit: https://github.com/yourusername/kuzu-memory
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--force)
                FORCE_INSTALL=true
                shift
                ;;
            -u|--uninstall)
                UNINSTALL=true
                shift
                ;;
            -t|--skip-test)
                SKIP_TEST=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --version)
                echo "KuzuMemory Claude Hooks Installer v${VERSION}"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi

    if [ "$VERBOSE" = true ]; then
        print_info "Detected OS: $OS"
    fi
}

# Find Claude Desktop configuration directory
find_claude_config() {
    local config_dir=""

    case "$OS" in
        macos)
            # macOS locations
            if [ -d "$HOME/Library/Application Support/Claude" ]; then
                config_dir="$HOME/Library/Application Support/Claude"
            elif [ -d "$HOME/Library/Application Support/Claude Desktop" ]; then
                config_dir="$HOME/Library/Application Support/Claude Desktop"
            fi
            ;;
        linux)
            # Linux locations
            if [ -d "$HOME/.config/claude" ]; then
                config_dir="$HOME/.config/claude"
            elif [ -d "$HOME/.config/Claude" ]; then
                config_dir="$HOME/.config/Claude"
            fi
            ;;
        windows)
            # Windows locations (through WSL or Git Bash)
            if [ -d "$HOME/AppData/Roaming/Claude" ]; then
                config_dir="$HOME/AppData/Roaming/Claude"
            fi
            ;;
    esac

    # Fallback to common locations
    if [ -z "$config_dir" ]; then
        if [ -d "$HOME/.claude" ]; then
            config_dir="$HOME/.claude"
        fi
    fi

    echo "$config_dir"
}

# Check prerequisites
check_prerequisites() {
    local errors=()

    print_step "Checking prerequisites..."

    # Check Python
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        errors+=("Python is not installed")
    else
        if [ "$VERBOSE" = true ]; then
            local python_version=$(python3 --version 2>&1 || python --version 2>&1)
            print_info "Found: $python_version"
        fi
    fi

    # Check kuzu-memory
    if ! command -v kuzu-memory &> /dev/null; then
        errors+=("kuzu-memory is not installed. Install with: pip install kuzu-memory")
    else
        if [ "$VERBOSE" = true ]; then
            local kuzu_version=$(kuzu-memory --version 2>&1 || echo "version unknown")
            print_info "Found kuzu-memory: $kuzu_version"
        fi
    fi

    # Check Git (for project detection)
    if ! command -v git &> /dev/null; then
        print_warning "Git not found - project detection may be limited"
    fi

    # Check for Claude Desktop
    local claude_config=$(find_claude_config)
    if [ -z "$claude_config" ]; then
        print_warning "Claude Desktop not detected - will create local configuration only"
    else
        print_success "Claude Desktop detected at: $claude_config"
        CLAUDE_CONFIG_DIR="$claude_config"
    fi

    # Report errors
    if [ ${#errors[@]} -gt 0 ]; then
        print_error "Prerequisites not met:"
        for error in "${errors[@]}"; do
            echo "  • $error"
        done
        return 1
    fi

    print_success "All prerequisites met"
    return 0
}

# Install Claude hooks
install_hooks() {
    print_step "Installing Claude hooks..."

    # Use kuzu-memory CLI to install
    if [ "$FORCE_INSTALL" = true ]; then
        kuzu-memory claude install --force
    else
        kuzu-memory claude install
    fi

    if [ $? -eq 0 ]; then
        print_success "Claude hooks installed successfully"
        return 0
    else
        print_error "Failed to install Claude hooks"
        return 1
    fi
}

# Uninstall Claude hooks
uninstall_hooks() {
    print_step "Uninstalling Claude hooks..."

    kuzu-memory claude uninstall --force

    if [ $? -eq 0 ]; then
        print_success "Claude hooks uninstalled successfully"
        return 0
    else
        print_error "Failed to uninstall Claude hooks"
        return 1
    fi
}

# Test installation
test_installation() {
    print_step "Testing installation..."

    # Run the test command
    kuzu-memory claude test

    if [ $? -eq 0 ]; then
        print_success "Installation test passed"
        return 0
    else
        print_warning "Some tests failed - check output above"
        return 1
    fi
}

# Show next steps
show_next_steps() {
    echo -e "\n${MAGENTA}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}                    ${GREEN}✨ Installation Complete! ✨${NC}                   ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════════╝${NC}"

    echo -e "\n${CYAN}Next Steps:${NC}"
    echo "1. Restart Claude Desktop (if running)"
    echo "2. Open your project in Claude"
    echo "3. KuzuMemory will automatically enhance your interactions!"

    echo -e "\n${CYAN}Useful Commands:${NC}"
    echo "  kuzu-memory claude status    # Check installation status"
    echo "  kuzu-memory claude test      # Test the integration"
    echo "  kuzu-memory stats            # View memory statistics"
    echo "  kuzu-memory recent           # Show recent memories"

    echo -e "\n${CYAN}Documentation:${NC}"
    echo "  • Project CLAUDE.md file has been created with guidelines"
    echo "  • Run 'kuzu-memory claude wizard' for interactive setup"
    echo "  • Visit https://github.com/yourusername/kuzu-memory for docs"
}

# Interactive mode
run_interactive() {
    print_header

    echo "This wizard will help you set up KuzuMemory with Claude Desktop."
    echo "Let's get started!"

    # Confirm project
    echo -e "\n${CYAN}Project Detection:${NC}"
    echo "Current directory: $(pwd)"
    read -p "Is this the correct project directory? (y/n) [y]: " confirm
    confirm=${confirm:-y}

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        read -p "Enter the project directory path: " project_path
        cd "$project_path" || {
            print_error "Invalid directory: $project_path"
            exit 1
        }
    fi

    # Run the wizard
    kuzu-memory claude wizard
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"

    # Detect OS
    detect_os

    # Print header
    print_header

    # Check prerequisites
    if ! check_prerequisites; then
        print_error "Prerequisites check failed. Please install missing components."
        exit 1
    fi

    # Handle uninstall
    if [ "$UNINSTALL" = true ]; then
        uninstall_hooks
        exit $?
    fi

    # Check if interactive mode
    if [ -t 0 ] && [ $# -eq 0 ]; then
        # No arguments and running interactively
        run_interactive
    else
        # Run installation
        install_hooks

        # Test if requested
        if [ "$SKIP_TEST" = false ]; then
            test_installation
        fi

        # Show next steps
        show_next_steps
    fi
}

# Run main function
main "$@"