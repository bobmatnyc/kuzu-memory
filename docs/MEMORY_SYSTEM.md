# Memory System Guide

**Complete guide to KuzuMemory's cognitive memory types and usage patterns**

> **Replaces**: This document consolidates and replaces:
> - `docs/MEMORY_GUIDE.md`
> - `docs/memory-system.md`

---

## 🧠 Memory System Overview

KuzuMemory uses a cognitive memory model inspired by human memory psychology. The system stores different types of information with varying retention policies and recall strategies, optimized for AI-enhanced development workflows.

### Core Concepts

- **Memory Types**: Six cognitive categories (SEMANTIC, PROCEDURAL, PREFERENCE, EPISODIC, WORKING, SENSORY)
- **Retention Policies**: Automatic expiration based on memory type
- **Graph Storage**: Kuzu embedded graph database for relationship modeling
- **Fast Recall**: Sub-100ms memory retrieval with intelligent caching
- **Project-Scoped**: Memories isolated per project for team collaboration

---

## 🎯 Memory Types (Standardized)

All memory types are standardized across Python and TypeScript implementations:

### SEMANTIC (Never Expires)
**Purpose**: Facts, specifications, identity information

**Use for**:
- Project identity and description
- Technical specifications
- System requirements
- Factual knowledge
- Team member information

**Examples**:
```bash
kuzu-memory memory store "This project is KuzuMemory, an AI memory system"
kuzu-memory memory store "KuzuMemory uses Python 3.11+ and Kuzu database"
kuzu-memory memory store "Alice works at TechCorp as Python developer"
```

**Storage**:
```python
memory.learn("This is a FastAPI-based microservice architecture")
# Automatically classified as SEMANTIC
```

### PROCEDURAL (Never Expires)
**Purpose**: Instructions, processes, patterns, how-to knowledge

**Use for**:
- Development workflows
- Best practices
- Code patterns
- Process documentation
- Implementation guidelines

**Examples**:
```bash
kuzu-memory memory store "Always use type hints in Python code"
kuzu-memory memory store "Run make test before committing code"
kuzu-memory memory store "Follow PEP 8 style guide for Python"
```

**Storage**:
```python
memory.learn("Use async/await patterns for all I/O operations")
# Automatically classified as PROCEDURAL
```

### PREFERENCE (Never Expires)
**Purpose**: Team/user preferences, conventions, style choices

**Use for**:
- Coding style preferences
- Tool choices
- Framework preferences
- Design decisions
- Personal preferences

**Examples**:
```bash
kuzu-memory memory store "Team prefers pytest over unittest"
kuzu-memory memory store "Use FastAPI instead of Flask for APIs"
kuzu-memory memory store "Prefer composition over inheritance"
```

**Storage**:
```python
memory.learn("User prefers dark mode for all interfaces")
# Automatically classified as PREFERENCE
```

### EPISODIC (30 days)
**Purpose**: Project decisions, events, experiences, temporal context

**Use for**:
- Project milestones
- Technical decisions
- Meeting outcomes
- Problem resolutions
- Change history

**Examples**:
```bash
kuzu-memory memory store "Decided to use Kuzu database for graph storage"
kuzu-memory memory store "Resolved performance issue by adding connection pooling"
kuzu-memory memory store "Migration to Python 3.11 completed on 2024-03-15"
```

**Storage**:
```python
memory.learn("Decided to migrate from REST to GraphQL for API")
# Automatically classified as EPISODIC
```

### WORKING (1 day)
**Purpose**: Current tasks, immediate priorities, active work

**Use for**:
- Today's tasks
- Current focus areas
- Active bugs
- Immediate todos
- Session context

**Examples**:
```bash
kuzu-memory memory store "Currently debugging the async learning system"
kuzu-memory memory store "Working on MCP server integration feature"
kuzu-memory memory store "Need to fix test failures in CI pipeline"
```

**Storage**:
```python
memory.learn("Currently implementing authentication system")
# Automatically classified as WORKING
```

### SENSORY (6 hours)
**Purpose**: UI/UX observations, system behavior, immediate feedback

**Use for**:
- UI observations
- Performance feedback
- System behavior notes
- Immediate impressions
- Transient observations

**Examples**:
```bash
kuzu-memory memory store "The CLI response feels slow during testing"
kuzu-memory memory store "UI button placement seems awkward on mobile"
kuzu-memory memory store "Database query taking longer than expected"
```

**Storage**:
```python
memory.learn("Page load time is noticeably slow on dashboard")
# Automatically classified as SENSORY
```

---

## 🔄 Memory Lifecycle

### Creation

```bash
# Explicit creation
kuzu-memory memory store "content" --type SEMANTIC

# Automatic classification
kuzu-memory learn "content"  # AI determines type
```

### Retrieval

```bash
# Query-based recall
kuzu-memory memory recall "what are my preferences?"

# Type-filtered recall
kuzu-memory memory recall "decisions" --type EPISODIC

# Recent memories
kuzu-memory recent --limit 10
```

### Expiration

Memory types expire automatically:

| Type | Retention | Use Case |
|------|-----------|----------|
| SEMANTIC | Never | Permanent facts |
| PROCEDURAL | Never | Timeless processes |
| PREFERENCE | Never | Lasting preferences |
| EPISODIC | 30 days | Recent decisions |
| WORKING | 1 day | Today's tasks |
| SENSORY | 6 hours | Immediate feedback |

### Cleanup

```bash
# Manual cleanup of expired memories
kuzu-memory cleanup

# Force cleanup (remove all expired)
kuzu-memory cleanup --force

# Preview cleanup without deletion
kuzu-memory cleanup --dry-run
```

---

## 🎯 Best Practices

### Memory Type Selection

**✅ DO**:
- Use SEMANTIC for facts that define the project
- Use PROCEDURAL for repeatable processes
- Use PREFERENCE for style and tool choices
- Use EPISODIC for time-bound decisions
- Use WORKING for current session context
- Use SENSORY for immediate observations

**❌ DON'T**:
- Don't store secrets in any memory type
- Don't mix temporal context in permanent memories
- Don't duplicate information across types
- Don't store overly verbose content

### Memory Content Quality

**Good Examples**:
```bash
✅ "Project uses PostgreSQL 13+ with connection pooling"
✅ "Always validate input with Pydantic models"
✅ "Team prefers pytest over unittest framework"
✅ "Decided to implement rate limiting with Redis"
```

**Bad Examples**:
```bash
❌ "stuff"  # Too vague
❌ "The database is... um... PostgreSQL maybe?"  # Uncertain
❌ "We should probably use Redis for caching or something"  # Indefinite
❌ "password=super_secret_123"  # Contains secrets
```

### Integration Patterns

#### Pattern 1: Pre-Process Prompts
```python
def ai_conversation(user_input):
    # Enhance with project context
    enhanced_input = enhance_with_memory(user_input)

    # Generate AI response
    response = ai_model.generate(enhanced_input)

    # Store the interaction
    store_learning(f"Q: {user_input} A: {response}")

    return response
```

#### Pattern 2: Post-Process Learning
```python
def handle_user_correction(original_response, user_feedback):
    # Store the correction
    store_learning(f"Correction: {user_feedback}", source='correction')

    # Generate improved response
    correction_context = f"Previous response was incorrect: {original_response}. User correction: {user_feedback}"
    enhanced_prompt = enhance_with_memory(correction_context)

    return ai_model.generate(enhanced_prompt)
```

#### Pattern 3: Context-Aware Responses
```python
def get_contextual_response(user_query):
    # Get recent project context
    recent_context = get_recent_context()

    # Build context-aware prompt
    context_summary = "\n".join([m['content'] for m in recent_context[:5]])
    full_prompt = f"Project Context:\n{context_summary}\n\nUser Query: {user_query}"

    return ai_model.generate(full_prompt)
```

---

## 📊 Project Memory Structure

### File Organization

```
your-project/
├── kuzu-memories/              # Memory database (git-committed)
│   ├── memories.db             # Main memory storage
│   ├── config.yaml             # Memory configuration
│   └── .gitkeep                # Ensures directory is tracked
├── .claude-mpm/                # Claude MPM integration
│   └── memories/
│       ├── PM.md               # Project management memory
│       ├── engineer.md         # Engineering patterns
│       └── qa.md               # QA strategies
└── CLAUDE.md                   # Project context for Claude
```

### Git Integration

**Commit to Repository**:
- ✅ `kuzu-memories/memories.db` (project knowledge)
- ✅ `kuzu-memories/config.yaml` (memory settings)
- ✅ `.claude-mpm/memories/` (specialized agent memories)
- ✅ `CLAUDE.md` (project instructions)

**Gitignore**:
- ❌ Temporary session data
- ❌ User-specific preferences
- ❌ Cache files

---

## 🔧 Configuration

### Memory Configuration (config.yaml)

```yaml
version: 1.0
project:
  name: "Your Project"
  description: "Project description"

storage:
  # Memory types to store
  memory_types:
    - SEMANTIC      # Facts and specifications
    - PROCEDURAL    # Processes and patterns
    - PREFERENCE    # Team preferences
    - EPISODIC      # Decisions and events
    # - WORKING     # Exclude ephemeral tasks
    # - SENSORY     # Exclude transient observations

  # Retention policies
  retention:
    SEMANTIC: -1        # Never expire
    PROCEDURAL: -1      # Never expire
    PREFERENCE: -1      # Never expire
    EPISODIC: 30        # 30 days
    WORKING: 1          # 1 day
    SENSORY: 0.25       # 6 hours

  # Size management
  max_size_mb: 50       # Warn if database exceeds this
  auto_compact: true    # Auto-compact on cleanup
```

### Memory Behavior Settings

```json
{
  "performance": {
    "max_recall_time_ms": 100,
    "max_generation_time_ms": 200
  },
  "memory": {
    "max_memories_per_project": 10000,
    "enable_auto_cleanup": true
  },
  "learning": {
    "min_content_length": 50,
    "excluded_patterns": ["password", "secret", "key", "token"]
  }
}
```

---

## 🚀 Advanced Memory Usage

### Specialized Agent Memories (.claude-mpm)

The `.claude-mpm/memories/` directory contains role-specific memory files:

#### PM.md - Project Management Memory
- **Purpose**: High-level project overview and coordination
- **Contains**: Architecture overview, key technologies, development standards
- **Use when**: Need project context, standards, or coordination information
- **Target agents**: Project managers, coordinators, documentation specialists

#### engineer.md - Engineering Implementation Patterns
- **Purpose**: Deep technical implementation knowledge
- **Contains**: Code patterns, architecture details, performance optimizations
- **Use when**: Implementing features, debugging, optimizing performance
- **Target agents**: Software engineers, architects, performance specialists

#### qa.md - Quality Assurance Testing Strategies
- **Purpose**: Testing approaches and quality standards
- **Contains**: Test patterns, performance targets, validation strategies
- **Use when**: Writing tests, validating functionality, ensuring quality
- **Target agents**: QA engineers, test automation specialists

### Cross-Role Memory Usage

```
🏗️  Project Management Tasks → PM.md
    • Project overview questions
    • Standards and conventions
    • Architecture decisions
    • Team coordination

💻 Engineering Tasks → engineer.md
    • Code implementation
    • Performance optimization
    • Architecture patterns
    • Technical debugging

🧪 Quality Assurance Tasks → qa.md
    • Test implementation
    • Performance validation
    • Quality standards
    • Testing strategies
```

### Memory Combination Strategies

For complex tasks, use multiple memories:

```
Feature Development Workflow:
1. PM.md → Understand requirements and standards
2. engineer.md → Learn implementation patterns
3. qa.md → Plan testing strategy
4. Implement with full context

Performance Optimization Workflow:
1. PM.md → Check performance targets
2. engineer.md → Review optimization patterns
3. qa.md → Understand benchmark requirements
4. Optimize with measurable goals
```

---

## 📊 Memory System Statistics

### View Statistics

```bash
# Basic stats
kuzu-memory status

# Detailed statistics
kuzu-memory status --detailed

# JSON output
kuzu-memory status --format json
```

### Statistics Include

- Total memories stored
- Memories by type
- Database size
- Recent activity
- Performance metrics
- Expiration schedule

### Example Output

```json
{
  "total_memories": 247,
  "by_type": {
    "SEMANTIC": 89,
    "PROCEDURAL": 56,
    "PREFERENCE": 34,
    "EPISODIC": 45,
    "WORKING": 18,
    "SENSORY": 5
  },
  "database_size_mb": 2.3,
  "last_cleanup": "2024-03-15T10:30:00Z",
  "performance": {
    "avg_recall_ms": 12,
    "avg_generation_ms": 45
  }
}
```

---

## 🔍 Troubleshooting

### Memory Not Being Recalled

**Check if memory exists**:
```bash
kuzu-memory recent --limit 50
kuzu-memory memory recall "exact search term"
```

**Verify memory type**:
```bash
# May have expired if WORKING or SENSORY
kuzu-memory status
```

**Check configuration**:
```bash
# Ensure memory type is enabled
cat kuzu-memories/config.yaml
```

### Database Size Growing Too Large

```bash
# Check size
du -h kuzu-memories/memories.db

# Compact database
kuzu-memory compact --remove-old --vacuum

# Archive old memories
kuzu-memory archive --older-than 180d --output archive.jsonl.gz
```

### Memory Quality Issues

**Improve memory extraction**:
- Use complete sentences
- Include specific details
- Avoid vague language
- Provide context

**Review stored memories**:
```bash
kuzu-memory recent --format json | jq '.[] | select(.confidence < 0.5)'
```

---

## 🎯 Memory Effectiveness Metrics

### Success Indicators

- ✅ Agents can quickly find relevant information
- ✅ Implementation follows established patterns
- ✅ Code quality meets documented standards
- ✅ Performance targets are consistently met
- ✅ Testing strategies are properly applied

### Warning Signs

- ❌ Agents asking for information that's in memory files
- ❌ Inconsistent implementation patterns
- ❌ Performance regressions
- ❌ Test coverage gaps
- ❌ Standards violations

---

## 🤝 Team Collaboration

### Sharing Project Memories

```bash
# Commit memories to git
git add kuzu-memories/ CLAUDE.md .claude-mpm/
git commit -m "Update project memories and patterns"
git push
```

### New Team Member Setup

```bash
# After cloning
git pull
kuzu-memory init  # Database already exists from git

# Memories are immediately available!
kuzu-memory status
kuzu-memory recent
```

### Handling Memory Conflicts

If multiple team members add memories simultaneously:

```bash
# The database is binary, so conflicts need special handling
# Option 1: Accept theirs (recommended for minor conflicts)
git checkout --theirs kuzu-memories/memories.db
git add kuzu-memories/memories.db
git commit -m "Resolved memory database conflict"

# Option 2: Merge both (for important memories)
kuzu-memory merge --theirs kuzu-memories/memories.db --mine kuzu-memories/memories.db.backup
```

---

## 🎓 Learning Resources

### Memory System Examples

```bash
# Example 1: Implementing New CLI Command
1. Check PM.md for CLI standards and patterns
2. Review engineer.md for Click framework usage
3. Implement following established patterns
4. Use qa.md to create appropriate tests
5. Update engineer.md with any new patterns

# Example 2: Performance Optimization
1. PM.md → Check performance targets (<100ms recall)
2. engineer.md → Review optimization techniques
3. Implement optimizations using documented patterns
4. qa.md → Create benchmark tests
5. Validate against documented performance targets

# Example 3: AI Integration Development
1. PM.md → Understand subprocess-based integration pattern
2. engineer.md → Review AIMemoryIntegration class patterns
3. Implement following universal integration pattern
4. qa.md → Test integration scenarios
5. Update memories with new integration patterns
```

---

## 📚 Related Documentation

- [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start guide
- [CLAUDE_SETUP.md](CLAUDE_SETUP.md) - Claude integration
- [AI_INTEGRATION.md](AI_INTEGRATION.md) - AI system integration patterns
- [DEVELOPER.md](DEVELOPER.md) - Developer documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture

---

**🧠 This memory system enables consistent, high-quality development by providing specialized, role-based knowledge that guides AI agents toward optimal solutions.**
