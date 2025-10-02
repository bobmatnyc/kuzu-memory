# KuzuMemory Integration Guide

Welcome to KuzuMemory! This guide shows you how to integrate KuzuMemory with Your AI System for intelligent, persistent memory.

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
const { KuzuMemoryIntegration } = require('./kuzu_memory_integration');

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
kuzu-memory learn "User: $user_input\nAI: $ai_response" --quiet --source conversation

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
# Enable CLI adapter for better performance
kuzu-memory optimize --enable-cli

# Monitor performance
kuzu-memory stats --detailed
```

## 🤖 Your AI System Specific Integration

### Integration Steps
1. **Initialize**: Run `kuzu-memory init` in your project
2. **Enhance**: Add memory context to prompts before sending to Your AI System
3. **Learn**: Store conversation outcomes for future reference
4. **Optimize**: Configure performance settings for your workflow

### Example Integration Code
```python
import subprocess

def enhance_for_your_ai_system(prompt):
    """Enhance prompt for Your AI System with memory context."""
    result = subprocess.run([
        'kuzu-memory', 'enhance', prompt, '--format', 'plain'
    ], capture_output=True, text=True, timeout=5)

    return result.stdout.strip() if result.returncode == 0 else prompt

def learn_from_your_ai_system(prompt, response):
    """Learn from Your AI System conversation."""
    learning = f"User: {prompt}\nYour AI System: {response}"
    subprocess.run([
        'kuzu-memory', 'learn', learning, '--quiet', '--source', 'your ai system'
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
# Interactive optimization
kuzu-memory optimize

# Enable CLI adapter (recommended)
kuzu-memory optimize --enable-cli
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
# Check system performance
kuzu-memory optimize

# Analyze temporal decay
kuzu-memory temporal-analysis --detailed
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
- **Performance**: `kuzu-memory optimize --help`

---

**KuzuMemory: Making Your AI System smarter, one memory at a time.** 🧠✨
