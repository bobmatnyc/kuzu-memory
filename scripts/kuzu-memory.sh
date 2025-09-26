#!/bin/bash
# KuzuMemory Development Shell Script
#
# This script runs KuzuMemory from source in the proper virtual environment.
# For production use, install via: pipx install kuzu-memory

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[KuzuMemory]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[KuzuMemory]${NC} $1"
}

print_error() {
    echo -e "${RED}[KuzuMemory]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[KuzuMemory]${NC} $1"
}

# Check if we're in the right directory
if [[ ! -f "$SCRIPT_DIR/src/kuzu_memory/__init__.py" ]]; then
    print_error "This script must be run from the KuzuMemory project root directory"
    print_error "Expected to find: src/kuzu_memory/__init__.py"
    exit 1
fi

# Function to find Python virtual environment
find_venv() {
    local venv_paths=(
        "$SCRIPT_DIR/venv"
        "$SCRIPT_DIR/.venv" 
        "$SCRIPT_DIR/env"
        "$HOME/.virtualenvs/kuzu-memory"
$HOME/.conda/envs/kuzu-memory
    )
    
    for venv_path in "${venv_paths[@]}"; do
        if [[ -d "$venv_path" ]]; then
            if [[ -f "$venv_path/bin/activate" ]]; then
                echo "$venv_path"
                return 0
            elif [[ -f "$venv_path/Scripts/activate" ]]; then  # Windows
                echo "$venv_path"
                return 0
            fi
        fi
    done
    
    return 1
}

# Function to create virtual environment if needed
setup_venv() {
    print_status "Setting up virtual environment..."
    
    # Try to find existing venv
    if VENV_PATH=$(find_venv); then
        print_success "Found existing virtual environment: $VENV_PATH"
        return 0
    fi
    
    # Create new venv
    local venv_dir="$SCRIPT_DIR/venv"
    print_status "Creating new virtual environment at: $venv_dir"
    
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv "$venv_dir"
    elif command -v python >/dev/null 2>&1; then
        python -m venv "$venv_dir"
    else
        print_error "Python not found. Please install Python 3.8 or higher."
        exit 1
    fi
    
    if [[ $? -eq 0 ]]; then
        print_success "Virtual environment created successfully"
        VENV_PATH="$venv_dir"
        return 0
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
}

# Function to activate virtual environment
activate_venv() {
    if [[ -z "$VENV_PATH" ]]; then
        if ! VENV_PATH=$(find_venv); then
            setup_venv
        fi
    fi
    
    local activate_script
    if [[ -f "$VENV_PATH/bin/activate" ]]; then
        activate_script="$VENV_PATH/bin/activate"
    elif [[ -f "$VENV_PATH/Scripts/activate" ]]; then  # Windows
        activate_script="$VENV_PATH/Scripts/activate"
    else
        print_error "Could not find activation script in: $VENV_PATH"
        exit 1
    fi
    
    print_status "Activating virtual environment: $VENV_PATH"
    source "$activate_script"
    
    # Verify activation
    if [[ "$VIRTUAL_ENV" != "$VENV_PATH" ]]; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi
}

# Function to install dependencies
install_deps() {
    print_status "Installing/updating dependencies..."
    
    # Upgrade pip first
    python -m pip install --upgrade pip
    
    # Install in development mode
    if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
    fi
    
    # Install in editable mode
    pip install -e "$SCRIPT_DIR"
    
    if [[ $? -eq 0 ]]; then
        print_success "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
}

# Function to check if dependencies are installed
check_deps() {
    python -c "import kuzu_memory" 2>/dev/null
    return $?
}

# Main execution
main() {
    print_status "KuzuMemory Development Environment"
    print_status "Running from source: $SCRIPT_DIR"
    
    # Setup and activate virtual environment
    activate_venv
    
    # Check if dependencies need to be installed
    if ! check_deps; then
        print_warning "Dependencies not found or outdated"
        install_deps
    fi
    
    # Add source directory to Python path
    export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
    
    # Execute KuzuMemory CLI with all arguments
    if [[ $# -eq 0 ]]; then
        # No arguments - show help
        python -m kuzu_memory.cli.commands --help
    else
        # Pass all arguments to the CLI
        python -m kuzu_memory.cli.commands "$@"
    fi
}

# Handle special commands
case "${1:-}" in
    --setup)
        print_status "Setting up development environment..."
        activate_venv
        install_deps
        print_success "Development environment ready!"
        print_status "Usage: ./kuzu-memory.sh [command] [options]"
        exit 0
        ;;
    --venv-info)
        if VENV_PATH=$(find_venv); then
            print_success "Virtual environment found: $VENV_PATH"
            if [[ -n "$VIRTUAL_ENV" ]]; then
                print_status "Currently activated: $VIRTUAL_ENV"
            else
                print_status "Not currently activated"
            fi
        else
            print_warning "No virtual environment found"
            print_status "Run: ./kuzu-memory.sh --setup"
        fi
        exit 0
        ;;
    --help-dev)
        echo "KuzuMemory Development Script"
        echo ""
        echo "Usage: ./kuzu-memory.sh [options] [kuzu-memory-args...]"
        echo ""
        echo "Development Options:"
        echo "  --setup      Set up development environment"
        echo "  --venv-info  Show virtual environment information"
        echo "  --help-dev   Show this help message"
        echo ""
        echo "All other arguments are passed to kuzu-memory CLI"
        echo ""
        echo "Examples:"
        echo "  ./kuzu-memory.sh --setup"
        echo "  ./kuzu-memory.sh demo"
        echo "  ./kuzu-memory.sh remember 'I love Python' --user-id dev"
        echo "  ./kuzu-memory.sh optimize --enable-cli"
        exit 0
        ;;
esac

# Run main function with all arguments
main "$@"
