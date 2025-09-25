# Core Features

## 🧠 **Memory Management**

### **Intelligent Memory Generation**
KuzuMemory automatically extracts meaningful information from content and creates structured memories.

**Features**:
- **Pattern Recognition** - Regex-based extraction of technical patterns, decisions, and preferences
- **Entity Extraction** - Identification of technologies, frameworks, tools, and concepts
- **Content Categorization** - Automatic classification into memory types (factual, preference, decision, etc.)
- **Importance Scoring** - Relevance scoring to prioritize important information

**Example**:
```bash
# Input content
kuzu-memory learn "We decided to use FastAPI with PostgreSQL for this project because it's fast and has great async support"

# Generated memories
- Decision: "Use FastAPI as web framework"
- Decision: "Use PostgreSQL as database"
- Reasoning: "FastAPI chosen for speed and async support"
- Technology: "FastAPI", "PostgreSQL"
```

### **Multi-Layer Deduplication**
Prevents duplicate memories through sophisticated deduplication strategies.

**Deduplication Layers**:
1. **Exact Hash Matching** - Identical content detection
2. **Normalized Text Matching** - Similar content with minor variations
3. **Semantic Similarity** - Content-based similarity detection
4. **Entity-Based Matching** - Same entities with different wording

**Configuration**:
```python
# Configurable similarity thresholds
similarity_threshold = 0.85  # 85% similarity threshold
hash_deduplication = True    # Enable exact hash matching
semantic_deduplication = True # Enable semantic similarity
```

### **Memory Types**
Different types of memories for different kinds of information.

**Supported Types**:
- **`FACTUAL`** - Objective facts about the project
- **`PREFERENCE`** - User or team preferences
- **`DECISION`** - Project decisions and their reasoning
- **`PATTERN`** - Code patterns and architectural choices
- **`ENTITY`** - Technologies, tools, and concepts
- **`TEMPORAL`** - Time-based information and events

---

## ⚡ **Performance Features**

### **Sub-100ms Context Retrieval**
Optimized for real-time AI integration with ultra-fast context retrieval.

**Performance Optimizations**:
- **Indexed Queries** - Optimized database indexes for common patterns
- **LRU Caching** - Frequently accessed memories cached in memory
- **Connection Pooling** - Reused database connections
- **Query Optimization** - Efficient graph database queries

**Benchmarks**:
```
Context Retrieval: 45ms avg (target: <100ms)
Memory Storage: 120ms avg (async, non-blocking)
Database Query: 8ms avg (target: <10ms)
Cache Hit Rate: 85% for frequent queries
```

### **Async Memory Operations**
Non-blocking memory operations that never delay AI responses.

**Async Features**:
- **Background Learning** - Memory storage happens in background threads
- **Queue Management** - Lightweight message queue for task management
- **Status Reporting** - Real-time status updates for long operations
- **Error Recovery** - Robust error handling without blocking main flow

**Usage**:
```bash
# Async by default - returns immediately
kuzu-memory learn "User prefers TypeScript" --quiet

# Sync mode for testing
kuzu-memory learn "Test memory" --sync
```

### **Intelligent Caching**
Multi-layer caching system for optimal performance.

**Caching Layers**:
- **Memory Cache** - In-memory LRU cache for frequently accessed memories
- **Query Cache** - Database query result caching
- **Connection Cache** - Database connection pooling
- **Metadata Cache** - Project metadata and configuration caching

---

## 🎯 **AI Integration Features**

### **Context Enhancement**
Automatically enhances AI prompts with relevant project context.

**Enhancement Process**:
1. **Query Analysis** - Analyze user prompt for relevant topics
2. **Memory Retrieval** - Find relevant memories using similarity scoring
3. **Context Building** - Construct enhanced prompt with context
4. **Confidence Scoring** - Provide confidence score for context relevance

**Example**:
```bash
# Original prompt
"How do I structure an API endpoint?"

# Enhanced prompt
"## Relevant Context:
- Project uses FastAPI as web framework
- Database is PostgreSQL with SQLAlchemy
- Team prefers async/await patterns

## User Question:
How do I structure an API endpoint?"
```

### **Learning from Conversations**
Automatically learns from AI conversations and user interactions.

**Learning Features**:
- **Conversation Analysis** - Extract learnings from AI conversations
- **User Corrections** - Learn from user feedback and corrections
- **Pattern Recognition** - Identify recurring patterns and preferences
- **Continuous Improvement** - Memory system gets better over time

**Integration Example**:
```python
# AI conversation flow
user_input = "How should I handle authentication?"
enhanced_prompt = enhance_with_memory(user_input)
ai_response = generate_ai_response(enhanced_prompt)

# Learn from the interaction (async, non-blocking)
store_learning(f"User asked about auth: {ai_response}")
```

### **Multiple Output Formats**
Flexible output formats for different integration needs.

**Supported Formats**:
- **`plain`** - Clean text for AI consumption
- **`json`** - Structured data for programmatic use
- **`context`** - Human-readable with metadata
- **`markdown`** - Formatted markdown output

---

## 📁 **Project-Based Features**

### **Git Integration**
Memories are stored in the project directory and committed to git.

**Git Features**:
- **Project-Specific Storage** - Memories stored in `kuzu-memories/` directory
- **Version Control** - Memory history tracked in git
- **Team Sharing** - Memories shared across team members
- **Branch Isolation** - Different memories for different branches (optional)

**Directory Structure**:
```
your-project/
├── kuzu-memories/
│   ├── database.kuzu
│   ├── config.json
│   └── backups/
├── .augment/
│   └── rules/
└── AGENTS.md
```

### **Project Discovery**
Automatic project detection and configuration.

**Discovery Features**:
- **Project Root Detection** - Finds project root using common indicators
- **Automatic Initialization** - Sets up memory system on first use
- **Configuration Inheritance** - Inherits settings from parent projects
- **Multi-Project Support** - Handles nested and related projects

### **Team Collaboration**
Features designed for team development workflows.

**Collaboration Features**:
- **Shared Context** - Same memories available to all team members
- **Consistent Responses** - AI gives consistent answers across team
- **Knowledge Preservation** - Project knowledge survives team changes
- **Onboarding Support** - New team members get instant context

---

## 🔧 **CLI Features**

### **Rich Command Interface**
Comprehensive CLI with rich help and examples.

**CLI Features**:
- **Rich Help System** - Detailed help with examples and use cases
- **Color Output** - Syntax highlighting and colored status messages
- **Progress Indicators** - Progress bars for long operations
- **Error Recovery** - Helpful error messages with suggestions

**Commands**:
```bash
kuzu-memory init          # Initialize project memories
kuzu-memory enhance       # Enhance prompts with context
kuzu-memory learn         # Store new memories (async by default)
kuzu-memory recall        # Search and retrieve memories
kuzu-memory recent        # Show recent memories
kuzu-memory stats         # Show system statistics
kuzu-memory project       # Show project information
```

### **Flexible Configuration**
Multiple configuration options for different use cases.

**Configuration Sources** (in order of precedence):
1. **CLI Arguments** - Command-line flags and options
2. **Environment Variables** - Runtime configuration
3. **Project Config** - Project-specific settings in `kuzu-memories/config.json`
4. **Global Config** - User-wide settings
5. **Default Config** - Built-in sensible defaults

### **Debug and Monitoring**
Built-in debugging and monitoring capabilities.

**Debug Features**:
- **Verbose Mode** - Detailed operation logging
- **Performance Timing** - Built-in performance measurement
- **Health Checks** - System health monitoring
- **Error Diagnostics** - Detailed error information

---

## 🔒 **Security Features**

### **Local-First Architecture**
All data stored locally with no external dependencies.

**Security Benefits**:
- **No External APIs** - No data sent to external services
- **Local Storage** - All memories stored in project directory
- **No Network Calls** - Works completely offline
- **Data Ownership** - Complete control over memory data

### **Input Validation**
Comprehensive input validation and sanitization.

**Validation Features**:
- **Content Sanitization** - Safe handling of user input
- **SQL Injection Prevention** - Parameterized queries
- **Path Traversal Protection** - Safe file system operations
- **Resource Limits** - Protection against resource exhaustion

---

## 📊 **Analytics Features**

### **Usage Statistics**
Built-in analytics for memory system usage and effectiveness.

**Statistics Tracked**:
- **Memory Counts** - Number of memories by type and source
- **Query Performance** - Response times and cache hit rates
- **Learning Effectiveness** - Success rates and error rates
- **Usage Patterns** - Most common queries and operations

**Example Output**:
```bash
$ kuzu-memory stats
📊 KuzuMemory Statistics

Memory Database:
  Total memories: 1,247
  Memory types: 5 (factual: 45%, preference: 20%, decision: 25%, pattern: 8%, entity: 2%)
  
Performance:
  Avg context retrieval: 42ms
  Cache hit rate: 87%
  Async queue size: 3 tasks
  
Usage:
  Queries today: 156
  Memories learned: 23
  Most active source: ai-conversation (67%)
```

### **Health Monitoring**
Continuous monitoring of system health and performance.

**Health Metrics**:
- **Database Health** - Connection status and query performance
- **Memory Usage** - System memory and cache usage
- **Queue Status** - Async queue health and processing times
- **Error Rates** - Error frequency and types

---

## 🔄 **Integration Features**

### **Universal AI Integration**
Works with any AI system through standard CLI interface.

**Integration Benefits**:
- **Language Agnostic** - Works with any programming language
- **Standard Interface** - Simple subprocess calls
- **No Dependencies** - No special libraries required
- **Universal Compatibility** - Works with any AI system

### **Auggie/Claude Integration**
Specialized integration for Auggie and Claude AI systems.

**Auggie Features**:
- **Markdown Rules** - Integration through `AGENTS.md` and `.augment/rules/`
- **Automatic Enhancement** - Prompts automatically enhanced with context
- **Async Learning** - Non-blocking learning from conversations
- **Status Reporting** - Integration status and health monitoring

**This comprehensive feature set makes KuzuMemory the ideal memory system for AI applications.** 🧠✨
