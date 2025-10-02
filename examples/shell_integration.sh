#!/bin/bash
# Shell Integration Example for KuzuMemory
#
# This script demonstrates how to integrate KuzuMemory with shell-based AI workflows.
# Uses direct CLI calls for maximum compatibility.

set -euo pipefail

# Configuration
PROJECT_PATH="${PROJECT_PATH:-$(pwd)}"
TIMEOUT="${TIMEOUT:-5}"
DEBUG="${DEBUG:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        echo -e "${YELLOW}[DEBUG]${NC} $1"
    fi
}

# Check if kuzu-memory is available
check_kuzu_memory() {
    if ! command -v kuzu-memory &> /dev/null; then
        log_error "kuzu-memory command not found. Please install KuzuMemory first."
        exit 1
    fi

    log_debug "kuzu-memory command found"
}

# Initialize project if needed
init_project_if_needed() {
    local kuzu_dir="$PROJECT_PATH/.kuzu-memory"

    if [[ ! -d "$kuzu_dir" ]]; then
        log_info "Initializing KuzuMemory for project..."
        if kuzu-memory init --project-root "$PROJECT_PATH"; then
            log_success "Project initialized successfully"
        else
            log_error "Failed to initialize project"
            exit 1
        fi
    else
        log_debug "Project already initialized"
    fi
}

# Enhance prompt with memory context
enhance_prompt() {
    local prompt="$1"
    local format="${2:-plain}"
    local max_memories="${3:-5}"

    log_debug "Enhancing prompt: $prompt"

    local enhanced
    if enhanced=$(timeout "$TIMEOUT" kuzu-memory enhance "$prompt" \
                 --format "$format" \
                 --max-memories "$max_memories" \
                 --project-root "$PROJECT_PATH" 2>/dev/null); then
        echo "$enhanced"
    else
        log_warn "Enhancement failed or timed out, using original prompt"
        echo "$prompt"
    fi
}

# Store learning content asynchronously
store_learning() {
    local content="$1"
    local source="${2:-ai-conversation}"
    local metadata="${3:-}"

    log_debug "Storing learning: ${content:0:50}..."

    local cmd=(kuzu-memory learn "$content" --source "$source" --quiet --project-root "$PROJECT_PATH")

    if [[ -n "$metadata" ]]; then
        cmd+=(--metadata "$metadata")
    fi

    # Fire and forget - run in background
    "${cmd[@]}" &
}

# Get project statistics
get_project_stats() {
    log_debug "Retrieving project statistics"

    if timeout "$TIMEOUT" kuzu-memory stats --format json --project-root "$PROJECT_PATH" 2>/dev/null; then
        return 0
    else
        log_warn "Failed to retrieve statistics"
        echo "{}"
        return 1
    fi
}

# AI conversation with memory (example function)
ai_conversation_with_memory() {
    local user_input="$1"

    log_info "User: $user_input"

    # Enhance prompt with memory context
    local enhanced_prompt
    enhanced_prompt=$(enhance_prompt "$user_input")

    # Send enhanced prompt to your AI system
    # Replace this with your actual AI system integration
    local ai_response
    ai_response=$(your_ai_system "$enhanced_prompt")

    log_info "AI: $ai_response"

    # Store the learning asynchronously
    local learning_content="User asked: $user_input\nAI responded: $ai_response"
    store_learning "$learning_content" "conversation"

    echo "$ai_response"
}

# Placeholder for your AI system integration
# Replace this with calls to your actual AI system (OpenAI, Anthropic, etc.)
your_ai_system() {
    local prompt="$1"
    echo "AI response to: $prompt"
}

# Test kuzu-memory functionality
test_functionality() {
    log_info "Testing KuzuMemory functionality"

    # Test basic commands
    if kuzu-memory --version >/dev/null 2>&1; then
        log_success "CLI version check passed"
    else
        log_error "CLI version check failed"
        exit 1
    fi

    # Test project-specific operations
    if kuzu-memory stats --project-root "$PROJECT_PATH" >/dev/null 2>&1; then
        log_success "Project stats check passed"
    else
        log_error "Project stats check failed"
        exit 1
    fi
}

# Main function
main() {
    log_info "KuzuMemory Shell Integration Example"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project)
                PROJECT_PATH="$2"
                shift 2
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: $0 [--project PATH] [--debug] [--timeout SECONDS]"
                echo "  --project PATH    Set project path"
                echo "  --debug          Enable debug output"
                echo "  --timeout SECONDS Set timeout for operations (default: 5)"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check prerequisites
    check_kuzu_memory
    init_project_if_needed

    # Example conversation
    local user_questions=(
        "How do I structure an API endpoint?"
        "What's the best way to handle database connections?"
        "How should I write tests for this project?"
    )

    for question in "${user_questions[@]}"; do
        echo
        ai_conversation_with_memory "$question"
    done

    # Show project statistics
    echo
    log_info "Project Memory Statistics:"
    local stats
    stats=$(get_project_stats)

    if [[ "$stats" != "{}" ]]; then
        echo "$stats" | jq . 2>/dev/null || echo "$stats"
    else
        log_warn "No statistics available"
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
