# Getting Started with KuzuMemory

**Quick start guide for developers integrating KuzuMemory into AI applications**

---

## 🚀 **Installation**

### **Prerequisites**
- Python 3.11 or higher
- pip or pipx (recommended)
- Git (for project-based memories)

### **Install KuzuMemory**
```bash
# Via pip (recommended)
pip install kuzu-memory

# Via pipx (isolated environment)
pipx install kuzu-memory

# Verify installation
kuzu-memory --version
```

### **Optional Dependencies**
```bash
# For advanced NER (Named Entity Recognition)
pip install kuzu-memory[ner]

# For development
pip install kuzu-memory[dev]
```

---

## 🎯 **First Steps**

### **1. Initialize Your First Project**
```bash
# Navigate to your project
cd your-ai-project

# Initialize KuzuMemory
kuzu-memory init

# Check status
kuzu-memory project
```

### **2. Store Your First Memory**
```bash
# Store project information
kuzu-memory remember "This project uses FastAPI with PostgreSQL database"

# Store a decision
kuzu-memory learn "We decided to use async/await patterns" --source team-decision
```

### **3. Retrieve Context**
```bash
# Get project context
kuzu-memory recall "What's our tech stack?"

# Enhance a prompt with context
kuzu-memory enhance "How do I connect to the database?" --format plain
```

### **4. Check Performance**
```bash
# View system statistics
kuzu-memory stats

# View recent memories
kuzu-memory recent --limit 5
```

---

## 🤖 **AI Integration**

### **Basic Integration Pattern**
```python
import subprocess
import json
from typing import Optional

def enhance_with_memory(prompt: str) -> str:
    """Enhance user prompt with project memories."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'enhance', prompt, '--format', 'plain'
        ], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Memory enhancement failed: {result.stderr}")
            return prompt
    except subprocess.TimeoutExpired:
        print("Memory enhancement timed out")
        return prompt

def store_learning(content: str, source: str = "ai-conversation") -> None:
    """Store learning asynchronously (non-blocking)."""
    subprocess.run([
        'kuzu-memory', 'learn', content,
        '--source', source, '--quiet'
    ], check=False)  # Fire and forget

# Example usage
user_input = "How do I structure an API endpoint?"
enhanced_prompt = enhance_with_memory(user_input)

# Generate AI response with enhanced context
ai_response = your_ai_system.generate(enhanced_prompt)

# Store the interaction for future learning (async)
interaction = f"Q: {user_input}\\nA: {ai_response}"
store_learning(interaction, "claude-conversation")
```

### **Advanced Integration with Error Handling**
```python
import subprocess
import json
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class KuzuMemoryClient:
    """Production-ready KuzuMemory client."""

    def __init__(self, timeout: int = 5, enable_quiet: bool = True):
        self.timeout = timeout
        self.enable_quiet = enable_quiet
        self._verify_installation()

    def _verify_installation(self) -> None:
        """Verify KuzuMemory is installed and accessible."""
        try:
            subprocess.run(['kuzu-memory', '--version'],
                         check=True, capture_output=True, timeout=2)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            raise RuntimeError("KuzuMemory CLI not found. Install with: pip install kuzu-memory")

    def enhance_prompt(self, prompt: str, format_type: str = "plain") -> Optional[str]:
        """Enhance prompt with context, return None on failure."""
        try:
            result = subprocess.run([
                'kuzu-memory', 'enhance', prompt,
                '--format', format_type
            ], capture_output=True, text=True, timeout=self.timeout)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f"Memory enhancement failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning("Memory enhancement timed out")
            return None
        except Exception as e:
            logger.error(f"Memory enhancement error: {e}")
            return None

    def store_memory(self, content: str, memory_type: str = "context",
                    source: str = "ai-system") -> bool:
        """Store memory, returns success status."""
        try:
            cmd = ['kuzu-memory', 'learn', content, '--source', source]
            if self.enable_quiet:
                cmd.append('--quiet')

            result = subprocess.run(cmd, timeout=self.timeout)
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.warning("Memory storage timed out")
            return False
        except Exception as e:
            logger.error(f"Memory storage error: {e}")
            return False

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get system statistics as JSON."""
        try:
            result = subprocess.run([
                'kuzu-memory', 'stats', '--format', 'json'
            ], capture_output=True, text=True, timeout=self.timeout)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.warning(f"Stats retrieval failed: {result.stderr}")
                return None

        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            logger.warning(f"Stats retrieval error: {e}")
            return None

# Usage example
memory_client = KuzuMemoryClient()

# Enhance prompts
enhanced = memory_client.enhance_prompt("How do I handle errors?")
if enhanced:
    print(f"Enhanced prompt: {enhanced}")

# Store learning
success = memory_client.store_memory(
    "User prefers detailed error messages with recovery suggestions",
    source="user-feedback"
)

# Monitor system
stats = memory_client.get_stats()
if stats:
    print(f"Memory count: {stats.get('memory_count', 0)}")
```

---

## 🔧 **Configuration**

### **Project Configuration**
Create `kuzu-config.json` in your project root:
```json
{
    "database_path": "./kuzu-memories",
    "max_memory_age_days": 30,
    "performance": {
        "query_timeout_ms": 100,
        "cache_size": 1000,
        "enable_cli_adapter": true
    },
    "memory_types": {
        "default_type": "context",
        "retention_policies": {
            "decision": 90,
            "pattern": 30,
            "solution": 60
        }
    },
    "integration": {
        "async_learning": true,
        "quiet_mode": true
    }
}
```

### **Environment Variables**
```bash
# Optional environment configuration
export KUZU_MEMORY_DB_PATH="/path/to/memories"
export KUZU_MEMORY_CONFIG="/path/to/config.json"
export KUZU_MEMORY_DEBUG=true
export KUZU_MEMORY_QUIET=true
```

---

## 🎮 **Common Patterns**

### **1. AI Chat with Memory**
```python
class MemoryEnabledChatbot:
    def __init__(self):
        self.memory_client = KuzuMemoryClient()

    def chat(self, user_input: str) -> str:
        # Enhance prompt with memories
        enhanced = self.memory_client.enhance_prompt(user_input)
        context_prompt = enhanced or user_input

        # Generate AI response
        ai_response = self.generate_response(context_prompt)

        # Store interaction (async)
        interaction = f"Human: {user_input}\\nAssistant: {ai_response}"
        self.memory_client.store_memory(interaction, source="chat")

        return ai_response
```

### **2. Project Onboarding Assistant**
```python
def onboard_new_developer(project_path: str):
    """Set up memories for new project member."""

    # Initialize memories if needed
    subprocess.run(['kuzu-memory', 'init'], cwd=project_path)

    # Store essential project info
    memories = [
        "This project follows microservices architecture",
        "We use TypeScript for frontend, Python for backend",
        "Database migrations are in db/migrations/",
        "All APIs must include error handling and logging"
    ]

    for memory in memories:
        subprocess.run([
            'kuzu-memory', 'remember', memory, '--source', 'onboarding'
        ], cwd=project_path)

    print("Project memories initialized for new developer!")
```

### **3. Code Review Assistant**
```python
def analyze_code_with_memory(code_snippet: str, file_path: str) -> str:
    """Analyze code using project memory context."""

    # Create context-aware prompt
    prompt = f"""
    Analyze this code from {file_path}:

    ```
    {code_snippet}
    ```

    Consider our project patterns and conventions.
    """

    # Enhance with project memories
    memory_client = KuzuMemoryClient()
    enhanced_prompt = memory_client.enhance_prompt(prompt)

    # Generate analysis (your AI system here)
    analysis = generate_code_analysis(enhanced_prompt or prompt)

    # Store findings for future reference
    finding = f"Code review: {file_path} - {analysis[:200]}..."
    memory_client.store_memory(finding, source="code-review")

    return analysis
```

---

## 📊 **Monitoring & Debugging**

### **Performance Monitoring**
```bash
# Monitor system performance
kuzu-memory stats --detailed

# View recent activities
kuzu-memory recent --format json | jq '.[].created_at'

# Check system health
kuzu-memory project --verbose
```

### **Debug Mode**
```bash
# Enable debug logging
kuzu-memory --debug enhance "test query"

# View detailed error information
kuzu-memory --debug learn "test memory" --verbose
```

### **Performance Testing**
```python
import time
import statistics

def benchmark_memory_operations():
    """Benchmark memory operations."""
    memory_client = KuzuMemoryClient()

    # Test enhance performance
    enhance_times = []
    for i in range(10):
        start = time.time()
        memory_client.enhance_prompt("test query")
        enhance_times.append((time.time() - start) * 1000)

    # Test learn performance
    learn_times = []
    for i in range(10):
        start = time.time()
        memory_client.store_memory(f"test memory {i}")
        learn_times.append((time.time() - start) * 1000)

    print(f"Enhance avg: {statistics.mean(enhance_times):.1f}ms")
    print(f"Learn avg: {statistics.mean(learn_times):.1f}ms")

    # Should be <100ms for enhance, <200ms for learn
    assert statistics.mean(enhance_times) < 100, "Enhance too slow"
    assert statistics.mean(learn_times) < 200, "Learn too slow"
```

---

## 🚨 **Common Issues**

### **Installation Issues**
```bash
# Python version check
python --version  # Should be 3.11+

# Reinstall if needed
pip uninstall kuzu-memory
pip install kuzu-memory

# Check installation
kuzu-memory --version
```

### **Permission Issues**
```bash
# Database permission error
chmod -R 755 kuzu-memories/

# Create directory if missing
mkdir -p kuzu-memories
kuzu-memory init --force
```

### **Performance Issues**
```bash
# Enable CLI adapter for better performance
kuzu-memory optimize --enable-cli

# Clear old memories
kuzu-memory cleanup --older-than 30d

# Rebuild database if corrupted
rm -rf kuzu-memories/
kuzu-memory init
```

### **Integration Issues**
```python
# Test basic CLI integration
def test_cli_integration():
    try:
        # Test basic command
        result = subprocess.run([
            'kuzu-memory', '--version'
        ], capture_output=True, text=True, timeout=5)

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        print("CLI integration working!")

    except Exception as e:
        print(f"CLI integration failed: {e}")
        raise
```

---

## 🎯 **Next Steps**

### **Explore Advanced Features**
1. **[Architecture](architecture.md)** - Understand system design
2. **[API Reference](api-reference.md)** - Complete CLI and API docs
3. **[Async Operations](async-operations.md)** - Non-blocking memory operations
4. **[Temporal Decay](temporal-decay.md)** - Memory retention policies

### **Integration Examples**
1. **[AI Integration](ai-integration.md)** - Comprehensive integration guide
2. **[Testing Guide](testing-guide.md)** - Testing strategies
3. **[Deployment Guide](deployment-guide.md)** - Production deployment

### **Contribute**
1. **[Contributing](contributing.md)** - How to contribute
2. **[Development Setup](development.md)** - Local development
3. **GitHub Issues** - Report bugs or request features

---

## 🤝 **Community & Support**

- **Documentation**: [docs/developer/](../developer/)
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Architecture and usage questions
- **Examples**: Check `examples/` directory

**Happy coding with KuzuMemory!** 🧠✨