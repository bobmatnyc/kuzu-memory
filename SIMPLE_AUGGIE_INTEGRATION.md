# 🎯 Simple Auggie Integration - CLI Only

**The right way to integrate KuzuMemory with AI systems: Just use CLI commands!**

No HTTP servers, no bridge complexity, no APIs. Just simple, fast CLI commands that any AI system can call directly.

---

## 🚀 **Why CLI-Only is Better**

### **❌ Complex Approach (HTTP Bridge):**
- HTTP server to maintain
- API endpoints to manage
- Network requests and responses
- Error handling complexity
- Port management issues

### **✅ Simple Approach (CLI Only):**
- Direct command execution
- Standard input/output
- Built-in error handling
- No network dependencies
- Works everywhere

---

## 🎯 **Core Integration Commands**

### **1. Enhance Prompts with Context**
```bash
# Get enhanced prompt with project context
kuzu-memory enhance "How do I structure this API?"

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

### **2. Store Learning from Conversations**
```bash
# Store user corrections
kuzu-memory learn "User prefers TypeScript over JavaScript"

# Store project decisions
kuzu-memory learn "We decided to use Redis for caching" --source decision

# Quiet mode for scripts
kuzu-memory learn "User likes dark mode" --quiet
```

### **3. View Recent Context**
```bash
# See recent memories
kuzu-memory recent

# JSON output for scripts
kuzu-memory recent --format json
```

---

## 🤖 **Auggie Integration Examples**

### **Python Integration (subprocess)**
```python
import subprocess
import json

def enhance_with_memory(user_prompt):
    """Enhance a user prompt with project context."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'enhance', user_prompt, '--format', 'plain'
        ], capture_output=True, text=True, check=True)
        
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return user_prompt  # Fallback to original

def store_learning(content, source='ai-conversation'):
    """Store learning from AI conversation."""
    subprocess.run([
        'kuzu-memory', 'learn', content, 
        '--source', source, '--quiet'
    ], check=False)  # Don't fail if storage fails

def get_recent_context():
    """Get recent project context."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'recent', '--format', 'json'
        ], capture_output=True, text=True, check=True)
        
        return json.loads(result.stdout)
    except:
        return []

# Usage in AI conversation
user_input = "How should I handle authentication?"
enhanced_prompt = enhance_with_memory(user_input)
ai_response = generate_ai_response(enhanced_prompt)

# Store the interaction
store_learning(f"User asked about authentication: {ai_response}")
```

### **Shell Script Integration**
```bash
#!/bin/bash
# Simple Auggie integration script

enhance_prompt() {
    local prompt="$1"
    kuzu-memory enhance "$prompt" --format plain 2>/dev/null || echo "$prompt"
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

## 🎮 **Quick Demo**

Let me show you how simple this is:

### **1. Initialize Project**
```bash
kuzu-memory init
```

### **2. Store Some Project Context**
```bash
kuzu-memory remember "This project uses FastAPI with PostgreSQL"
kuzu-memory learn "Team prefers pytest for testing"
kuzu-memory learn "We use Docker for deployment"
```

### **3. Enhance AI Prompts**
```bash
# Before enhancement
echo "How do I test this code?"

# After enhancement
kuzu-memory enhance "How do I test this code?"
# Output includes: "Team prefers pytest for testing"
```

### **4. Store AI Learning**
```bash
# After AI conversation
kuzu-memory learn "User prefers detailed error messages" --source ai-feedback
```

---

## 🔧 **Integration Patterns**

### **Pattern 1: Pre-Process Prompts**
```python
def ai_conversation(user_input):
    # Enhance with project context
    enhanced_input = enhance_with_memory(user_input)
    
    # Generate AI response
    response = ai_model.generate(enhanced_input)
    
    # Store the interaction
    store_learning(f"Q: {user_input} A: {response}")
    
    return response
```

### **Pattern 2: Post-Process Learning**
```python
def handle_user_correction(original_response, user_feedback):
    # Store the correction
    store_learning(f"Correction: {user_feedback}", source='correction')
    
    # Generate improved response
    correction_context = f"Previous response was incorrect: {original_response}. User correction: {user_feedback}"
    enhanced_prompt = enhance_with_memory(correction_context)
    
    return ai_model.generate(enhanced_prompt)
```

### **Pattern 3: Context-Aware Responses**
```python
def get_contextual_response(user_query):
    # Get recent project context
    recent_context = get_recent_context()
    
    # Build context-aware prompt
    context_summary = "\n".join([m['content'] for m in recent_context[:5]])
    full_prompt = f"Project Context:\n{context_summary}\n\nUser Query: {user_query}"
    
    return ai_model.generate(full_prompt)
```

---

## 🎯 **Command Reference**

### **Core Commands**
```bash
kuzu-memory init                    # Initialize project memories
kuzu-memory enhance "prompt"        # Add context to prompt
kuzu-memory learn "content"         # Store learning
kuzu-memory recent                  # Show recent memories
kuzu-memory recall "query"          # Find specific memories
kuzu-memory stats                   # Show statistics
```

### **AI-Friendly Options**
```bash
--format json                       # JSON output for scripts
--format plain                      # Just the result, no formatting
--quiet                            # Suppress output
--max-memories N                   # Limit context size
```

---

## 🚀 **Benefits of CLI-Only Approach**

### **✅ Simplicity**
- No servers to manage
- No network configuration
- No API versioning
- Just commands that work

### **✅ Reliability**
- No network failures
- No port conflicts
- No HTTP timeouts
- Direct process execution

### **✅ Performance**
- No network overhead
- Direct memory access
- Fast command execution
- Minimal latency

### **✅ Universality**
- Works with any programming language
- Works in any environment
- Works with any AI system
- Works locally and remotely

---

## 🎉 **Ready to Use!**

### **For Auggie Integration:**
1. **Initialize**: `kuzu-memory init` in your project
2. **Enhance prompts**: Call `kuzu-memory enhance` before AI calls
3. **Store learning**: Call `kuzu-memory learn` after interactions
4. **Check context**: Use `kuzu-memory recent` for debugging

### **No HTTP Server Needed!**
- ❌ No `kuzu-memory bridge` command needed
- ❌ No port management
- ❌ No API endpoints
- ✅ Just simple CLI commands

**This is the right way to integrate AI with project memory - simple, fast, and reliable!** 🎯✨
