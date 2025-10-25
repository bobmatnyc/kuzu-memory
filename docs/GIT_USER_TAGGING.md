# Git Username Tagging for Memories

## Overview

KuzuMemory now automatically tags all memories with the git user identity, enabling:
- **Multi-user namespacing**: Separate memories by developer/user
- **Git commit attribution**: Track which developer created which memory from commits
- **User filtering**: Query memories by specific user
- **Team collaboration**: Support multiple developers working on same project

## Features

### 1. Automatic Git User Detection

KuzuMemory automatically detects the git user on initialization using a priority fallback chain:

1. **git config user.email** (highest priority, globally unique)
2. **git config user.name** (fallback if email not set)
3. **System username** (last resort via `getpass.getuser()`)

```python
from kuzu_memory import KuzuMemory

# Auto-detects git user on initialization
memory = KuzuMemory()
print(f"Using user: {memory.get_current_user_id()}")
# Output: Using user: john@example.com
```

### 2. All Memories Auto-Tagged

Every memory created is automatically tagged with `user_id`:

```python
from kuzu_memory import KuzuMemory

memory = KuzuMemory()

# Generate memories - auto-tagged with current git user
memory.generate_memories("User preference: Python for backend")

# Remember - also auto-tagged
memory.remember("Dark mode preferred")

# All memories now have user_id field populated
```

### 3. Git Commits Tagged with Author

Git sync automatically tags commits with the committer's email:

```python
from kuzu_memory import KuzuMemory

memory = KuzuMemory()

# Git commits are synced with author/committer email as user_id
# Priority: commit.committer.email > commit.author.email
```

Each git commit memory includes:
- `user_id`: Committer's email (who actually committed)
- `metadata.commit_author`: Original author information
- `metadata.commit_committer`: Committer information

### 4. User Filtering

Query memories by specific user:

```python
from kuzu_memory import KuzuMemory

memory = KuzuMemory()

# Get all memories from specific user
user_memories = memory.get_memories_by_user("john@example.com", limit=100)

# Get list of all users who created memories
all_users = memory.get_users()
print(f"Users: {all_users}")
# Output: Users: ['john@example.com', 'jane@example.com']

# Check current user
current_user = memory.get_current_user_id()
print(f"Current user: {current_user}")
```

## Configuration

### Enable/Disable Auto-Tagging

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig.default()

# Disable auto-tagging (user_id will be None for new memories)
config.memory.auto_tag_git_user = False

memory = KuzuMemory(config=config)
```

### Manual User ID Override

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig.default()

# Force specific user_id (overrides git detection)
config.memory.user_id_override = "custom@example.com"

memory = KuzuMemory(config=config)
print(memory.get_current_user_id())
# Output: custom@example.com
```

### Multi-User Features

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig.default()

# Enable multi-user features (default: True)
config.memory.enable_multi_user = True

memory = KuzuMemory(config=config)

# Statistics will include user breakdown
stats = memory.get_statistics()
print(stats["user_stats"])
# Output: {'total_users': 2, 'users': ['john@example.com', 'jane@example.com'], 'current_user': 'john@example.com'}
```

### YAML Configuration

```yaml
# config.yaml
memory:
  auto_tag_git_user: true  # Auto-detect from git
  user_id_override: null   # Manual override (null = auto-detect)
  enable_multi_user: true  # Enable multi-user features

git_sync:
  enabled: true
  # Git commits will be tagged with author/committer email
```

## Implementation Details

### GitUserProvider

The `GitUserProvider` utility handles git user detection:

```python
from kuzu_memory.utils.git_user import GitUserProvider

# Get complete user information
user_info = GitUserProvider.get_git_user_info()
print(user_info.user_id)    # Primary identifier
print(user_info.email)      # Git email (if available)
print(user_info.name)       # Git name (if available)
print(user_info.source)     # Detection source: git_email, git_name, system_user

# Get just the user ID
user_id = GitUserProvider.get_git_user_id()

# Check if git is available
if GitUserProvider.is_git_available():
    print("Git user configured")

# Clear cache (useful for testing)
GitUserProvider.clear_cache()
```

### Memory Model

The `Memory` model includes `user_id` field:

```python
from kuzu_memory.core.models import Memory, MemoryType

memory = Memory(
    content="User preference: Dark mode",
    memory_type=MemoryType.PREFERENCE,
    user_id="john@example.com",  # Auto-populated by KuzuMemory
    metadata={
        "git_user_info": {
            "user_id": "john@example.com",
            "email": "john@example.com",
            "name": "John Doe",
            "source": "git_email"
        }
    }
)
```

### Storage Layer

MemoryStore provides user filtering queries:

```python
from kuzu_memory.storage.memory_store import MemoryStore

# Get memories by user (with caching)
memories = store.get_memories_by_user("john@example.com", limit=50)

# Get all unique users
users = store.get_users()
```

Queries use Cypher with user_id filtering:

```cypher
MATCH (m:Memory)
WHERE m.user_id = $user_id
  AND (m.valid_to IS NULL OR m.valid_to > $now)
RETURN m
ORDER BY m.created_at DESC
LIMIT $limit
```

## Migration Notes

### Backward Compatibility

- **Existing memories**: Continue to work with `user_id = None`
- **New memories**: Auto-tagged with current git user
- **No schema changes**: `user_id` field already existed in Memory model
- **Optional feature**: Can be disabled with `auto_tag_git_user = false`

### Migration Steps

1. **Update KuzuMemory**: Pull latest version with git user tagging
2. **Verify git config**: Ensure `git config user.email` is set
3. **Test auto-detection**: Check `memory.get_current_user_id()`
4. **Re-tag old memories** (optional):

```python
from kuzu_memory import KuzuMemory

memory = KuzuMemory()

# Get all memories without user_id
recent = memory.get_recent_memories(limit=1000)
untagged = [m for m in recent if m.user_id is None]

# Re-tag with current user (if desired)
current_user = memory.get_current_user_id()
for mem in untagged:
    mem.user_id = current_user
    # Would need update method to persist (not implemented yet)
```

## Multi-User Roadmap

### Current State (v1.3.4)
- ✅ All memories tagged with current git user
- ✅ Git commits tagged with author/committer
- ✅ User filtering queries available
- ✅ Statistics include user breakdown
- ✅ Backward compatible (existing memories work)

### Future Enhancements (v1.4.0+)

1. **User-scoped recall**: Filter attach_memories by user
   ```python
   # Future API
   context = memory.attach_memories(
       prompt="What are my preferences?",
       user_id="john@example.com"  # Only recall john's memories
   )
   ```

2. **Shared vs Personal memories**: Tag memories as team-shared or user-private
   ```python
   # Future API
   memory.remember(
       "Team convention: Use black for formatting",
       shared=True  # Visible to all users
   )
   ```

3. **User permissions**: Control who can read/write memories
   ```python
   # Future API
   memory.set_permissions(
       memory_id="abc123",
       read_users=["john@example.com", "jane@example.com"],
       write_users=["john@example.com"]
   )
   ```

4. **A/B testing support**: Explicitly document A/B tests
   ```python
   # Future API
   memory.create_ab_test(
       name="dark_mode_preference",
       variants=["light", "dark"],
       user_id="john@example.com"
   )
   ```

## Best Practices

### 1. Configure Git Email
Always set git email for best results:
```bash
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```

### 2. Team Projects
For team projects, ensure each developer has their git email configured:
```bash
# Each developer should have unique email
git config user.email "developer@company.com"
```

### 3. CI/CD Environments
In CI/CD, you may want to override with bot user:
```python
config = KuzuMemoryConfig.default()
config.memory.user_id_override = "ci-bot@company.com"
memory = KuzuMemory(config=config)
```

### 4. User Filtering
When querying by user, use consistent identifiers:
```python
# Good: Use email for consistency
user_memories = memory.get_memories_by_user("john@example.com")

# Avoid: Mixing email and name
user_memories = memory.get_memories_by_user("John Doe")  # May not match
```

### 5. Statistics Monitoring
Monitor user statistics to track team memory usage:
```python
stats = memory.get_statistics()
user_stats = stats.get("user_stats", {})
print(f"Active users: {user_stats['total_users']}")
print(f"Users: {user_stats['users']}")
```

## Troubleshooting

### User ID is None
**Cause**: Git not configured or detection failed
**Solution**:
```bash
# Set git email
git config user.email "you@example.com"

# Or use manual override
config.memory.user_id_override = "fallback@example.com"
```

### Multiple User IDs for Same Person
**Cause**: Inconsistent git config across machines
**Solution**: Use same email everywhere
```bash
# Check current config
git config --global user.email

# Set consistently across all machines
git config --global user.email "canonical@example.com"
```

### Git Commits Not Tagged
**Cause**: GitPython not installed or git sync disabled
**Solution**:
```bash
# Install GitPython
pip install gitpython

# Enable git sync
config.git_sync.enabled = true
```

### System Username Fallback
**Cause**: Git not installed or not configured
**Solution**: Install git and configure user:
```bash
# Install git
brew install git  # macOS
apt-get install git  # Ubuntu

# Configure
git config --global user.email "you@example.com"
```

## Testing

Run comprehensive test suite:
```bash
pytest tests/test_git_user.py -v
```

Tests cover:
- Git user detection (email, name, system fallback)
- KuzuMemory integration (auto-tagging, override, disable)
- Memory generation and remember()
- Git sync author tagging
- User filtering queries
- Statistics with user breakdown

## API Reference

### KuzuMemory Methods

```python
# Get current user ID
user_id: str | None = memory.get_current_user_id()

# Get all users
users: list[str] = memory.get_users()

# Get memories by user
memories: list[Memory] = memory.get_memories_by_user(
    user_id="john@example.com",
    limit=100
)

# Statistics with user info
stats: dict = memory.get_statistics()
# Returns: {..., "user_stats": {"total_users": N, "users": [...], "current_user": "..."}}
```

### GitUserProvider Methods

```python
from kuzu_memory.utils.git_user import GitUserProvider

# Get complete user info
user_info: GitUserInfo = GitUserProvider.get_git_user_info(project_root=None)

# Get just user ID
user_id: str = GitUserProvider.get_git_user_id(project_root=None)

# Check availability
is_available: bool = GitUserProvider.is_git_available(project_root=None)

# Clear cache
GitUserProvider.clear_cache()
```

### Configuration Options

```python
from kuzu_memory import KuzuMemoryConfig

config = KuzuMemoryConfig.default()

# Memory user configuration
config.memory.auto_tag_git_user = True      # Auto-detect from git
config.memory.user_id_override = None       # Manual override
config.memory.enable_multi_user = True      # Multi-user features
```

## Examples

### Example 1: Team Project with Multiple Developers

```python
from kuzu_memory import KuzuMemory

# Each developer's KuzuMemory auto-detects their git user
memory = KuzuMemory()

# Developer A (alice@company.com) generates memories
memory.generate_memories("Prefer async/await for I/O operations")

# Developer B (bob@company.com) on different machine
# Their memories are tagged with bob@company.com

# List all developers
developers = memory.get_users()
print(f"Team: {developers}")
# Output: Team: ['alice@company.com', 'bob@company.com']

# Get Alice's preferences
alice_prefs = memory.get_memories_by_user("alice@company.com")
```

### Example 2: CI/CD Bot Memories

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig.default()
config.memory.user_id_override = "ci-bot@company.com"

memory = KuzuMemory(config=config)

# CI bot generates deployment memories
memory.remember("Deployed v1.2.3 to production")

# Later, filter bot memories
bot_memories = memory.get_memories_by_user("ci-bot@company.com")
```

### Example 3: Git Commit Attribution

```python
from kuzu_memory import KuzuMemory

memory = KuzuMemory()

# Git commits from different authors are tagged
# Commits by alice@company.com have user_id="alice@company.com"
# Commits by bob@company.com have user_id="bob@company.com"

# Get all of Alice's commits
alice_commits = memory.get_memories_by_user(
    "alice@company.com",
    limit=100
)

# Filter by source to get only git commits
git_commits = [m for m in alice_commits if m.source_type == "git_sync"]
```

## Security Considerations

### 1. Email Privacy
- Git emails are stored in memories
- Consider using work emails vs personal emails
- Use `.gitignore` to exclude sensitive memory databases

### 2. Multi-User Access
- Current implementation: no access control (all users see all memories)
- Future: implement permissions (read/write access control)
- Consider separate databases for strict isolation

### 3. User Enumeration
- `get_users()` exposes all user IDs in database
- Future: add configuration to hide user list
- Consider privacy implications for shared projects

## Performance

### Caching
- Git user detection is cached (only runs once per KuzuMemory instance)
- User filtering queries are cached (TTL: 300s by default)
- User list is cached (invalidated on new memory creation)

### Query Performance
- User filtering uses indexed `user_id` field
- O(log n) query time with database indexes
- Batch operations support user filtering

### Memory Overhead
- Minimal: adds one string field per memory (~20 bytes for email)
- Cached user list: ~20 bytes per user
- Git user info cache: ~100 bytes total

## Conclusion

Git username tagging enables KuzuMemory to support multi-developer teams while maintaining backward compatibility. The automatic detection and fallback chain ensures reliable user identification across different environments.

Key benefits:
- ✅ **Zero configuration**: Auto-detects from git
- ✅ **Backward compatible**: Existing memories continue working
- ✅ **Team-ready**: Supports multiple developers
- ✅ **Flexible**: Can override or disable as needed
- ✅ **Git integration**: Commits tagged with author

For questions or issues, see [TROUBLESHOOTING](#troubleshooting) or open a GitHub issue.
