# 🎯 Augment Rules for KuzuMemory Integration

**Seamless integration between Auggie and KuzuMemory using Augment rules!**

This guide shows how to set up Augment rules that automatically:
- 💾 **Store memories** from interesting user prompts
- 🧠 **Enhance prompts** with relevant project context
- 🔄 **Learn continuously** from conversations

---

## 🚀 **Quick Setup**

### **1. Initialize KuzuMemory in Your Project**
```bash
cd your-project
kuzu-memory init
```

### **2. Copy the Augment Rules**
Copy the `augment_rules/` directory to your project or Augment configuration location.

### **3. Configure Augment Rules**
Add these rules to your Augment configuration:

```python
# In your Augment rules configuration
from augment_rules.kuzu_memory_integration import main as kuzu_memory_integration

# Rule that runs on every user prompt
@augment_rule(trigger="user_prompt")
def integrate_kuzu_memory(prompt):
    """Automatically integrate KuzuMemory with user prompts."""
    result = kuzu_memory_integration(prompt)
    
    # Use the enhanced prompt for AI response
    enhanced_prompt = result['enhanced_prompt']
    
    # Log the integration summary
    if result['actions_taken']:
        print(f"🧠 KuzuMemory: {result['summary']}")
    
    return enhanced_prompt
```

---

## 🎯 **Available Rules**

### **Rule 1: Memory Storage (`kuzu_memory_storage.py`)**
Automatically stores interesting information from user prompts.

**What it stores:**
- User preferences and decisions
- Project information and specifications
- Team conventions and practices
- Technical requirements and constraints
- Learning and corrections

**Example:**
```python
from augment_rules.kuzu_memory_storage import main as store_memory

result = store_memory("We decided to use FastAPI for this project")
# Result: {'stored': True, 'content': 'We decided to use FastAPI...'}
```

### **Rule 2: Prompt Enhancement (`kuzu_memory_enhancement.py`)**
Automatically enhances prompts with relevant project context.

**What it enhances:**
- Technical questions about implementation
- Project-specific queries
- Decision-making questions
- Code-related questions
- Best practice inquiries

**Example:**
```python
from augment_rules.kuzu_memory_enhancement import main as enhance_prompt

result = enhance_prompt("How do I structure an API endpoint?")
# Result: Enhanced prompt with project context about FastAPI, conventions, etc.
```

### **Rule 3: Complete Integration (`kuzu_memory_integration.py`)**
Combines both storage and enhancement for seamless integration.

**Example:**
```python
from augment_rules.kuzu_memory_integration import main as integrate

result = integrate("How should I handle authentication in this project?")
# Result: Enhanced prompt + stored any new information
```

---

## 🔧 **Configuration Options**

### **Customizing Storage Behavior**
```python
# Store only specific types of information
result = kuzu_memory_integration(prompt, store_memories=True)

# Disable storage completely
result = kuzu_memory_integration(prompt, store_memories=False)
```

### **Customizing Enhancement Behavior**
```python
# Enhance prompts with context
result = kuzu_memory_integration(prompt, enhance_prompts=True)

# Disable enhancement
result = kuzu_memory_integration(prompt, enhance_prompts=False)
```

### **Custom Source Tags**
```python
# Tag memories with custom sources
from augment_rules.kuzu_memory_storage import store_memory

store_memory("Team decision: Use TypeScript", source="team-meeting")
store_memory("User feedback: Prefer dark mode", source="user-feedback")
```

---

## 🎮 **Usage Examples**

### **Example 1: Automatic Context Enhancement**
```
User: "How do I structure an API endpoint?"

Without KuzuMemory:
→ Generic API advice

With KuzuMemory:
→ "Based on your project using FastAPI with PostgreSQL..."
```

### **Example 2: Learning from Conversations**
```
User: "We decided to use Redis for caching"
→ KuzuMemory automatically stores this decision

Later...
User: "What caching solution should I use?"
→ KuzuMemory enhances with: "Your project uses Redis for caching..."
```

### **Example 3: Team Knowledge Sharing**
```
Developer A: "Our convention is to use pytest for testing"
→ Stored in project memories

Developer B: "How should I write tests?"
→ Enhanced with team conventions automatically
```

---

## 🔍 **Rule Logic**

### **Storage Triggers**
The storage rule activates when prompts contain:
- Preferences: "prefer", "like", "choose"
- Decisions: "decided", "we use", "our approach"
- Technical specs: "framework", "database", "API"
- Team conventions: "convention", "standard", "practice"
- Learning: "actually", "correction", "should be"

### **Enhancement Triggers**
The enhancement rule activates for:
- Technical questions: "how do I", "what's the best way"
- Implementation queries: "implement", "build", "create"
- Project questions: "this project", "our system"
- Decision questions: "should we", "which", "recommend"

### **Smart Filtering**
- **Skips short prompts** (< 5 words)
- **Ignores greetings** ("hi", "thanks", "ok")
- **Avoids pure questions** without context
- **Prevents duplicate storage**

---

## 📊 **Monitoring Integration**

### **Check What's Being Stored**
```bash
# View recent memories
kuzu-memory recent

# Search for specific memories
kuzu-memory recall "team conventions"

# View project statistics
kuzu-memory stats
```

### **Debug Rule Behavior**
```python
# Test storage rule
from augment_rules.kuzu_memory_storage import main as test_storage
result = test_storage("We use FastAPI for APIs")
print(result)

# Test enhancement rule
from augment_rules.kuzu_memory_enhancement import main as test_enhancement
result = test_enhancement("How do I build an API?")
print(result)
```

---

## 🎯 **Best Practices**

### **1. Project Initialization**
Always run `kuzu-memory init` in your project root before using the rules.

### **2. Git Integration**
Commit the `kuzu-memories/` directory to share context with your team:
```bash
git add kuzu-memories/
git commit -m "Add project memory system"
```

### **3. Rule Placement**
Place rules early in your Augment pipeline to enhance prompts before AI processing.

### **4. Performance**
The rules are designed to be fast (<100ms) but you can disable them for performance-critical scenarios.

---

## 🆘 **Troubleshooting**

### **Rules Not Working**
```bash
# Check if kuzu-memory is available
kuzu-memory --help

# Test rules manually
python augment_rules/kuzu_memory_integration.py
```

### **No Context Being Added**
```bash
# Check if memories exist
kuzu-memory stats

# Add some test memories
kuzu-memory learn "This project uses FastAPI"
```

### **Storage Failing**
```bash
# Check project structure
kuzu-memory project

# Reinitialize if needed
kuzu-memory init --force
```

---

## 🎉 **Ready to Use!**

### **Simple Integration:**
```python
# Add to your Augment configuration
@augment_rule(trigger="user_prompt")
def kuzu_memory_rule(prompt):
    from augment_rules.kuzu_memory_integration import main
    result = main(prompt)
    return result['enhanced_prompt']
```

### **Advanced Integration:**
```python
@augment_rule(trigger="user_prompt")
def advanced_kuzu_memory(prompt, context):
    from augment_rules.kuzu_memory_integration import main
    
    result = main(prompt)
    
    # Log integration actions
    if result['actions_taken']:
        context.log(f"KuzuMemory: {result['summary']}")
    
    # Store AI response after generation
    @after_response
    def store_response(ai_response):
        from augment_rules.kuzu_memory_storage import store_memory
        store_memory(f"Q: {prompt} A: {ai_response}", source="ai-conversation")
    
    return result['enhanced_prompt']
```

**Now your Auggie instance will automatically have persistent project memory!** 🧠✨
