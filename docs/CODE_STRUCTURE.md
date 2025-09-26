# KuzuMemory - Code Structure Analysis

**Comprehensive architectural analysis for AI agent optimization**

---

## 🏗️ **Architecture Overview**

KuzuMemory follows a **layered architecture** optimized for performance and AI integration:

```
┌─────────────────────────────────────────────────────────────┐
│                 CLI INTERFACE LAYER                         │
│  commands.py (2003 lines) - Rich CLI with Click framework  │
│  • Main entry point: kuzu-memory command                   │
│  • 20+ commands: init, remember, recall, enhance, learn    │
│  • Rich formatting with fallbacks                          │
└─────────────────────────────────────────────────────────────┘
           │
┌─────────────────────────────────────────────────────────────┐
│                ASYNC MEMORY LAYER                           │
│  async_cli.py, queue_manager.py, background_learner.py     │
│  • Non-blocking learn operations                           │
│  • Task queue management                                   │
│  • Status reporting system                                 │
└─────────────────────────────────────────────────────────────┘
           │
┌─────────────────────────────────────────────────────────────┐
│                CORE MEMORY ENGINE                           │
│  memory.py, models.py, config.py                          │
│  • Primary KuzuMemory class                               │
│  • Memory and MemoryContext models                        │
│  • Configuration management                               │
└─────────────────────────────────────────────────────────────┘
           │
┌─────────────────────────────────────────────────────────────┐
│              SPECIALIZED SUBSYSTEMS                         │
│  storage/ recall/ extraction/ integrations/               │
│  • Database adapters (Kuzu CLI + Python API)              │
│  • Memory recall strategies                               │
│  • Entity and pattern extraction                          │
│  • AI system integrations (Auggie)                        │
└─────────────────────────────────────────────────────────────┘
           │
┌─────────────────────────────────────────────────────────────┐
│                KUZU GRAPH DATABASE                          │
│  .kuzu-memory/memories.db or kuzu-memories/memories.db    │
│  • Memories, entities, relationships                       │
│  • Optimized for <100ms queries                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 **Core Classes and Responsibilities**

### **🖥️ CLI Layer (src/kuzu_memory/cli/)**

#### **commands.py (2003 lines)**
- **Main CLI entry point** with Click framework
- **Rich formatting** with graceful fallbacks
- **20+ commands** organized by function:

```python
# Primary Commands
cli()           # Main entry point with help system
init()          # Initialize project memories
remember()      # Store memories from text
recall()        # Find relevant memories
enhance()       # Enhance prompts with context
learn()         # Async learning from AI conversations

# Utility Commands
project()       # Show project information
stats()         # Memory statistics
recent()        # Recent memories
examples()      # Usage examples
setup()         # Interactive setup wizard
tips()          # Best practices

# Advanced Commands
optimize()      # Performance optimization
cleanup()       # Remove expired memories
quickstart()    # 3-minute guided setup
demo()          # Instant demo mode
```

### **⚡ Async Memory Layer (src/kuzu_memory/async_memory/)**

#### **AsyncMemoryCLI**
- **Non-blocking learn operations** for AI integration
- **Task queue management** with background processing
- **Status reporting** for long-running operations

#### **MemoryQueueManager**
```python
class TaskType(Enum):
    LEARN = "learn"
    GENERATE = "generate"
    CLEANUP = "cleanup"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

#### **BackgroundLearner**
- **Asynchronous memory processing**
- **Batch operations** for performance
- **Error recovery** and retry logic

### **🧠 Core Memory Engine (src/kuzu_memory/core/)**

#### **KuzuMemory** (Primary Interface)
```python
class KuzuMemory:
    def attach_memories(prompt, max_memories=10) -> MemoryContext:
        """<100ms context retrieval for AI systems"""

    def generate_memories(content, agent_id=None) -> List[str]:
        """<200ms memory generation and storage"""

    def get_statistics() -> Dict[str, Any]:
        """System performance and usage statistics"""
```

#### **Memory Models**
```python
class MemoryType(str, Enum):
    IDENTITY = "identity"      # Never expires
    PREFERENCE = "preference"   # Never expires
    DECISION = "decision"       # 90 days
    PATTERN = "pattern"        # 30 days
    SOLUTION = "solution"      # 60 days
    STATUS = "status"          # 6 hours
    CONTEXT = "context"        # 1 day

class Memory(BaseModel):
    # Core content
    id: str
    content: str
    content_hash: str  # SHA256 for deduplication

    # Temporal
    created_at: datetime
    valid_from: datetime
    valid_to: Optional[datetime]

    # Classification
    memory_type: MemoryType
    importance: float  # 0.0-1.0
    confidence: float  # 0.0-1.0

    # Source tracking
    agent_id: str
    session_id: Optional[str]
    metadata: Dict[str, Any]
```

#### **Configuration System**
```python
class KuzuMemoryConfig:
    storage: StorageConfig
    recall: RecallConfig
    extraction: ExtractionConfig
    performance: PerformanceConfig
    retention: RetentionConfig
```

---

## 🔧 **Specialized Subsystems**

### **💾 Storage Layer (src/kuzu_memory/storage/)**

#### **KuzuAdapter Hierarchy**
```python
# Dual adapter system for performance
create_kuzu_adapter(db_path, config):
    if config.storage.use_cli_adapter:
        return KuzuCLIAdapter(db_path)  # 2-3x faster
    else:
        return KuzuPythonAdapter(db_path)  # More control
```

#### **MemoryStore** (664 lines)
- **Batch operations** for performance
- **Deduplication** via content hashes
- **Memory lifecycle** management
- **Relationship tracking** between memories

### **🔍 Recall System (src/kuzu_memory/recall/)**

#### **RecallCoordinator**
```python
class RecallCoordinator:
    def recall_memories(prompt, strategy="auto") -> List[Memory]:
        """Orchestrate multi-strategy recall"""
```

#### **Recall Strategies** (433 lines)
```python
class RecallStrategy(ABC):
    KeywordStrategy     # TF-IDF + semantic matching
    EntityStrategy      # Named entity recognition
    TemporalStrategy    # Time-based relevance
    PatternStrategy     # Code pattern matching
    HybridStrategy      # Combination approach
```

### **🔬 Extraction System (src/kuzu_memory/extraction/)**

#### **Entity Extraction** (551 lines)
- **Pattern-based NER** (no LLM required)
- **Technology detection** (frameworks, languages)
- **Person and organization** recognition
- **Custom entity types** for project-specific terms

#### **Pattern Extraction** (473 lines)
```python
class PatternExtractor:
    def extract_preferences() -> List[str]:
        """I prefer X over Y for Z"""

    def extract_decisions() -> List[str]:
        """We decided to use X because Y"""

    def extract_identity() -> List[str]:
        """My name is X, I work at Y"""
```

### **🤖 AI Integrations (src/kuzu_memory/integrations/)**

#### **Auggie Integration** (888 lines)
```python
class AuggieIntegration:
    def enhance_prompt(prompt, user_id) -> Dict:
        """Add personal context to prompts"""

    def learn_from_interaction(prompt, response, feedback) -> Dict:
        """Extract learning from AI conversations"""

    def get_integration_statistics() -> Dict:
        """Monitor AI integration performance"""
```

---

## 📊 **Data Flow Architecture**

### **🔄 Memory Storage Flow**
```
User Input → CLI Command → Content Analysis → Pattern Extraction →
Entity Recognition → Memory Generation → Deduplication Check →
Database Storage → Relationship Building → Index Updates
```

### **⚡ Memory Recall Flow**
```
Query → Strategy Selection → Multi-Strategy Search →
Relevance Ranking → Confidence Scoring → Context Assembly →
Response Enhancement → Performance Monitoring
```

### **🚀 AI Integration Flow**
```
AI System → subprocess('kuzu-memory enhance') → Context Retrieval →
Enhanced Prompt → AI Response → subprocess('kuzu-memory learn --quiet') →
Async Learning → Background Processing → Memory Storage
```

---

## 📈 **Performance Characteristics**

### **⏱️ Response Time Targets**
- **Memory Recall**: <100ms (synchronous, required for AI)
- **Memory Generation**: <200ms (can be async for learning)
- **CLI Commands**: <50ms startup time
- **Database Queries**: <10ms individual operations

### **🔧 Performance Optimizations**
- **CLI Adapter**: 2-3x faster than Python API
- **Connection Pooling**: Reuse database connections
- **LRU Caching**: Cache frequent queries
- **Batch Operations**: Group database writes
- **Async Learning**: Non-blocking for AI integration

### **📊 Scalability Features**
- **Memory Deduplication**: Prevent storage bloat
- **Automatic Cleanup**: Remove expired memories
- **Efficient Indexing**: Fast text search capabilities
- **Streaming Results**: Handle large query results

---

## 🧪 **Testing Architecture**

### **📁 Test Structure**
```
tests/
├── unit/           # Component testing
├── integration/    # Cross-component testing
├── e2e/           # End-to-end CLI testing
├── benchmarks/    # Performance testing
├── regression/    # Data integrity testing
└── fixtures/      # Test data and utilities
```

### **🎯 Test Coverage Goals**
- **Core Memory Engine**: >95% coverage
- **CLI Commands**: >90% coverage
- **Storage Layer**: >95% coverage
- **Performance Tests**: All critical paths
- **Integration Tests**: All AI system interfaces

---

## 🔧 **Development Patterns**

### **📝 Code Style Standards**
- **Black formatting** (88 character line length)
- **Type hints** throughout codebase
- **Comprehensive docstrings** for all public methods
- **Pydantic models** for data validation
- **Enum types** for controlled vocabularies

### **🔒 Error Handling Strategy**
```python
# Custom exception hierarchy
KuzuMemoryError
├── ConfigurationError
├── DatabaseError
├── PerformanceError
├── ValidationError
└── IntegrationError
```

### **📈 Logging and Monitoring**
- **Structured logging** with Python logging module
- **Performance metrics** tracking
- **Debug mode** support with detailed output
- **Quiet mode** for AI integration scenarios

---

## 🎯 **Key Integration Points for AI Agents**

### **🤖 Primary AI Interface**
```bash
# Always use these patterns for AI integration
kuzu-memory enhance "user prompt" --format plain  # <100ms
kuzu-memory learn "ai learning" --quiet           # async, fire-and-forget
```

### **📊 System Monitoring**
```bash
kuzu-memory stats --detailed    # Performance monitoring
kuzu-memory project --verbose   # Project health check
```

### **⚙️ Configuration Management**
```bash
kuzu-memory optimize --enable-cli  # Performance tuning
kuzu-memory init --force          # Reset if needed
```

---

## 🔍 **File Size Analysis**

| File | Lines | Purpose | Priority |
|------|-------|---------|----------|
| cli/commands.py | 2003 | Main CLI interface | 🔴 Critical |
| installers/universal.py | 982 | Installation system | 🟡 Important |
| integrations/auggie.py | 888 | AI integration | 🔴 Critical |
| storage/memory_store.py | 664 | Database operations | 🔴 Critical |
| extraction/entities.py | 551 | Entity recognition | 🟢 Standard |
| storage/kuzu_adapter.py | 504 | Database adapter | 🔴 Critical |
| core/models.py | 433 | Data models | 🔴 Critical |
| recall/strategies.py | 433 | Memory recall | 🔴 Critical |

---

## 💡 **Optimization Opportunities**

### **🚀 Performance Improvements**
1. **CLI Adapter Usage**: Enable for 2-3x performance boost
2. **Connection Pooling**: Optimize database connections
3. **Query Caching**: Cache frequent recall patterns
4. **Batch Processing**: Group related operations

### **🔧 Maintainability Enhancements**
1. **Plugin Architecture**: Modular extraction strategies
2. **Configuration Profiles**: Environment-specific settings
3. **API Documentation**: OpenAPI specs for integrations
4. **Monitoring Dashboard**: Real-time system health

---

**🎯 This analysis provides the foundation for AI agents to understand, modify, and extend the KuzuMemory codebase effectively.**