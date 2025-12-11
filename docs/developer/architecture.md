# KuzuMemory Architecture Documentation

**Version**: 1.0
**Last Updated**: September 2024

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Core Components](#core-components)
4. [Database Design](#database-design)
5. [Memory System](#memory-system)
6. [API Design](#api-design)
7. [Performance Architecture](#performance-architecture)
8. [Integration Points](#integration-points)
9. [Security & Privacy](#security--privacy)
10. [Extension Architecture](#extension-architecture)

---

## System Overview

### Purpose and Design Philosophy

KuzuMemory is an intelligent memory system designed specifically for AI applications, providing persistent, project-specific memory that enables AI assistants to maintain context across conversations without requiring LLM calls.

**Core Design Principles:**
- **Performance First**: Sub-100ms context retrieval, async learning
- **AI-Optimized**: Designed specifically for AI system integration
- **Project-Centric**: Memories are project-specific, not user-specific
- **Git-Integrated**: Memories are committed and shared with the team
- **Zero-Config**: Works out of the box with intelligent defaults
- **CLI-First**: Simple command-line interface for all operations

### Key Features and Capabilities

- 🧠 **Intelligent Memory Classification**: Automatic categorization with NLP
- ⚡ **High Performance**: <100ms context retrieval, async learning operations
- 🔄 **AI Integration**: Seamless integration with AI systems via subprocess
- 📁 **Project-Based**: Project-specific memories with git commit support
- 🚀 **Zero Configuration**: Sensible defaults with optional customization
- 🎯 **CLI-First**: Complete functionality through command-line interface
- 📊 **Graph Database**: Kuzu graph database for relationship modeling
- 🔍 **Entity Extraction**: Automatic entity and pattern recognition
- ⏰ **Temporal Decay**: Memory expiration based on type and importance
- 🌐 **Cross-Platform**: Runs on Windows, macOS, and Linux

### Performance Targets and Characteristics

| Operation | Target Time | Implementation |
|-----------|-------------|----------------|
| Context Retrieval (`enhance`) | <100ms | Synchronous, optimized queries |
| Memory Learning (`learn`) | Async/Non-blocking | Background queue processing |
| Memory Generation (`remember`) | <200ms | Synchronous with validation |
| Database Initialization | <500ms | Schema creation and validation |
| Entity Extraction | <50ms | Rule-based + optional NLP |
| Classification | <20ms | Pattern matching with ML fallback |

### Cross-Platform Compatibility

- **Python**: 3.11+ required for modern type hints and performance
- **Database**: Kuzu graph database (embedded, no external dependencies)
- **Operating Systems**: Windows, macOS, Linux
- **Installation**: pip, pipx, or development installation
- **Integration**: Subprocess-based for universal AI system compatibility

---

## Architecture Diagrams

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            KuzuMemory System                            │
├─────────────────────────────────────────────────────────────────────────┤
│                              CLI Layer                                  │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────┐ │
│  │enhance  │ learn   │remember │ recall  │ stats   │project │ init   │ │
│  │ <100ms  │ async   │ <200ms  │ <100ms  │ <50ms   │ <50ms  │ <500ms │ │
│  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                          Integration Layer                              │
│  ┌─────────────────┬─────────────────┬─────────────────────────────────┐ │
│  │   MCP Server    │ Async Memory    │    AI Integration Adapters      │ │
│  │ (Claude Code)   │   System        │   (Auggie, Universal Subprocess)│ │
│  └─────────────────┴─────────────────┴─────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                             Core Engine                                 │
│  ┌──────────────┬────────────────┬──────────────┬───────────────────────┐ │
│  │ Memory Core  │ Recall         │ NLP          │ Monitoring &          │ │
│  │ (Generation, │ Coordinator    │ Classifier   │ Performance           │ │
│  │  Validation) │ (Strategies)   │ (Entities)   │ (Metrics, Timing)     │ │
│  └──────────────┴────────────────┴──────────────┴───────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                            Storage Layer                                │
│  ┌────────────────┬─────────────────┬────────────────┬─────────────────┐ │
│  │ Memory Store   │ Connection Pool │ Caching Layer  │ Query Builder   │ │
│  │ (CRUD Ops)     │ (Performance)   │ (LRU, Embedds) │ (Optimization)  │ │
│  └────────────────┴─────────────────┴────────────────┴─────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                           Database Layer                                │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    Kuzu Graph Database                              │ │
│  │  Memory Nodes ←→ Entity Nodes ←→ Session Nodes                     │ │
│  │       ↓               ↓               ↓                             │ │
│  │  Relationships: MENTIONS, RELATES_TO, BELONGS_TO_SESSION            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
AI System (Claude, Auggie, etc.)
          │
          │ subprocess call
          ▼
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│    CLI Interface    │◄───┤   MCP Protocol       │◄───┤  Claude Code    │
│ (commands.py)       │    │ (server.py)          │    │  Integration    │
└─────────┬───────────┘    └──────────────────────┘    └─────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Core Memory Engine                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Memory    │  │   Recall    │  │     NLP     │  │   Async Queue   │ │
│  │   Engine    │◄─┤ Coordinator │  │ Classifier  │  │   Manager       │ │
│  │             │  │             │  │             │  │                 │ │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
│         │                                                               │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Storage Abstraction                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Memory    │  │ Connection  │  │   Cache     │  │   Kuzu CLI      │ │
│  │   Store     │◄─┤    Pool     │◄─┤   Layer     │  │   Adapter       │ │
│  │             │  │             │  │  (LRU)      │  │  (Performance)  │ │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
│         │                                                               │
└─────────┼───────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────┐
   │ Kuzu Database   │
   │  (.kuzu-memory/ │
   │   memories.db)  │
   └─────────────────┘
```

### Data Flow Pipeline

```
User Input: "How do I structure the API?"
                │
                ▼
        ┌───────────────┐
        │ CLI enhance   │ ──── Performance Target: <100ms
        │   Command     │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │  Input        │ ──── Validate and sanitize input
        │ Validation    │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │   Memory      │ ──── Query database for relevant memories
        │   Recall      │      Strategy: entity, pattern, or full-text
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │   Context     │ ──── Combine memories with original prompt
        │  Assembly     │      Format: markdown, plain, or JSON
        └───────┬───────┘
                │
                ▼
        Enhanced Prompt Output
        ┌─────────────────────┐
        │ ## Relevant Context:│
        │ - Use FastAPI       │
        │ - Follow REST API   │
        │                     │
        │ How do I structure  │
        │ the API?            │
        └─────────────────────┘
```

### Memory Processing Pipeline

```
Input: "User prefers TypeScript over JavaScript"
                │
                ▼
        ┌───────────────┐
        │ learn Command │ ──── Async operation (fire-and-forget)
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │   Content     │ ──── Validate content, generate hash
        │ Preprocessing │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │     NLP       │ ──── Extract entities: ["TypeScript", "JavaScript"]
        │ Classification│      Classify type: PREFERENCE
        └───────┬───────┘      Confidence: 0.95
                │
                ▼
        ┌───────────────┐
        │ Deduplication │ ──── Check content_hash for duplicates
        │    Check      │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │ Memory Store  │ ──── Save to database with relationships
        │   Creation    │      Create entity nodes and connections
        └───────┬───────┘
                │
                ▼
         Memory Stored
        ┌─────────────────────┐
        │ ID: uuid            │
        │ Type: PREFERENCE    │
        │ Importance: 0.9     │
        │ Entities: [TS, JS]  │
        │ Valid: Never expires│
        └─────────────────────┘
```

### NLP Classification Pipeline

```
Raw Text Input
        │
        ▼
┌───────────────┐
│   Pattern     │ ──── Regex patterns for quick classification
│   Matching    │      "prefers" → PREFERENCE (confidence: 0.8)
└───────┬───────┘      "decided" → DECISION (confidence: 0.9)
        │
        ▼
┌───────────────┐
│   Entity      │ ──── Extract named entities using NLTK/spaCy
│ Extraction    │      People, Organizations, Technologies
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   Intent      │ ──── Detect user intent from keywords
│  Detection    │      LEARNING, QUESTION, CORRECTION, STATUS
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   Confidence  │ ──── Combine scores from multiple sources
│  Calculation  │      Pattern: 0.8, Entity: 0.9, Intent: 0.7
└───────┬───────┘      Final: min(0.8, average) = 0.8
        │
        ▼
Classification Result
┌─────────────────────┐
│ Type: PREFERENCE    │
│ Confidence: 0.8     │
│ Entities: [...]     │
│ Intent: LEARNING    │
│ Keywords: [...]     │
└─────────────────────┘
```

---

## Core Components

### Memory Engine (src/kuzu_memory/core/)

**Primary Responsibility**: Central orchestrator for all memory operations

**Key Files**:
- `memory.py`: Main KuzuMemory class with attach_memories() and generate_memories()
- `models.py`: Pydantic models for Memory, MemoryContext, MemoryType
- `config.py`: Configuration management and validation
- `internal_models.py`: Internal data structures

**Performance Characteristics**:
- Memory initialization: <100ms
- Context retrieval: <100ms (attach_memories)
- Memory generation: <200ms (generate_memories)

**API Contract**:
```python
class KuzuMemory:
    def attach_memories(self, prompt: str, **kwargs) -> MemoryContext
    def generate_memories(self, content: str, **kwargs) -> List[Memory]
```

### Storage Layer (src/kuzu_memory/storage/)

**Primary Responsibility**: Database abstraction and query optimization

**Key Files**:
- `memory_store.py`: CRUD operations for memories
- `kuzu_adapter.py`: Python API adapter for Kuzu database
- `kuzu_cli_adapter.py`: CLI-based adapter for performance
- `schema.py`: Database schema definition and migrations
- `query_builder.py`: Query optimization and building

**Architecture Pattern**: Repository pattern with adapter abstraction
- `MemoryStore` provides high-level operations
- `KuzuAdapter` handles database-specific operations
- Connection pooling for performance optimization

### NLP Classifier (src/kuzu_memory/nlp/)

**Primary Responsibility**: Automatic memory classification and entity extraction

**Key Files**:
- `classifier.py`: Main classification engine with NLTK integration
- `patterns.py`: Pattern definitions for quick classification

**Classification Pipeline**:
1. **Pattern Matching**: Fast regex-based classification (primary method)
2. **Entity Extraction**: NLTK/spaCy for named entity recognition
3. **Intent Detection**: Keyword-based intent classification
4. **ML Classification**: Optional scikit-learn pipeline (fallback)

**Performance**: <20ms for classification, <50ms with entity extraction

### Async Operations (src/kuzu_memory/async_memory/)

**Primary Responsibility**: Non-blocking memory operations for AI integration

**Key Files**:
- `background_learner.py`: Async memory learning processor
- `queue_manager.py`: Task queue management
- `async_cli.py`: Async CLI wrapper
- `status_reporter.py`: Background operation monitoring

**Architecture**: Producer-consumer pattern with background processing
- CLI commands enqueue tasks (fire-and-forget)
- Background workers process queue
- Status monitoring for operation tracking

### CLI Interface (src/kuzu_memory/cli/)

**Primary Responsibility**: Command-line interface for all operations

**Key Files**:
- `commands.py`: Main CLI commands (enhance, learn, remember, etc.)
- `memory_commands.py`: Memory-specific operations
- `project_commands.py`: Project management commands
- `mcp_commands.py`: MCP server integration

**Design Pattern**: Click-based command hierarchy with rich formatting
- Modular command organization
- Rich terminal output with progress indicators
- Error handling with user-friendly messages

### Integrations (src/kuzu_memory/integrations/)

**Primary Responsibility**: AI system integration adapters

**Key Files**:
- `mcp_server.py`: Model Context Protocol server for Claude Code
- `auggie.py`: Auggie/Claude integration with rule generation
- `auggie_rules.py`: Automatic rule file generation

**Integration Patterns**:
- **MCP Protocol**: JSON-RPC server for Claude Code
- **Subprocess Pattern**: Universal CLI-based integration
- **File-based Integration**: Rule files and configuration

---

## Database Design

### Kuzu Graph Database Schema

KuzuMemory uses a graph database to model relationships between memories, entities, and sessions.

**Node Types**:

```cypher
// Core memory storage
CREATE NODE TABLE Memory (
    id STRING PRIMARY KEY,           // Unique memory identifier
    content STRING,                  // Memory content text
    content_hash STRING,            // SHA256 for deduplication
    created_at TIMESTAMP,           // Creation timestamp
    valid_from TIMESTAMP,           // Validity start time
    valid_to TIMESTAMP,             // Expiration time (NULL = never)
    accessed_at TIMESTAMP,          // Last access time
    access_count INT32,             // Access frequency tracking
    memory_type STRING,             // MemoryType enum value
    importance FLOAT,               // Importance score (0-1)
    confidence FLOAT,               // Classification confidence
    source_type STRING,             // Source of memory
    agent_id STRING,               // Creating agent identifier
    user_id STRING,                // Associated user
    session_id STRING,             // Session context
    metadata STRING                // JSON metadata
);

// Entity nodes for relationship modeling
CREATE NODE TABLE Entity (
    id STRING PRIMARY KEY,           // Unique entity identifier
    name STRING,                    // Entity name/value
    entity_type STRING,             // Type (PERSON, ORG, TECH, etc.)
    normalized_name STRING,         // Normalized for matching
    first_seen TIMESTAMP,           // First occurrence
    last_seen TIMESTAMP,            // Most recent occurrence
    mention_count INT32,            // Frequency tracking
    confidence FLOAT                // Extraction confidence
);

// Session tracking for conversation context
CREATE NODE TABLE Session (
    id STRING PRIMARY KEY,           // Session identifier
    user_id STRING,                 // Associated user
    agent_id STRING,               // Agent in session
    created_at TIMESTAMP,           // Session start
    last_activity TIMESTAMP,        // Last activity
    memory_count INT32,             // Memories in session
    metadata STRING                 // Session metadata
);

// Schema version tracking
CREATE NODE TABLE SchemaVersion (
    version STRING PRIMARY KEY,      // Schema version
    created_at TIMESTAMP,           // Migration time
    description STRING              // Migration description
);
```

**Relationship Types**:

```cypher
// Memory mentions entity (with position tracking)
CREATE REL TABLE MENTIONS (
    FROM Memory TO Entity,
    confidence FLOAT,               // Mention confidence
    position_start INT32,           // Start position in text
    position_end INT32,             // End position in text
    extraction_method STRING        // How entity was extracted
);

// Memory relates to another memory
CREATE REL TABLE RELATES_TO (
    FROM Memory TO Memory,
    relationship_type STRING,       // Relationship type
    strength FLOAT,                // Relationship strength
    created_at TIMESTAMP          // When relationship was created
);

// Memory belongs to session
CREATE REL TABLE BELONGS_TO_SESSION (
    FROM Memory TO Session,
    created_at TIMESTAMP          // When memory was added to session
);

// Entity co-occurrence relationships
CREATE REL TABLE CO_OCCURS_WITH (
    FROM Entity TO Entity,
    co_occurrence_count INT32,      // How often entities appear together
    last_co_occurrence TIMESTAMP   // Most recent co-occurrence
);
```

### Indexing Strategy

Kuzu automatically creates indices for PRIMARY KEY fields. Additional query optimization comes from:

1. **Hash-based Lookups**: content_hash for deduplication
2. **Temporal Queries**: created_at, valid_to for time-based filtering
3. **Type-based Queries**: memory_type for classification filtering
4. **Importance Ranking**: importance, confidence for relevance scoring

### Query Patterns

**Common Query Types**:

1. **Context Retrieval**: Find memories relevant to prompt
   ```cypher
   MATCH (m:Memory)
   WHERE (m.valid_to IS NULL OR m.valid_to > $current_time)
   AND m.importance >= $min_importance
   RETURN m ORDER BY m.importance DESC, m.created_at DESC
   LIMIT $limit
   ```

2. **Entity-based Search**: Find memories containing specific entities
   ```cypher
   MATCH (m:Memory)-[mentions:MENTIONS]->(e:Entity)
   WHERE e.normalized_name IN $entity_list
   AND (m.valid_to IS NULL OR m.valid_to > $current_time)
   RETURN m, e, mentions.confidence
   ORDER BY m.importance DESC
   ```

3. **Deduplication**: Check for existing similar content
   ```cypher
   MATCH (m:Memory)
   WHERE m.content_hash = $hash
   RETURN m
   ```

4. **Temporal Queries**: Get recent memories
   ```cypher
   MATCH (m:Memory)
   WHERE m.created_at > $since_time
   AND (m.valid_to IS NULL OR m.valid_to > $current_time)
   RETURN m ORDER BY m.created_at DESC
   ```

---

## Memory System

### Memory Types and Retention Policies

KuzuMemory implements a sophisticated memory classification system with automatic retention management:

```python
class MemoryType(str, Enum):
    IDENTITY = "identity"        # Never expire (user/system facts)
    PREFERENCE = "preference"    # Never expire (settings/preferences)
    DECISION = "decision"        # 90 days (architectural decisions)
    PATTERN = "pattern"         # 30 days (code patterns)
    SOLUTION = "solution"       # 60 days (problem-solution pairs)
    STATUS = "status"          # 6 hours (current state)
    CONTEXT = "context"        # 1 day (session context)
```

**Retention Logic**:
- **Never Expire**: IDENTITY, PREFERENCE types for persistent facts
- **Long-term**: DECISION (90d), SOLUTION (60d) for important information
- **Medium-term**: PATTERN (30d) for learning patterns
- **Short-term**: STATUS (6h), CONTEXT (1d) for temporary state

**Importance Scoring**:
- **Critical (1.0)**: IDENTITY memories
- **High (0.9)**: PREFERENCE, DECISION memories
- **Medium (0.7)**: PATTERN, SOLUTION memories
- **Low (0.3-0.5)**: STATUS, CONTEXT memories

### Classification Pipeline

**Stage 1: Pattern Matching**
- Fast regex-based classification using predefined patterns
- Confidence: 0.7-0.9 depending on pattern strength
- Examples:
  - "I prefer X" → PREFERENCE (0.8)
  - "We decided to use Y" → DECISION (0.9)
  - "The current status is Z" → STATUS (0.7)

**Stage 2: Entity Extraction**
```python
@dataclass
class EntityExtractionResult:
    people: List[str]           # Person names
    organizations: List[str]     # Company/org names
    locations: List[str]        # Geographic locations
    technologies: List[str]     # Programming languages, frameworks
    projects: List[str]         # Project/repository names
    dates: List[str]           # Temporal references
    all_entities: List[str]    # Combined entity list
```

**Stage 3: Intent Detection**
- Keyword-based intent classification
- Intents: LEARNING, QUESTION, CORRECTION, STATUS, COMMAND
- Used for context enhancement and response generation

**Stage 4: Confidence Scoring**
- Combine scores from pattern matching, entity extraction, and intent detection
- Final confidence = min(pattern_confidence, average_component_confidence)
- Confidence threshold: 0.6 minimum for storage

### Entity Extraction

**Rule-based Extraction** (Primary):
```python
ENTITY_PATTERNS = {
    'PERSON': [
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',     # John Smith
        r'@[a-zA-Z0-9_]+',                   # @username
    ],
    'TECHNOLOGY': [
        r'\b(Python|JavaScript|TypeScript|React|Vue|Angular)\b',
        r'\b[A-Z][a-z]*JS\b',               # ReactJS, VueJS
        r'\.(py|js|ts|jsx|tsx|vue)\b',      # File extensions
    ],
    'PROJECT': [
        r'\b[a-z-]+/[a-z-]+\b',            # github-style repos
        r'\b[A-Z][a-zA-Z0-9]*Project\b',    # ProjectName
    ]
}
```

**NLP-based Extraction** (Optional):
- NLTK for named entity recognition
- spaCy integration for advanced NER
- Used when rule-based extraction confidence is low

### Intent Detection

**Intent Categories**:
```python
INTENT_KEYWORDS = {
    'LEARNING': ['prefer', 'like', 'better', 'should use'],
    'QUESTION': ['how', 'what', 'why', 'when', 'where', '?'],
    'CORRECTION': ['wrong', 'mistake', 'actually', 'correction'],
    'STATUS': ['currently', 'now', 'status', 'state'],
    'COMMAND': ['do', 'create', 'build', 'implement', 'fix']
}
```

**Intent Scoring**:
- Count keyword matches weighted by position and context
- Boost score for question marks, imperative verbs
- Used for context assembly and response formatting

### Confidence Scoring

**Multi-factor Confidence Calculation**:
```python
def calculate_confidence(
    pattern_score: float,
    entity_score: float,
    intent_score: float,
    content_length: int
) -> float:
    # Base confidence from pattern matching
    base_confidence = pattern_score

    # Boost for entity extraction
    entity_boost = min(entity_score * 0.2, 0.3)

    # Intent detection contribution
    intent_boost = min(intent_score * 0.1, 0.1)

    # Length penalty for very short content
    length_penalty = 0.0
    if content_length < 10:
        length_penalty = 0.2

    final_confidence = base_confidence + entity_boost + intent_boost - length_penalty
    return max(0.0, min(1.0, final_confidence))
```

---

## API Design

### Core API Methods

**KuzuMemory Class** (Primary Interface):

```python
class KuzuMemory:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize with database path and configuration."""

    def attach_memories(
        self,
        prompt: str,
        limit: int = 10,
        min_importance: float = 0.3,
        strategy: str = "auto",
        format_style: str = "markdown"
    ) -> MemoryContext:
        """
        Attach relevant memories to prompt.
        Performance target: <100ms
        """

    def generate_memories(
        self,
        content: str,
        source_type: str = "conversation",
        agent_id: str = "default",
        session_id: Optional[str] = None
    ) -> List[Memory]:
        """
        Generate memories from content.
        Performance target: <200ms
        """
```

### CLI Commands

**Memory Operations**:
```bash
# Context enhancement (synchronous, <100ms)
kuzu-memory enhance "How do I structure the API?" --format plain

# Memory learning (async, fire-and-forget)
kuzu-memory learn "User prefers TypeScript" --quiet

# Direct memory storage (synchronous, <200ms)
kuzu-memory remember "Project uses FastAPI with PostgreSQL"

# Memory recall (synchronous, <100ms)
kuzu-memory recall "database setup" --limit 5
```

**Project Management**:
```bash
# Initialize project memory system
kuzu-memory init

# Project statistics and health
kuzu-memory stats --detailed

# Recent memories
kuzu-memory recent --format json --limit 10

# Memory cleanup
kuzu-memory cleanup --expired --force
```

**System Operations**:
```bash
# Performance optimization
kuzu-memory optimize --enable-cli

# Export memories
kuzu-memory export --format json --output memories.json

# Import memories
kuzu-memory import --file memories.json
```

### MCP Protocol Integration

**Available MCP Tools**:
```json
{
  "tools": [
    {
      "name": "kuzu_memory_enhance",
      "description": "Enhance prompt with project memories",
      "inputSchema": {
        "type": "object",
        "properties": {
          "prompt": {"type": "string"},
          "format": {"type": "string", "enum": ["markdown", "plain", "json"]},
          "limit": {"type": "integer", "default": 10}
        }
      }
    },
    {
      "name": "kuzu_memory_learn",
      "description": "Store new memory (async)",
      "inputSchema": {
        "type": "object",
        "properties": {
          "content": {"type": "string"},
          "source": {"type": "string", "default": "ai-conversation"}
        }
      }
    }
  ]
}
```

### Extension Points

**Custom Classifiers**:
```python
class CustomClassifier:
    def classify_memory(self, content: str) -> ClassificationResult:
        """Implement custom classification logic."""
        pass

    def extract_entities(self, content: str) -> EntityExtractionResult:
        """Implement custom entity extraction."""
        pass
```

**Storage Adapters**:
```python
class StorageAdapter:
    def store_memory(self, memory: Memory) -> str:
        """Store memory and return ID."""
        pass

    def retrieve_memories(self, query: Dict[str, Any]) -> List[Memory]:
        """Retrieve memories matching query."""
        pass
```

---

## Performance Architecture

### Caching Strategies

**Multi-Level Caching Architecture**:

```
Application Layer
    │
    ▼
┌─────────────────┐
│   LRU Cache     │ ──── Recent memories, query results
│   (Memory)      │      Capacity: 1000 items, TTL: 1 hour
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Embeddings      │ ──── Entity embeddings for similarity
│    Cache        │      Capacity: 5000 items, TTL: 24 hours
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Connection      │ ──── Database connections
│    Pool         │      Pool size: 10, Timeout: 30s
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Kuzu Database   │ ──── Persistent storage
│   (Disk)        │
└─────────────────┘
```

**Cache Implementation**:
```python
class MemoryCache:
    def __init__(self, capacity: int = 1000, ttl: int = 3600):
        self.cache = LRUCache(capacity)
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """Get cached item with TTL check."""

    def set(self, key: str, value: Any) -> None:
        """Cache item with timestamp."""

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
```

### Connection Pooling

**Database Connection Management**:
```python
class KuzuConnectionPool:
    def __init__(self, db_path: Path, pool_size: int = 10):
        self.db_path = db_path
        self.pool = Queue(maxsize=pool_size)
        self.active_connections = 0
        self.max_connections = pool_size

    async def acquire(self) -> KuzuConnection:
        """Acquire connection from pool or create new."""

    async def release(self, conn: KuzuConnection) -> None:
        """Return connection to pool."""

    def close_all(self) -> None:
        """Close all connections in pool."""
```

### Async Operations

**Background Processing Architecture**:

```python
class AsyncMemorySystem:
    def __init__(self):
        self.queue_manager = QueueManager()
        self.background_learner = BackgroundLearner()
        self.status_reporter = StatusReporter()

    async def enqueue_learning(self, content: str) -> str:
        """Enqueue memory for background processing."""
        task_id = str(uuid4())
        await self.queue_manager.enqueue(task_id, {
            'operation': 'learn',
            'content': content,
            'timestamp': datetime.now()
        })
        return task_id

    async def process_queue(self) -> None:
        """Background worker for processing queued operations."""
        while True:
            task = await self.queue_manager.dequeue()
            if task:
                await self.background_learner.process_task(task)
```

### Query Optimization

**Query Performance Patterns**:

1. **Index Usage**: Primary keys and common filter fields
2. **Query Planning**: Optimize JOIN operations for graph traversals
3. **Batch Operations**: Group multiple operations for efficiency
4. **Result Limiting**: Always use LIMIT clauses for large result sets

**Optimized Query Examples**:
```cypher
// Efficient memory retrieval with indices
MATCH (m:Memory)
WHERE m.memory_type IN $types
AND (m.valid_to IS NULL OR m.valid_to > $now)
AND m.importance >= $min_importance
RETURN m
ORDER BY m.importance DESC, m.created_at DESC
LIMIT $limit

// Entity-based search with relationship pruning
MATCH (m:Memory)-[r:MENTIONS]->(e:Entity)
WHERE e.normalized_name IN $entities
AND r.confidence >= 0.7
AND (m.valid_to IS NULL OR m.valid_to > $now)
RETURN m, e, r.confidence
ORDER BY m.importance DESC, r.confidence DESC
LIMIT $limit
```

### Performance Monitoring

**Metrics Collection**:
```python
@dataclass
class PerformanceMetrics:
    operation: str
    duration_ms: float
    memory_usage_mb: float
    db_queries: int
    cache_hits: int
    cache_misses: int
    timestamp: datetime

class PerformanceMonitor:
    def track_operation(self, operation: str) -> ContextManager:
        """Context manager for tracking operation performance."""

    def get_metrics(self, since: datetime) -> List[PerformanceMetrics]:
        """Retrieve performance metrics."""

    def generate_report(self) -> Dict[str, Any]:
        """Generate performance report."""
```

**Performance Targets Monitoring**:
- Track all operations against target times
- Alert when operations exceed thresholds
- Automatic query optimization recommendations
- Memory usage tracking and leak detection

---

## Integration Points

### Claude Code / MCP

**MCP Server Architecture**:
```python
class MCPServer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.kuzu_memory = self._initialize_memory()

    async def handle_enhance_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory enhancement requests from Claude Code."""

    async def handle_learn_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle async learning requests."""

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Return available MCP tools."""
```

**Integration Flow**:
1. Claude Code sends MCP request via JSON-RPC
2. MCP server validates request parameters
3. Server calls appropriate KuzuMemory methods
4. Results formatted and returned to Claude Code
5. Async operations queued for background processing

### AI System Integration Patterns

**Universal Subprocess Pattern**:
```python
import subprocess

def enhance_with_memory(prompt: str) -> str:
    """Universal pattern for AI system integration."""
    result = subprocess.run([
        'kuzu-memory', 'enhance', prompt, '--format', 'plain'
    ], capture_output=True, text=True, timeout=5)

    if result.returncode == 0:
        return result.stdout.strip()
    else:
        logger.error(f"Memory enhancement failed: {result.stderr}")
        return prompt  # Fallback to original prompt

def learn_async(content: str, source: str = "ai-conversation") -> None:
    """Non-blocking learning for AI conversations."""
    subprocess.run([
        'kuzu-memory', 'learn', content,
        '--source', source, '--quiet'
    ], check=False)  # Fire and forget
```

**Integration Benefits**:
- **Language Agnostic**: Works with any AI system that can call subprocess
- **No Dependencies**: No Python imports required
- **Fast**: CLI optimized for performance
- **Reliable**: Process isolation prevents memory leaks
- **Scalable**: Multiple AI systems can use same memory store

### Auggie Integration

**Auggie Rule Generation**:
```python
def generate_auggie_rules(memory_store: MemoryStore) -> str:
    """Generate .augment/rules/ files from project memories."""

    # Get project memories
    memories = memory_store.get_memories_by_type([
        MemoryType.IDENTITY,
        MemoryType.PREFERENCE,
        MemoryType.DECISION
    ])

    # Group by category
    rules = {
        'project-context.md': [],
        'preferences.md': [],
        'decisions.md': []
    }

    # Generate rule content
    for memory in memories:
        if memory.memory_type == MemoryType.IDENTITY:
            rules['project-context.md'].append(f"- {memory.content}")
        elif memory.memory_type == MemoryType.PREFERENCE:
            rules['preferences.md'].append(f"- {memory.content}")
        elif memory.memory_type == MemoryType.DECISION:
            rules['decisions.md'].append(f"- {memory.content}")

    return rules
```

**Auggie Workflow**:
1. User interacts with Auggie
2. Auggie calls kuzu-memory enhance before generating response
3. Enhanced context improves response quality
4. Auggie response triggers kuzu-memory learn (async)
5. Learned information available for future interactions

### Subprocess Architecture

**Process Management**:
```python
class SubprocessManager:
    def __init__(self, cli_path: str):
        self.cli_path = cli_path
        self.timeout = 10  # seconds

    def call_sync(self, command: List[str]) -> subprocess.CompletedProcess:
        """Synchronous CLI call with timeout."""
        return subprocess.run(
            [self.cli_path] + command,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )

    def call_async(self, command: List[str]) -> None:
        """Asynchronous CLI call (fire-and-forget)."""
        subprocess.Popen(
            [self.cli_path] + command + ['--quiet'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
```

**Error Handling**:
- Timeout protection for all subprocess calls
- Graceful degradation when CLI unavailable
- Error logging without blocking AI system
- Fallback to original prompts when enhancement fails

---

## Security & Privacy

### Data Handling

**Content Validation**:
```python
class ContentValidator:
    def __init__(self):
        self.sensitive_patterns = [
            r'password[:\s].*',
            r'api[_\s]?key[:\s].*',
            r'token[:\s].*',
            r'secret[:\s].*',
            r'\b[A-Za-z0-9+/]{40,}\b',  # Base64 tokens
        ]

    def contains_sensitive_data(self, content: str) -> bool:
        """Check if content contains sensitive information."""
        content_lower = content.lower()
        return any(
            re.search(pattern, content_lower, re.IGNORECASE)
            for pattern in self.sensitive_patterns
        )

    def sanitize_content(self, content: str) -> str:
        """Remove or mask sensitive information."""
        sanitized = content
        for pattern in self.sensitive_patterns:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        return sanitized
```

**Credential Filtering**:
- Automatic detection of passwords, API keys, tokens
- Content sanitization before storage
- Warning messages for potentially sensitive content
- Option to skip storage for high-risk content

### Project Isolation

**Database Isolation**:
- Each project maintains separate database (`.kuzu-memory/`)
- No cross-project memory access
- Project detection via git repository or explicit configuration
- Memory scope limited to current working directory

**Permission Model**:
- File system permissions protect database access
- No network communication (offline-first design)
- No user authentication (project-based security)
- Memory sharing through git commit (explicit team sharing)

**Privacy Guarantees**:
- No data transmission to external servers
- No LLM calls for memory operations
- Local processing only
- User control over all stored data

### Access Control

**Project-Level Access**:
```python
class ProjectAccessControl:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.allowed_paths = [
            project_root,
            project_root / '.kuzu-memory',
            project_root / 'kuzu-memories'
        ]

    def validate_access(self, requested_path: Path) -> bool:
        """Validate access to requested path."""
        return any(
            requested_path.is_relative_to(allowed)
            for allowed in self.allowed_paths
        )

    def get_memory_scope(self) -> Dict[str, Any]:
        """Get memory access scope for current project."""
        return {
            'project_root': str(self.project_root),
            'database_path': str(self.project_root / '.kuzu-memory'),
            'git_committed': (self.project_root / 'kuzu-memories').exists()
        }
```

**Data Retention Control**:
- User-configurable retention policies
- Automatic cleanup of expired memories
- Manual cleanup commands
- Export functionality for data portability

---

## Extension Architecture

### Plugin System Design

**Plugin Interface**:
```python
class KuzuMemoryPlugin:
    """Base class for KuzuMemory plugins."""

    name: str
    version: str

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration."""

    def enhance_classification(
        self,
        content: str,
        base_result: ClassificationResult
    ) -> ClassificationResult:
        """Enhance or override base classification."""

    def extract_entities(self, content: str) -> List[str]:
        """Custom entity extraction."""

    def process_memory(self, memory: Memory) -> Memory:
        """Post-process memory before storage."""

    def enhance_recall(
        self,
        prompt: str,
        base_memories: List[Memory]
    ) -> List[Memory]:
        """Enhance or filter recall results."""
```

**Plugin Registration**:
```python
class PluginManager:
    def __init__(self):
        self.plugins: Dict[str, KuzuMemoryPlugin] = {}

    def register_plugin(self, plugin: KuzuMemoryPlugin) -> None:
        """Register a plugin."""
        self.plugins[plugin.name] = plugin
        plugin.initialize(self.get_plugin_config(plugin.name))

    def get_classification_plugins(self) -> List[KuzuMemoryPlugin]:
        """Get plugins that enhance classification."""
        return [p for p in self.plugins.values() if hasattr(p, 'enhance_classification')]
```

### Custom Classifiers

**Domain-Specific Classification**:
```python
class TechnicalClassifier(KuzuMemoryPlugin):
    """Classifier optimized for technical content."""

    name = "technical_classifier"
    version = "1.0.0"

    def __init__(self):
        self.tech_patterns = {
            'CODE_REVIEW': r'(review|looks good|LGTM|needs changes)',
            'BUG_REPORT': r'(bug|issue|error|broken|not working)',
            'FEATURE_REQUEST': r'(feature|enhancement|would be nice)',
            'ARCHITECTURE': r'(architecture|design|pattern|structure)'
        }

    def enhance_classification(
        self,
        content: str,
        base_result: ClassificationResult
    ) -> ClassificationResult:
        """Enhance classification with technical patterns."""

        for tech_type, pattern in self.tech_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                # Override base classification with technical type
                return ClassificationResult(
                    memory_type=MemoryType.PATTERN,
                    confidence=max(base_result.confidence, 0.8),
                    keywords=base_result.keywords + [tech_type.lower()],
                    entities=base_result.entities,
                    metadata={'technical_type': tech_type}
                )

        return base_result
```

### Storage Adapters

**Alternative Storage Backends**:
```python
class StorageAdapter:
    """Abstract storage adapter interface."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize storage backend."""

    def store_memory(self, memory: Memory) -> str:
        """Store memory and return ID."""

    def retrieve_memories(
        self,
        query: Dict[str, Any],
        limit: int = 10
    ) -> List[Memory]:
        """Retrieve memories matching query."""

    def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing memory."""

    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory by ID."""

class PostgreSQLAdapter(StorageAdapter):
    """PostgreSQL storage adapter example."""

    def initialize(self, config: Dict[str, Any]) -> None:
        self.connection_string = config['connection_string']
        self.table_prefix = config.get('table_prefix', 'kuzu_')
        # Initialize PostgreSQL connection

    def store_memory(self, memory: Memory) -> str:
        # Convert Memory to PostgreSQL storage format
        # Handle relationships and entities
        pass
```

**Adapter Registration**:
```python
def register_storage_adapter(name: str, adapter_class: Type[StorageAdapter]):
    """Register custom storage adapter."""
    STORAGE_ADAPTERS[name] = adapter_class

def create_storage_adapter(adapter_type: str, config: Dict[str, Any]) -> StorageAdapter:
    """Create storage adapter instance."""
    if adapter_type not in STORAGE_ADAPTERS:
        raise ValueError(f"Unknown storage adapter: {adapter_type}")

    adapter = STORAGE_ADAPTERS[adapter_type]()
    adapter.initialize(config)
    return adapter
```

### Custom Recall Strategies

**Recall Strategy Interface**:
```python
class RecallStrategy:
    """Base class for memory recall strategies."""

    name: str

    def calculate_relevance(
        self,
        memory: Memory,
        prompt: str,
        context: Dict[str, Any]
    ) -> float:
        """Calculate relevance score for memory given prompt."""

    def filter_memories(
        self,
        memories: List[Memory],
        prompt: str,
        limit: int
    ) -> List[Memory]:
        """Filter and rank memories for prompt."""

class SemanticRecallStrategy(RecallStrategy):
    """Semantic similarity-based recall."""

    name = "semantic"

    def __init__(self):
        # Initialize embedding model (optional dependency)
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            self.model = None

    def calculate_relevance(
        self,
        memory: Memory,
        prompt: str,
        context: Dict[str, Any]
    ) -> float:
        """Calculate semantic similarity."""
        if not self.model:
            return 0.0

        prompt_embedding = self.model.encode([prompt])
        memory_embedding = self.model.encode([memory.content])

        # Cosine similarity
        similarity = cosine_similarity(prompt_embedding, memory_embedding)[0][0]
        return similarity
```

This comprehensive architecture documentation provides a complete technical overview of the KuzuMemory system, enabling developers to understand the system deeply and maintain feature parity across different implementations. The document covers all major architectural aspects while maintaining focus on the core design principles of performance, AI optimization, and project-centric memory management.