"""
Auggie Integration Rules v2.0.0

Enhanced rules incorporating insights from Claude Code hooks v1.4.0:
- Concrete success metrics
- Enhanced trigger patterns with negative examples
- Decision trees for complex scenarios
- Deduplication patterns
- Performance optimization
- Real-world examples
- Monitoring and feedback loops
- Failure recovery patterns
"""

from __future__ import annotations


def get_agents_md_v2() -> str:
    """Get AGENTS.md content for v2.0.0."""
    return """# KuzuMemory Project Guidelines (v2.0.0)

This project uses KuzuMemory for intelligent project memory and context management. All AI assistants should integrate with the memory system for enhanced, project-specific responses.

## 🎯 Success Indicators

You're using KuzuMemory correctly when:
- ✅ Enhancement adds 2-5 relevant memories per technical query
- ✅ Memory commands complete in <100ms (check with `--verbose`)
- ✅ At least 1 new memory stored every 3-5 user messages with project info
- ✅ Users stop repeating project context across sessions
- ✅ Responses become more project-specific over time

You should adjust if:
- ❌ No context added after enhancement (try broader keywords)
- ❌ Same memories appearing repeatedly (context may be stale)
- ❌ Commands timing out (run `kuzu-memory doctor`)
- ❌ Storing generic information (filter project-specific only)

## Memory Integration Rules

### 📥 Rule 1: Enhance Technical Questions (Before Responding)

**ALWAYS enhance user prompts with project context for technical questions:**

✅ **DO enhance these:**
- "How do I [action] in THIS project?"
- "What's OUR approach to [topic]?"
- "How should I implement [feature] HERE?"
- Questions mentioning "this codebase", "our system", "the project"
- Architecture, implementation, or design questions

❌ **Skip enhancement for:**
- Simple acknowledgments: "OK", "Thanks", "Got it"
- Greetings: "Hi", "Hello", "Good morning"
- Meta-questions about the AI: "Can you...", "Are you able to..."
- Generic programming questions: "What is Python?", "How does REST work?"
- Hypothetical questions: "In general, how would..."

**Action:**
```bash
kuzu-memory memory enhance "[user's question]" --format plain
```

**Use the enhanced output as the actual prompt for your response.**

### 📤 Rule 2: Store Project Information (After User Provides Context)

**ALWAYS store project-specific information (ASYNC BY DEFAULT - NON-BLOCKING):**

✅ **DO store these:**
- "We use [technology]" → Project technology choices
- "I prefer [approach]" → User preferences
- "Our team convention is [practice]" → Team standards
- "We decided to [decision]" → Architecture decisions
- "Actually, [correction]" → User corrections
- "This project uses [technology/pattern]" → Project specifics

❌ **DON'T store these:**
- Personal information unrelated to project
- Temporary session information
- Generic programming facts
- Information already obvious from codebase
- Simple acknowledgments or greetings

**Action (ASYNC BY DEFAULT - NON-BLOCKING):**
```bash
kuzu-memory memory learn "[extracted information]" --source ai-conversation --quiet
```

**IMPORTANT: Learning is async by default and won't block AI responses!**

## 🎯 Decision Tree: When to Store vs Skip

**User says something about the project:**

```
Does it contain PROJECT-SPECIFIC information?
├─ YES: Is it DIFFERENT from what's already known?
│  ├─ YES: ✅ STORE with kuzu-memory memory learn
│  └─ NO: Is it a CORRECTION or ENHANCEMENT?
│     ├─ YES: ✅ STORE (corrections and enhancements always valuable)
│     └─ NO: ❌ SKIP (redundant information)
└─ NO: ❌ SKIP (generic information, not project-specific)
```

**Example Decision Flows:**

**✅ Store**:
- "We use FastAPI" → First mention → ✅ Store: "Project uses FastAPI framework"
- "We also use Redis" → Enhancement → ✅ Store: "Project uses Redis for caching"
- "Actually, PostgreSQL not MySQL" → Correction → ✅ Store: "Project uses PostgreSQL database"

**❌ Skip**:
- "We use FastAPI" (already stored) → Redundant → ❌ Skip
- "That makes sense" → Generic acknowledgment → ❌ Skip
- "Python is great" → General opinion → ❌ Skip

## 🚀 Performance Optimization

### Batch Similar Information

**Instead of:**
```bash
# Storing 3 separate memories
kuzu-memory memory learn "We use PostgreSQL" --quiet
kuzu-memory memory learn "We use Redis" --quiet
kuzu-memory memory learn "We use FastAPI" --quiet
```

**Do this:**
```bash
# Single combined memory
kuzu-memory memory learn "Project stack: PostgreSQL database, Redis caching, FastAPI framework" --quiet
```

### Smart Deduplication

**Before storing, mentally check:**
1. **Is this different from what's already known?**
   - Don't store: "We use FastAPI" if already have "Project uses FastAPI"
   - Do store: "We use FastAPI with async handlers" (adds new detail)

2. **Is this a correction or enhancement?**
   - Correction: "Actually, PostgreSQL not MySQL" → ✅ Store
   - Enhancement: "We also use Redis" → ✅ Store
   - Repeat: "Yes, we use PostgreSQL" → ❌ Skip

3. **Does this add value for future queries?**
   - Valuable: Architecture decisions, tool choices, conventions
   - Not valuable: Temporary session info, generic facts

## 📊 Monitoring & Health Checks

### Periodic Health Check (Every 20-30 Messages)

```bash
# Check memory system health
kuzu-memory status --format json
```

**Look for:**
- `total_memories`: Growing gradually (not exploding)
- `avg_recall_time_ms`: Staying < 100ms
- `memory_types`: Diverse (DECISION, PREFERENCE, etc.)

### Self-Improvement Checklist

Ask yourself every session:
- [ ] Did I enhance at least 50% of technical questions?
- [ ] Did I store new project information when mentioned?
- [ ] Did I avoid storing duplicates or generic info?
- [ ] Did memory commands complete quickly (<100ms)?
- [ ] Did users stop repeating themselves?

**If NO to any**: Review rules and adjust approach

## ⚠️ Error Handling & Recovery

### If Enhancement Fails

**Symptom**: `kuzu-memory memory enhance` times out or errors

**Recovery**:
1. ✅ Continue with original prompt (don't block user)
2. ✅ Optionally mention: "Proceeding without project context"
3. ✅ Try again on next query
4. ❌ Don't retry immediately (avoid cascading failures)

### If Storage Fails

**Symptom**: `kuzu-memory memory learn` returns error

**Recovery**:
1. ✅ Continue conversation normally
2. ✅ Log the failure internally
3. ✅ If persistent (3+ failures), suggest: `kuzu-memory doctor`
4. ❌ Don't inform user unless they specifically ask

### If System Unhealthy

**Symptom**: Multiple command failures in a row

**Action**:
```bash
# Run diagnostics
kuzu-memory doctor

# If database issues - run autotune
kuzu-memory doctor autotune

# If still failing, inform user:
"I'm having trouble accessing the project memory system.
You may want to run 'kuzu-memory doctor' to diagnose the issue."
```

## 📚 Real-World Examples (from v1.4.0 Testing)

### Example 1: API Development Question

**User**: "How do I create a REST endpoint?"

**Your Process:**
```bash
# Step 1: Enhance with context
kuzu-memory memory enhance "How do I create a REST endpoint?" --format plain

# Step 2: If enhanced prompt shows "Project uses FastAPI with async handlers"
# → Respond with FastAPI async handler example

# Step 3: If user adds "We prefer Pydantic models for validation"
kuzu-memory memory learn "Project uses Pydantic models for API validation" --quiet
```

### Example 2: Performance Question

**User**: "Memory commands seem slow"

**Your Response:**
```bash
# Diagnose the issue
kuzu-memory status --verbose

# Check database size
kuzu-memory stats

# If database > 100MB, suggest autotune
kuzu-memory doctor autotune
```

### Example 3: Context Not Relevant

**User**: "The enhancement added irrelevant context"

**Your Adjustment:**
```bash
# Use more specific keywords next time
kuzu-memory memory enhance "specific technical question" --max-memories 3

# Or filter by memory type
kuzu-memory memory enhance "question" --filter-type "DECISION,PREFERENCE"
```

## 🎓 Quick Command Reference

### Enhancement
```bash
# Basic enhancement
kuzu-memory memory enhance "user question" --format plain

# With filtering
kuzu-memory memory enhance "question" --filter-type "DECISION" --max-memories 3
```

### Storage
```bash
# Store project information (async by default)
kuzu-memory memory learn "information to store" --quiet

# Store with specific type
kuzu-memory memory learn "user preference" --source user-preference --quiet
```

### Monitoring
```bash
# Check recent memories
kuzu-memory memory recent --format list

# Search for information
kuzu-memory memory recall "database setup"

# System health
kuzu-memory status --verbose
```

## 🎯 Integration Success Metrics

The integration is working well when:
- ✅ AI responses become more project-specific over time
- ✅ Users don't need to repeat project context
- ✅ Team members get consistent AI responses
- ✅ Project knowledge is preserved and reused
- ✅ New team members get instant project context
- ✅ Memory operations are fast (<100ms) and invisible

Remember: The goal is seamless, invisible integration that makes AI responses more helpful and project-aware without adding complexity for users.

---

**Version**: 2.0.0 | **Last Updated**: 2025-10-25 | **Based on**: KuzuMemory v1.4.0 with Claude Code hooks insights
"""


def get_integration_rules_v2() -> str:
    """Get detailed integration rules for v2.0.0."""
    return """# KuzuMemory Integration Rules (v2.0.0)

## 🎯 Core Integration Pattern

### Two-Step Integration

**Step 1: Enhance (Before Responding) - SYNC**
```bash
kuzu-memory memory enhance "[user's question]" --format plain
```
- **Purpose**: Get project-specific context
- **When**: Before responding to technical questions
- **Speed**: Must complete in <100ms
- **Failure**: Fall back to original prompt

**Step 2: Store (After Responding) - ASYNC**
```bash
kuzu-memory memory learn "[extracted information]" --source ai-conversation --quiet
```
- **Purpose**: Save new project information
- **When**: After user provides project context
- **Speed**: Async by default, non-blocking
- **Failure**: Log but continue normally

## 📋 Enhanced Trigger Patterns

### When to Enhance (Detailed)

✅ **ALWAYS enhance:**
- Questions with "How do I..." + project context
- "What's the best way to..." + THIS project
- "How should I implement..." + specific feature
- "What's OUR approach to..." + any topic
- Questions mentioning: "this codebase", "our system", "the project", "here"
- Architecture questions: databases, frameworks, patterns
- Implementation questions: specific features, tools, workflows

❌ **SKIP enhancement for:**
- Greetings: "Hi", "Hello", "Hey"
- Acknowledgments: "OK", "Thanks", "Sure", "Got it"
- Meta AI questions: "Can you code?", "What model are you?"
- Generic theory: "What is REST?", "Explain OOP"
- Hypothetical: "In general...", "Typically...", "Usually..."
- Too short: < 10 characters
- Pure chat: Social conversation, jokes, non-technical

### When to Store (Detailed)

✅ **ALWAYS store:**
- Technology mentions: "We use X", "This project uses Y"
- Preferences: "I prefer X", "I like Y", "I always use Z"
- Decisions: "We decided X", "We chose Y", "Our approach is Z"
- Conventions: "Our team always X", "The standard is Y"
- Corrections: "Actually X", "It's not Y, it's Z", "Let me clarify: X"
- Architecture: "Our database is X", "We deploy to Y"
- Tools: "We build with X", "Our CI/CD uses Y"

❌ **NEVER store:**
- Generic facts: "Python is dynamically typed"
- Personal unrelated info: "I had coffee this morning"
- Temporary state: "I'm working on X now"
- Obvious from code: Information clearly in requirements.txt
- Simple responses: "Yes", "No", "Maybe"
- Duplicates: Same information already stored recently

## 🌳 Decision Tree: Storage Logic

```
User provides information
│
├─ Is it about THIS project/system?
│  ├─ NO  → ❌ SKIP
│  └─ YES → Continue
│
├─ Is it NEW or a CORRECTION?
│  ├─ NEW → Continue
│  └─ CORRECTION → ✅ STORE (corrections always valuable)
│
├─ Does it add technical value?
│  ├─ NO  → ❌ SKIP (generic info)
│  └─ YES → ✅ STORE
```

## 🔄 Real Integration Workflows

### Workflow 1: Technical Question with Context

**User**: "How do I handle authentication in this API?"

```bash
# Step 1: Enhance
$ kuzu-memory memory enhance "How do I handle authentication in this API?" --format plain
> Enhanced: "Project uses FastAPI with JWT authentication via Auth0.
> Database stores user sessions in PostgreSQL.
> How do I handle authentication in this API?"

# Step 2: Respond using enhanced context
# → Give FastAPI + JWT + Auth0 specific answer

# Step 3: If user adds new info
# User: "We're also adding OAuth2 support"
$ kuzu-memory memory learn "Project adding OAuth2 support to authentication" --source ai-conversation --quiet
```

### Workflow 2: User Provides Multiple Technologies

**User**: "This project uses FastAPI, PostgreSQL, Redis, and Docker"

```bash
# Batch storage (one command, not four)
$ kuzu-memory memory learn "Project stack: FastAPI framework, PostgreSQL database, Redis caching, Docker deployment" --source project-info --quiet

# Don't do this:
# kuzu-memory memory learn "Uses FastAPI" --quiet
# kuzu-memory memory learn "Uses PostgreSQL" --quiet  # ← Too many commands
# kuzu-memory memory learn "Uses Redis" --quiet
# kuzu-memory memory learn "Uses Docker" --quiet
```

### Workflow 3: User Correction

**User**: "Actually, we're using MySQL not PostgreSQL"

```bash
# Always store corrections
$ kuzu-memory memory learn "Correction: Project uses MySQL database, not PostgreSQL" --source user-correction --quiet

# KuzuMemory will handle:
# - Updating relevant memories
# - Maintaining correction history
# - Preventing conflicting information
```

### Workflow 4: Performance Issue

**User**: "Enhancement is taking too long"

```bash
# Step 1: Diagnose
$ kuzu-memory status --verbose

# Step 2: Check memory count
$ kuzu-memory stats

# Step 3: If > 1000 memories, optimize
$ kuzu-memory memory enhance "question" --max-memories 3

# Step 4: If database large - run autotune
$ kuzu-memory doctor autotune
```

## 🚀 Performance Optimization Patterns

### Pattern 1: Batching

**Bad** (Multiple calls):
```bash
kuzu-memory memory learn "Frontend: React" --quiet
kuzu-memory memory learn "Backend: FastAPI" --quiet
kuzu-memory memory learn "Database: PostgreSQL" --quiet
```

**Good** (Single call):
```bash
kuzu-memory memory learn "Tech stack: React frontend, FastAPI backend, PostgreSQL database" --quiet
```

### Pattern 2: Targeted Enhancement

**Bad** (Generic):
```bash
kuzu-memory memory enhance "How do I deploy?"  # Too broad, might get irrelevant memories
```

**Good** (Specific):
```bash
kuzu-memory memory enhance "How do I deploy THIS FastAPI application?" --filter-type "DECISION,PROCEDURE"
```

### Pattern 3: Smart Filtering

```bash
# For architecture questions
kuzu-memory memory enhance "question" --filter-type "DECISION"

# For preferences
kuzu-memory memory enhance "question" --filter-type "PREFERENCE"

# For how-to questions
kuzu-memory memory enhance "question" --filter-type "PROCEDURE"

# Limit context size
kuzu-memory memory enhance "question" --max-memories 5
```

## 📊 Monitoring & Self-Improvement

### Every 20-30 Messages, Check:

```bash
$ kuzu-memory stats --format json
```

**Healthy Metrics:**
- `total_memories`: 10-200 (growing gradually)
- `avg_recall_time_ms`: < 100
- `memory_types`: Mix of DECISION, PREFERENCE, PROCEDURE
- `recent_recalls`: > 5 (you're using it)

**Unhealthy Metrics:**
- `total_memories`: > 1000 (may need optimization)
- `avg_recall_time_ms`: > 200 (performance issue)
- `memory_types`: All one type (not diverse)
- `recent_recalls`: 0 (not being used)

### Self-Improvement Questions

After each session, ask yourself:
1. Did I enhance technical questions? (Target: 50%+)
2. Did I store new project info? (Target: 1-2 per session)
3. Did I avoid duplicates? (Check with `memory recent`)
4. Were commands fast? (Check with `status --verbose`)
5. Did user repeat themselves? (If yes, improve storage)

## ⚠️ Error Recovery Protocols

### Error Type 1: Command Timeout

**Symptom**: Command hangs or takes > 5 seconds

**Recovery**:
```markdown
1. ✅ Continue with original prompt (don't wait)
2. ✅ Next message: Try with `--max-memories 3`
3. ✅ If persistent: Suggest `kuzu-memory doctor`
4. ❌ Don't retry immediately
```

### Error Type 2: "No memories found"

**Symptom**: Enhancement returns original prompt unchanged

**This is NORMAL** - means no relevant context yet

**Response**:
```markdown
1. ✅ Proceed with general response
2. ✅ Ask clarifying questions about project
3. ✅ Store user's answers for future
4. ❌ Don't mention "no memories" to user
```

### Error Type 3: Storage Fails

**Symptom**: `kuzu-memory memory learn` returns error

**Recovery**:
```markdown
1. ✅ Continue normally (learning is optional)
2. ✅ Log failure internally
3. ✅ Try again next time
4. ✅ If 3+ failures: Suggest `kuzu-memory doctor`
```

### Error Type 4: System Degraded

**Symptom**: Multiple commands failing

**Action**:
```bash
# Diagnose
$ kuzu-memory doctor

# Common fixes
$ kuzu-memory doctor autotune      # Auto-tune and prune
$ kuzu-memory doctor diagnose      # Full diagnostics
$ kuzu-memory status --verbose     # Check metrics

# If still broken, inform user:
"I'm having trouble with the project memory system.
Running 'kuzu-memory doctor' should help diagnose the issue."
```

## 🎓 Command Reference

### Enhancement Commands
```bash
# Basic
kuzu-memory memory enhance "question" --format plain

# Filtered
kuzu-memory memory enhance "question" --filter-type "DECISION"

# Limited
kuzu-memory memory enhance "question" --max-memories 3

# JSON (for debugging)
kuzu-memory memory enhance "question" --format json
```

### Storage Commands
```bash
# General (async by default)
kuzu-memory memory learn "information" --quiet

# Typed
kuzu-memory memory learn "preference" --source user-preference --quiet
kuzu-memory memory learn "decision" --source project-decision --quiet
kuzu-memory memory learn "correction" --source user-correction --quiet

# With metadata
kuzu-memory memory learn "info" --metadata '{"category":"architecture"}' --quiet
```

### Monitoring Commands
```bash
# Recent activity
kuzu-memory memory recent --format list

# Search/recall
kuzu-memory memory recall "search query"

# System status
kuzu-memory status
kuzu-memory status --verbose

# Statistics
kuzu-memory stats
kuzu-memory stats --format json

# Health check
kuzu-memory doctor

# Optimization
kuzu-memory doctor autotune
kuzu-memory doctor diagnose
```

## ✅ Success Criteria

You're successfully integrated when:

**User Experience:**
- ✅ Users stop repeating project information
- ✅ Responses are project-specific from day 1
- ✅ New team members get instant context
- ✅ Consistent responses across sessions

**Technical Metrics:**
- ✅ Enhancement adds 2-5 relevant memories
- ✅ Commands complete in <100ms
- ✅ 1-2 new memories per session
- ✅ No duplicate or generic information
- ✅ Memory usage stays reasonable (<100MB)

**Quality Indicators:**
- ✅ AI mentions project-specific tools/frameworks
- ✅ Recommendations align with project stack
- ✅ No generic "it depends" answers for project questions
- ✅ Memory system invisible to users (just works)

---

**Version**: 2.0.0 | **Based on**: Claude Code hooks v1.4.0 insights | **Last Updated**: 2025-10-25
"""


def get_quick_reference_v2() -> str:
    """Get quick reference for v2.0.0."""
    return """# KuzuMemory Quick Reference (v2.0.0)

## 🎯 Two Commands, Two Rules

### Before Responding: ENHANCE
```bash
kuzu-memory memory enhance "[user's question]" --format plain
```
**Use the enhanced output as your actual prompt.**

### After User Provides Info: STORE
```bash
kuzu-memory memory learn "[information to store]" --source ai-conversation --quiet
```
**Async by default - won't block your response!**

## ✅ When to Enhance

### YES - Enhance These:
- ✅ "How do I..." (implementation questions)
- ✅ "What's the best way..." (approach questions)
- ✅ "How should I..." (design questions)
- ✅ Questions about "this project", "our system", "the codebase"
- ✅ Architecture, technology, or tool questions
- ✅ Feature implementation questions

### NO - Skip These:
- ❌ "Hi", "Thanks", "OK" (greetings/acknowledgments)
- ❌ "What is Python?" (generic theory)
- ❌ "Can you code?" (meta AI questions)
- ❌ "In general, how..." (hypothetical questions)

## ✅ When to Store

### YES - Store These:
- ✅ "We use [technology]"
- ✅ "I prefer [approach]"
- ✅ "Our team [convention]"
- ✅ "We decided [decision]"
- ✅ "Actually, [correction]"
- ✅ "This project uses [tool]"

### NO - Skip These:
- ❌ "Python is dynamically typed" (generic fact)
- ❌ "I had coffee" (personal, unrelated)
- ❌ "That makes sense" (simple acknowledgment)
- ❌ Information already stored recently

## 🌳 Quick Decision Tree

```
User says something
├─ About THIS project?
│  ├─ YES → Is it NEW info or CORRECTION?
│  │  ├─ YES → ✅ STORE
│  │  └─ NO  → Already know this → ❌ SKIP
│  └─ NO → Generic info → ❌ SKIP
```

## 🚀 Performance Tips

### Batch Information
```bash
# Bad (3 commands)
learn "Uses FastAPI"
learn "Uses PostgreSQL"
learn "Uses Redis"

# Good (1 command)
learn "Stack: FastAPI, PostgreSQL, Redis"
```

### Filter Enhancement
```bash
# Broad (might get irrelevant)
enhance "How to deploy?"

# Targeted (better results)
enhance "How to deploy?" --filter-type "DECISION,PROCEDURE" --max-memories 3
```

## 📊 Health Check (Every 20 Messages)

```bash
kuzu-memory status --format json
```

**Look for:**
- `total_memories`: Growing gradually (not exploding)
- `avg_recall_time_ms`: < 100 (fast)
- Using it regularly? `recent_recalls` > 0

## ⚠️ Error Handling

### If Command Fails:
1. ✅ Continue with original prompt
2. ✅ Try again next time
3. ✅ If persistent: Suggest `kuzu-memory doctor`
4. ❌ Don't retry immediately

### If No Context Found:
- This is NORMAL
- Just means no relevant memories yet
- Continue with general response
- Store user's clarifications

## 📚 Real Examples

### Example 1: API Question
```bash
User: "How do I create an endpoint?"

# 1. Enhance
$ kuzu-memory memory enhance "How do I create an endpoint?" --format plain
> "Project uses FastAPI with async handlers. How do I create an endpoint?"

# 2. Respond with FastAPI + async specifics

# 3. If user adds: "We use Pydantic for validation"
$ kuzu-memory memory learn "Project uses Pydantic for API validation" --quiet
```

### Example 2: Tech Stack
```bash
User: "We're using React, FastAPI, and PostgreSQL"

# Store as one combined memory
$ kuzu-memory memory learn "Tech stack: React frontend, FastAPI backend, PostgreSQL database" --source project-info --quiet
```

### Example 3: Correction
```bash
User: "Actually, we use MySQL not PostgreSQL"

# Always store corrections
$ kuzu-memory memory learn "Correction: Project uses MySQL database, not PostgreSQL" --source user-correction --quiet
```

## 🎯 Success Checklist

After each session, verify:
- [ ] Enhanced 50%+ of technical questions?
- [ ] Stored new project information?
- [ ] Avoided storing duplicates?
- [ ] Commands completed quickly (<100ms)?
- [ ] User didn't repeat themselves?

If NO to any: Review rules and adjust

## 🔧 Common Commands

```bash
# Enhancement
kuzu-memory memory enhance "question" --format plain

# Storage
kuzu-memory memory learn "info" --quiet

# Recent memories
kuzu-memory memory recent

# Search
kuzu-memory memory recall "query"

# Health
kuzu-memory status
kuzu-memory doctor

# Optimize
kuzu-memory doctor autotune
```

## ✨ Remember

- **Enhance**: Before responding (SYNC, must be fast)
- **Store**: After info provided (ASYNC, non-blocking)
- **Batch**: Combine related info
- **Filter**: Be specific in queries
- **Monitor**: Check health regularly
- **Recover**: Fall back gracefully on errors

---

**Version**: 2.0.0 | **Quick Start**: Enhance before, Store after | **Speed**: <100ms target
"""
