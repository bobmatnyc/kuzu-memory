"""
Package manager implementations for KuzuMemory installation.

Contains integration examples and templates for different programming languages.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .system_utils import FileOperations

logger = logging.getLogger(__name__)


class IntegrationTemplates:
    """Templates for various programming language integrations."""

    @staticmethod
    def get_python_integration() -> str:
        """Get Python integration template."""
        return '''#!/usr/bin/env python3
"""
Python Integration Example for KuzuMemory

This module demonstrates how to integrate KuzuMemory with Python AI applications.
Uses subprocess calls for reliability and compatibility.
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Any, Optional


class KuzuMemoryIntegration:
    """
    Python integration for KuzuMemory AI memory system.

    Provides simple, reliable integration using CLI subprocess calls.
    This approach ensures compatibility and avoids import conflicts.
    """

    def __init__(self, project_path: Optional[str] = None, timeout: int = 5) -> None:
        """
        Initialize KuzuMemory integration.

        Args:
            project_path: Path to project root (auto-detected if None)
            timeout: Timeout for CLI operations in seconds
        """
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.timeout = timeout

    def enhance_prompt(self, prompt: str, format: str = 'plain',
                      max_memories: int = 5) -> str:
        """
        Enhance a prompt with relevant memory context.

        Args:
            prompt: Original prompt to enhance
            format: Output format ('plain', 'context', 'json')
            max_memories: Maximum memories to include

        Returns:
            Enhanced prompt with context
        """
        try:
            cmd = [
                'kuzu-memory', 'enhance', prompt,
                '--format', format,
                '--max-memories', str(max_memories),
                '--project-root', str(self.project_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True
            )

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            print(f"Warning: Enhancement timed out after {self.timeout}s", file=sys.stderr)
            return prompt
        except subprocess.CalledProcessError as e:
            print(f"Warning: Enhancement failed: {e}", file=sys.stderr)
            return prompt
        except FileNotFoundError:
            print("Error: kuzu-memory command not found", file=sys.stderr)
            return prompt

    def store_learning(self, content: str, source: str = 'ai-conversation',
                      quiet: bool = True, metadata: Optional[dict[str, Any]] = None) -> bool:
        """
        Store learning content asynchronously (non-blocking).

        Args:
            content: Content to learn from
            source: Source identifier
            quiet: Suppress output (recommended for AI workflows)
            metadata: Additional metadata as dict

        Returns:
            True if learning was queued successfully
        """
        try:
            cmd = [
                'kuzu-memory', 'learn', content,
                '--source', source,
                '--project-root', str(self.project_path)
            ]

            if quiet:
                cmd.append('--quiet')

            if metadata:
                cmd.extend(['--metadata', json.dumps(metadata)])

            # Fire and forget - don't check return code
            subprocess.run(cmd, timeout=self.timeout, check=False)
            return True

        except Exception as e:
            print(f"Warning: Learning failed: {e}", file=sys.stderr)
            return False

    def get_project_stats(self) -> dict[str, Any]:
        """
        Get project memory statistics.

        Returns:
            Dictionary with project statistics
        """
        try:
            cmd = [
                'kuzu-memory', 'stats',
                '--format', 'json',
                '--project-root', str(self.project_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True
            )

            return json.loads(result.stdout)

        except Exception as e:
            print(f"Warning: Stats retrieval failed: {e}", file=sys.stderr)
            return {}


# Example usage functions
def ai_conversation_with_memory(user_input: str, memory: KuzuMemoryIntegration) -> str:
    """
    Example of AI conversation enhanced with memory.

    Args:
        user_input: User's input/question
        memory: KuzuMemory integration instance

    Returns:
        AI response
    """
    # Enhance prompt with memory context
    enhanced_prompt = memory.enhance_prompt(user_input)

    # Send enhanced prompt to your AI system
    ai_response = your_ai_system(enhanced_prompt)

    # Store the learning asynchronously (non-blocking)
    learning_content = f"User asked: {user_input}\\nAI responded: {ai_response}"
    memory.store_learning(learning_content, source="conversation")

    return ai_response


def your_ai_system(prompt: str) -> str:
    """
    Placeholder for your AI system integration.
    Replace with actual AI model calls (OpenAI, Anthropic, etc.)
    """
    return f"AI response to: {prompt}"


def main() -> None:
    """Example usage of KuzuMemory integration."""
    print("KuzuMemory Python Integration Example")

    # Initialize memory integration
    memory = KuzuMemoryIntegration()

    # Example conversation
    questions = [
        "How do I structure an API endpoint?",
        "What's the best way to handle database connections?",
        "How should I write tests for this project?"
    ]

    for question in questions:
        print(f"\\nUser: {question}")
        response = ai_conversation_with_memory(question, memory)
        print(f"AI: {response}")

    # Show project statistics
    print("\\nProject Memory Statistics:")
    stats = memory.get_project_stats()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
'''

    @staticmethod
    def get_javascript_integration() -> str:
        """Get JavaScript/Node.js integration template."""
        return """#!/usr/bin/env node
/**
 * JavaScript/Node.js Integration Example for KuzuMemory
 *
 * This module demonstrates how to integrate KuzuMemory with JavaScript AI applications.
 * Uses child_process.spawn for reliable CLI integration.
 */

const { spawn } = require('child_process');
const path = require('path');

class KuzuMemoryIntegration {
    /**
     * Initialize KuzuMemory integration.
     *
     * @param {string} projectPath - Path to project root (auto-detected if null)
     * @param {number} timeout - Timeout for CLI operations in milliseconds
     */
    constructor(projectPath = null, timeout = 5000) {
        this.projectPath = projectPath || process.cwd();
        this.timeout = timeout;
    }

    /**
     * Enhance a prompt with relevant memory context.
     *
     * @param {string} prompt - Original prompt to enhance
     * @param {string} format - Output format ('plain', 'context', 'json')
     * @param {number} maxMemories - Maximum memories to include
     * @returns {Promise<string>} Enhanced prompt with context
     */
    async enhancePrompt(prompt, format = 'plain', maxMemories = 5) {
        try {
            const args = [
                'enhance', prompt,
                '--format', format,
                '--max-memories', maxMemories.toString(),
                '--project-root', this.projectPath
            ];

            const result = await this._runCommand('kuzu-memory', args);
            return result.trim();

        } catch (error) {
            console.warn(`Enhancement failed: ${error.message}`);
            return prompt;
        }
    }

    /**
     * Store learning content asynchronously (non-blocking).
     *
     * @param {string} content - Content to learn from
     * @param {string} source - Source identifier
     * @param {boolean} quiet - Suppress output (recommended for AI workflows)
     * @param {Object} metadata - Additional metadata
     * @returns {Promise<boolean>} True if learning was queued successfully
     */
    async storeLearning(content, source = 'ai-conversation', quiet = true, metadata = null) {
        try {
            const args = [
                'learn', content,
                '--source', source,
                '--project-root', this.projectPath
            ];

            if (quiet) {
                args.push('--quiet');
            }

            if (metadata) {
                args.push('--metadata', JSON.stringify(metadata));
            }

            // Fire and forget - don't wait for completion
            this._runCommand('kuzu-memory', args, false);
            return true;

        } catch (error) {
            console.warn(`Learning failed: ${error.message}`);
            return false;
        }
    }

    /**
     * Get project memory statistics.
     *
     * @returns {Promise<Object>} Project statistics object
     */
    async getProjectStats() {
        try {
            const args = [
                'stats',
                '--format', 'json',
                '--project-root', this.projectPath
            ];

            const result = await this._runCommand('kuzu-memory', args);
            return JSON.parse(result);

        } catch (error) {
            console.warn(`Stats retrieval failed: ${error.message}`);
            return {};
        }
    }

    /**
     * Run a command using child_process.spawn.
     *
     * @param {string} command - Command to run
     * @param {Array<string>} args - Command arguments
     * @param {boolean} wait - Whether to wait for completion
     * @returns {Promise<string>} Command output
     * @private
     */
    _runCommand(command, args, wait = true) {
        return new Promise((resolve, reject) => {
            const child = spawn(command, args);

            let stdout = '';
            let stderr = '';

            child.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            child.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            if (!wait) {
                resolve(''); // For fire-and-forget operations
                return;
            }

            const timer = setTimeout(() => {
                child.kill();
                reject(new Error(`Command timed out after ${this.timeout}ms`));
            }, this.timeout);

            child.on('close', (code) => {
                clearTimeout(timer);

                if (code === 0) {
                    resolve(stdout);
                } else {
                    reject(new Error(`Command failed with code ${code}: ${stderr}`));
                }
            });

            child.on('error', (error) => {
                clearTimeout(timer);
                reject(error);
            });
        });
    }
}

/**
 * Example of AI conversation enhanced with memory.
 *
 * @param {string} userInput - User's input/question
 * @param {KuzuMemoryIntegration} memory - KuzuMemory integration instance
 * @returns {Promise<string>} AI response
 */
async function aiConversationWithMemory(userInput, memory) {
    // Enhance prompt with memory context
    const enhancedPrompt = await memory.enhancePrompt(userInput);

    // Send enhanced prompt to your AI system
    const aiResponse = await yourAISystem(enhancedPrompt);

    // Store the learning asynchronously (non-blocking)
    const learningContent = `User asked: ${userInput}\\nAI responded: ${aiResponse}`;
    await memory.storeLearning(learningContent, 'conversation');

    return aiResponse;
}

/**
 * Placeholder for your AI system integration.
 * Replace with actual AI model calls (OpenAI, Anthropic, etc.)
 *
 * @param {string} prompt - Enhanced prompt
 * @returns {Promise<string>} AI response
 */
async function yourAISystem(prompt) {
    return `AI response to: ${prompt}`;
}

/**
 * Example usage of KuzuMemory integration.
 */
async function main() {
    console.log('KuzuMemory JavaScript Integration Example');

    // Initialize memory integration
    const memory = new KuzuMemoryIntegration();

    // Example conversation
    const questions = [
        "How do I structure an API endpoint?",
        "What's the best way to handle database connections?",
        "How should I write tests for this project?"
    ];

    for (const question of questions) {
        console.log(`\\nUser: ${question}`);
        const response = await aiConversationWithMemory(question, memory);
        console.log(`AI: ${response}`);
    }

    // Show project statistics
    console.log('\\nProject Memory Statistics:');
    const stats = await memory.getProjectStats();
    console.log(JSON.stringify(stats, null, 2));
}

// Run main function if this file is executed directly
if (require.main === module) {
    main().catch(console.error);
}

module.exports = { KuzuMemoryIntegration, aiConversationWithMemory };
"""

    @staticmethod
    def get_shell_integration() -> str:
        """Get shell script integration template."""
        return """#!/bin/bash
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
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

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
    if enhanced=$(timeout "$TIMEOUT" kuzu-memory enhance "$prompt" \\
                 --format "$format" \\
                 --max-memories "$max_memories" \\
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
    local learning_content="User asked: $user_input\\nAI responded: $ai_response"
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
"""

    @staticmethod
    def get_integration_guide(ai_system: str = "Your AI System") -> str:
        """Get the main integration guide markdown."""
        return f"""# KuzuMemory Integration Guide

Welcome to KuzuMemory! This guide shows you how to integrate KuzuMemory with {ai_system} for intelligent, persistent memory.

## 🎯 Overview

KuzuMemory provides:
- **Sub-100ms context retrieval** for AI responses
- **Async learning operations** (non-blocking)
- **Project-specific memory** (git-committed)
- **Universal compatibility** via CLI interface

## 🚀 Quick Start

### 1. Initialize Your Project
```bash
cd your-project
kuzu-memory init
```

### 2. Basic Usage Pattern
```bash
# Store project information
kuzu-memory remember "This project uses FastAPI with PostgreSQL"

# Enhance AI prompts with context
enhanced=$(kuzu-memory enhance "How do I deploy this?" --format plain)

# Learn from conversations (async)
kuzu-memory learn "User prefers TypeScript over JavaScript" --quiet
```

## 🔧 Integration Patterns

### Python Integration
See `examples/python_integration.py` for a complete Python integration example.

```python
from kuzu_memory_integration import KuzuMemoryIntegration

# Initialize
memory = KuzuMemoryIntegration()

# Enhance prompts
enhanced = memory.enhance_prompt("How do I structure an API?")

# Store learning (async)
memory.store_learning("User asked about API structure", "conversation")
```

### JavaScript/Node.js Integration
See `examples/javascript_integration.js` for a complete JavaScript example.

```javascript
const {{ KuzuMemoryIntegration }} = require('./kuzu_memory_integration');

// Initialize
const memory = new KuzuMemoryIntegration();

// Enhance prompts
const enhanced = await memory.enhancePrompt("How do I handle auth?");

// Store learning (async)
await memory.storeLearning("User asked about authentication", "conversation");
```

### Shell Integration
See `examples/shell_integration.sh` for a complete shell script example.

```bash
# Source the integration functions
source examples/shell_integration.sh

# Enhance prompts
enhanced=$(enhance_prompt "How do I optimize performance?")

# Store learning (background)
store_learning "User asked about performance" "conversation"
```

## 📚 Integration Examples

### AI Conversation Flow
```bash
# 1. User asks a question
user_input="How should I structure my database models?"

# 2. Enhance with project context
enhanced=$(kuzu-memory enhance "$user_input" --format plain)

# 3. Send enhanced prompt to AI
ai_response=$(your_ai_system "$enhanced")

# 4. Learn from the interaction (async)
kuzu-memory learn "User: $user_input\\nAI: $ai_response" --quiet --source conversation

# 5. Return response to user
echo "$ai_response"
```

### Batch Learning
```bash
# Learn from multiple sources
kuzu-memory learn "Team uses microservices architecture" --source team-decision
kuzu-memory learn "Prefer async/await over callbacks" --source code-style
kuzu-memory learn "Deploy to AWS ECS with Fargate" --source deployment
```

### Smart Context Enhancement
```bash
# Different enhancement formats
kuzu-memory enhance "deployment question" --format context  # Full context
kuzu-memory enhance "deployment question" --format plain    # Context only
kuzu-memory enhance "deployment question" --format json     # Structured data
```

## ⚡ Performance Best Practices

### 1. Keep Recalls Fast (< 100ms)
```bash
# Limit memories for speed
kuzu-memory enhance "question" --max-memories 3

# Use plain format for fastest processing
kuzu-memory enhance "question" --format plain
```

### 2. Use Async Learning
```bash
# Always use --quiet for AI workflows (non-blocking)
kuzu-memory learn "content" --quiet

# Sync learning only for testing
kuzu-memory learn "test content" --sync
```

### 3. Optimize System
```bash
# Auto-tune for large databases
kuzu-memory doctor autotune

# Run diagnostics
kuzu-memory doctor diagnose
```

## 🤖 {ai_system} Specific Integration

### Integration Steps
1. **Initialize**: Run `kuzu-memory init` in your project
2. **Enhance**: Add memory context to prompts before sending to {ai_system}
3. **Learn**: Store conversation outcomes for future reference
4. **Optimize**: Configure performance settings for your workflow

### Example Integration Code
```python
import subprocess

def enhance_for_{ai_system.lower().replace(" ", "_")}(prompt):
    \"\"\"Enhance prompt for {ai_system} with memory context.\"\"\"
    result = subprocess.run([
        'kuzu-memory', 'enhance', prompt, '--format', 'plain'
    ], capture_output=True, text=True, timeout=5)

    return result.stdout.strip() if result.returncode == 0 else prompt

def learn_from_{ai_system.lower().replace(" ", "_")}(prompt, response):
    \"\"\"Learn from {ai_system} conversation.\"\"\"
    learning = f"User: {{prompt}}\\n{ai_system}: {{response}}"
    subprocess.run([
        'kuzu-memory', 'learn', learning, '--quiet', '--source', '{ai_system.lower()}'
    ], check=False)
```

## 📊 Monitoring and Maintenance

### Check System Status
```bash
# Project overview
kuzu-memory project --verbose

# Memory statistics
kuzu-memory stats --detailed

# Recent activity
kuzu-memory recent --limit 20
```

### Cleanup and Optimization
```bash
# Remove expired memories
kuzu-memory cleanup

# Performance analysis
kuzu-memory temporal-analysis --limit 10

# Test performance
time kuzu-memory recall "test query"
```

## 🔧 Configuration

### Basic Configuration
```bash
# Create configuration file
kuzu-memory create-config ./kuzu-config.json

# Edit configuration as needed
# Key settings: memory limits, temporal decay, performance options
```

### Performance Tuning
```bash
# Auto-tune database performance
kuzu-memory doctor autotune

# Run full diagnostics
kuzu-memory doctor diagnose
```

## 📁 File Structure

After integration, your project will have:
```
your-project/
├── .kuzu-memory/           # Memory database and config
│   ├── memories.db         # Kuzu graph database
│   └── config.json        # Configuration file
├── examples/              # Integration examples
│   ├── python_integration.py
│   ├── javascript_integration.js
│   └── shell_integration.sh
└── kuzu-memory-integration.md  # This guide
```

## 🆘 Troubleshooting

### Common Issues
1. **Slow responses**: Use `--max-memories 3` and `--format plain`
2. **CLI not found**: Install with `pip install kuzu-memory`
3. **Permission errors**: Check write access to project directory
4. **Memory not working**: Ensure `kuzu-memory init` was run

### Debug Mode
```bash
# Enable debug logging
kuzu-memory --debug command

# Test functionality
kuzu-memory stats --detailed
```

### Performance Issues
```bash
# Auto-tune database
kuzu-memory doctor autotune

# Manual prune if needed
kuzu-memory prune --strategy percentage --percentage 20
```

## 🎯 Next Steps

1. **Explore Examples**: Check the `examples/` directory
2. **Read Documentation**: See project documentation for advanced features
3. **Join Community**: Contribute to the project or ask questions
4. **Optimize**: Fine-tune performance for your specific use case

## 📚 Additional Resources

- **CLI Reference**: `kuzu-memory --help`
- **Examples**: See `examples/` directory
- **Configuration**: `kuzu-memory create-config --help`
- **Diagnostics**: `kuzu-memory doctor --help`

---

**KuzuMemory: Making {ai_system} smarter, one memory at a time.** 🧠✨
"""


class ExampleGenerator:
    """Generates example files for different integration scenarios."""

    @staticmethod
    def create_python_example(project_root: Path) -> bool:
        """Create Python integration example."""
        examples_dir = project_root / "examples"
        if not FileOperations.ensure_directory(examples_dir):
            return False

        python_content = IntegrationTemplates.get_python_integration()
        python_path = examples_dir / "python_integration.py"

        if not FileOperations.write_file(python_path, python_content):
            return False

        FileOperations.make_executable(python_path)
        return True

    @staticmethod
    def create_javascript_example(project_root: Path) -> bool:
        """Create JavaScript integration example."""
        examples_dir = project_root / "examples"
        if not FileOperations.ensure_directory(examples_dir):
            return False

        js_content = IntegrationTemplates.get_javascript_integration()
        js_path = examples_dir / "javascript_integration.js"

        if not FileOperations.write_file(js_path, js_content):
            return False

        FileOperations.make_executable(js_path)
        return True

    @staticmethod
    def create_shell_example(project_root: Path) -> bool:
        """Create shell script integration example."""
        examples_dir = project_root / "examples"
        if not FileOperations.ensure_directory(examples_dir):
            return False

        shell_content = IntegrationTemplates.get_shell_integration()
        shell_path = examples_dir / "shell_integration.sh"

        if not FileOperations.write_file(shell_path, shell_content):
            return False

        FileOperations.make_executable(shell_path)
        return True

    @staticmethod
    def create_integration_guide(project_root: Path, ai_system: str = "Your AI System") -> bool:
        """Create main integration guide."""
        guide_content = IntegrationTemplates.get_integration_guide(ai_system)
        guide_path = project_root / "kuzu-memory-integration.md"

        return FileOperations.write_file(guide_path, guide_content)
