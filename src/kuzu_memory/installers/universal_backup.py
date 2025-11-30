"""
Universal Installer for KuzuMemory

Creates generic integration files that work with any AI system.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseInstaller, InstallationError, InstallationResult

logger = logging.getLogger(__name__)


class UniversalInstaller(BaseInstaller):
    """
    Universal installer for any AI system integration.

    Creates generic integration files and examples that can be
    adapted for any AI system.
    """

    @property
    def ai_system_name(self) -> str:
        return "Universal"

    @property
    def required_files(self) -> list[str]:
        return [
            "kuzu-memory-integration.md",
            "examples/python_integration.py",
            "examples/javascript_integration.js",
            "examples/shell_integration.sh",
        ]

    @property
    def description(self) -> str:
        return (
            "Creates universal integration files and examples that work with any AI system. "
            "Includes Python, JavaScript, and shell integration examples."
        )

    def install(self, force: bool = False, **kwargs: Any) -> InstallationResult:
        """
        Install universal integration files.

        Args:
            force: Force installation even if files exist
            **kwargs: Additional options
                - language: Primary language for examples (python, javascript, shell)
                - ai_system: Name of AI system for customization

        Returns:
            InstallationResult with installation details
        """
        try:
            # Check prerequisites
            errors = self.check_prerequisites()
            if errors:
                raise InstallationError(f"Prerequisites not met: {'; '.join(errors)}")

            # Get options
            primary_language = kwargs.get("language", "python")
            ai_system = kwargs.get("ai_system", "Your AI System")

            # Check if already installed and not forcing
            if not force:
                existing_files: list[Any] = []
                for file_pattern in self.required_files:
                    file_path = self.project_root / file_pattern
                    if file_path.exists():
                        existing_files.append(str(file_path))

                if existing_files:
                    raise InstallationError(
                        f"Universal integration already exists. Use --force to overwrite. "
                        f"Existing files: {', '.join(existing_files)}"
                    )

            # Install main integration guide
            self._install_integration_guide(ai_system)

            # Install examples
            self._install_python_example()
            self._install_javascript_example()
            self._install_shell_example()

            # Add language-specific note
            if primary_language != "python":
                self.warnings.append(
                    f"Primary language set to {primary_language}. "
                    f"See examples/{primary_language}_integration for your language."
                )

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=f"Successfully installed universal integration for {ai_system}",
                warnings=self.warnings,
            )

        except Exception as e:
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=f"Installation failed: {e}",
                warnings=self.warnings,
            )

    def _install_integration_guide(self, ai_system: str) -> None:
        """Install the main integration guide."""
        guide_content = f"""# KuzuMemory Integration Guide

This project uses KuzuMemory for intelligent project memory and context management. This guide shows how to integrate KuzuMemory with {ai_system}.

## Quick Start

### 1. Initialize KuzuMemory
```bash
kuzu-memory init
```

### 2. Basic Integration Pattern
```bash
# Enhance user prompts with project context (sync, fast)
kuzu-memory enhance "user question" --format plain

# Store learning from conversations (async, non-blocking)
kuzu-memory learn "information to store" --source ai-conversation --quiet
```

## Integration Architecture

### Two-Step Process
1. **Enhancement** (Synchronous): Add project context to user prompts
2. **Learning** (Asynchronous): Store information from conversations

### Performance Characteristics
- **Enhancement**: <100ms (synchronous, needed immediately)
- **Learning**: Async by default (non-blocking, happens in background)

## Command Reference

### Context Enhancement
```bash
# Basic enhancement
kuzu-memory enhance "How do I deploy this app?" --format plain

# JSON output for programmatic use
kuzu-memory enhance "What database should I use?" --format json

# Limit context size
kuzu-memory enhance "How do I test this?" --max-memories 3 --format plain
```

### Memory Storage
```bash
# Store project information (async by default)
kuzu-memory learn "Project uses FastAPI with PostgreSQL" --quiet

# Store with specific source
kuzu-memory learn "User prefers TypeScript" --source user-preference --quiet

# Store with metadata
kuzu-memory learn "API rate limit is 1000/hour" --metadata '{{"component": "api"}}' --quiet
```

### Project Management
```bash
# View project status
kuzu-memory project

# Show recent memories
kuzu-memory recent --format list

# Search for information
kuzu-memory recall "database setup"

# View statistics
kuzu-memory stats
```

## Integration Examples

See the `examples/` directory for complete integration examples:

- **Python**: `examples/python_integration.py`
- **JavaScript**: `examples/javascript_integration.js`
- **Shell**: `examples/shell_integration.sh`

## Best Practices

### For AI Integration
1. **Always enhance technical questions** - Use project context for better responses
2. **Store project information** - Learn from user interactions
3. **Handle errors gracefully** - Don't fail main flow on memory errors
4. **Use async learning** - Never block AI responses

### Performance Optimization
1. **Use timeouts** - Prevent hanging on memory operations
2. **Cache frequently used context** - Improve response times
3. **Monitor performance** - Track enhancement and learning times
4. **Limit context size** - Use `--max-memories` for large projects

### Error Handling
1. **Fallback to original prompt** - If enhancement fails
2. **Continue on storage failure** - Learning is optional
3. **Log errors appropriately** - For debugging and monitoring
4. **Provide user feedback** - When appropriate

## Monitoring and Debugging

### Check System Health
```bash
# View system statistics
kuzu-memory stats --detailed

# Check recent activity
kuzu-memory recent --count 20

# View project information
kuzu-memory project
```

### Debug Mode
```bash
# Enable debug output
kuzu-memory enhance "question" --debug
kuzu-memory learn "information" --debug
```

### Performance Monitoring
```bash
# Time commands for performance testing
time kuzu-memory enhance "How do I optimize this?"
time kuzu-memory learn "Performance optimization note"
```

## Troubleshooting

### Common Issues

**Command not found:**
```bash
# Check installation
which kuzu-memory
pip show kuzu-memory
```

**Slow performance:**
```bash
# Check system health
kuzu-memory stats --detailed

# Clear cache if needed
rm -rf kuzu-memories/.cache
```

**Database issues:**
```bash
# Reinitialize database
kuzu-memory init --force
```

### Getting Help
- Use `kuzu-memory COMMAND --help` for command-specific help
- Add `--debug` flag for detailed error information
- Check the examples in the `examples/` directory
- Review the KuzuMemory documentation

## Success Metrics

Your integration is working well when:
- ✅ AI responses become more project-specific over time
- ✅ Users don't need to repeat project context
- ✅ Team members get consistent AI responses
- ✅ Project knowledge is preserved across conversations
- ✅ New team members get instant project context

## Next Steps

1. **Customize the integration** - Adapt examples to your specific AI system
2. **Add project information** - Store initial project context
3. **Monitor performance** - Track enhancement and learning effectiveness
4. **Train your team** - Share integration patterns and best practices

Remember: The goal is seamless, invisible integration that makes AI responses more helpful and project-aware.
"""

        guide_path = self.project_root / "kuzu-memory-integration.md"
        if not self.write_file(guide_path, guide_content):
            raise InstallationError("Failed to create integration guide")

    def _install_python_example(self) -> None:
        """Install Python integration example."""
        python_content = '''#!/usr/bin/env python3
"""
KuzuMemory Python Integration Example

This example shows how to integrate KuzuMemory with a Python-based AI system.
"""

import subprocess
import json
import time
import logging
from typing import Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KuzuMemoryIntegration:
    """
    KuzuMemory integration for Python AI systems.

    Provides methods for enhancing prompts and storing learning.
    """

    def __init__(self, project_path: Optional[str] = None, timeout: int = 5) -> None:
        """
        Initialize integration.

        Args:
            project_path: Path to project directory (optional)
            timeout: Timeout for memory operations in seconds
        """
        self.project_path = project_path
        self.timeout = timeout

    def enhance_prompt(self, prompt: str, format: str = 'plain',
                      max_memories: int = 5) -> str:
        """
        Enhance prompt with project context.

        Args:
            prompt: Original user prompt
            format: Output format ('plain', 'json', 'context')
            max_memories: Maximum memories to include

        Returns:
            Enhanced prompt with project context
        """
        cmd = [
            'kuzu-memory', 'enhance', prompt,
            '--format', format,
            '--max-memories', str(max_memories)
        ]

        if self.project_path:
            cmd.extend(['--project', self.project_path])

        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout
            )

            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Enhancement completed in {elapsed:.1f}ms")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            logger.warning(f"Enhancement timed out after {self.timeout}s")
            return prompt
        except subprocess.CalledProcessError as e:
            logger.warning(f"Enhancement failed: {e}")
            return prompt
        except Exception as e:
            logger.error(f"Enhancement error: {e}")
            return prompt

    def store_learning(self, content: str, source: str = 'ai-conversation',
                      metadata: Optional[dict[str, Any]] = None) -> bool:
        """
        Store learning asynchronously.

        Args:
            content: Content to store
            source: Source of the learning
            metadata: Additional metadata

        Returns:
            True if submission successful, False otherwise
        """
        cmd = [
            'kuzu-memory', 'learn', content,
            '--source', source,
            '--quiet'
        ]

        if metadata:
            cmd.extend(['--metadata', json.dumps(metadata)])

        if self.project_path:
            cmd.extend(['--project', self.project_path])

        try:
            start_time = time.time()
            subprocess.run(cmd, check=False, timeout=self.timeout)

            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Learning submitted in {elapsed:.1f}ms")

            return True

        except subprocess.TimeoutExpired:
            logger.warning(f"Learning submission timed out after {self.timeout}s")
            return False
        except Exception as e:
            logger.warning(f"Learning submission failed: {e}")
            return False

    def get_project_stats(self) -> dict[str, Any]:
        """
        Get project memory statistics.

        Returns:
            Dictionary with project statistics
        """
        cmd = ['kuzu-memory', 'stats', '--format', 'json']

        if self.project_path:
            cmd.extend(['--project', self.project_path])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout
            )

            return json.loads(result.stdout)

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


def ai_conversation_with_memory(user_input: str, memory: KuzuMemoryIntegration) -> str:
    """
    Example AI conversation function with memory integration.

    Args:
        user_input: User's input/question
        memory: KuzuMemory integration instance

    Returns:
        AI response
    """
    # Step 1: Enhance prompt with project context
    enhanced_prompt = memory.enhance_prompt(user_input)

    # Step 2: Generate AI response (replace with your AI system)
    ai_response = your_ai_system(enhanced_prompt)

    # Step 3: Store learning from conversation (async, non-blocking)
    memory.store_learning(f"Q: {user_input} A: {ai_response}")

    return ai_response


def your_ai_system(prompt: str) -> str:
    """
    Placeholder for your AI system.

    Replace this with your actual AI system call.
    """
    return f"AI Response to: {prompt}"


def main() -> None:
    """Example usage of KuzuMemory integration."""
    # Initialize memory integration
    memory = KuzuMemoryIntegration()

    # Example conversation
    user_questions = [
        "How do I structure an API endpoint?",
        "What's the best way to handle database connections?",
        "How should I write tests for this project?"
    ]

    for question in user_questions:
        print(f"\\nUser: {question}")
        response = ai_conversation_with_memory(question, memory)
        print(f"AI: {response}")

    # Show project statistics
    stats = memory.get_project_stats()
    if stats:
        print(f"\\nProject Memory Stats:")
        print(f"Total memories: {stats.get('total_memories', 0)}")
        print(f"Recent queries: {stats.get('recent_queries', 0)}")


if __name__ == "__main__":
    main()
'''

        examples_dir = self.project_root / "examples"
        python_path = examples_dir / "python_integration.py"
        if not self.write_file(python_path, python_content):
            raise InstallationError("Failed to create Python example")

    def _install_javascript_example(self) -> None:
        """Install JavaScript integration example."""
        js_content = """#!/usr/bin/env node
/**
 * KuzuMemory JavaScript Integration Example
 *
 * This example shows how to integrate KuzuMemory with a JavaScript/Node.js AI system.
 */

const { spawn, execSync } = require('child_process');
const fs = require('fs');

class KuzuMemoryIntegration {
    /**
     * Initialize KuzuMemory integration.
     *
     * @param {string} projectPath - Path to project directory (optional)
     * @param {number} timeout - Timeout for operations in milliseconds
     */
    constructor(projectPath = null, timeout = 5000) {
        this.projectPath = projectPath;
        this.timeout = timeout;
    }

    /**
     * Enhance prompt with project context.
     *
     * @param {string} prompt - Original user prompt
     * @param {string} format - Output format ('plain', 'json', 'context')
     * @param {number} maxMemories - Maximum memories to include
     * @returns {string} Enhanced prompt
     */
    enhancePrompt(prompt, format = 'plain', maxMemories = 5) {
        try {
            const cmd = [
                'kuzu-memory', 'enhance', prompt,
                '--format', format,
                '--max-memories', maxMemories.toString()
            ];

            if (this.projectPath) {
                cmd.push('--project', this.projectPath);
            }

            const startTime = Date.now();
            const result = execSync(cmd.join(' '), {
                encoding: 'utf8',
                timeout: this.timeout
            });

            const elapsed = Date.now() - startTime;
            console.log(`Enhancement completed in ${elapsed}ms`);

            return result.trim();

        } catch (error) {
            console.warn(`Enhancement failed: ${error.message}`);
            return prompt; // Fallback to original
        }
    }

    /**
     * Store learning asynchronously.
     *
     * @param {string} content - Content to store
     * @param {string} source - Source of the learning
     * @param {Object} metadata - Additional metadata
     * @returns {boolean} True if submission successful
     */
    storeLearning(content, source = 'ai-conversation', metadata = null) {
        try {
            const cmd = [
                'kuzu-memory', 'learn', content,
                '--source', source,
                '--quiet'
            ];

            if (metadata) {
                cmd.push('--metadata', JSON.stringify(metadata));
            }

            if (this.projectPath) {
                cmd.push('--project', this.projectPath);
            }

            const startTime = Date.now();

            // Spawn async process (non-blocking)
            const child = spawn(cmd[0], cmd.slice(1), {
                detached: true,
                stdio: 'ignore'
            });

            child.unref(); // Don't wait for completion

            const elapsed = Date.now() - startTime;
            console.log(`Learning submitted in ${elapsed}ms`);

            return true;

        } catch (error) {
            console.warn(`Learning submission failed: ${error.message}`);
            return false;
        }
    }

    /**
     * Get project memory statistics.
     *
     * @returns {Object} Project statistics
     */
    getProjectStats() {
        try {
            const cmd = ['kuzu-memory', 'stats', '--format', 'json'];

            if (this.projectPath) {
                cmd.push('--project', this.projectPath);
            }

            const result = execSync(cmd.join(' '), {
                encoding: 'utf8',
                timeout: this.timeout
            });

            return JSON.parse(result);

        } catch (error) {
            console.error(`Failed to get stats: ${error.message}`);
            return {};
        }
    }
}

/**
 * Example AI conversation function with memory integration.
 *
 * @param {string} userInput - User's input/question
 * @param {KuzuMemoryIntegration} memory - Memory integration instance
 * @returns {string} AI response
 */
function aiConversationWithMemory(userInput, memory) {
    // Step 1: Enhance prompt with project context
    const enhancedPrompt = memory.enhancePrompt(userInput);

    // Step 2: Generate AI response (replace with your AI system)
    const aiResponse = yourAISystem(enhancedPrompt);

    // Step 3: Store learning from conversation (async, non-blocking)
    memory.storeLearning(`Q: ${userInput} A: ${aiResponse}`);

    return aiResponse;
}

/**
 * Placeholder for your AI system.
 * Replace this with your actual AI system call.
 *
 * @param {string} prompt - Enhanced prompt
 * @returns {string} AI response
 */
function yourAISystem(prompt) {
    return `AI Response to: ${prompt}`;
}

/**
 * Example usage of KuzuMemory integration.
 */
function main() {
    // Initialize memory integration
    const memory = new KuzuMemoryIntegration();

    // Example conversation
    const userQuestions = [
        "How do I structure an API endpoint?",
        "What's the best way to handle database connections?",
        "How should I write tests for this project?"
    ];

    userQuestions.forEach(question => {
        console.log(`\\nUser: ${question}`);
        const response = aiConversationWithMemory(question, memory);
        console.log(`AI: ${response}`);
    });

    // Show project statistics
    setTimeout(() => {
        const stats = memory.getProjectStats();
        if (Object.keys(stats).length > 0) {
            console.log(`\\nProject Memory Stats:`);
            console.log(`Total memories: ${stats.total_memories || 0}`);
            console.log(`Recent queries: ${stats.recent_queries || 0}`);
        }
    }, 1000); // Wait a bit for async operations
}

// Run example if this file is executed directly
if (require.main === module) {
    main();
}

module.exports = { KuzuMemoryIntegration };
"""

        examples_dir = self.project_root / "examples"
        js_path = examples_dir / "javascript_integration.js"
        if not self.write_file(js_path, js_content):
            raise InstallationError("Failed to create JavaScript example")

    def _install_shell_example(self) -> None:
        """Install shell integration example."""
        shell_content = """#!/bin/bash
# KuzuMemory Shell Integration Example
#
# This example shows how to integrate KuzuMemory with shell-based AI systems.

set -e  # Exit on error

# Configuration
TIMEOUT=5
PROJECT_PATH=""
DEBUG=false

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
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to enhance prompts with project context
enhance_prompt() {
    local prompt="$1"
    local format="${2:-plain}"
    local max_memories="${3:-5}"

    local cmd="kuzu-memory enhance \\"$prompt\\" --format $format --max-memories $max_memories"

    if [[ -n "$PROJECT_PATH" ]]; then
        cmd="$cmd --project \\"$PROJECT_PATH\\""
    fi

    if [[ "$DEBUG" == "true" ]]; then
        log_info "Running: $cmd"
    fi

    local start_time=$(date +%s%3N)

    # Try to enhance prompt, fallback to original on failure
    if result=$(timeout $TIMEOUT bash -c "$cmd" 2>/dev/null); then
        local end_time=$(date +%s%3N)
        local elapsed=$((end_time - start_time))

        if [[ "$DEBUG" == "true" ]]; then
            log_info "Enhancement completed in ${elapsed}ms"
        fi

        echo "$result"
    else
        if [[ "$DEBUG" == "true" ]]; then
            log_warn "Enhancement failed, using original prompt"
        fi
        echo "$prompt"
    fi
}

# Function to store learning asynchronously
store_learning() {
    local content="$1"
    local source="${2:-ai-conversation}"
    local metadata="$3"

    local cmd="kuzu-memory learn \\"$content\\" --source \\"$source\\" --quiet"

    if [[ -n "$metadata" ]]; then
        cmd="$cmd --metadata \\"$metadata\\""
    fi

    if [[ -n "$PROJECT_PATH" ]]; then
        cmd="$cmd --project \\"$PROJECT_PATH\\""
    fi

    if [[ "$DEBUG" == "true" ]]; then
        log_info "Running: $cmd"
    fi

    local start_time=$(date +%s%3N)

    # Run in background (async, non-blocking)
    if timeout $TIMEOUT bash -c "$cmd" >/dev/null 2>&1 &; then
        local end_time=$(date +%s%3N)
        local elapsed=$((end_time - start_time))

        if [[ "$DEBUG" == "true" ]]; then
            log_info "Learning submitted in ${elapsed}ms"
        fi

        return 0
    else
        if [[ "$DEBUG" == "true" ]]; then
            log_warn "Learning submission failed"
        fi
        return 1
    fi
}

# Function to get project statistics
get_project_stats() {
    local cmd="kuzu-memory stats --format json"

    if [[ -n "$PROJECT_PATH" ]]; then
        cmd="$cmd --project \\"$PROJECT_PATH\\""
    fi

    if result=$(timeout $TIMEOUT bash -c "$cmd" 2>/dev/null); then
        echo "$result"
    else
        echo "{}"
    fi
}

# Example AI conversation function with memory integration
ai_conversation_with_memory() {
    local user_input="$1"

    log_info "User: $user_input"

    # Step 1: Enhance prompt with project context
    local enhanced_prompt
    enhanced_prompt=$(enhance_prompt "$user_input")

    # Step 2: Generate AI response (replace with your AI system)
    local ai_response
    ai_response=$(your_ai_system "$enhanced_prompt")

    # Step 3: Store learning from conversation (async, non-blocking)
    store_learning "Q: $user_input A: $ai_response"

    log_success "AI: $ai_response"
}

# Placeholder for your AI system
# Replace this with your actual AI system call
your_ai_system() {
    local prompt="$1"
    echo "AI Response to: $prompt"
}

# Function to check if KuzuMemory is available
check_kuzu_memory() {
    if ! command -v kuzu-memory &> /dev/null; then
        log_error "kuzu-memory command not found. Please install KuzuMemory first:"
        log_error "pip install kuzu-memory"
        exit 1
    fi

    log_success "KuzuMemory is available"
}

# Function to initialize project if needed
init_project_if_needed() {
    if [[ ! -d "kuzu-memories" ]]; then
        log_info "Initializing KuzuMemory for this project..."
        if kuzu-memory init; then
            log_success "KuzuMemory initialized"
        else
            log_error "Failed to initialize KuzuMemory"
            exit 1
        fi
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

        examples_dir = self.project_root / "examples"
        shell_path = examples_dir / "shell_integration.sh"
        if not self.write_file(shell_path, shell_content):
            raise InstallationError("Failed to create shell example")

        # Make shell script executable
        try:
            shell_path.chmod(0o755)
        except Exception as e:
            self.warnings.append(f"Could not make shell script executable: {e}")
