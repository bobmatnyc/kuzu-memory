# KuzuMemory - Implementation Product Requirements Document

**Project:** KuzuMemory  
**Version:** 1.0.0  
**Target:** Claude Code Implementation  
**Python Version:** 3.11+  
**Estimated Implementation Time:** 40-60 hours

---

## 1. Executive Summary

### 1.1 Objective

Implement KuzuMemory, a lightweight, embedded graph-based memory system for AI applications that stores and retrieves contextual memories without requiring LLM calls. The system should integrate seamlessly with existing chatbots and AI frameworks through a simple two-method API.

### 1.2 Core Requirements

1. **No LLM Dependencies**: Operate using pattern matching and local NER only
2. **Simple API**: Two primary methods: `attach_memories()` and `generate_memories()`
3. **Embedded Database**: Use Kuzu for local, single-file graph storage
4. **Git-Friendly**: Database file should be <10MB for direct git commits
5. **Fast Performance**: <10ms for memory operations

### 1.3 Success Criteria

- [ ] Memory recall in <10ms without LLM calls
- [ ] Database size <5MB after 10,000 memories
- [ ] Zero external dependencies for core operations
- [ ] Works offline completely
- [ ] Can be committed directly to git

---

## 2. Technical Architecture

### 2.1 Project Structure

```
kuzu-memory/
├── pyproject.toml
├── README.md
├── requirements.txt
├── setup.py
├── src/
│   └── kuzu_memory/
│       ├── __init__.py
│       ├── __version__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── memory.py          # Main KuzuMemory class
│       │   ├── models.py          # Data models
│       │   └── config.py          # Configuration
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── kuzu_adapter.py    # Kuzu database interface
│       │   ├── cache.py           # LRU cache layer
│       │   └── schema.py          # Database schema
│       ├── extraction/
│       │   ├── __init__.py
│       │   ├── patterns.py        # Pattern-based extraction
│       │   ├── entities.py        # Entity extraction
│       │   └── relationships.py   # Relationship detection
│       ├── recall/
│       │   ├── __init__.py
│       │   ├── strategies.py      # Recall strategies
│       │   ├── ranking.py         # Memory ranking
│       │   └── context.py         # Context building
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── text_processing.py
│       │   └── validation.py
│       └── cli/
│           ├── __init__.py
│           └── commands.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── examples/
    ├── basic_usage.py
    ├── chatbot_integration.py
    └── git_workflow.py
```

### 2.2 Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "kuzu>=0.4.0",           # Graph database
    "pydantic>=2.0",         # Data validation
    "click>=8.1.0",          # CLI
    "pyyaml>=6.0",          # Configuration
    "python-dateutil>=2.8",  # Date handling
    "typing-extensions>=4.5" # Python 3.11+ compatibility
]

[project.optional-dependencies]
ner = [
    "spacy>=3.5",           # Optional NER
    "en-core-web-sm"        # Small English model
]
```

---

## 3. Core Implementation Requirements

### 3.1 Main API Class

```python
# src/kuzu_memory/core/memory.py

from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import re

class KuzuMemory:
    """Main interface for memory operations."""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize KuzuMemory.
        
        Args:
            db_path: Path to database file (default: .kuzu_memory/memories.db)
            config: Optional configuration dict
        """
        self.db_path = db_path or Path(".kuzu_memory/memories.db")
        self.config = config or self._default_config()
        self._initialize_database()
        self._initialize_cache()
        self._load_patterns()
    
    def attach_memories(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto"
    ) -> MemoryContext:
        """
        PRIMARY API METHOD 1: Retrieve relevant memories for a prompt.
        
        Args:
            prompt: User input to find memories for
            max_memories: Maximum number of memories to return
            strategy: Recall strategy (auto|keyword|entity|temporal)
            
        Returns:
            MemoryContext object containing:
                - original_prompt: The input prompt
                - enhanced_prompt: Prompt with memories injected
                - memories: List of relevant Memory objects
                - confidence: Confidence score (0-1)
                
        Performance Requirement: Must complete in <10ms
        """
        # Implementation required
        pass
    
    def generate_memories(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "conversation"
    ) -> List[str]:
        """
        PRIMARY API METHOD 2: Extract and store memories from content.
        
        Args:
            content: Text to extract memories from (usually LLM response)
            metadata: Additional context (user_id, session_id, etc.)
            source: Origin of content
            
        Returns:
            List of created memory IDs
            
        Performance Requirement: Must complete in <20ms
        """
        # Implementation required
        pass
```

### 3.2 Data Models

```python
# src/kuzu_memory/core/models.py

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

class MemoryType(Enum):
    """Types of memories with different retention policies."""
    IDENTITY = "identity"        # User/system facts (never expire)
    PREFERENCE = "preference"    # Settings and preferences
    DECISION = "decision"        # Architectural decisions
    PATTERN = "pattern"         # Code patterns
    SOLUTION = "solution"       # Problem-solution pairs
    STATUS = "status"          # Current state (expire quickly)
    CONTEXT = "context"        # Session context (expire daily)

class Memory(BaseModel):
    """Core memory model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    content_hash: str  # SHA256 for deduplication
    
    # Temporal
    created_at: datetime = Field(default_factory=datetime.now)
    valid_from: datetime = Field(default_factory=datetime.now)
    valid_to: Optional[datetime] = None  # None = currently valid
    
    # Classification
    memory_type: MemoryType = MemoryType.CONTEXT
    importance: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Source tracking
    source_type: str = "conversation"
    agent_id: str = "default"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    entities: List[str] = Field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if memory is currently valid."""
        return self.valid_to is None

class MemoryContext(BaseModel):
    """Context object returned by attach_memories()."""
    original_prompt: str
    enhanced_prompt: str
    memories: List[Memory]
    confidence: float = Field(ge=0.0, le=1.0)
    token_count: int = 0
    strategy_used: str = "auto"
    
    def to_system_message(self) -> str:
        """Format as system message for LLM."""
        if not self.memories:
            return self.original_prompt
            
        context = "## Relevant Context:\n"
        for mem in self.memories:
            context += f"- {mem.content}\n"
        
        return f"{context}\n{self.original_prompt}"
```

### 3.3 Pattern-Based Extraction (No LLM)

```python
# src/kuzu_memory/extraction/patterns.py

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ExtractedMemory:
    """Memory extracted from text."""
    content: str
    confidence: float
    memory_type: MemoryType
    pattern_used: str

class PatternExtractor:
    """Extract memories using regex patterns - NO LLM REQUIRED."""
    
    # Explicit memory patterns
    REMEMBER_PATTERNS = [
        (r"[Rr]emember that (.*?)(?:\.|$)", 0.95),
        (r"[Dd]on't forget (?:that )?(.*?)(?:\.|$)", 0.95),
        (r"[Ff]or (?:future )?reference[,:]?\s*(.*?)(?:\.|$)", 0.90),
        (r"[Aa]lways (.*?)(?:\.|$)", 0.95),
        (r"[Nn]ever (.*?)(?:\.|$)", 0.95),
    ]
    
    # Identity patterns
    IDENTITY_PATTERNS = [
        (r"[Mm]y name is (.*?)(?:\.|$)", 1.0),
        (r"I (?:work at|work for|am at) (.*?)(?:\.|$)", 0.95),
        (r"I am (?:a|an) (.*?)(?:\.|$)", 0.90),
        (r"I'?m (?:a|an) (.*?)(?:\.|$)", 0.90),
    ]
    
    # Preference patterns
    PREFERENCE_PATTERNS = [
        (r"I prefer (.*?)(?:\.|$)", 0.95),
        (r"I (?:like|love|enjoy) (.*?)(?:\.|$)", 0.85),
        (r"I (?:don't|do not) (?:like|want) (.*?)(?:\.|$)", 0.85),
        (r"(?:Please|please) (?:always )?(.*?)(?:\.|$)", 0.80),
    ]
    
    # Decision patterns
    DECISION_PATTERNS = [
        (r"[Ww]e (?:decided|agreed) (?:to |on )?(.*?)(?:\.|$)", 0.95),
        (r"[Ll]et's (?:go with|use) (.*?)(?:\.|$)", 0.90),
        (r"[Ww]e'?(?:ll| will) (?:use|go with) (.*?)(?:\.|$)", 0.90),
    ]
    
    # Correction patterns (high importance)
    CORRECTION_PATTERNS = [
        (r"[Aa]ctually,?\s*(?:it's |its |it is )(.*?)(?:\.|$)", 0.95),
        (r"[Nn]o,?\s*(?:it's |its |it is )(.*?)(?:\.|$)", 0.95),
        (r"[Cc]orrection:\s*(.*?)(?:\.|$)", 1.0),
    ]
    
    def extract_memories(self, text: str) -> List[ExtractedMemory]:
        """Extract all potential memories from text."""
        memories = []
        
        # Check each pattern type
        pattern_sets = [
            (self.REMEMBER_PATTERNS, MemoryType.CONTEXT),
            (self.IDENTITY_PATTERNS, MemoryType.IDENTITY),
            (self.PREFERENCE_PATTERNS, MemoryType.PREFERENCE),
            (self.DECISION_PATTERNS, MemoryType.DECISION),
            (self.CORRECTION_PATTERNS, MemoryType.CONTEXT),  # High importance
        ]
        
        for patterns, memory_type in pattern_sets:
            for pattern, confidence in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    content = match.group(1).strip()
                    if content and len(content) > 5:  # Min length check
                        memories.append(ExtractedMemory(
                            content=content,
                            confidence=confidence,
                            memory_type=memory_type,
                            pattern_used=pattern
                        ))
        
        return self._deduplicate(memories)
    
    def _deduplicate(self, memories: List[ExtractedMemory]) -> List[ExtractedMemory]:
        """Remove duplicate memories."""
        seen = set()
        unique = []
        for mem in memories:
            # Normalize for comparison
            normalized = mem.content.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(mem)
        return unique
```

### 3.4 Entity Extraction (No LLM)

```python
# src/kuzu_memory/extraction/entities.py

import re
from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass
class Entity:
    """Extracted entity."""
    text: str
    entity_type: str
    confidence: float = 0.9

class EntityExtractor:
    """Extract entities using patterns - NO LLM REQUIRED."""
    
    # Entity patterns
    PATTERNS = {
        "project": r"\b(?:project|app|application|service)\s+([A-Z][A-Za-z0-9]+)",
        "person": r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b(?:\s+(?:is|was|works|said))",
        "technology": r"\b(Python|JavaScript|TypeScript|React|Docker|Kubernetes|AWS|Java|C\+\+|Rust|Go)\b",
        "file": r"\b([\w\-]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md|txt|csv))\b",
        "url": r"(https?://[^\s]+)",
        "email": r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Z|a-z]{2,})\b",
        "version": r"\b(?:v|version\s*)(\d+\.\d+(?:\.\d+)?)\b",
        "date": r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b",
    }
    
    # Common names to filter out (avoid false positives)
    COMMON_WORDS = {
        "is", "was", "the", "and", "or", "if", "then", 
        "when", "where", "what", "who", "why", "how"
    }
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract all entities from text."""
        entities = []
        
        for entity_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity_text = match.group(1) if match.groups() else match.group(0)
                
                # Filter common words
                if entity_text.lower() not in self.COMMON_WORDS:
                    entities.append(Entity(
                        text=entity_text,
                        entity_type=entity_type,
                        confidence=0.9
                    ))
        
        return self._deduplicate_entities(entities)
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities."""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.text.lower(), entity.entity_type)
            if key not in seen:
                seen.add(key)
                unique.append(entity)
                
        return unique
```

### 3.5 Kuzu Database Schema

```python
# src/kuzu_memory/storage/schema.py

SCHEMA = """
-- Core memory table
CREATE NODE TABLE IF NOT EXISTS Memory (
    id STRING PRIMARY KEY,
    content TEXT NOT NULL,
    content_hash STRING UNIQUE,
    
    -- Temporal
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INT32 DEFAULT 0,
    
    -- Classification
    memory_type STRING NOT NULL,
    importance FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 1.0,
    
    -- Source
    source_type STRING DEFAULT 'conversation',
    agent_id STRING DEFAULT 'default',
    user_id STRING,
    session_id STRING,
    
    -- Metadata (JSON)
    metadata STRING
);

-- Entity table
CREATE NODE TABLE IF NOT EXISTS Entity (
    id STRING PRIMARY KEY,
    name STRING NOT NULL,
    entity_type STRING NOT NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mention_count INT32 DEFAULT 1
);

-- Relationships
CREATE REL TABLE IF NOT EXISTS MENTIONS (
    FROM Memory TO Entity,
    confidence FLOAT DEFAULT 1.0
);

CREATE REL TABLE IF NOT EXISTS RELATES_TO (
    FROM Memory TO Memory,
    relationship_type STRING
);

-- Indexes for performance
CREATE INDEX idx_memory_content ON Memory(content);
CREATE INDEX idx_memory_type ON Memory(memory_type);
CREATE INDEX idx_memory_valid ON Memory(valid_from, valid_to);
CREATE INDEX idx_entity_name ON Entity(name);
"""
```

### 3.6 Recall Implementation

```python
# src/kuzu_memory/recall/strategies.py

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re

class RecallStrategy:
    """Memory recall without LLM."""
    
    def __init__(self, db_connection):
        self.db = db_connection
        
    def recall(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto"
    ) -> List[Memory]:
        """Recall memories relevant to prompt."""
        
        if strategy == "auto":
            strategies = [
                self.keyword_recall,
                self.entity_recall,
                self.temporal_recall,
            ]
            
            # Run all strategies in parallel
            all_memories = []
            for strategy_func in strategies:
                memories = strategy_func(prompt, limit=max_memories)
                all_memories.extend(memories)
            
            # Rank and deduplicate
            return self._rank_and_dedupe(all_memories, max_memories)
            
        elif strategy == "keyword":
            return self.keyword_recall(prompt, max_memories)
        elif strategy == "entity":
            return self.entity_recall(prompt, max_memories)
        elif strategy == "temporal":
            return self.temporal_recall(prompt, max_memories)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def keyword_recall(self, prompt: str, limit: int) -> List[Memory]:
        """Simple keyword matching."""
        # Extract important keywords
        keywords = self._extract_keywords(prompt)
        
        if not keywords:
            return []
        
        # Query database
        query = """
            MATCH (m:Memory)
            WHERE m.valid_to IS NULL
            AND ({conditions})
            RETURN m
            ORDER BY m.importance DESC, m.created_at DESC
            LIMIT $limit
        """
        
        conditions = " OR ".join([f"m.content CONTAINS '{kw}'" for kw in keywords])
        query = query.format(conditions=conditions)
        
        results = self.db.execute(query, {"limit": limit})
        return [self._row_to_memory(row) for row in results]
    
    def entity_recall(self, prompt: str, limit: int) -> List[Memory]:
        """Find memories through entity relationships."""
        # Extract entities from prompt
        extractor = EntityExtractor()
        entities = extractor.extract_entities(prompt)
        
        if not entities:
            return []
        
        # Query through entity relationships
        query = """
            MATCH (e:Entity)-[:MENTIONS]-(m:Memory)
            WHERE e.name IN $entity_names
            AND m.valid_to IS NULL
            RETURN DISTINCT m
            ORDER BY m.importance DESC
            LIMIT $limit
        """
        
        entity_names = [e.text for e in entities]
        results = self.db.execute(query, {
            "entity_names": entity_names,
            "limit": limit
        })
        
        return [self._row_to_memory(row) for row in results]
    
    def temporal_recall(self, prompt: str, limit: int) -> List[Memory]:
        """Recall recent or time-relevant memories."""
        # Look for temporal markers
        time_markers = self._extract_time_references(prompt)
        
        if "recent" in prompt.lower() or "latest" in prompt.lower():
            # Get recent memories
            query = """
                MATCH (m:Memory)
                WHERE m.created_at > $since
                AND m.valid_to IS NULL
                RETURN m
                ORDER BY m.created_at DESC
                LIMIT $limit
            """
            
            since = datetime.now() - timedelta(days=7)
            results = self.db.execute(query, {
                "since": since,
                "limit": limit
            })
            
            return [self._row_to_memory(row) for row in results]
        
        return []
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", 
                     "what", "how", "when", "where", "who", "why",
                     "do", "does", "did", "we", "our", "my", "your"}
        
        # Tokenize and filter
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords[:5]  # Top 5 keywords
    
    def _rank_and_dedupe(self, memories: List[Memory], limit: int) -> List[Memory]:
        """Rank memories by relevance and remove duplicates."""
        # Remove duplicates by ID
        seen_ids = set()
        unique = []
        for mem in memories:
            if mem.id not in seen_ids:
                seen_ids.add(mem.id)
                unique.append(mem)
        
        # Sort by importance and recency
        unique.sort(
            key=lambda m: (m.importance, -m.created_at.timestamp()),
            reverse=True
        )
        
        return unique[:limit]
```

### 3.7 CLI Implementation

```python
# src/kuzu_memory/cli/commands.py

import click
from pathlib import Path
from kuzu_memory import KuzuMemory

@click.group()
def cli():
    """KuzuMemory CLI."""
    pass

@cli.command()
@click.option('--path', default='.kuzu_memory', help='Memory directory path')
def init(path):
    """Initialize memory database."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    
    # Create initial database
    memory = KuzuMemory(db_path=path / "memories.db")
    
    # Create config
    config_path = path / "config.yaml"
    with open(config_path, 'w') as f:
        f.write("""# KuzuMemory Configuration
version: 1.0

storage:
  max_size_mb: 50
  auto_compact: true
  
recall:
  max_memories: 10
  strategies:
    - keyword
    - entity
    - temporal
""")
    
    # Create .gitkeep
    (path / ".gitkeep").touch()
    
    click.echo(f"✅ Initialized KuzuMemory at {path}")
    click.echo("📝 Remember to add memories.db to git!")

@cli.command()
@click.argument('content')
@click.option('--path', default='.kuzu_memory/memories.db')
def remember(content, path):
    """Store a memory."""
    memory = KuzuMemory(db_path=Path(path))
    ids = memory.generate_memories(content)
    click.echo(f"✅ Stored {len(ids)} memories")

@cli.command()
@click.argument('query')
@click.option('--path', default='.kuzu_memory/memories.db')
@click.option('--limit', default=5)
def recall(query, path, limit):
    """Recall memories."""
    memory = KuzuMemory(db_path=Path(path))
    context = memory.attach_memories(query, max_memories=limit)
    
    click.echo(f"Found {len(context.memories)} memories:")
    for mem in context.memories:
        click.echo(f"  - {mem.content[:100]}...")

@cli.command()
@click.option('--path', default='.kuzu_memory/memories.db')
def stats(path):
    """Show database statistics."""
    memory = KuzuMemory(db_path=Path(path))
    stats = memory.get_statistics()
    
    click.echo(f"📊 Database Statistics:")
    click.echo(f"  Memories: {stats['total_memories']}")
    click.echo(f"  Entities: {stats['total_entities']}")
    click.echo(f"  File size: {stats['db_size_mb']:.2f} MB")

if __name__ == '__main__':
    cli()
```

---

## 4. Testing Requirements

### 4.1 Unit Tests

```python
# tests/unit/test_memory.py

import pytest
from pathlib import Path
from kuzu_memory import KuzuMemory

def test_initialization(tmp_path):
    """Test memory initialization."""
    db_path = tmp_path / "test.db"
    memory = KuzuMemory(db_path=db_path)
    assert db_path.exists()

def test_remember(tmp_path):
    """Test memory storage."""
    memory = KuzuMemory(db_path=tmp_path / "test.db")
    
    # Store memory
    content = "User: My name is Alice\nAssistant: Nice to meet you, Alice!"
    ids = memory.generate_memories(content)
    
    assert len(ids) > 0
    
def test_recall(tmp_path):
    """Test memory recall."""
    memory = KuzuMemory(db_path=tmp_path / "test.db")
    
    # Store memory
    memory.generate_memories("My name is Alice and I work at TechCorp")
    
    # Recall
    context = memory.attach_memories("Who am I?")
    
    assert len(context.memories) > 0
    assert "Alice" in context.enhanced_prompt

def test_pattern_extraction():
    """Test pattern-based extraction."""
    from kuzu_memory.extraction.patterns import PatternExtractor
    
    extractor = PatternExtractor()
    text = "Remember that we use Python for backend development. Always use type hints."
    
    memories = extractor.extract_memories(text)
    
    assert len(memories) >= 2
    assert any("Python" in m.content for m in memories)
    assert any("type hints" in m.content for m in memories)

def test_entity_extraction():
    """Test entity extraction without LLM."""
    from kuzu_memory.extraction.entities import EntityExtractor
    
    extractor = EntityExtractor()
    text = "Alice and Bob are working on ProjectAlpha using Python"
    
    entities = extractor.extract_entities(text)
    
    assert any(e.text == "Alice" for e in entities)
    assert any(e.text == "ProjectAlpha" for e in entities)
    assert any(e.text == "Python" for e in entities)

def test_performance(tmp_path, benchmark):
    """Test performance requirements."""
    memory = KuzuMemory(db_path=tmp_path / "test.db")
    
    # Pre-populate with memories
    for i in range(100):
        memory.generate_memories(f"Test memory {i}")
    
    # Benchmark recall
    result = benchmark(memory.attach_memories, "test query")
    
    # Should complete in <10ms
    assert benchmark.stats["mean"] < 0.010  # 10ms
```

### 4.2 Integration Tests

```python
# tests/integration/test_integration.py

def test_chatbot_integration(tmp_path):
    """Test integration with simple chatbot."""
    from kuzu_memory import KuzuMemory
    
    memory = KuzuMemory(db_path=tmp_path / "test.db")
    
    # Simulate conversation
    user_input = "My name is Alice and I prefer Python"
    
    # Attach memories (should be empty first time)
    context = memory.attach_memories(user_input)
    assert len(context.memories) == 0
    
    # Generate memories from interaction
    response = "Nice to meet you, Alice! Python is a great choice."
    memory.generate_memories(f"User: {user_input}\nAssistant: {response}")
    
    # Now memories should be available
    context = memory.attach_memories("What's my name?")
    assert len(context.memories) > 0
    assert any("Alice" in m.content for m in context.memories)

def test_git_integration(tmp_path):
    """Test git-friendly file sizes."""
    memory = KuzuMemory(db_path=tmp_path / "test.db")
    
    # Generate 1000 memories
    for i in range(1000):
        memory.generate_memories(f"Memory number {i}: Some content here")
    
    # Check file size
    db_size = (tmp_path / "test.db").stat().st_size
    
    # Should be < 1MB for 1000 memories
    assert db_size < 1_000_000
```

---

## 5. Performance Requirements

### 5.1 Benchmarks

| Operation | Requirement | Measurement Method |
|-----------|------------|-------------------|
| `attach_memories()` | < 10ms | pytest-benchmark |
| `generate_memories()` | < 20ms | pytest-benchmark |
| Entity extraction | < 5ms | Unit test |
| Pattern matching | < 3ms | Unit test |
| Database query | < 5ms | Integration test |
| Cache hit | < 1ms | Unit test |

### 5.2 Memory Requirements

- RAM usage: < 50MB for typical usage
- Database size: < 500 bytes per memory
- Cache size: Configurable, default 10MB

---

## 6. Deployment & Distribution

### 6.1 Package Setup

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="kuzu-memory",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "kuzu>=0.4.0",
        "pydantic>=2.0",
        "click>=8.1",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "kuzu-memory=kuzu_memory.cli.commands:cli",
        ],
    },
)
```

### 6.2 Installation Instructions

```bash
# For users
pip install kuzu-memory

# For development
git clone https://github.com/yourusername/kuzu-memory
cd kuzu-memory
pip install -e ".[dev]"

# Initialize in project
kuzu-memory init
```

---

## 7. Documentation Requirements

### 7.1 User Documentation

1. **README.md** - Installation, quick start, basic usage
2. **DEPLOYMENT.md** - Git integration, team setup
3. **API.md** - Complete API reference
4. **EXAMPLES.md** - Integration examples

### 7.2 Code Documentation

- All public methods must have docstrings
- Type hints for all parameters and returns
- Examples in docstrings for main API methods

---

## 8. Success Criteria Checklist

### Core Functionality
- [ ] `attach_memories()` returns relevant memories in <10ms
- [ ] `generate_memories()` extracts memories in <20ms
- [ ] Pattern extraction works without LLM
- [ ] Entity extraction works without LLM
- [ ] Database operations are atomic and safe

### Performance
- [ ] 10,000 memories = <5MB database
- [ ] No external API calls for core operations
- [ ] Works completely offline
- [ ] Cache improves performance by >50%

### Integration
- [ ] Simple chatbot example works
- [ ] Git workflow documented
- [ ] Database can be committed to git
- [ ] CLI tools functional

### Quality
- [ ] 90%+ test coverage
- [ ] All tests pass
- [ ] No security vulnerabilities
- [ ] Clean code (pylint score >9.0)

---

## 9. Implementation Timeline

### Week 1: Core Infrastructure
- [ ] Project setup and structure
- [ ] Basic KuzuMemory class
- [ ] Data models
- [ ] Database schema

### Week 2: Extraction
- [ ] Pattern-based extraction
- [ ] Entity extraction
- [ ] Relationship detection
- [ ] Memory deduplication

### Week 3: Recall
- [ ] Keyword recall
- [ ] Entity recall
- [ ] Temporal recall
- [ ] Ranking algorithm

### Week 4: Integration & Polish
- [ ] CLI implementation
- [ ] Testing suite
- [ ] Documentation
- [ ] Examples

### Week 5: Optimization & Release
- [ ] Performance optimization
- [ ] Cache implementation
- [ ] Package preparation
- [ ] Release to PyPI

---

## 10. Code to Start With

Create a new Python project and implement the following files in order:

1. `pyproject.toml` - Project configuration
2. `src/kuzu_memory/__init__.py` - Package initialization
3. `src/kuzu_memory/core/models.py` - Data models
4. `src/kuzu_memory/extraction/patterns.py` - Pattern extraction
5. `src/kuzu_memory/storage/schema.py` - Database schema
6. `src/kuzu_memory/core/memory.py` - Main API class
7. `tests/unit/test_memory.py` - Basic tests

Start with these files and incrementally add functionality, testing each component as you build it.

---

*This PRD provides a complete implementation specification for KuzuMemory. The system is designed to be simple, fast, and completely independent of LLMs while providing powerful memory capabilities through pattern matching and graph relationships.*