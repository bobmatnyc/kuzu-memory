# KuzuMemory - Developer Guide

**Comprehensive development documentation for contributors and AI agents**

---

## 🎯 **Quick Navigation**

- [Architecture Overview](#architecture-overview) - System design and components
- [Development Setup](#development-setup) - Getting started quickly
- [Core Systems](#core-systems) - Deep dive into key components
- [Performance Guide](#performance-guide) - Optimization and monitoring
- [Testing Strategy](#testing-strategy) - Comprehensive testing approach
- [AI Integration](#ai-integration) - Building AI-powered features
- [Deployment](#deployment) - Release and distribution process

---

## 🏗️ **Architecture Overview**

### **🔄 System Components Diagram**

```
┌───────────────────────────────────────────────────────────────┐
│                        CLI INTERFACE                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│  │   Commands  │ │  Rich UI    │ │ Error       │             │
│  │   (Click)   │ │  Fallbacks  │ │ Handling    │             │
│  └─────────────┘ └─────────────┘ └─────────────┘             │
└───────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────────────────────────────────────┐
│                     ASYNC MEMORY LAYER                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│  │ Queue       │ │ Background  │ │ Status      │             │
│  │ Manager     │ │ Learner     │ │ Reporter    │             │
│  └─────────────┘ └─────────────┘ └─────────────┘             │
└───────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────────────────────────────────────┐
│                    CORE MEMORY ENGINE                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│  │ KuzuMemory  │ │ Memory      │ │ Config      │             │
│  │ (Main API)  │ │ Models      │ │ Management  │             │
│  └─────────────┘ └─────────────┘ └─────────────┘             │
└───────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────────────────────────────────────┐
│                   SPECIALIZED SUBSYSTEMS                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│  │ Storage     │ │ Recall      │ │ Extraction  │             │
│  │ Layer       │ │ System      │ │ Engine      │             │
│  └─────────────┘ └─────────────┘ └─────────────┘             │
└───────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────────────────────────────────────┐
│                    KUZU GRAPH DATABASE                       │
│          Memories • Entities • Relationships                 │
└───────────────────────────────────────────────────────────────┘
```

### **🚀 Data Flow Architecture**

#### **Memory Storage Pipeline**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ User Input  │───▶│ CLI Command │───▶│ Validation  │
└─────────────┘    └─────────────┘    └─────────────┘
                                               │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Pattern     │◀───│ Entity      │◀───│ Content     │
│ Extraction  │    │ Recognition │    │ Analysis    │
└─────────────┘    └─────────────┘    └─────────────┘
        │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Memory      │───▶│ Dedup       │───▶│ Database    │
│ Generation  │    │ Check       │    │ Storage     │
└─────────────┘    └─────────────┘    └─────────────┘
```

#### **Memory Recall Pipeline**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Query       │───▶│ Strategy    │───▶│ Multi-      │
│ Analysis    │    │ Selection   │    │ Strategy    │
└─────────────┘    └─────────────┘    └─────────────┘
                                               │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Context     │◀───│ Relevance   │◀───│ Search      │
│ Assembly    │    │ Ranking     │    │ Execution   │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## ⚡ **Development Setup**

### **🔧 Prerequisites**
- Python 3.11+ (required for type hints and performance)
- Kuzu CLI (optional, but recommended for 2-3x performance boost)
- Git (for version control and team collaboration)

### **🚀 Quick Setup (5 minutes)**
```bash
# 1. Clone and navigate
git clone <repository>
cd kuzu-memory

# 2. Single command setup
make dev-setup    # Installs deps + initializes memories

# 3. Verify installation
make memory-test  # Performance test
make quality     # Code quality check
```

### **📦 Manual Setup**
```bash
# Install development dependencies
make dev

# Initialize project memories
make init

# Run tests to verify
make test
```

### **🔍 Development Tools Configuration**

#### **IDE Setup (VS Code recommended)**
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"]
}
```

#### **Git Hooks (Automatic)**
```bash
# Pre-commit hooks (auto-installed with make dev)
pre-commit install

# Manual quality check before commits
make pre-commit
```

---

## 🧠 **Core Systems Deep Dive**

### **💾 Memory Storage System**

#### **KuzuMemory Class (Primary API)**
```python
class KuzuMemory:
    """
    Main interface optimized for AI integration.
    Performance targets: <100ms recall, <200ms generation
    """

    def attach_memories(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto"
    ) -> MemoryContext:
        """
        PRIMARY AI INTEGRATION METHOD
        Retrieve relevant memories for prompt enhancement
        Target: <100ms response time
        """

    def generate_memories(
        self,
        content: str,
        agent_id: str = "default",
        source: str = "conversation"
    ) -> List[str]:
        """
        Extract and store memories from content
        Target: <200ms processing time
        Can be called asynchronously for AI learning
        """
```

#### **Memory Model System**
```python
class Memory(BaseModel):
    """
    Core memory model with temporal validity and classification
    """
    # Content
    content: str              # The actual memory text
    content_hash: str         # SHA256 for deduplication

    # Temporal
    created_at: datetime      # When created
    valid_from: datetime      # When becomes valid
    valid_to: Optional[datetime]  # When expires (None = never)

    # Classification
    memory_type: MemoryType   # IDENTITY, PREFERENCE, DECISION, etc.
    importance: float         # 0.0-1.0 relevance score
    confidence: float         # 0.0-1.0 confidence in accuracy

    # Tracking
    agent_id: str            # Which agent created it
    session_id: Optional[str] # Grouping sessions
    metadata: Dict[str, Any]  # Additional context
```

#### **Memory Types and Retention**
```python
class MemoryType(str, Enum):
    IDENTITY = "identity"      # Never expires (name, role, company)
    PREFERENCE = "preference"   # Never expires (likes, dislikes)
    DECISION = "decision"       # 90 days (architectural choices)
    PATTERN = "pattern"        # 30 days (code patterns)
    SOLUTION = "solution"      # 60 days (problem solutions)
    STATUS = "status"          # 6 hours (current state)
    CONTEXT = "context"        # 1 day (session context)
```

### **🔍 Memory Recall System**

#### **Multi-Strategy Recall**
```python
class RecallStrategy(ABC):
    """Base class for memory recall strategies"""

    @abstractmethod
    def recall(self, prompt: str, max_memories: int) -> List[Memory]:
        pass

# Implemented Strategies
KeywordStrategy     # TF-IDF + semantic matching
EntityStrategy      # Named entity recognition
TemporalStrategy    # Time-based relevance
PatternStrategy     # Code pattern matching
HybridStrategy      # Weighted combination
```

#### **Recall Coordinator**
```python
class RecallCoordinator:
    """
    Orchestrates multi-strategy recall for optimal results
    """

    def recall_memories(
        self,
        prompt: str,
        strategy: str = "auto"
    ) -> List[Memory]:
        """
        Auto-selects best strategy based on prompt characteristics
        Falls back to hybrid approach for complex queries
        """
```

### **🚀 Async Processing System**

#### **Background Learning**
```python
class BackgroundLearner:
    """
    Handles async memory processing for AI integration
    Non-blocking operations for learn commands
    """

    def queue_learning_task(
        self,
        content: str,
        source: str = "ai-conversation"
    ) -> str:
        """
        Queue learning task for background processing
        Returns task_id for status tracking
        """
```

#### **Task Queue Management**
```python
class MemoryQueueManager:
    """
    Manages async task processing with status tracking
    """

    def enqueue_task(self, task: MemoryTask) -> str:
        """Add task to processing queue"""

    def get_task_status(self, task_id: str) -> TaskStatus:
        """Check processing status"""
```

---

## ⚡ **Performance Guide**

### **🎯 Performance Targets**
- **Memory Recall**: <100ms (critical for AI responsiveness)
- **Memory Generation**: <200ms (can be async for learning)
- **CLI Startup**: <50ms (immediate user feedback)
- **Database Operations**: <10ms per query

### **🔧 Optimization Strategies**

#### **1. Database Adapter Selection**
```bash
# CLI Adapter (Recommended - 2-3x faster)
kuzu-memory optimize --enable-cli

# Python API (More control, slower)
kuzu-memory optimize --disable-cli
```

#### **2. Connection Pooling**
```python
# Automatic connection reuse
class KuzuAdapter:
    _connection_pool: Dict[str, Connection] = {}

    def get_connection(self, db_path: str) -> Connection:
        """Reuse connections for performance"""
```

#### **3. Query Optimization**
```python
# Batch operations
def batch_store_memories(memories: List[Memory]) -> None:
    """Store multiple memories in single transaction"""

# Indexed queries
def indexed_recall(entities: List[str]) -> List[Memory]:
    """Use entity indexes for fast lookups"""
```

#### **4. Caching Strategy**
```python
# LRU caching for frequent queries
@lru_cache(maxsize=1000)
def cached_entity_lookup(entity: str) -> List[Memory]:
    """Cache entity-based lookups"""
```

### **📊 Performance Monitoring**

#### **Built-in Metrics**
```bash
# System performance
kuzu-memory stats --detailed

# Memory operation timing
time kuzu-memory recall "test query"

# Database size monitoring
kuzu-memory project --verbose
```

#### **Custom Profiling**
```bash
# CPU profiling
make profile

# Memory usage profiling
python -m memory_profiler src/kuzu_memory/cli/commands.py
```

---

## 🧪 **Testing Strategy**

### **📁 Test Architecture**
```
tests/
├── unit/              # Component isolation testing
│   ├── test_models.py           # Data model validation
│   ├── test_memory.py           # Core memory operations
│   ├── test_deduplication.py    # Content deduplication
│   └── test_extraction.py       # Pattern extraction
├── integration/       # Cross-component testing
│   ├── test_kuzu_memory.py      # Full system integration
│   └── test_auggie_integration.py # AI system integration
├── e2e/              # End-to-end CLI testing
│   └── test_complete_workflows.py # Full user workflows
├── benchmarks/       # Performance testing
│   └── test_performance.py      # Speed and scalability
└── regression/       # Data integrity testing
    ├── test_data_integrity.py   # Database consistency
    └── test_performance_regression.py # Performance tracking
```

### **🎯 Testing Commands**
```bash
# Run all tests
make test

# Specific test categories
python -m pytest tests/unit/ -v           # Unit tests only
python -m pytest tests/integration/ -v    # Integration tests
python -m pytest tests/e2e/ -v           # End-to-end tests

# Performance testing
python -m pytest tests/benchmarks/ -v --benchmark-only

# Coverage reporting
make test  # Includes HTML coverage report
```

### **📊 Coverage Targets**
- **Core Memory Engine**: >95% (critical functionality)
- **CLI Commands**: >90% (user-facing features)
- **Storage Layer**: >95% (data integrity critical)
- **AI Integration**: >85% (complex integration scenarios)

### **🔬 Test Categories**

#### **Unit Tests (Fast, Isolated)**
```python
def test_memory_model_validation():
    """Test Pydantic model validation rules"""

def test_content_hash_generation():
    """Test SHA256 hash generation for deduplication"""

def test_memory_type_retention():
    """Test automatic retention policy application"""
```

#### **Integration Tests (Realistic Scenarios)**
```python
def test_full_memory_lifecycle():
    """Test create → store → recall → expire cycle"""

def test_ai_integration_workflow():
    """Test subprocess-based AI integration pattern"""
```

#### **Performance Tests (Speed Validation)**
```python
@pytest.mark.benchmark
def test_recall_performance(benchmark):
    """Ensure recall operations complete within 100ms"""

@pytest.mark.benchmark
def test_generation_performance(benchmark):
    """Ensure generation operations complete within 200ms"""
```

---

## 🤖 **AI Integration**

### **🔌 Universal AI Integration Pattern**

#### **Standard Integration (Recommended)**
```python
import subprocess
from typing import Optional

class AIMemoryIntegration:
    """Standard pattern for any AI system integration"""

    def enhance_prompt(self, prompt: str) -> str:
        """Enhance prompt with project memories"""
        try:
            result = subprocess.run([
                'kuzu-memory', 'enhance', prompt,
                '--format', 'plain'
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return prompt  # Fallback to original

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return prompt  # Graceful degradation

    def learn_async(self, content: str, source: str = "ai") -> None:
        """Store learning asynchronously (fire-and-forget)"""
        subprocess.run([
            'kuzu-memory', 'learn', content,
            '--source', source, '--quiet'
        ], check=False)  # Never block AI responses
```

#### **Auggie/Claude Specific Integration**
```python
class AuggieMemoryIntegration:
    """Enhanced integration with Auggie AI system"""

    def enhance_with_rules(
        self,
        prompt: str,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """Use Auggie-specific enhancement with rule engine"""

    def learn_from_feedback(
        self,
        prompt: str,
        response: str,
        feedback: Optional[str] = None
    ) -> None:
        """Learn from user corrections and feedback"""
```

### **📊 Integration Monitoring**
```bash
# AI integration statistics
kuzu-memory auggie stats --verbose

# Performance monitoring
time kuzu-memory enhance "test prompt"
time kuzu-memory learn "test learning" --quiet
```

---

## 🚀 **Deployment**

### **📦 Build Process**
```bash
# Single command build
make build

# Manual build steps
make quality     # Ensure code quality
make test       # Run full test suite
python -m build # Create distribution packages
```

### **🔄 Release Process**
```bash
# Automated release
make publish

# Manual release steps
1. Update version in pyproject.toml
2. Update CHANGELOG.md
3. make build
4. python -m twine upload dist/*
5. Create GitHub release tag
```

### **🐳 Container Deployment**
```dockerfile
# Dockerfile example
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

CMD ["kuzu-memory", "quickstart"]
```

---

## 🔧 **Configuration Management**

### **⚙️ Configuration Hierarchy**
```python
class KuzuMemoryConfig:
    """Hierarchical configuration with environment overrides"""

    storage: StorageConfig          # Database settings
    performance: PerformanceConfig  # Speed and resource limits
    recall: RecallConfig           # Memory retrieval settings
    extraction: ExtractionConfig   # Content analysis settings
    retention: RetentionConfig     # Memory lifecycle management
```

### **📁 Configuration Sources (Priority Order)**
1. **Command line arguments** (highest priority)
2. **Environment variables** (`KUZU_MEMORY_*`)
3. **Configuration file** (`kuzu-memory.yaml`)
4. **Project defaults** (in `kuzu-memories/config.yaml`)
5. **System defaults** (lowest priority)

### **🎯 Example Configuration**
```yaml
# kuzu-memory.yaml
storage:
  use_cli_adapter: true    # Use CLI for performance
  connection_pool_size: 10

performance:
  max_recall_time_ms: 100.0
  max_generation_time_ms: 200.0
  batch_size: 50

recall:
  default_strategy: "hybrid"
  max_memories: 10
  confidence_threshold: 0.5
```

---

## 🤝 **Contributing Guidelines**

### **📋 Development Workflow**
1. **Fork and clone** the repository
2. **Create feature branch**: `git checkout -b feature/description`
3. **Make changes** following code style guidelines
4. **Run quality checks**: `make quality`
5. **Run tests**: `make test`
6. **Commit with clear message**: Follow conventional commits
7. **Push and create PR** with detailed description

### **🎯 Code Style Requirements**
- **Black formatting** (88 characters)
- **Type hints** for all public methods
- **Comprehensive docstrings** with examples
- **Error handling** with custom exceptions
- **Performance considerations** documented

### **✅ Pull Request Checklist**
- [ ] Code follows style guidelines (`make format`)
- [ ] All tests pass (`make test`)
- [ ] Type checking passes (`make typecheck`)
- [ ] Performance impact assessed
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated for user-facing changes

---

## 🔍 **Troubleshooting**

### **🚨 Common Issues**

#### **Performance Issues**
```bash
# Enable CLI adapter for speed
kuzu-memory optimize --enable-cli

# Check database size
kuzu-memory project --verbose

# Run performance diagnostics
make memory-test
```

#### **Database Issues**
```bash
# Reinitialize database
kuzu-memory init --force

# Check database integrity
kuzu-memory stats --detailed

# Clean expired memories
kuzu-memory cleanup --force
```

#### **Integration Issues**
```bash
# Test AI integration pattern
python -c "
import subprocess
result = subprocess.run(['kuzu-memory', '--help'],
                       capture_output=True, text=True)
print('CLI available:', result.returncode == 0)
"

# Debug with verbose output
kuzu-memory --debug enhance "test prompt"
```

---

## 📚 **Additional Resources**

### **📖 Documentation Links**
- [CLAUDE.md](CLAUDE.md) - Priority-based instructions for AI agents
- [CODE_STRUCTURE.md](CODE_STRUCTURE.md) - Detailed architectural analysis
- [Makefile](Makefile) - Single-path command workflows
- [pyproject.toml](pyproject.toml) - Package configuration and dependencies

### **🛠️ Development Tools**
- **Kuzu CLI**: https://docs.kuzudb.com/installation
- **Click Documentation**: https://click.palletsprojects.com/
- **Pydantic Guide**: https://pydantic-docs.helpmanual.io/
- **pytest Documentation**: https://docs.pytest.org/

### **🎯 Best Practices**
- Always use subprocess calls for AI integration
- Keep recall operations under 100ms
- Use async learning for non-blocking operations
- Follow single-path principle (ONE way to do anything)
- Prioritize documentation: 🔴 Critical → 🟡 Important → 🟢 Standard → ⚪ Optional

---

**🧠 This developer guide provides everything needed to contribute effectively to KuzuMemory and build robust AI-powered memory systems.**