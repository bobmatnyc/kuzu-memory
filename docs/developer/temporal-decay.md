# Enhanced Temporal Decay & Memory Ranking

## 🕒 **Overview**

KuzuMemory provides a **sophisticated temporal decay system** that uses **soft ranking instead of hard expiration**. Rather than deleting old memories, the system gradually reduces their relevance in search results while preserving all information.

### **🎯 Key Innovation: Soft Decay vs Hard Expiration**
- **✅ Soft ranking decay** - Memories become less relevant over time but are never lost
- **✅ Configurable decay functions** - Exponential, linear, sigmoid, power-law, and more
- **✅ Recent memory boost** - Fresh memories get priority in ranking
- **✅ Type-specific decay rates** - Different memory types age at different rates
- **✅ Adaptive weighting** - Temporal score dynamically affects ranking weight
- **✅ Preservation of information** - No data loss, just reduced relevance

### **🚀 Enhanced Features**
- **Multiple decay functions** with configurable parameters
- **Recent memory boosting** for time-sensitive information
- **Type-specific half-life periods** for optimal relevance
- **Adaptive ranking weights** that respond to memory age
- **Detailed analysis tools** for understanding decay behavior
- **Performance optimized** ranking with temporal intelligence

---

## 🎯 **Enhanced Temporal Decay System**

### **🧠 How Soft Decay Works**

Instead of deleting memories, KuzuMemory uses **temporal decay as a ranking factor**:

1. **Memories are timestamped** when created
2. **Decay score calculated** based on age and memory type
3. **Ranking weight adjusted** by temporal decay score
4. **Recent memories boosted** for immediate relevance
5. **All memories preserved** but older ones rank lower

### **📊 Decay Functions Available**

| Function | Formula | Best For | Characteristics |
|----------|---------|----------|-----------------|
| **Exponential** | `exp(-age/half_life)` | General use | Smooth, natural decay |
| **Linear** | `max(0, 1-age/(2*half_life))` | Gradual decline | Steady, predictable |
| **Sigmoid** | `1/(1+exp((age-half_life)/steepness))` | Sharp transitions | S-curve, delayed then rapid |
| **Power Law** | `(half_life/(half_life+age))²` | Long tail effects | Slow start, accelerating |
| **Logarithmic** | `1/(1+log(1+age/half_life))` | Gentle aging | Very gradual decline |
| **Step** | Discrete levels | Testing/debugging | Clear thresholds |

### **⚡ Memory Type Decay Parameters**

| Memory Type | Half-Life | Decay Function | Min Score | Recent Boost | Rationale |
|-------------|-----------|----------------|-----------|--------------|-----------|
| **IDENTITY** | 365 days | Linear | 80% | 1.0x | Core facts stay relevant |
| **PREFERENCE** | 180 days | Exponential | 60% | 1.2x | Settings change slowly |
| **DECISION** | 90 days | Exponential | 30% | 1.3x | Architecture evolves |
| **PATTERN** | 45 days | Sigmoid | 10% | 1.4x | Code patterns change |
| **SOLUTION** | 60 days | Exponential | 20% | 1.3x | Solutions become outdated |
| **STATUS** | 1 day | Exponential | 1% | 2.0x | Current state is fleeting |
| **CONTEXT** | 7 days | Power Law | 5% | 1.8x | Session context fades |

### **Retention Logic**
```python
# Built-in retention periods
retention_map = {
    MemoryType.IDENTITY: None,                    # Never expire
    MemoryType.PREFERENCE: None,                  # Never expire
    MemoryType.DECISION: timedelta(days=90),      # 90 days
    MemoryType.PATTERN: timedelta(days=30),       # 30 days
    MemoryType.SOLUTION: timedelta(days=60),      # 60 days
    MemoryType.STATUS: timedelta(hours=6),        # 6 hours
    MemoryType.EPISODIC: timedelta(days=1),       # 1 day
}
```

---

## ⚙️ **Configuration**

### **Default Configuration**
```json
{
  "retention": {
    "enable_auto_cleanup": true,
    "cleanup_interval_hours": 24,
    "custom_retention": {},
    "max_total_memories": 100000,
    "cleanup_batch_size": 1000
  }
}
```

### **Configuration Options**

#### **`enable_auto_cleanup`** (boolean, default: `true`)
- **Purpose**: Enable/disable automatic cleanup of expired memories
- **Impact**: When disabled, memories never expire automatically
- **Use case**: Disable for debugging or when you want manual control

#### **`cleanup_interval_hours`** (integer, default: `24`)
- **Purpose**: How often to run automatic cleanup (in hours)
- **Range**: 1-168 hours (1 hour to 1 week)
- **Impact**: More frequent cleanup uses more CPU but keeps database smaller

#### **`custom_retention`** (object, default: `{}`)
- **Purpose**: Override default retention periods for specific memory types
- **Format**: `{"memory_type": days}` or `{"memory_type": null}` for never expire
- **Example**: `{"pattern": 14, "solution": 30, "status": null}`

#### **`max_total_memories`** (integer, default: `100000`)
- **Purpose**: Maximum total memories before triggering aggressive cleanup
- **Impact**: Prevents unbounded memory growth
- **Behavior**: When exceeded, oldest memories are cleaned up first

#### **`cleanup_batch_size`** (integer, default: `1000`)
- **Purpose**: Number of memories to process in each cleanup batch
- **Impact**: Larger batches are more efficient but use more memory
- **Range**: 100-10000 recommended

---

## 🎛️ **Custom Configuration Examples**

### **1. Conservative Retention (Keep Everything Longer)**
```json
{
  "retention": {
    "enable_auto_cleanup": true,
    "cleanup_interval_hours": 48,
    "custom_retention": {
      "pattern": 90,      // 90 days instead of 30
      "solution": 180,    // 180 days instead of 60
      "status": 24,       // 24 hours instead of 6
      "context": 7        // 7 days instead of 1
    },
    "max_total_memories": 200000
  }
}
```

### **2. Aggressive Cleanup (Faster Expiration)**
```json
{
  "retention": {
    "enable_auto_cleanup": true,
    "cleanup_interval_hours": 6,
    "custom_retention": {
      "pattern": 7,       // 7 days instead of 30
      "solution": 14,     // 14 days instead of 60
      "status": 1,        // 1 hour instead of 6
      "context": 0.25     // 6 hours instead of 1 day
    },
    "max_total_memories": 10000,
    "cleanup_batch_size": 500
  }
}
```

### **3. Permanent Storage (No Expiration)**
```json
{
  "retention": {
    "enable_auto_cleanup": false,
    "custom_retention": {
      "pattern": null,    // Never expire
      "solution": null,   // Never expire
      "status": null,     // Never expire
      "context": null     // Never expire
    }
  }
}
```

### **4. Development Mode (Quick Expiration for Testing)**
```json
{
  "retention": {
    "enable_auto_cleanup": true,
    "cleanup_interval_hours": 1,
    "custom_retention": {
      "pattern": 0.1,     // ~2.4 hours
      "solution": 0.25,   // 6 hours
      "status": 0.01,     // ~15 minutes
      "context": 0.04     // ~1 hour
    },
    "max_total_memories": 1000,
    "cleanup_batch_size": 100
  }
}
```

---

## 🎮 **CLI Commands**

### **🕒 Temporal Decay Analysis**
```bash
# Analyze recent memories with temporal decay
kuzu-memory temporal-analysis --limit 5

# Analyze specific memory type
kuzu-memory temporal-analysis --memory-type pattern --limit 10

# Detailed analysis with full breakdown
kuzu-memory temporal-analysis --limit 3 --format detailed

# JSON output for programmatic analysis
kuzu-memory temporal-analysis --format json --limit 5
```

### **🔍 Enhanced Memory Recall**
```bash
# Recall with ranking explanation
kuzu-memory recall "database setup" --explain-ranking

# See how temporal decay affects results
kuzu-memory recall "recent changes" --strategy temporal

# Compare different strategies
kuzu-memory recall "python patterns" --strategy auto
```

### **⚙️ Configuration Management**
```bash
# Create example configuration with temporal decay
kuzu-memory create-config my-config.json

# Use custom temporal decay configuration
kuzu-memory --config examples/temporal-decay-config.json recall "test"

# Check current temporal settings
kuzu-memory stats --detailed
```

### **📊 Monitoring & Analysis**
```bash
# View memory statistics with temporal info
kuzu-memory stats

# Show recent memories (ranked by temporal decay)
kuzu-memory recent --count 50

# Analyze temporal patterns
kuzu-memory temporal-analysis --memory-type decision --format detailed
```

---

## 🔍 **How Temporal Decay Works**

### **1. Memory Creation**
```python
# When memories are created, expiration is calculated
memory = Memory(
    content="Project uses FastAPI",
    memory_type=MemoryType.DECISION,  # 90-day retention
    created_at=datetime.now(),
    valid_to=datetime.now() + timedelta(days=90)  # Auto-calculated
)
```

### **2. Query-Time Filtering**
```sql
-- All queries automatically exclude expired memories
MATCH (m:Memory)
WHERE (m.valid_to IS NULL OR m.valid_to > $current_time)
  AND m.content CONTAINS $search_term
RETURN m
```

### **3. Background Cleanup**
```python
# Runs every cleanup_interval_hours
def background_cleanup():
    if config.retention.enable_auto_cleanup:
        cleaned_count = cleanup_expired_memories()
        logger.info(f"Cleaned up {cleaned_count} expired memories")
```

### **4. Batch Processing**
```python
# Processes memories in configurable batches
def cleanup_expired_memories():
    batch_size = config.retention.cleanup_batch_size
    total_cleaned = 0
    
    while True:
        batch_cleaned = cleanup_batch(batch_size)
        total_cleaned += batch_cleaned
        
        if batch_cleaned < batch_size:
            break  # No more expired memories
    
    return total_cleaned
```

---

## 📊 **Monitoring & Analytics**

### **Memory Statistics**
```bash
$ kuzu-memory stats --detailed

📊 Memory Statistics:
  Total memories: 1,247
  Active memories: 1,198
  Expired (pending cleanup): 49
  
Retention Status:
  IDENTITY: 45 memories (never expire)
  PREFERENCE: 23 memories (never expire)
  DECISION: 234 memories (expire in 90 days)
  PATTERN: 456 memories (expire in 30 days)
  SOLUTION: 234 memories (expire in 60 days)
  STATUS: 12 memories (expire in 6 hours)
  CONTEXT: 194 memories (expire in 1 day)

Cleanup Statistics:
  Last cleanup: 2024-01-15 10:30:00
  Memories cleaned: 156
  Next cleanup: 2024-01-16 10:30:00
```

### **Performance Impact**
- **Query Performance**: Expired memories are filtered at query time (minimal impact)
- **Storage Efficiency**: Regular cleanup prevents database bloat
- **Memory Usage**: Batch processing limits memory usage during cleanup
- **CPU Usage**: Background cleanup runs during low-activity periods

---

## 🚨 **Best Practices**

### **For Production Systems**
1. **Enable auto-cleanup**: Keep `enable_auto_cleanup: true`
2. **Monitor cleanup frequency**: Adjust `cleanup_interval_hours` based on memory creation rate
3. **Set reasonable limits**: Use `max_total_memories` to prevent unbounded growth
4. **Batch size optimization**: Tune `cleanup_batch_size` for your system's memory constraints

### **For Development**
1. **Faster expiration**: Use shorter retention periods for testing
2. **Frequent cleanup**: Set `cleanup_interval_hours: 1` for rapid iteration
3. **Manual cleanup**: Use `kuzu-memory cleanup --force` between tests
4. **Disable for debugging**: Set `enable_auto_cleanup: false` when debugging memory issues

### **For Team Collaboration**
1. **Consistent configuration**: Commit retention config to git
2. **Document decisions**: Explain custom retention policies in project docs
3. **Monitor team usage**: Adjust retention based on team memory creation patterns
4. **Backup important memories**: Use `IDENTITY` or `PREFERENCE` types for critical information

---

## 🔧 **Troubleshooting**

### **Common Issues**

**Memories disappearing too quickly:**
```json
{
  "retention": {
    "custom_retention": {
      "pattern": 60,    // Increase from 30 to 60 days
      "solution": 120   // Increase from 60 to 120 days
    }
  }
}
```

**Database growing too large:**
```json
{
  "retention": {
    "cleanup_interval_hours": 6,    // More frequent cleanup
    "max_total_memories": 50000,    // Lower limit
    "custom_retention": {
      "status": 1,      // Reduce from 6 hours to 1 hour
      "context": 0.5    // Reduce from 1 day to 12 hours
    }
  }
}
```

**Cleanup not running:**
- Check `enable_auto_cleanup: true`
- Verify `cleanup_interval_hours` is reasonable
- Run manual cleanup: `kuzu-memory cleanup --force`
- Check logs for cleanup errors

**Performance issues during cleanup:**
- Reduce `cleanup_batch_size` (e.g., from 1000 to 500)
- Increase `cleanup_interval_hours` to spread load
- Run cleanup during off-peak hours

**The temporal decay system ensures KuzuMemory remains performant and relevant while preserving important project knowledge.** 🕒✨
