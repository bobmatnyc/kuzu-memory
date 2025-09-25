# KuzuMemory Quick Reference

## Two-Step Integration

### Step 1: Enhance Questions (Before Responding)
```bash
kuzu-memory enhance "[user's question]" --format plain
```
**Use the enhanced output as your actual prompt.**

### Step 2: Store Information (After User Provides Context - ASYNC BY DEFAULT)
```bash
kuzu-memory learn "[information to store]" --source ai-conversation --quiet
```
**Note: Learning is async by default and won't block your response!**

## When to Enhance

✅ **DO enhance these:**
- "How do I..." questions
- "What's the best way..." questions  
- "How should I..." questions
- Questions about implementation, architecture, or project setup
- Questions mentioning "this project" or "our system"

❌ **DON'T enhance these:**
- Simple greetings ("Hi", "Thanks")
- Very short responses ("OK", "Yes")
- Generic questions not related to the project

## When to Store

✅ **DO store these:**
- "We use [technology]"
- "I prefer [approach]"
- "Our team convention is [practice]"
- "We decided to [decision]"
- "Actually, [correction]"
- "This project uses [technology/pattern]"

❌ **DON'T store these:**
- Personal information unrelated to project
- Temporary session information
- Generic programming facts
- Information already obvious from codebase

## Command Templates

### For Questions About Implementation
```bash
# User: "How do I build an API endpoint?"
kuzu-memory enhance "How do I build an API endpoint?" --format plain
# Use enhanced output for response
```

### For Project Information
```bash
# User: "We're using PostgreSQL for the database"
kuzu-memory learn "Project uses PostgreSQL for the database" --source ai-conversation --quiet
```

### For User Preferences
```bash
# User: "I prefer async/await over callbacks"
kuzu-memory learn "User prefers async/await over callbacks" --source user-preference --quiet
```

### For Team Conventions
```bash
# User: "Our team always uses pytest for testing"
kuzu-memory learn "Team convention: use pytest for all testing" --source team-convention --quiet
```

## Error Handling

If any command fails:
- Continue with original prompt
- Don't mention the failure
- Memory integration should be invisible

## Performance

- Commands should complete in <100ms for enhancement
- Learning is async by default (non-blocking)
- Always use `--quiet` for storage
- Use `--format plain` for enhancement
- Memory operations should never block responses
