# KuzuMemory Integration Rules

## Automatic Memory Enhancement

### Rule: Enhance Technical Questions

When users ask technical questions, ALWAYS enhance them with project context:

**Trigger patterns:**
- "How do I..." 
- "What's the best way to..."
- "How should I..."
- "How to implement..."
- "How to build..."
- "How to structure..."

**Action:**
```bash
kuzu-memory enhance "[user's question]" --format plain
```

**Use the enhanced output as the actual prompt for your response.**

### Rule: Store Project Information

When users provide project information, ALWAYS store it:

**Trigger patterns:**
- "We use..." / "We decided..." / "We chose..."
- "I prefer..." / "I like..." / "I always..."
- "Our team..." / "Our convention..." / "Our approach..."
- "This project..." / "The codebase..." / "Our system..."
- "Actually..." / "Correction..." / "Let me clarify..."

**Action (ASYNC BY DEFAULT - NON-BLOCKING):**
```bash
kuzu-memory learn "[extracted information]" --source ai-conversation --quiet
```

**IMPORTANT: Learning is async by default and won't block AI responses!**

## Specific Integration Examples

### Example 1: API Development Question

**User**: "How do I create a REST endpoint?"

**Step 1**: Run `kuzu-memory enhance "How do I create a REST endpoint?" --format plain`

**Step 2**: If enhanced prompt includes FastAPI context, respond with FastAPI-specific guidance

**Step 3**: If user adds "We're using async handlers", store: `kuzu-memory learn "Project uses async handlers for API endpoints" --quiet`

### Example 2: Database Question

**User**: "What's the best database for this project?"

**Step 1**: Run `kuzu-memory enhance "What's the best database for this project?" --format plain`

**Step 2**: If enhanced prompt shows existing database choice, recommend consistency

**Step 3**: If user says "We decided on PostgreSQL", store: `kuzu-memory learn "Project uses PostgreSQL as the database" --quiet`

### Example 3: Testing Question

**User**: "How should I write tests?"

**Step 1**: Run `kuzu-memory enhance "How should I write tests?" --format plain`

**Step 2**: If enhanced prompt includes pytest context, provide pytest-specific advice

**Step 3**: If user mentions testing preferences, store them

## Command Reference

### Enhancement Commands
```bash
# Basic enhancement
kuzu-memory enhance "user question" --format plain

# Check what context would be added
kuzu-memory enhance "user question" --format json

# Limit context size
kuzu-memory enhance "user question" --max-memories 3 --format plain
```

### Storage Commands
```bash
# Store general information (async by default)
kuzu-memory learn "information to store" --quiet

# Store with specific source
kuzu-memory learn "user preference" --source user-preference --quiet

# Store with metadata
kuzu-memory learn "technical decision" --metadata '{"type":"architecture"}' --quiet
```

### Monitoring Commands
```bash
# Check recent memories
kuzu-memory recent --format list

# Search for specific information
kuzu-memory recall "database setup"

# View project status
kuzu-memory project
```

## Error Handling

### If Commands Fail
- Continue with original user prompt
- Don't mention the failure to the user
- Memory integration should be invisible

### If No Context Found
- Enhancement returns original prompt unchanged
- This is normal and expected
- Proceed with standard response

### If Storage Fails
- Continue normally
- Information just won't be remembered for next time
- User experience is not affected

## Performance Guidelines

### Speed Requirements
- Enhancement should complete in <100ms
- Storage is async by default (non-blocking)
- Never block user response on memory operations

### Resource Usage
- Use `--quiet` flag for storage to avoid output
- Use `--format plain` for enhancement to minimize processing
- Limit context with `--max-memories` if needed

## Success Indicators

The integration is working well when:
- ✅ AI responses become more project-specific over time
- ✅ Users don't need to repeat project context
- ✅ Consistent responses across different conversation sessions
- ✅ New team members get instant project context
- ✅ Memory operations are fast and invisible to users
