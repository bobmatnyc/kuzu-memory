# AI Integration Guide

**Universal patterns for integrating KuzuMemory with any AI system**

> **Replaces**: This document consolidates and replaces:
> - `docs/auggie_integration.md`
> - `docs/SIMPLE_AUGGIE_INTEGRATION.md`

---

## 🎯 Integration Philosophy

**The Right Way: CLI-Only Integration**

KuzuMemory integrates with AI systems through simple subprocess calls to CLI commands. No HTTP servers, no complex APIs, no network dependencies - just fast, reliable command execution.

### Why CLI-Only is Superior

**❌ Complex Approach (HTTP Bridge)**:
- HTTP server to maintain
- API endpoints to manage
- Network requests and responses
- Error handling complexity
- Port management issues
- Additional failure points

**✅ Simple Approach (CLI Only)**:
- Direct command execution
- Standard input/output
- Built-in error handling
- No network dependencies
- Works everywhere
- Single point of integration

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Initialize Project Memories

```bash
# In your project directory
kuzu-memory init

# This creates kuzu-memories/ directory with database
```

### Step 2: Universal Integration Pattern

```python
import subprocess

def enhance_with_memory(prompt: str) -> str:
    """Enhance prompt with project memories"""
    result = subprocess.run([
        'kuzu-memory', 'enhance', prompt, '--format', 'plain'
    ], capture_output=True, text=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else prompt

def learn_async(content: str, source: str = "ai-conversation") -> None:
    """Store learning asynchronously (non-blocking)"""
    subprocess.run([
        'kuzu-memory', 'learn', content,
        '--source', source, '--quiet'
    ], check=False)  # Fire and forget

# Usage in AI workflow
user_query = "How do I optimize database queries?"
enhanced_query = enhance_with_memory(user_query)
ai_response = your_ai_system(enhanced_query)
learn_async(f"User asked about DB optimization: {ai_response}")
```

### Step 3: Test the Integration

```bash
# Test enhancement works
python -c "
import subprocess
result = subprocess.run(['kuzu-memory', 'enhance', 'test query', '--format', 'plain'],
                       capture_output=True, text=True, timeout=5)
print('✅ Enhancement works:', result.returncode == 0)

result = subprocess.run(['kuzu-memory', 'learn', 'test learning', '--quiet'])
print('✅ Async learning works:', result.returncode == 0)
"
```

---

## 🎯 Core Integration Commands

### 1. Enhance Prompts with Context

```bash
# Get enhanced prompt with project context
kuzu-memory memory enhance "How do I structure this API?"

# Output:
# 🧠 Enhanced with 3 memories (confidence: 0.85)
#
# ## Relevant Context:
# 1. Project uses FastAPI framework
# 2. Database is PostgreSQL
# 3. We follow REST API conventions
#
# ## User Message:
# How do I structure this API?
```

**Python Implementation**:
```python
import subprocess
import json

def enhance_with_memory(user_prompt: str) -> str:
    """Enhance a user prompt with project context."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'enhance', user_prompt, '--format', 'plain'
        ], capture_output=True, text=True, check=True, timeout=5)

        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return user_prompt  # Fallback to original
    except subprocess.TimeoutExpired:
        return user_prompt  # Fallback on timeout
```

### 2. Store Learning from Conversations

```bash
# Store user corrections
kuzu-memory learn "User prefers TypeScript over JavaScript"

# Store project decisions
kuzu-memory learn "We decided to use Redis for caching" --source decision

# Quiet mode for scripts (no output)
kuzu-memory learn "User likes dark mode" --quiet
```

**Python Implementation**:
```python
def store_learning(content: str, source: str = 'ai-conversation') -> bool:
    """Store learning from AI conversation."""
    try:
        subprocess.run([
            'kuzu-memory', 'learn', content,
            '--source', source, '--quiet'
        ], check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False  # Don't fail if storage fails
```

### 3. View Recent Context

```bash
# See recent memories
kuzu-memory recent

# JSON output for scripts
kuzu-memory recent --format json
```

**Python Implementation**:
```python
def get_recent_context(limit: int = 10) -> list:
    """Get recent project context."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'recent',
            '--format', 'json',
            '--limit', str(limit)
        ], capture_output=True, text=True, check=True, timeout=5)

        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return []
```

---

## 🔄 Complete Integration Patterns

### Pattern 1: Pre-Process Prompts

**Use Case**: Enhance every user prompt with relevant project context

```python
def ai_conversation(user_input: str) -> str:
    """Complete AI conversation with memory enhancement."""
    # Enhance with project context
    enhanced_input = enhance_with_memory(user_input)

    # Generate AI response
    response = ai_model.generate(enhanced_input)

    # Store the interaction
    store_learning(f"Q: {user_input} A: {response}")

    return response
```

### Pattern 2: Post-Process Learning

**Use Case**: Learn from user corrections and improve over time

```python
def handle_user_correction(original_response: str, user_feedback: str) -> str:
    """Handle user correction and generate improved response."""
    # Store the correction
    store_learning(f"Correction: {user_feedback}", source='correction')

    # Generate improved response
    correction_context = (
        f"Previous response was incorrect: {original_response}. "
        f"User correction: {user_feedback}"
    )
    enhanced_prompt = enhance_with_memory(correction_context)

    return ai_model.generate(enhanced_prompt)
```

### Pattern 3: Context-Aware Responses

**Use Case**: Build responses with full project context awareness

```python
def get_contextual_response(user_query: str) -> str:
    """Get context-aware response using recent memories."""
    # Get recent project context
    recent_context = get_recent_context(limit=5)

    # Build context-aware prompt
    context_summary = "\n".join([m['content'] for m in recent_context])
    full_prompt = f"""Project Context:
{context_summary}

User Query: {user_query}"""

    return ai_model.generate(full_prompt)
```

### Pattern 4: Real-Time Conversation Loop

**Use Case**: Interactive conversation with continuous learning

```python
def enhanced_conversation_loop():
    """Example of real-time integration."""
    print("AI Assistant with Memory (type 'quit' to exit)")

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == 'quit':
            break

        # Enhance with memory context
        enhanced_prompt = enhance_with_memory(user_input)

        # Generate AI response
        ai_response = generate_response(enhanced_prompt)

        # Store for learning
        store_learning(f"Q: {user_input} A: {ai_response}")

        print(f"AI: {ai_response}")
```

---

## 🤖 AI System-Specific Examples

### Auggie Integration

```python
# Auggie-specific integration
import subprocess

class AuggieMemoryIntegration:
    """KuzuMemory integration for Auggie."""

    def enhance_prompt(self, user_message: str) -> str:
        """Enhance Auggie prompt with project context."""
        result = subprocess.run([
            'kuzu-memory', 'enhance', user_message, '--format', 'plain'
        ], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            return result.stdout.strip()
        return user_message

    def store_conversation(self, user_msg: str, ai_response: str, user_feedback: str = None):
        """Store Auggie conversation in memory."""
        if user_feedback:
            # Store correction
            subprocess.run([
                'kuzu-memory', 'learn',
                f"Correction: {user_feedback}",
                '--source', 'auggie-correction', '--quiet'
            ], check=False)
        else:
            # Store normal conversation
            subprocess.run([
                'kuzu-memory', 'learn',
                f"Q: {user_msg} A: {ai_response}",
                '--source', 'auggie-conversation', '--quiet'
            ], check=False)

# Usage
auggie_memory = AuggieMemoryIntegration()
enhanced = auggie_memory.enhance_prompt("How do I code this?")
auggie_memory.store_conversation(user_msg, ai_response, user_feedback)
```

### Claude Integration

```python
# Claude-specific integration (via subprocess)
def claude_with_memory(prompt: str) -> str:
    """Enhance Claude prompts with project memory."""
    # Get project context
    enhanced_prompt = enhance_with_memory(prompt)

    # Call Claude (example using hypothetical claude_cli)
    result = subprocess.run([
        'claude', 'chat', enhanced_prompt
    ], capture_output=True, text=True)

    response = result.stdout.strip()

    # Store the interaction
    store_learning(f"Claude Q: {prompt} A: {response}")

    return response
```

### OpenAI GPT Integration

```python
import openai

def gpt_with_memory(prompt: str, model: str = "gpt-4") -> str:
    """Enhance GPT prompts with project memory."""
    # Enhance with project context
    enhanced_prompt = enhance_with_memory(prompt)

    # Call OpenAI API
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant with project context."},
            {"role": "user", "content": enhanced_prompt}
        ]
    )

    ai_response = response.choices[0].message.content

    # Store the interaction
    store_learning(f"GPT Q: {prompt} A: {ai_response}")

    return ai_response
```

---

## 🐚 Shell Script Integration

For shell-based AI systems:

```bash
#!/bin/bash
# Simple AI integration script

enhance_prompt() {
    local prompt="$1"
    kuzu-memory memory enhance "$prompt" --format plain 2>/dev/null || echo "$prompt"
}

store_learning() {
    local content="$1"
    kuzu-memory learn "$content" --quiet 2>/dev/null || true
}

# Usage
USER_PROMPT="What's our deployment process?"
ENHANCED_PROMPT=$(enhance_prompt "$USER_PROMPT")

# Use enhanced prompt with AI system
AI_RESPONSE=$(call_ai_system "$ENHANCED_PROMPT")

# Store the learning
store_learning "User asked about deployment: $AI_RESPONSE"
```

---

## 🎯 Command Reference

### Core Commands

```bash
kuzu-memory init                    # Initialize project memories
kuzu-memory memory enhance "prompt"        # Add context to prompt
kuzu-memory learn "content"         # Store learning
kuzu-memory recent                  # Show recent memories
kuzu-memory memory recall "query"          # Find specific memories
kuzu-memory status                   # Show statistics
```

### AI-Friendly Options

```bash
--format json                       # JSON output for scripts
--format plain                      # Just the result, no formatting
--quiet                            # Suppress output
--max-memories N                   # Limit context size
--timeout N                        # Set timeout in seconds
```

---

## 🚀 Benefits of CLI Integration

### Simplicity
- ✅ No servers to manage
- ✅ No network configuration
- ✅ No API versioning
- ✅ Just commands that work

### Reliability
- ✅ No network failures
- ✅ No port conflicts
- ✅ No HTTP timeouts
- ✅ Direct process execution

### Performance
- ✅ No network overhead
- ✅ Direct memory access
- ✅ Fast command execution (<100ms)
- ✅ Minimal latency

### Universality
- ✅ Works with any programming language
- ✅ Works in any environment
- ✅ Works with any AI system
- ✅ Works locally and remotely

---

## 💡 Advanced Integration Techniques

### Custom Learning Rules

```python
def create_custom_rule(name: str, pattern: str, action: str):
    """Create custom learning rules via CLI."""
    subprocess.run([
        'kuzu-memory', 'rule', 'create',
        '--name', name,
        '--pattern', pattern,
        '--action', action
    ], check=True)

# Example
create_custom_rule(
    name="Prefer FastAPI",
    pattern="api|rest|endpoint",
    action="add_context:User prefers FastAPI for API development"
)
```

### Session Tracking

```python
class MemorySession:
    """Track AI conversation sessions with memory."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.turn_count = 0

    def process_turn(self, user_msg: str, ai_response: str):
        """Process a conversation turn."""
        self.turn_count += 1

        # Enhance user message
        enhanced_msg = enhance_with_memory(user_msg)

        # Store interaction
        store_learning(
            f"[Session {self.session_id} Turn {self.turn_count}] "
            f"Q: {user_msg} A: {ai_response}"
        )

        return enhanced_msg

    def get_stats(self) -> dict:
        """Get session statistics."""
        result = subprocess.run([
            'kuzu-memory', 'stats', '--format', 'json'
        ], capture_output=True, text=True, check=True)

        stats = json.loads(result.stdout)
        stats['session_turns'] = self.turn_count
        return stats
```

### Error Recovery

```python
def robust_enhance(prompt: str, max_retries: int = 3) -> str:
    """Enhance with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            result = subprocess.run([
                'kuzu-memory', 'enhance', prompt, '--format', 'plain'
            ], capture_output=True, text=True, check=True, timeout=5)

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                continue  # Retry
            return prompt  # Fallback on final failure

        except subprocess.CalledProcessError:
            return prompt  # Fallback immediately on error

    return prompt
```

---

## 📊 Monitoring & Analytics

### Session Statistics

```python
def get_session_summary() -> dict:
    """Get comprehensive session summary."""
    stats = json.loads(subprocess.run([
        'kuzu-memory', 'stats', '--format', 'json'
    ], capture_output=True, text=True, check=True).stdout)

    return {
        'total_memories': stats['total_memories'],
        'recent_activity': stats.get('recent_activity', 0),
        'database_size_mb': stats.get('database_size_mb', 0),
        'avg_recall_ms': stats.get('performance', {}).get('avg_recall_ms', 0)
    }
```

### Performance Metrics

Track these metrics for your integration:

- **Context Injection Time**: Target <50ms
- **Memory Storage Time**: Target <100ms
- **API Response Times**: Monitor subprocess execution
- **Memory Database Size**: Keep under 50MB
- **Success Rate**: Track enhancement and storage success

---

## 🆘 Troubleshooting

### Common Issues

#### Command Not Found

```bash
# Check if kuzu-memory is installed
which kuzu-memory

# Install if missing
pipx install kuzu-memory

# Or add to PATH
export PATH="$PATH:$HOME/.local/bin"
```

#### Slow Performance

```bash
# Enable CLI adapter for better performance
kuzu-memory optimize --enable-cli

# Monitor performance
kuzu-memory status --detailed

# Check database size
du -h kuzu-memories/memories.db
```

#### Integration Errors

```python
# Add comprehensive error handling
try:
    enhanced = enhance_with_memory(prompt)
except subprocess.TimeoutExpired:
    print("Memory enhancement timed out, using original prompt")
    enhanced = prompt
except subprocess.CalledProcessError as e:
    print(f"Memory enhancement failed: {e}")
    enhanced = prompt
```

---

## 🎓 Complete Examples

### Example 1: Simple Chatbot

```python
#!/usr/bin/env python3
"""Simple chatbot with KuzuMemory integration."""

import subprocess
import sys

def enhance(prompt):
    result = subprocess.run(
        ['kuzu-memory', 'enhance', prompt, '--format', 'plain'],
        capture_output=True, text=True, timeout=5
    )
    return result.stdout.strip() if result.returncode == 0 else prompt

def learn(content):
    subprocess.run(
        ['kuzu-memory', 'learn', content, '--quiet'],
        check=False
    )

def main():
    print("Chatbot with Memory (type 'quit' to exit)\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == 'quit':
            break

        # Enhance and respond
        enhanced = enhance(user_input)
        response = f"Processed: {enhanced}"  # Replace with actual AI

        print(f"Bot: {response}\n")

        # Learn from interaction
        learn(f"Q: {user_input} A: {response}")

if __name__ == '__main__':
    main()
```

### Example 2: Documentation Assistant

```python
#!/usr/bin/env python3
"""Documentation assistant with project memory."""

import subprocess
import sys

def get_documentation_context(topic):
    """Get relevant documentation from memory."""
    result = subprocess.run(
        ['kuzu-memory', 'recall', topic, '--format', 'json'],
        capture_output=True, text=True, timeout=5
    )

    if result.returncode == 0:
        import json
        memories = json.loads(result.stdout)
        return [m['content'] for m in memories[:3]]
    return []

def main():
    if len(sys.argv) < 2:
        print("Usage: doc-assistant <topic>")
        sys.exit(1)

    topic = ' '.join(sys.argv[1:])
    context = get_documentation_context(topic)

    if context:
        print(f"Documentation for '{topic}':\n")
        for i, doc in enumerate(context, 1):
            print(f"{i}. {doc}\n")
    else:
        print(f"No documentation found for '{topic}'")

if __name__ == '__main__':
    main()
```

---

## 📚 Related Documentation

- [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start guide
- [CLAUDE_SETUP.md](CLAUDE_SETUP.md) - Claude-specific integration
- [MEMORY_SYSTEM.md](MEMORY_SYSTEM.md) - Memory types and usage
- [DEVELOPER.md](DEVELOPER.md) - Developer documentation

---

## 🎯 Key Takeaways

### What to Do

✅ **Use subprocess for CLI integration** - Simple and reliable
✅ **Enhance prompts before AI calls** - Add project context
✅ **Store learnings asynchronously** - Non-blocking storage
✅ **Handle errors gracefully** - Fallback to original prompt
✅ **Monitor performance** - Keep operations under 100ms

### What NOT to Do

❌ **Don't use HTTP bridge** - Unnecessary complexity
❌ **Don't block on learning** - Use async/fire-and-forget
❌ **Don't ignore timeouts** - Always set timeout limits
❌ **Don't skip error handling** - Always have fallbacks
❌ **Don't store secrets** - Filter sensitive information

---

**🎯 This is the right way to integrate AI with project memory - simple, fast, and reliable!**
