"""
Auggie/Claude Installer for KuzuMemory

Sets up Augment rules and integration files for seamless Auggie integration.
"""

import logging

from .base import BaseInstaller, InstallationError, InstallationResult

logger = logging.getLogger(__name__)


class AuggieInstaller(BaseInstaller):
    """
    Installer for Auggie/Claude AI system integration.

    Sets up Augment rules that automatically integrate KuzuMemory
    with Auggie conversations.
    """

    @property
    def ai_system_name(self) -> str:
        return "Auggie/Claude"

    @property
    def required_files(self) -> list[str]:
        return [
            "AGENTS.md",
            ".augment/rules/kuzu-memory-integration.md",
            ".augment/rules/memory-quick-reference.md",
        ]

    @property
    def description(self) -> str:
        return (
            "Sets up Augment rules for automatic KuzuMemory integration. "
            "Enables context enhancement and learning from conversations."
        )

    def check_prerequisites(self) -> list[str]:
        """Check Auggie-specific prerequisites."""
        errors = super().check_prerequisites()

        # Check if KuzuMemory is initialized
        kuzu_dir = self.project_root / "kuzu-memories"
        if not kuzu_dir.exists():
            errors.append("KuzuMemory not initialized. Run 'kuzu-memory init' first.")

        return errors

    def install(self, force: bool = False, **kwargs) -> InstallationResult:
        """
        Install Auggie integration.

        Args:
            force: Force installation even if files exist
            **kwargs: Additional options (unused for Auggie)

        Returns:
            InstallationResult with installation details
        """
        try:
            # Check prerequisites
            errors = self.check_prerequisites()
            if errors:
                raise InstallationError(f"Prerequisites not met: {'; '.join(errors)}")

            # Check if already installed and not forcing
            if not force:
                existing_files = []
                for file_pattern in self.required_files:
                    file_path = self.project_root / file_pattern
                    if file_path.exists():
                        existing_files.append(str(file_path))

                if existing_files:
                    raise InstallationError(
                        f"Auggie integration already exists. Use --force to overwrite. "
                        f"Existing files: {', '.join(existing_files)}"
                    )

            # Install main AGENTS.md file
            self._install_agents_md()

            # Install detailed integration rules
            self._install_integration_rules()

            # Install quick reference
            self._install_quick_reference()

            # Create installation result
            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message="Successfully installed Auggie integration with KuzuMemory",
                warnings=self.warnings,
            )

        except Exception as e:
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=f"Installation failed: {e}",
                warnings=self.warnings,
            )

    def _install_agents_md(self):
        """Install the main AGENTS.md file."""
        agents_content = """# KuzuMemory Project Guidelines

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
"""

        agents_path = self.project_root / "AGENTS.md"
        if not self.write_file(agents_path, agents_content):
            raise InstallationError("Failed to create AGENTS.md")

    def _install_integration_rules(self):
        """Install detailed integration rules."""
        integration_content = """# KuzuMemory Integration Rules

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
kuzu-memory memory enhance "[user's question]" --format plain
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
kuzu-memory memory learn "[extracted information]" --source ai-conversation --quiet
```

**IMPORTANT: Learning is async by default and won't block AI responses!**

## Specific Integration Examples

### Example 1: API Development Question

**User**: "How do I create a REST endpoint?"

**Step 1**: Run `kuzu-memory memory enhance "How do I create a REST endpoint?" --format plain`

**Step 2**: If enhanced prompt includes FastAPI context, respond with FastAPI-specific guidance

**Step 3**: If user adds "We're using async handlers", store: `kuzu-memory memory learn "Project uses async handlers for API endpoints" --quiet`

### Example 2: Database Question

**User**: "What's the best database for this project?"

**Step 1**: Run `kuzu-memory memory enhance "What's the best database for this project?" --format plain`

**Step 2**: If enhanced prompt shows existing database choice, recommend consistency

**Step 3**: If user says "We decided on PostgreSQL", store: `kuzu-memory memory learn "Project uses PostgreSQL as the database" --quiet`

### Example 3: Testing Question

**User**: "How should I write tests?"

**Step 1**: Run `kuzu-memory memory enhance "How should I write tests?" --format plain`

**Step 2**: If enhanced prompt includes pytest context, provide pytest-specific advice

**Step 3**: If user mentions testing preferences, store them

## Command Reference

### Enhancement Commands
```bash
# Basic enhancement
kuzu-memory memory enhance "user question" --format plain

# Check what context would be added
kuzu-memory memory enhance "user question" --format json

# Limit context size
kuzu-memory memory enhance "user question" --max-memories 3 --format plain
```

### Storage Commands
```bash
# Store general information (async by default)
kuzu-memory memory learn "information to store" --quiet

# Store with specific source
kuzu-memory memory learn "user preference" --source user-preference --quiet

# Store with metadata
kuzu-memory memory learn "technical decision" --metadata '{"type":"architecture"}' --quiet
```

### Monitoring Commands
```bash
# Check recent memories
kuzu-memory memory recent --format list

# Search for specific information
kuzu-memory memory recall "database setup"

# View project status
kuzu-memory status
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
"""

        rules_dir = self.project_root / ".augment" / "rules"
        rules_path = rules_dir / "kuzu-memory-integration.md"
        if not self.write_file(rules_path, integration_content):
            raise InstallationError("Failed to create integration rules")

    def _install_quick_reference(self):
        """Install quick reference guide."""
        reference_content = """# KuzuMemory Quick Reference

## Two-Step Integration

### Step 1: Enhance Questions (Before Responding)
```bash
kuzu-memory memory enhance "[user's question]" --format plain
```
**Use the enhanced output as your actual prompt.**

### Step 2: Store Information (After User Provides Context - ASYNC BY DEFAULT)
```bash
kuzu-memory memory learn "[information to store]" --source ai-conversation --quiet
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
kuzu-memory memory enhance "How do I build an API endpoint?" --format plain
# Use enhanced output for response
```

### For Project Information
```bash
# User: "We're using PostgreSQL for the database"
kuzu-memory memory learn "Project uses PostgreSQL for the database" --source ai-conversation --quiet
```

### For User Preferences
```bash
# User: "I prefer async/await over callbacks"
kuzu-memory memory learn "User prefers async/await over callbacks" --source user-preference --quiet
```

### For Team Conventions
```bash
# User: "Our team always uses pytest for testing"
kuzu-memory memory learn "Team convention: use pytest for all testing" --source team-convention --quiet
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
"""

        rules_dir = self.project_root / ".augment" / "rules"
        reference_path = rules_dir / "memory-quick-reference.md"
        if not self.write_file(reference_path, reference_content):
            raise InstallationError("Failed to create quick reference")
