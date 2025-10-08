# KuzuMemory Project Guidelines

This project uses KuzuMemory for intelligent project memory and context management. All AI assistants should integrate with the memory system for enhanced, project-specific responses.

## Memory Integration Rules

### Before Responding to User Queries

**ALWAYS enhance user prompts with project context using KuzuMemory:**

1. For technical questions, implementation queries, or project-specific questions, run:
   ```bash
   kuzu-memory memory enhance "[user's question]" --format plain
   ```

2. Use the enhanced prompt (which includes relevant project context) instead of the original user question

3. If the enhanced prompt is significantly longer than the original, it means relevant project context was found and should be used

### After Providing Responses

**ALWAYS store interesting information for future context (ASYNC BY DEFAULT - NON-BLOCKING):**

1. If the user provides project information, decisions, preferences, or corrections, run:
   ```bash
   kuzu-memory memory learn "[information to store]" --source ai-conversation --quiet
   ```

2. Store information like:
   - User preferences: "User prefers TypeScript over JavaScript"
   - Project decisions: "We decided to use PostgreSQL as the database"
   - Team conventions: "Our team uses pytest for all testing"
   - Architecture choices: "This project uses microservices architecture"
   - User corrections: "Actually, we use Redis for caching, not Memcached"

**IMPORTANT: Learning operations are ASYNC BY DEFAULT and will not block your response to the user. No special flags needed - async is the default behavior.**

### What to Store

Store information when users mention:
- **Preferences**: "I prefer...", "I like...", "I always use..."
- **Decisions**: "We decided...", "We chose...", "Our approach is..."
- **Technologies**: "This project uses...", "We're using...", "Our stack includes..."
- **Conventions**: "Our team convention...", "We always...", "The standard is..."
- **Corrections**: "Actually...", "That's not right...", "Let me clarify..."
- **Requirements**: "We need...", "It must...", "The requirement is..."

### What to Enhance

Enhance prompts for:
- **Technical questions**: "How do I...", "What's the best way...", "How should I..."
- **Implementation queries**: "How to implement...", "How to build...", "How to structure..."
- **Project-specific questions**: Questions about "this project", "our system", "the codebase"
- **Decision-making**: "Should we...", "Which is better...", "What do you recommend..."
- **Architecture questions**: Questions about databases, frameworks, patterns, deployment

### Example Integration Flow

**User asks**: "How should I structure an API endpoint?"

**Step 1 - Enhance (SYNC)**: Run `kuzu-memory memory enhance "How should I structure an API endpoint?" --format plain`
- This is **synchronous** and fast (<100ms) - needed for immediate response

**Step 2 - Respond**: Use the enhanced prompt (which might include context like "This project uses FastAPI with PostgreSQL") to provide a project-specific answer

**Step 3 - Learn (ASYNC BY DEFAULT)**: If the user provides additional context in their response, store it with `kuzu-memory memory learn`
- This is **asynchronous by default** and non-blocking - happens in background

## Project Context Commands

### Check Project Memory Status
```bash
kuzu-memory status
kuzu-memory memory recent
```

### Manual Memory Operations
```bash
# Store project information
kuzu-memory memory store "Project uses FastAPI with PostgreSQL and Redis"

# Search for specific information
kuzu-memory memory recall "What database do we use?"

# View recent memories
kuzu-memory memory recent --format list
```

## Integration Guidelines

### Performance Requirements
- **Enhancement operations**: Must be fast (<100ms) - these are synchronous and block AI response
- **Learning operations**: Can be slower (up to 200ms) - these are asynchronous by default and don't block
- Always use `--quiet` flag when storing to avoid cluttering output
- Use `--format plain` for enhancements to get clean output
- Learning is async by default - no special flags needed

### Error Handling
- If KuzuMemory commands fail, continue with the original prompt
- **Enhancement failures**: Fall back to original prompt, don't block response
- **Learning failures**: Log but don't affect user experience - learning is optional
- Memory integration should enhance, not hinder, the user experience

### Async vs Sync Operations
- **SYNC (blocking)**: `kuzu-memory memory enhance` - needed immediately for AI response
- **ASYNC (non-blocking, DEFAULT)**: `kuzu-memory memory learn` - happens in background by default
- **Rule**: Never let learning block the AI response to the user

## Success Metrics

The memory integration is working well when:
- AI responses become more project-specific over time
- Users don't need to repeat project context
- Team members get consistent AI responses
- Project knowledge is preserved and reused
- New team members get instant project context

Remember: The goal is seamless, invisible integration that makes AI responses more helpful and project-aware without adding complexity for users.
