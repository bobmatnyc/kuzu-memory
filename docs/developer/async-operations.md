# Async Operations Guide

## 🚀 **Async Architecture Overview**

KuzuMemory uses a **lightweight message queue system** to provide non-blocking memory operations that never delay AI responses. This is crucial for real-time AI integration.

### **Core Principle**
- **Enhancement**: Synchronous (fast, <100ms) - needed immediately for AI responses
- **Learning**: Asynchronous (non-blocking) - happens in background without delaying user

---

## 🎯 **Async vs Sync Operations**

### **Synchronous Operations (Blocking)**
Operations that must complete before returning a result:

```bash
# Context enhancement - needed immediately
kuzu-memory enhance "How do I deploy this?" --format plain
# Returns: Enhanced prompt with context (45ms avg)
```

**Use Cases:**
- Context enhancement for AI prompts
- Memory retrieval for immediate use
- System status checks
- Configuration queries

### **Asynchronous Operations (Non-blocking)**
Operations that can happen in the background:

```bash
# Learning - async by default
kuzu-memory learn "User prefers TypeScript" --quiet
# Returns: Immediately, processing happens in background
```

**Use Cases:**
- Storing memories from conversations
- Learning from user interactions
- Batch memory operations
- System maintenance tasks

---

## 🏗️ **Async System Components**

### **1. Queue Manager**
Lightweight message queue for task management.

**Features:**
- **Worker Threads** - Configurable number of background workers (default: 2)
- **Task Prioritization** - Higher priority for important operations
- **Queue Limits** - Prevents memory exhaustion (default: 100 tasks)
- **Error Recovery** - Robust error handling and retry logic

**Configuration:**
```python
# In kuzu-memories/config.json
{
  "async": {
    "max_workers": 2,
    "max_queue_size": 100,
    "worker_timeout": 30,
    "retry_attempts": 3
  }
}
```

### **2. Background Learner**
Processes learning tasks without blocking main thread.

**Features:**
- **Memory Generation** - Extracts patterns and entities from content
- **Deduplication** - Prevents duplicate memories
- **Batch Processing** - Efficient processing of multiple tasks
- **Performance Monitoring** - Tracks processing times and success rates

### **3. Status Reporter**
Monitors async operations and provides status updates.

**Features:**
- **Health Monitoring** - Tracks system health and performance
- **Progress Reporting** - Real-time status for long operations
- **Error Alerting** - Notifications of failures and issues
- **Metrics Collection** - Performance and usage statistics

---

## 🎮 **Using Async Operations**

### **Basic Async Learning**
```bash
# Default behavior - async, non-blocking
kuzu-memory learn "Team decided to use Docker for deployment" --quiet

# Returns immediately, learning happens in background
# No output in quiet mode, task queued for processing
```

### **Monitoring Async Operations**
```bash
# Check system status
kuzu-memory stats

# Output shows async queue status:
# Async queue size: 3 tasks
# Tasks completed: 156
# Tasks failed: 2
# Avg processing time: 120ms
```

### **Sync Mode for Testing**
```bash
# Force synchronous processing
kuzu-memory learn "Test memory" --sync

# Output:
# ℹ️  Using synchronous processing
# ✅ Stored 1 memories
```

---

## 🔧 **Programming with Async Operations**

### **Python Integration**
```python
import subprocess
import time

def async_learning_example():
    # Store learning asynchronously (returns immediately)
    start_time = time.time()
    
    subprocess.run([
        'kuzu-memory', 'learn', 
        'User prefers detailed error messages',
        '--source', 'user-preference',
        '--quiet'
    ], check=False)
    
    elapsed = (time.time() - start_time) * 1000
    print(f"Learning submission took {elapsed:.1f}ms")  # ~5ms
    
    # Continue with other work immediately
    print("Continuing with other operations...")
    
    # Learning happens in background, doesn't block this code

def sync_enhancement_example():
    # Enhancement is always synchronous (needed immediately)
    start_time = time.time()
    
    result = subprocess.run([
        'kuzu-memory', 'enhance',
        'How should I handle errors?',
        '--format', 'plain'
    ], capture_output=True, text=True, check=True)
    
    elapsed = (time.time() - start_time) * 1000
    print(f"Enhancement took {elapsed:.1f}ms")  # ~45ms
    
    return result.stdout.strip()
```

### **JavaScript Integration**
```javascript
const { spawn, execSync } = require('child_process');

function asyncLearning(content, source = 'ai-conversation') {
    // Non-blocking learning
    const child = spawn('kuzu-memory', [
        'learn', content, 
        '--source', source, 
        '--quiet'
    ], {
        detached: true,
        stdio: 'ignore'
    });
    
    child.unref(); // Don't wait for completion
    console.log('Learning task submitted');
}

function syncEnhancement(prompt) {
    // Blocking enhancement (needed immediately)
    try {
        const result = execSync(`kuzu-memory enhance "${prompt}" --format plain`, {
            encoding: 'utf8',
            timeout: 5000
        });
        return result.trim();
    } catch (error) {
        return prompt; // Fallback
    }
}

// Usage
asyncLearning('User prefers async/await patterns');
const enhanced = syncEnhancement('How do I handle promises?');
```

---

## 📊 **Performance Characteristics**

### **Async Learning Performance**
```
Task Submission: ~5ms (immediate return)
Background Processing: ~120ms avg
Queue Throughput: ~50 tasks/second
Memory Usage: ~10MB for 100 queued tasks
```

### **Sync Enhancement Performance**
```
Context Retrieval: ~45ms avg (target: <100ms)
Cache Hit Rate: ~87%
Memory Usage: ~5MB for cached contexts
Timeout: 5 seconds (configurable)
```

### **System Limits**
```
Max Queue Size: 100 tasks (configurable)
Max Workers: 2 threads (configurable)
Max Task Age: 300 seconds (auto-cleanup)
Max Memory Usage: 50MB (configurable)
```

---

## 🔍 **Monitoring and Debugging**

### **Queue Status**
```bash
# Check async queue status
kuzu-memory stats --detailed

# Output includes:
# Queue Stats:
#   Queue size: 3 tasks
#   Active tasks: 1 processing
#   Completed: 156 tasks
#   Failed: 2 tasks
#   Avg processing time: 120ms
```

### **Task Tracking**
```python
# Advanced: Track specific tasks (future feature)
import subprocess
import json

def track_learning_task():
    # Submit learning task
    result = subprocess.run([
        'kuzu-memory', 'learn', 
        'Important project decision',
        '--format', 'json'  # Returns task ID
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        task_info = json.loads(result.stdout)
        task_id = task_info.get('task_id')
        print(f"Task {task_id} submitted")
        
        # Check task status (future feature)
        # status = check_task_status(task_id)
```

### **Error Handling**
```python
def robust_async_learning(content):
    try:
        subprocess.run([
            'kuzu-memory', 'learn', content, '--quiet'
        ], check=False, timeout=10)
        return True
    except subprocess.TimeoutExpired:
        print("Learning task submission timed out")
        return False
    except Exception as e:
        print(f"Learning task failed: {e}")
        return False
```

---

## ⚙️ **Configuration**

### **Async System Configuration**
```json
{
  "async": {
    "enabled": true,
    "max_workers": 2,
    "max_queue_size": 100,
    "worker_timeout_seconds": 30,
    "task_retry_attempts": 3,
    "cleanup_interval_seconds": 60,
    "max_task_age_seconds": 300
  },
  "performance": {
    "max_recall_time_ms": 100.0,
    "max_generation_time_ms": 200.0,
    "enable_performance_monitoring": true
  }
}
```

### **Environment Variables**
```bash
# Override async settings
export KUZU_MEMORY_ASYNC_WORKERS=4
export KUZU_MEMORY_ASYNC_QUEUE_SIZE=200
export KUZU_MEMORY_ASYNC_TIMEOUT=60

# Disable async for debugging
export KUZU_MEMORY_ASYNC_DISABLED=1
```

---

## 🚨 **Troubleshooting Async Operations**

### **Common Issues**

**Queue Full:**
```bash
# Check queue status
kuzu-memory stats

# If queue is full, wait or increase size
# Temporary: wait for queue to drain
# Permanent: increase max_queue_size in config
```

**Slow Processing:**
```bash
# Check processing times
kuzu-memory stats --detailed

# If processing is slow:
# 1. Increase worker count
# 2. Check database performance
# 3. Review memory content complexity
```

**Tasks Failing:**
```bash
# Check error rates
kuzu-memory stats

# High failure rate indicates:
# 1. Database issues
# 2. Disk space problems
# 3. Permission issues
# 4. Memory content issues
```

### **Debug Mode**
```bash
# Enable debug output for async operations
kuzu-memory learn "Debug test" --debug

# Output shows:
# DEBUG: Submitting task to async queue
# DEBUG: Task queued with ID: abc123
# DEBUG: Worker thread processing task
# DEBUG: Task completed in 125ms
```

---

## 🎯 **Best Practices**

### **For AI Integration**
1. **Always use async learning** - Never block AI responses
2. **Always use sync enhancement** - Context needed immediately
3. **Handle failures gracefully** - Don't fail main flow on memory errors
4. **Monitor performance** - Track enhancement and learning times

### **For High-Volume Applications**
1. **Increase worker count** - More workers for higher throughput
2. **Increase queue size** - Handle traffic bursts
3. **Monitor queue health** - Prevent queue overflow
4. **Use batch operations** - More efficient for multiple items

### **For Development**
1. **Use sync mode for testing** - Easier to debug and verify
2. **Monitor async operations** - Check stats regularly
3. **Test error conditions** - Ensure graceful degradation
4. **Profile performance** - Optimize for your use case

**The async system ensures KuzuMemory never blocks AI responses while continuously learning and improving.** 🚀✨
