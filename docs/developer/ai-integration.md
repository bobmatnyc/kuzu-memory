# AI Integration Guide

## 🤖 **Universal AI Integration**

KuzuMemory is designed to integrate with **any AI system** through a simple, universal CLI interface. No special libraries, APIs, or dependencies required.

### **Integration Philosophy**
- **CLI-First** - Standard subprocess interface works everywhere
- **Language Agnostic** - Works with Python, JavaScript, Go, Rust, etc.
- **AI System Agnostic** - Works with Claude, GPT, Llama, custom models, etc.
- **Simple Interface** - Two main operations: enhance prompts, store learning

---

## 🎯 **Core Integration Pattern**

### **Two-Step Integration**
Every AI integration follows the same simple pattern:

```
1. ENHANCE: Add project context to user prompts (sync, fast)
2. LEARN: Store information from conversations (async, non-blocking)
```

### **Basic Integration Flow**
```python
import subprocess

def ai_conversation_with_memory(user_input):
    # Step 1: Enhance prompt with project context (sync, <100ms)
    enhanced_prompt = enhance_prompt(user_input)
    
    # Step 2: Generate AI response using enhanced prompt
    ai_response = your_ai_system(enhanced_prompt)
    
    # Step 3: Store learning from conversation (async, non-blocking)
    store_learning(f"Q: {user_input} A: {ai_response}")
    
    return ai_response

def enhance_prompt(user_input):
    """Add project context to user prompt."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'enhance', user_input, '--format', 'plain'
        ], capture_output=True, text=True, check=True, timeout=5)
        return result.stdout.strip()
    except:
        return user_input  # Fallback to original on error

def store_learning(content):
    """Store learning from conversation (async, non-blocking)."""
    subprocess.run([
        'kuzu-memory', 'learn', content, '--source', 'ai-conversation', '--quiet'
    ], check=False)  # Don't fail if storage fails
```

---

## 🚀 **Language-Specific Examples**

### **Python Integration**
```python
import subprocess
import json
from typing import Optional

class KuzuMemoryIntegration:
    def __init__(self, project_path: Optional[str] = None):
        self.project_path = project_path
    
    def enhance_prompt(self, prompt: str, format: str = 'plain') -> str:
        """Enhance prompt with project context."""
        cmd = ['kuzu-memory', 'enhance', prompt, '--format', format]
        if self.project_path:
            cmd.extend(['--project', self.project_path])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  check=True, timeout=5)
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return prompt  # Fallback on timeout
        except subprocess.CalledProcessError:
            return prompt  # Fallback on error
    
    def store_learning(self, content: str, source: str = 'ai-conversation') -> bool:
        """Store learning asynchronously."""
        cmd = ['kuzu-memory', 'learn', content, '--source', source, '--quiet']
        if self.project_path:
            cmd.extend(['--project', self.project_path])
        
        try:
            subprocess.run(cmd, check=False, timeout=10)
            return True
        except:
            return False  # Don't fail the main flow
    
    def get_project_stats(self) -> dict:
        """Get project memory statistics."""
        cmd = ['kuzu-memory', 'stats', '--format', 'json']
        if self.project_path:
            cmd.extend(['--project', self.project_path])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  check=True, timeout=5)
            return json.loads(result.stdout)
        except:
            return {}

# Usage
memory = KuzuMemoryIntegration()
enhanced = memory.enhance_prompt("How do I deploy this app?")
memory.store_learning("User asked about deployment")
```

### **JavaScript/Node.js Integration**
```javascript
const { spawn, execSync } = require('child_process');

class KuzuMemoryIntegration {
    constructor(projectPath = null) {
        this.projectPath = projectPath;
    }
    
    enhancePrompt(prompt, format = 'plain') {
        try {
            const cmd = ['kuzu-memory', 'enhance', prompt, '--format', format];
            if (this.projectPath) {
                cmd.push('--project', this.projectPath);
            }
            
            const result = execSync(cmd.join(' '), { 
                encoding: 'utf8', 
                timeout: 5000 
            });
            return result.trim();
        } catch (error) {
            return prompt; // Fallback on error
        }
    }
    
    storeLearning(content, source = 'ai-conversation') {
        const cmd = ['kuzu-memory', 'learn', content, '--source', source, '--quiet'];
        if (this.projectPath) {
            cmd.push('--project', this.projectPath);
        }
        
        // Async, non-blocking
        const child = spawn(cmd[0], cmd.slice(1), { 
            detached: true, 
            stdio: 'ignore' 
        });
        child.unref();
    }
    
    async getProjectStats() {
        try {
            const cmd = ['kuzu-memory', 'stats', '--format', 'json'];
            if (this.projectPath) {
                cmd.push('--project', this.projectPath);
            }
            
            const result = execSync(cmd.join(' '), { 
                encoding: 'utf8', 
                timeout: 5000 
            });
            return JSON.parse(result);
        } catch (error) {
            return {};
        }
    }
}

// Usage
const memory = new KuzuMemoryIntegration();
const enhanced = memory.enhancePrompt("How do I deploy this app?");
memory.storeLearning("User asked about deployment");
```

### **Go Integration**
```go
package main

import (
    "context"
    "encoding/json"
    "os/exec"
    "strings"
    "time"
)

type KuzuMemoryIntegration struct {
    ProjectPath string
}

func (k *KuzuMemoryIntegration) EnhancePrompt(prompt, format string) (string, error) {
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    
    args := []string{"enhance", prompt, "--format", format}
    if k.ProjectPath != "" {
        args = append(args, "--project", k.ProjectPath)
    }
    
    cmd := exec.CommandContext(ctx, "kuzu-memory", args...)
    output, err := cmd.Output()
    if err != nil {
        return prompt, nil // Fallback on error
    }
    
    return strings.TrimSpace(string(output)), nil
}

func (k *KuzuMemoryIntegration) StoreLearning(content, source string) error {
    args := []string{"learn", content, "--source", source, "--quiet"}
    if k.ProjectPath != "" {
        args = append(args, "--project", k.ProjectPath)
    }
    
    cmd := exec.Command("kuzu-memory", args...)
    go cmd.Run() // Async, non-blocking
    
    return nil
}

func (k *KuzuMemoryIntegration) GetProjectStats() (map[string]interface{}, error) {
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    
    args := []string{"stats", "--format", "json"}
    if k.ProjectPath != "" {
        args = append(args, "--project", k.ProjectPath)
    }
    
    cmd := exec.CommandContext(ctx, "kuzu-memory", args...)
    output, err := cmd.Output()
    if err != nil {
        return make(map[string]interface{}), nil
    }
    
    var stats map[string]interface{}
    json.Unmarshal(output, &stats)
    return stats, nil
}

// Usage
func main() {
    memory := &KuzuMemoryIntegration{}
    enhanced, _ := memory.EnhancePrompt("How do I deploy this app?", "plain")
    memory.StoreLearning("User asked about deployment", "ai-conversation")
}
```

---

## 🎮 **Integration Patterns**

### **Pattern 1: Simple Enhancement**
For basic context injection without learning.

```python
def simple_ai_with_context(user_input):
    # Just enhance the prompt
    enhanced = subprocess.run([
        'kuzu-memory', 'enhance', user_input, '--format', 'plain'
    ], capture_output=True, text=True).stdout.strip()
    
    return your_ai_system(enhanced)
```

### **Pattern 2: Learning AI Assistant**
For AI that learns from conversations.

```python
def learning_ai_assistant(user_input):
    # Enhance prompt
    enhanced = enhance_prompt(user_input)
    
    # Generate response
    response = your_ai_system(enhanced)
    
    # Learn from interaction (async)
    store_learning(f"Q: {user_input} A: {response}")
    
    return response
```

### **Pattern 3: Feedback Learning**
For AI that learns from user corrections.

```python
def feedback_learning_ai(user_input, previous_response=None, user_feedback=None):
    # Learn from feedback if provided
    if user_feedback and previous_response:
        store_learning(f"Correction: {previous_response} -> {user_feedback}", 
                      source='user-correction')
    
    # Enhance and respond
    enhanced = enhance_prompt(user_input)
    response = your_ai_system(enhanced)
    
    # Store new interaction
    store_learning(f"Q: {user_input} A: {response}")
    
    return response
```

### **Pattern 4: Batch Processing**
For processing multiple inputs efficiently.

```python
def batch_ai_processing(inputs):
    results = []
    
    for user_input in inputs:
        # Enhance each input
        enhanced = enhance_prompt(user_input)
        response = your_ai_system(enhanced)
        results.append(response)
        
        # Store learning (async, won't block)
        store_learning(f"Q: {user_input} A: {response}")
    
    return results
```

---

## 🔧 **Advanced Integration Features**

### **Error Handling**
Robust error handling for production systems.

```python
def robust_ai_integration(user_input):
    try:
        # Try to enhance prompt
        enhanced = enhance_prompt(user_input)
    except Exception as e:
        # Log error but continue with original prompt
        logger.warning(f"Memory enhancement failed: {e}")
        enhanced = user_input
    
    # Generate AI response
    response = your_ai_system(enhanced)
    
    # Try to store learning (don't fail if it doesn't work)
    try:
        store_learning(f"Q: {user_input} A: {response}")
    except Exception as e:
        logger.warning(f"Memory storage failed: {e}")
    
    return response
```

### **Performance Monitoring**
Monitor integration performance.

```python
import time

def monitored_ai_integration(user_input):
    start_time = time.time()
    
    # Enhance prompt (should be <100ms)
    enhance_start = time.time()
    enhanced = enhance_prompt(user_input)
    enhance_time = (time.time() - enhance_start) * 1000
    
    # Generate response
    ai_start = time.time()
    response = your_ai_system(enhanced)
    ai_time = (time.time() - ai_start) * 1000
    
    # Store learning (async, measure submission time only)
    learn_start = time.time()
    store_learning(f"Q: {user_input} A: {response}")
    learn_time = (time.time() - learn_start) * 1000
    
    total_time = (time.time() - start_time) * 1000
    
    # Log performance metrics
    logger.info(f"AI Integration Performance: "
               f"enhance={enhance_time:.1f}ms, "
               f"ai={ai_time:.1f}ms, "
               f"learn={learn_time:.1f}ms, "
               f"total={total_time:.1f}ms")
    
    return response
```

### **Configuration Management**
Configurable integration settings.

```python
class ConfigurableAIIntegration:
    def __init__(self, config):
        self.enhance_timeout = config.get('enhance_timeout', 5)
        self.learn_timeout = config.get('learn_timeout', 10)
        self.enable_learning = config.get('enable_learning', True)
        self.fallback_on_error = config.get('fallback_on_error', True)
    
    def process(self, user_input):
        # Configurable enhancement
        enhanced = self.enhance_prompt(user_input)
        response = your_ai_system(enhanced)
        
        # Configurable learning
        if self.enable_learning:
            self.store_learning(f"Q: {user_input} A: {response}")
        
        return response
```

---

## 📊 **Integration Best Practices**

### **Performance Best Practices**
1. **Always use timeouts** - Prevent hanging on memory operations
2. **Fallback gracefully** - Continue with original prompt if enhancement fails
3. **Don't block on learning** - Learning is async and optional
4. **Monitor performance** - Track enhancement and learning times

### **Error Handling Best Practices**
1. **Never fail the main flow** - Memory operations should never break AI responses
2. **Log errors appropriately** - Log memory errors for debugging
3. **Provide fallbacks** - Always have a fallback strategy
4. **Handle timeouts** - Set reasonable timeouts for all operations

### **Integration Best Practices**
1. **Start simple** - Begin with basic enhancement, add learning later
2. **Test thoroughly** - Test with and without memory system
3. **Monitor usage** - Track memory system effectiveness
4. **Document integration** - Document how memory enhances your AI system

**KuzuMemory's universal CLI interface makes it easy to integrate with any AI system in any language.** 🤖✨
