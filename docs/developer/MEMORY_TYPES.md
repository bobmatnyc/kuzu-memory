# KuzuMemory Cognitive Memory Types

## Overview

KuzuMemory uses a cognitive memory type system based on human memory psychology. This system provides intuitive categorization and appropriate retention policies for different types of memories.

## The Six Cognitive Memory Types

### 1. EPISODIC - Personal Experiences and Events
**Purpose**: Stores memories of specific events, experiences, and temporal occurrences.

**Characteristics**:
- Retention: 30 days (experiences fade over time)
- Importance: 0.7 (medium-high priority)
- Examples: Project decisions, meeting outcomes, deployment events

**Use Cases**:
```python
# Project decisions
"Yesterday we decided to use FastAPI instead of Flask"
"In the last sprint we implemented user authentication"

# Development events
"Fixed the critical bug in payment processing on Sept 15"
"Deployed version 2.1.0 to production last week"

# Team experiences
"Had a productive retrospective meeting"
"Discovered performance bottleneck during load testing"
```

**Pattern Matching**:
- Contains temporal references: "yesterday", "last week", "on Monday"
- Decision language: "we decided", "we chose", "agreed to"
- Event language: "happened", "occurred", "took place"

---

### 2. SEMANTIC - Facts and General Knowledge
**Purpose**: Stores factual information, definitions, and general knowledge that doesn't change.

**Characteristics**:
- Retention: Never expires (facts are permanent)
- Importance: 1.0 (highest priority)
- Examples: Identity information, technical specifications, constants

**Use Cases**:
```python
# Identity facts
"My name is Alice Johnson"
"I work as a Senior Software Engineer"
"Team lead is John Smith"

# Technical specifications
"API rate limit is 1000 requests per minute"
"Database uses PostgreSQL version 14"
"Server runs on AWS EC2 t3.medium instances"

# General knowledge
"Python is an interpreted programming language"
"REST APIs use HTTP methods for operations"
"Git is a distributed version control system"
```

**Pattern Matching**:
- Definitive statements: "is", "are", "equals"
- Identity patterns: "my name is", "I am", "we are"
- Factual language: "the specification says", "according to"

---

### 3. PROCEDURAL - Instructions and How-To Content
**Purpose**: Stores step-by-step instructions, procedures, and methodological knowledge.

**Characteristics**:
- Retention: Never expires (procedures remain relevant)
- Importance: 0.9 (high priority)
- Examples: Deployment steps, coding patterns, troubleshooting guides

**Use Cases**:
```python
# Deployment procedures
"To deploy: 1) Run tests 2) Build image 3) Push to registry 4) Update k8s"
"Release process requires approval from tech lead and product owner"

# Development procedures
"Always write unit tests before implementing features"
"Code review checklist: security, performance, maintainability"

# Troubleshooting steps
"If API returns 500: check logs, verify DB connection, restart service"
"Memory leak debugging: use profiler, check object references"
```

**Pattern Matching**:
- Imperative language: "run", "execute", "perform"
- Sequential indicators: "first", "then", "next", "finally"
- Instructional patterns: "how to", "steps to", "process for"

---

### 4. WORKING - Tasks and Current Focus
**Purpose**: Stores current tasks, immediate priorities, and short-term work items.

**Characteristics**:
- Retention: 1 day (tasks are short-lived)
- Importance: 0.5 (medium priority)
- Examples: TODOs, current issues, immediate priorities

**Use Cases**:
```python
# Current tasks
"Need to review PR #123 before end of day"
"Working on implementing OAuth integration"
"Debugging the failing CI pipeline"

# Immediate priorities
"High priority: fix production issue with user login"
"Today's goal: complete user dashboard wireframes"

# Status updates
"Currently blocked on API key approval"
"Waiting for design feedback on new feature"
"In the middle of refactoring authentication module"
```

**Pattern Matching**:
- Task language: "need to", "working on", "todo"
- Urgency indicators: "urgent", "priority", "asap"
- Status language: "currently", "in progress", "blocked"

---

### 5. SENSORY - Sensory Descriptions
**Purpose**: Stores sensory observations and environmental descriptions.

**Characteristics**:
- Retention: 6 hours (sensory memories fade quickly)
- Importance: 0.3 (low priority)
- Examples: UI feedback, system behavior observations, user experience notes

**Use Cases**:
```python
# User interface observations
"The button appears too small on mobile screens"
"Loading spinner feels slow, takes about 3 seconds"
"Color contrast seems poor in dark mode"

# System behavior
"API response time feels sluggish during peak hours"
"Database queries are noticeably slower after the update"
"Server monitoring dashboard shows intermittent spikes"

# Environmental context
"Office is quite noisy during standup meetings"
"Screen glare makes code review difficult in afternoon"
"New keyboard feels more responsive for coding"
```

**Pattern Matching**:
- Sensory verbs: "feels", "looks", "sounds", "seems"
- Appearance language: "appears", "shows", "displays"
- Experiential language: "notice", "observe", "sense"

---

### 6. PREFERENCE - User/Team Preferences
**Purpose**: Stores preferred approaches, styles, and configuration choices.

**Characteristics**:
- Retention: Never expires (preferences persist)
- Importance: 0.9 (high priority)
- Examples: Coding standards, tool choices, workflow preferences

**Use Cases**:
```python
# Coding preferences
"Team prefers TypeScript over JavaScript"
"Always use async/await instead of callbacks"
"Prefer composition over inheritance in design"

# Tool preferences
"Use VSCode for development environment"
"Prefer Postgres over MySQL for relational data"
"Team standard is Prettier with 2-space indentation"

# Workflow preferences
"Daily standups at 9 AM work best for the team"
"Prefer feature branches over direct commits to main"
"Code reviews should be completed within 24 hours"
```

**Pattern Matching**:
- Preference language: "prefer", "like", "choose"
- Standards language: "always", "should", "standard"
- Choice language: "use", "go with", "opt for"

## Memory Type Classification

### Automatic Classification

The system uses NLP patterns to automatically classify memories:

```python
from kuzu_memory.nlp.classifier import MemoryClassifier

classifier = MemoryClassifier()

# Examples of automatic classification
result = classifier.classify("My name is Alice")
# result.memory_type == MemoryType.SEMANTIC

result = classifier.classify("Yesterday we decided to use React")
# result.memory_type == MemoryType.EPISODIC

result = classifier.classify("To deploy, run npm run build")
# result.memory_type == MemoryType.PROCEDURAL
```

### Manual Classification

You can also specify memory types explicitly:

```python
from kuzu_memory.core.models import Memory, MemoryType

# Explicit type specification
memory = Memory(
    content="Team prefers functional programming",
    memory_type=MemoryType.PREFERENCE,
    entities=["team", "functional programming"],
    importance=0.9
)
```

## Retention Policies

Each memory type has a different retention policy based on its characteristics:

| Type | Retention | Rationale |
|------|-----------|-----------|
| SEMANTIC | Never expires | Facts don't change |
| PROCEDURAL | Never expires | Instructions remain useful |
| PREFERENCE | Never expires | Preferences persist |
| EPISODIC | 30 days | Experiences fade over time |
| WORKING | 1 day | Tasks are short-lived |
| SENSORY | 6 hours | Sensory memories fade quickly |

## Importance Scoring

Memory importance affects recall priority:

- **1.0 (SEMANTIC)**: Critical facts always surface first
- **0.9 (PROCEDURAL, PREFERENCE)**: Important but not critical
- **0.7 (EPISODIC)**: Relevant context, medium priority
- **0.5 (WORKING)**: Current but temporary relevance
- **0.3 (SENSORY)**: Low priority, background context

## Integration with AI Systems

### For AI Assistants

When integrating with AI systems, use memory types to provide appropriate context:

```python
import subprocess

def get_context_by_type(query: str, memory_types: list = None) -> str:
    """Get context filtered by memory types."""
    cmd = ['kuzu-memory', 'recall', query]
    if memory_types:
        cmd.extend(['--types', ','.join(memory_types)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

# Get only factual context
facts = get_context_by_type("database setup", ["SEMANTIC", "PROCEDURAL"])

# Get recent decisions and events
recent_context = get_context_by_type("recent changes", ["EPISODIC", "WORKING"])
```

### For Learning Systems

Store different types of learnings appropriately:

```python
def store_learning(content: str, source: str = "ai-interaction"):
    """Store learning with automatic type classification."""
    subprocess.run([
        'kuzu-memory', 'learn', content,
        '--source', source, '--quiet'
    ], check=False)

# Usage examples
store_learning("User prefers dark mode UI")  # -> PREFERENCE
store_learning("Fixed authentication bug today")  # -> EPISODIC
store_learning("Always validate input parameters")  # -> PROCEDURAL
```

## Best Practices

### Classification Guidelines

1. **Be specific about temporal context**:
   - "Yesterday we decided..." → EPISODIC
   - "We always decide..." → PREFERENCE/PROCEDURAL

2. **Distinguish facts from experiences**:
   - "Alice is the team lead" → SEMANTIC
   - "Alice was promoted last month" → EPISODIC

3. **Separate instructions from preferences**:
   - "Run tests with pytest command" → PROCEDURAL
   - "Team prefers pytest over unittest" → PREFERENCE

### Memory Quality

1. **Include relevant entities**: Help the system find related memories
2. **Use clear, specific language**: Avoid ambiguous references
3. **Provide context when needed**: Include enough information for understanding
4. **Avoid sensitive information**: Never store passwords or secret keys

### Performance Considerations

- **SEMANTIC** and **PROCEDURAL** memories are cached aggressively (never expire)
- **EPISODIC** memories use temporal indexing for efficient retrieval
- **WORKING** memories are optimized for quick access but rapid expiration
- **SENSORY** memories have minimal storage overhead due to short retention

## Migration from Legacy Types

The system automatically converts legacy memory types:

| Legacy Type | Cognitive Type | Auto-Conversion |
|------------|----------------|-----------------|
| IDENTITY   | SEMANTIC      | ✅ Automatic |
| PREFERENCE | PREFERENCE    | ✅ No change |
| DECISION   | EPISODIC      | ✅ Automatic |
| PATTERN    | PROCEDURAL    | ✅ Automatic |
| SOLUTION   | PROCEDURAL    | ✅ Automatic |
| STATUS     | WORKING       | ✅ Automatic |
| CONTEXT    | EPISODIC      | ✅ Automatic |

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration instructions.

## Testing Memory Types

```bash
# Test classification accuracy
pytest tests/test_memory_classification.py -v

# Test retention policies
pytest tests/test_memory_retention.py -v

# Test type-specific recall
pytest tests/test_type_recall.py -v

# Performance test by type
pytest tests/test_type_performance.py -v
```

## Troubleshooting

### Common Issues

1. **Incorrect Classification**:
   - Review patterns in `kuzu_memory/nlp/patterns/`
   - Use explicit type specification for edge cases
   - Report classification errors for pattern improvement

2. **Unexpected Retention**:
   - Check memory type: some types never expire
   - Verify configuration: retention can be overridden
   - Use `kuzu-memory stats --detailed` to check retention settings

3. **Poor Recall Performance**:
   - Ensure proper entity extraction for better matching
   - Use multiple memory types in queries for broader results
   - Check importance scoring for priority issues

### Debugging

```bash
# Check memory type distribution
kuzu-memory stats --by-type

# List memories by type
kuzu-memory list --type SEMANTIC --format json

# Debug classification
kuzu-memory classify "your text here" --debug
```

## Future Enhancements

- **Dynamic importance scoring** based on usage patterns
- **Cross-type relationship modeling** for enhanced recall
- **Adaptive retention policies** based on memory access frequency
- **Multi-modal memory types** for handling different content types