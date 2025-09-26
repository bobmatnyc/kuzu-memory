# KuzuMemory: Memory Models and Architecture

## Overview

KuzuMemory implements a cognitive memory model inspired by human memory systems. This document explains the theoretical foundation, architectural design, and practical implementation of the memory model.

## Cognitive Memory Theory

### Foundation

KuzuMemory's memory model is based on established cognitive psychology research on human memory systems:

1. **Multi-Store Model** (Atkinson & Shiffrin, 1968): Different types of information are processed and stored differently
2. **Levels of Processing** (Craik & Lockhart, 1972): Deeper processing leads to better retention
3. **Working Memory Model** (Baddeley & Hitch, 1974): Temporary storage with limited capacity
4. **Episodic vs Semantic Memory** (Tulving, 1972): Distinction between personal experiences and factual knowledge

### Memory Types in Cognitive Science

| Memory Type | Scientific Basis | KuzuMemory Implementation |
|------------|------------------|---------------------------|
| **Episodic** | Personal experiences, events with temporal context | Project events, decisions, historical context |
| **Semantic** | General knowledge, facts, concepts | Identity information, specifications, constants |
| **Procedural** | Skills, procedures, how-to knowledge | Instructions, processes, methodologies |
| **Working** | Temporary storage for current processing | Active tasks, immediate priorities |
| **Sensory** | Brief retention of sensory information | UI observations, system behavior notes |
| **Preference** | Long-term preferences and habits | User/team choices, configuration preferences |

## KuzuMemory Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                 Memory Model Architecture                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Input Layer   │    │ Processing Layer │    │  Storage Layer  │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Text Content  │ -> │ • NLP Classifier │ -> │ • Kuzu Graph DB │
│ • Context Info  │    │ • Entity Extract │    │ • Memory Nodes  │
│ • Metadata      │    │ • Relationship   │    │ • Entity Nodes  │
│                 │    │   Detection      │    │ • Relationships │
└─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Recall Layer                             │
├─────────────────┐    ├─────────────────┐    ├─────────────────┐
│ • Query Parser  │    │ • Graph Queries │    │ • Result Ranker │
│ • Entity Match  │    │ • Similarity    │    │ • Context Build │
│ • Type Filter   │    │ • Temporal      │    │ • Formatting    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Memory Storage Model

#### Graph Database Schema

```cypher
// Memory node structure
CREATE (m:Memory {
    id: string,
    content: string,
    memory_type: enum,
    importance: float,
    created_at: timestamp,
    expires_at: timestamp?,
    source: string,
    metadata: map
})

// Entity node structure
CREATE (e:Entity {
    id: string,
    name: string,
    type: string,
    canonical_name: string
})

// Relationships
CREATE (m)-[:CONTAINS]->(e)  // Memory contains entity
CREATE (m)-[:RELATED_TO]->(m2)  // Memory related to another memory
CREATE (e)-[:SAME_AS]->(e2)  // Entity equivalence
CREATE (m)-[:DERIVED_FROM]->(m2)  // Memory derived from another
```

#### Memory Node Properties

```python
class Memory:
    # Core properties
    id: str                    # Unique identifier
    content: str              # The actual memory text
    memory_type: MemoryType   # Cognitive type classification

    # Metadata
    importance: float         # 0.0 to 1.0 importance score
    created_at: datetime      # When memory was created
    expires_at: datetime?     # When memory expires (if applicable)
    source: str              # Origin of the memory

    # Relationships
    entities: List[Entity]    # Extracted entities
    related_memories: List[Memory]  # Related memories

    # Classification metadata
    confidence: float         # Classification confidence
    patterns_matched: List[str]  # Patterns that matched during classification
```

## Memory Type Characteristics

### Detailed Type Models

#### 1. EPISODIC Memories
```python
class EpisodicMemory(Memory):
    """Personal experiences and temporal events."""

    # Characteristics
    retention_days = 30
    importance_base = 0.7

    # Typical patterns
    patterns = [
        r"yesterday we (decided|chose|agreed)",
        r"last (week|month|sprint) we",
        r"during the (meeting|call|session)"
    ]

    # Example content
    examples = [
        "Yesterday we decided to use FastAPI for the backend",
        "In last week's retrospective we identified performance issues",
        "During the architecture review we chose microservices"
    ]
```

#### 2. SEMANTIC Memories
```python
class SemanticMemory(Memory):
    """Factual information and general knowledge."""

    # Characteristics
    retention_days = None  # Never expires
    importance_base = 1.0

    # Typical patterns
    patterns = [
        r"(my name is|I am|we are)",
        r"(the API|database|system) (is|uses|runs)",
        r"(definition|specification) of"
    ]

    # Example content
    examples = [
        "My name is Alice and I'm the tech lead",
        "The API uses PostgreSQL version 14",
        "The system runs on AWS EC2 instances"
    ]
```

#### 3. PROCEDURAL Memories
```python
class ProceduralMemory(Memory):
    """Instructions and procedural knowledge."""

    # Characteristics
    retention_days = None  # Never expires
    importance_base = 0.9

    # Typical patterns
    patterns = [
        r"to (deploy|build|test|run)",
        r"(steps|process|procedure) (to|for)",
        r"(always|never|should) (use|do|avoid)"
    ]

    # Example content
    examples = [
        "To deploy: run tests, build image, push to registry",
        "Always use type hints in Python functions",
        "The debugging process: check logs, verify config, restart service"
    ]
```

#### 4. WORKING Memories
```python
class WorkingMemory(Memory):
    """Current tasks and immediate focus."""

    # Characteristics
    retention_days = 1  # Very short retention
    importance_base = 0.5

    # Typical patterns
    patterns = [
        r"(need to|have to|must) (review|fix|implement)",
        r"currently (working|debugging|implementing)",
        r"(todo|task|priority):"
    ]

    # Example content
    examples = [
        "Need to review PR #123 before end of day",
        "Currently debugging the authentication service",
        "High priority: fix the payment gateway issue"
    ]
```

#### 5. SENSORY Memories
```python
class SensoryMemory(Memory):
    """Sensory observations and descriptions."""

    # Characteristics
    retention_days = 0.25  # 6 hours
    importance_base = 0.3

    # Typical patterns
    patterns = [
        r"(looks|sounds|feels|seems) (like|too|very)",
        r"(appears|displays|shows) (to be|as)",
        r"(notice|observe|see) that"
    ]

    # Example content
    examples = [
        "The UI looks cluttered on mobile devices",
        "API response time feels slow during peak hours",
        "The loading animation seems to take forever"
    ]
```

#### 6. PREFERENCE Memories
```python
class PreferenceMemory(Memory):
    """User and team preferences."""

    # Characteristics
    retention_days = None  # Never expires
    importance_base = 0.9

    # Typical patterns
    patterns = [
        r"(prefer|like|choose) (to use|using)",
        r"(always|never|usually) (use|do|prefer)",
        r"(team|we) (standard|convention|preference)"
    ]

    # Example content
    examples = [
        "Team prefers TypeScript over JavaScript",
        "I always use async/await instead of callbacks",
        "We prefer composition over inheritance in design"
    ]
```

## Memory Lifecycle

### Creation Pipeline

```python
def create_memory(content: str, source: str = "user") -> Memory:
    """Complete memory creation pipeline."""

    # 1. Content preprocessing
    cleaned_content = preprocess_text(content)

    # 2. NLP classification
    classification = nlp_classifier.classify(cleaned_content)
    memory_type = classification.memory_type
    confidence = classification.confidence

    # 3. Entity extraction
    entities = entity_extractor.extract(cleaned_content)

    # 4. Importance scoring
    importance = calculate_importance(memory_type, entities, content)

    # 5. Expiration calculation
    expires_at = calculate_expiration(memory_type, importance)

    # 6. Memory creation
    memory = Memory(
        content=cleaned_content,
        memory_type=memory_type,
        importance=importance,
        expires_at=expires_at,
        entities=entities,
        source=source,
        metadata={
            'classification_confidence': confidence,
            'patterns_matched': classification.patterns
        }
    )

    # 7. Storage and relationship building
    store_memory(memory)
    build_relationships(memory)

    return memory
```

### Retrieval Pipeline

```python
def retrieve_memories(query: str, memory_types: List[MemoryType] = None) -> List[Memory]:
    """Complete memory retrieval pipeline."""

    # 1. Query preprocessing
    processed_query = preprocess_query(query)
    query_entities = entity_extractor.extract(processed_query)

    # 2. Candidate selection
    candidates = graph_db.find_candidates(
        entities=query_entities,
        memory_types=memory_types,
        exclude_expired=True
    )

    # 3. Relevance scoring
    scored_candidates = []
    for memory in candidates:
        score = calculate_relevance(memory, processed_query, query_entities)
        scored_candidates.append((memory, score))

    # 4. Ranking and filtering
    ranked_memories = rank_by_importance_and_relevance(scored_candidates)

    # 5. Result formatting
    return [memory for memory, score in ranked_memories[:10]]
```

## Memory Relationships

### Relationship Types

1. **Entity-Based Relationships**
   ```cypher
   // Memories sharing entities are related
   MATCH (m1:Memory)-[:CONTAINS]->(e:Entity)<-[:CONTAINS]-(m2:Memory)
   WHERE m1.id <> m2.id
   CREATE (m1)-[:SHARES_ENTITY {entity: e.name}]->(m2)
   ```

2. **Temporal Relationships**
   ```cypher
   // Memories created close in time
   MATCH (m1:Memory), (m2:Memory)
   WHERE abs(duration.between(m1.created_at, m2.created_at).seconds) < 3600
   CREATE (m1)-[:TEMPORAL_PROXIMITY]->(m2)
   ```

3. **Hierarchical Relationships**
   ```cypher
   // Working memories derived from procedural memories
   MATCH (proc:Memory {memory_type: 'PROCEDURAL'}), (work:Memory {memory_type: 'WORKING'})
   WHERE work.content CONTAINS proc.entities[0].name
   CREATE (work)-[:DERIVED_FROM]->(proc)
   ```

### Relationship Scoring

```python
def calculate_relationship_strength(memory1: Memory, memory2: Memory) -> float:
    """Calculate the strength of relationship between two memories."""

    strength = 0.0

    # Entity overlap
    common_entities = set(memory1.entity_names) & set(memory2.entity_names)
    entity_strength = len(common_entities) / max(len(memory1.entities), len(memory2.entities))
    strength += entity_strength * 0.4

    # Type compatibility
    type_compatibility = get_type_compatibility(memory1.memory_type, memory2.memory_type)
    strength += type_compatibility * 0.3

    # Temporal proximity
    time_diff = abs((memory1.created_at - memory2.created_at).total_seconds())
    temporal_strength = max(0, 1 - (time_diff / (7 * 24 * 3600)))  # Decay over 7 days
    strength += temporal_strength * 0.2

    # Content similarity (cosine similarity of embeddings)
    content_similarity = cosine_similarity(memory1.embedding, memory2.embedding)
    strength += content_similarity * 0.1

    return min(1.0, strength)
```

## Performance Optimizations

### Indexing Strategy

```cypher
// Primary indexes
CREATE INDEX memory_type_idx ON :Memory(memory_type);
CREATE INDEX memory_importance_idx ON :Memory(importance);
CREATE INDEX memory_created_at_idx ON :Memory(created_at);
CREATE INDEX entity_name_idx ON :Entity(name);

// Composite indexes for common queries
CREATE INDEX memory_type_importance_idx ON :Memory(memory_type, importance);
CREATE INDEX memory_active_idx ON :Memory(memory_type) WHERE expires_at IS NULL OR expires_at > datetime();
```

### Caching Strategy

```python
class MemoryCache:
    """Multi-level caching for memory operations."""

    def __init__(self):
        # L1: Recently accessed memories
        self.l1_cache = LRUCache(maxsize=100)

        # L2: Frequently accessed entities
        self.l2_entity_cache = LRUCache(maxsize=1000)

        # L3: Query result cache
        self.l3_query_cache = TTLCache(maxsize=500, ttl=300)  # 5 minute TTL

    def get_memory(self, memory_id: str) -> Memory:
        # Check L1 first
        if memory_id in self.l1_cache:
            return self.l1_cache[memory_id]

        # Load from database and cache
        memory = self.db.get_memory(memory_id)
        self.l1_cache[memory_id] = memory
        return memory

    def query_memories(self, query_hash: str) -> List[Memory]:
        # Check L3 query cache
        if query_hash in self.l3_query_cache:
            return self.l3_query_cache[query_hash]

        # Execute query and cache result
        results = self.db.execute_query(query_hash)
        self.l3_query_cache[query_hash] = results
        return results
```

## Memory Evolution and Learning

### Adaptive Importance Scoring

```python
class AdaptiveImportance:
    """Learning system that adjusts importance scores based on usage."""

    def __init__(self):
        self.access_counts = defaultdict(int)
        self.recall_success = defaultdict(float)

    def update_memory_importance(self, memory: Memory, accessed: bool, helpful: bool):
        """Update importance based on usage patterns."""

        self.access_counts[memory.id] += 1

        if helpful:
            self.recall_success[memory.id] = (
                self.recall_success[memory.id] * 0.9 + 1.0 * 0.1
            )
        else:
            self.recall_success[memory.id] *= 0.95

        # Adjust importance
        access_boost = min(0.2, self.access_counts[memory.id] * 0.01)
        success_factor = self.recall_success[memory.id]

        new_importance = memory.importance + access_boost * success_factor
        memory.importance = min(1.0, new_importance)
```

### Pattern Evolution

```python
class PatternLearner:
    """Learns new classification patterns from user corrections."""

    def learn_from_correction(self, content: str, predicted_type: MemoryType,
                             correct_type: MemoryType):
        """Learn new patterns from classification corrections."""

        if predicted_type != correct_type:
            # Extract distinguishing features
            features = self.extract_features(content)

            # Update pattern weights
            self.update_pattern_weights(features, correct_type, positive=True)
            self.update_pattern_weights(features, predicted_type, positive=False)

            # Generate new patterns if needed
            if self.should_create_pattern(content, correct_type):
                new_pattern = self.generate_pattern(content, correct_type)
                self.add_pattern(correct_type, new_pattern)
```

## Integration Patterns

### AI Assistant Integration

```python
class AIIntegration:
    """Memory integration for AI assistants."""

    def enhance_prompt(self, user_prompt: str) -> str:
        """Enhance user prompt with relevant memories."""

        # Get relevant memories
        memories = self.memory_store.recall(user_prompt)

        # Filter by relevance and importance
        relevant_memories = self.filter_memories(memories, min_importance=0.7)

        # Group by type for structured context
        context_by_type = self.group_by_type(relevant_memories)

        # Build enhanced prompt
        enhanced_prompt = self.build_enhanced_prompt(user_prompt, context_by_type)

        return enhanced_prompt

    def learn_from_conversation(self, conversation: str, source: str = "ai-chat"):
        """Extract learnings from AI conversation."""

        # Extract potential memories
        potential_memories = self.extract_learnings(conversation)

        # Create memories asynchronously
        for content in potential_memories:
            self.memory_store.create_memory_async(content, source=source)
```

## Best Practices for Memory Model Usage

### 1. Memory Creation
- **Be specific**: Include relevant context and entities
- **Use appropriate sources**: Track where memories come from
- **Avoid duplicates**: Check for similar existing memories
- **Include metadata**: Add relevant tags and categories

### 2. Memory Retrieval
- **Use type filters**: Specify relevant memory types for better results
- **Combine strategies**: Use both entity matching and semantic similarity
- **Consider temporal context**: Recent memories may be more relevant
- **Respect importance scores**: Higher importance memories should surface first

### 3. Memory Management
- **Regular cleanup**: Remove expired and low-value memories
- **Monitor performance**: Track retrieval times and accuracy
- **Update relationships**: Maintain connection between related memories
- **Backup regularly**: Export memories for disaster recovery

## Summary

The KuzuMemory memory model provides a sophisticated yet practical approach to storing and retrieving contextual information for AI systems. By modeling human cognitive memory systems, it achieves intuitive behavior while maintaining high performance and scalability.

Key benefits:
- **Scientific foundation**: Based on established cognitive psychology research
- **Intuitive classification**: Memory types match human understanding
- **Optimized performance**: Graph database with intelligent indexing and caching
- **Adaptive learning**: System improves over time through usage patterns
- **AI-friendly**: Designed specifically for AI assistant integration

For implementation details, see [MEMORY_TYPES.md](MEMORY_TYPES.md) and [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md).