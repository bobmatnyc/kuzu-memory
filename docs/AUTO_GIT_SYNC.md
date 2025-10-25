# Automatic Git Commit Indexing

KuzuMemory now supports automatic git commit message indexing, making project context available without manual intervention.

## Overview

The automatic git sync feature indexes significant git commits as EPISODIC memories, providing relevant commit history when you need project context. This happens automatically based on configurable triggers and intervals.

## Configuration

Auto-sync is configured in `GitSyncConfig` with the following options:

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig()
config.git_sync.auto_sync_enabled = True           # Master switch (default: True)
config.git_sync.auto_sync_on_enhance = True        # Sync when attach_memories() called (default: True)
config.git_sync.auto_sync_on_learn = False         # Sync when generate_memories() called (default: False)
config.git_sync.auto_sync_interval_hours = 24      # Minimum hours between syncs (default: 24)
config.git_sync.auto_sync_max_commits = 50         # Max commits per sync (default: 50)

memory = KuzuMemory(config=config)
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `auto_sync_enabled` | `True` | Enable/disable automatic syncing globally |
| `auto_sync_on_enhance` | `True` | Trigger sync when `attach_memories()` is called |
| `auto_sync_on_learn` | `False` | Trigger sync when `generate_memories()` is called |
| `auto_sync_interval_hours` | `24` | Minimum hours between syncs (0 = only trigger-based) |
| `auto_sync_max_commits` | `50` | Maximum commits to sync in one operation |

## How It Works

### Trigger Points

Auto-sync can be triggered at these points:

1. **On Init** (`trigger="init"`): When `KuzuMemory` is initialized
2. **On Enhance** (`trigger="enhance"`): When `attach_memories()` is called (if enabled)
3. **On Learn** (`trigger="learn"`): When `generate_memories()` is called (if enabled)
4. **Periodic** (`trigger="periodic"`): Based on interval configuration

### Sync Behavior

1. **Interval Check**: Before syncing, checks if enough time has elapsed since last sync
2. **Incremental Mode**: After first sync, only indexes new commits
3. **State Persistence**: Tracks last sync time and commit SHA in `.kuzu-memory/git_sync_state.json`
4. **Non-Blocking**: Sync failures don't block main operations
5. **Silent by Default**: Only logs when commits are actually synced

### State File

Auto-sync maintains state in `.kuzu-memory/git_sync_state.json`:

```json
{
  "last_sync": "2024-10-25T15:00:00",
  "last_commit_sha": "abc123def456",
  "commits_synced": 145
}
```

## Usage Examples

### Basic Usage (Default Behavior)

```python
from kuzu_memory import KuzuMemory

# Auto-sync happens automatically during initialization
memory = KuzuMemory()

# Auto-sync checks on enhance (if interval elapsed)
context = memory.attach_memories("How do I deploy?")
# First time: Syncs commits
# Next 24 hours: Skips sync
# After 24 hours: Syncs new commits

# Manual sync still works
from kuzu_memory.integrations.git_sync import GitSyncManager

git_sync = GitSyncManager(
    repo_path=".",
    config=memory.config.git_sync,
    memory_store=memory.memory_store
)
result = git_sync.sync(mode="auto")
print(f"Synced {result['commits_synced']} commits")
```

### Disable Auto-Sync

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig()
config.git_sync.auto_sync_enabled = False  # Disable all auto-sync

memory = KuzuMemory(config=config)
# Auto-sync will never run
```

### Aggressive Sync (Every Operation)

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig()
config.git_sync.auto_sync_on_enhance = True
config.git_sync.auto_sync_on_learn = True
config.git_sync.auto_sync_interval_hours = 0  # Disable interval, always sync

memory = KuzuMemory(config=config)
# Every enhance/learn will trigger sync
```

### Conservative Sync (Daily Only)

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig()
config.git_sync.auto_sync_on_enhance = False  # Don't sync on enhance
config.git_sync.auto_sync_on_learn = False    # Don't sync on learn
config.git_sync.auto_sync_interval_hours = 24  # Only sync once daily on init

memory = KuzuMemory(config=config)
# Sync only happens during initialization, max once per 24 hours
```

### Force Sync (Ignore Interval)

```python
from kuzu_memory import KuzuMemory

memory = KuzuMemory()

# Force sync regardless of interval
if hasattr(memory, 'auto_git_sync') and memory.auto_git_sync:
    result = memory.auto_git_sync.force_sync(verbose=True)
    print(f"Force synced {result.get('commits_synced', 0)} commits")
```

### Check Sync State

```python
from kuzu_memory import KuzuMemory

memory = KuzuMemory()

if hasattr(memory, 'auto_git_sync') and memory.auto_git_sync:
    state = memory.auto_git_sync.get_sync_state()
    print(f"Last sync: {state['last_sync']}")
    print(f"Total commits synced: {state['commits_synced']}")
```

## Performance Impact

Auto-sync is designed to have minimal performance impact:

- **Interval-based**: Default 24-hour interval prevents frequent syncing
- **Incremental**: Only indexes new commits after first sync
- **Limited commits**: Max 50 commits per sync by default
- **Non-blocking**: Sync failures are logged but don't stop operations
- **Background-like**: Runs synchronously but quickly (<100ms typical)

### Performance Targets

- **First sync** (50 commits): <200ms
- **Incremental sync** (5 new commits): <50ms
- **Skip check** (within interval): <1ms

## Architecture

### Components

1. **AutoGitSyncManager** (`auto_git_sync.py`):
   - Manages automatic triggering logic
   - Tracks sync state and intervals
   - Provides force sync functionality

2. **GitSyncManager** (`git_sync.py`):
   - Performs actual commit indexing
   - Filters significant commits
   - Converts commits to memories

3. **KuzuMemory Integration** (`memory.py`):
   - Initializes auto-sync on startup
   - Triggers auto-sync in `attach_memories()` and `generate_memories()`
   - Gracefully handles sync failures

### Integration Points

```
KuzuMemory.__init__()
  └─> _initialize_git_sync()
      ├─> Creates GitSyncManager
      └─> Creates AutoGitSyncManager
          └─> Loads state from .kuzu-memory/git_sync_state.json

KuzuMemory.attach_memories()
  └─> _auto_git_sync("enhance")
      └─> AutoGitSyncManager.auto_sync_if_needed()
          ├─> Checks interval
          └─> Calls GitSyncManager.sync()

KuzuMemory.generate_memories()
  └─> _auto_git_sync("learn")
      └─> AutoGitSyncManager.auto_sync_if_needed()
```

## Testing

Comprehensive tests are provided in `tests/unit/test_auto_git_sync.py`:

```bash
# Run auto-sync tests
pytest tests/unit/test_auto_git_sync.py -v

# Test coverage
pytest tests/unit/test_auto_git_sync.py --cov=kuzu_memory.integrations.auto_git_sync
```

### Test Coverage

- ✅ State persistence and loading
- ✅ Interval-based triggering
- ✅ Trigger-specific configuration
- ✅ Incremental vs. initial sync modes
- ✅ Error handling and recovery
- ✅ Corrupted state file recovery
- ✅ Force sync functionality

## Troubleshooting

### Auto-sync not running

1. Check if git sync is enabled:
   ```python
   print(memory.config.git_sync.enabled)  # Should be True
   print(memory.config.git_sync.auto_sync_enabled)  # Should be True
   ```

2. Check if git is available:
   ```python
   if hasattr(memory, 'auto_git_sync') and memory.auto_git_sync:
       print(memory.auto_git_sync.git_sync.is_available())
   ```

3. Check interval:
   ```python
   state = memory.auto_git_sync.get_sync_state()
   print(f"Last sync: {state['last_sync']}")
   print(f"Interval: {memory.config.git_sync.auto_sync_interval_hours} hours")
   ```

### Clear sync state (force next sync)

```python
import json
from pathlib import Path

state_path = Path.home() / ".kuzu-memory" / "git_sync_state.json"
if state_path.exists():
    state_path.unlink()  # Delete state file
    print("Sync state cleared - next operation will trigger sync")
```

### Disable for testing

```python
from kuzu_memory import KuzuMemory, KuzuMemoryConfig

config = KuzuMemoryConfig()
config.git_sync.enabled = False  # Disable git sync entirely

memory = KuzuMemory(config=config)
```

## Migration Guide

### Upgrading from Manual Sync

If you were using manual `kuzu-memory git sync`:

**Before:**
```bash
# Manual sync required
kuzu-memory git sync
```

**After:**
```python
# Auto-sync handles this automatically
memory = KuzuMemory()
context = memory.attach_memories("query")
# Commits are automatically indexed
```

**Recommendation:**
- Keep manual sync for CI/CD pipelines
- Use auto-sync for interactive development
- Combine both for best coverage

### Configuration Changes

No breaking changes. New fields have sensible defaults:
- `auto_sync_enabled=True` - Enabled by default
- `auto_sync_on_enhance=True` - Syncs on enhance
- `auto_sync_on_learn=False` - Opt-in for learn
- `auto_sync_interval_hours=24` - Once daily max

## Best Practices

1. **Development**: Use default settings for automatic context
2. **CI/CD**: Disable auto-sync and use manual `git sync`
3. **Performance-critical**: Set `auto_sync_on_enhance=False` and rely on periodic sync
4. **Testing**: Disable git sync entirely to avoid side effects
5. **Large repos**: Increase `auto_sync_max_commits` for comprehensive history

## Future Enhancements

Potential improvements planned:

- [ ] Background thread for truly async syncing
- [ ] Webhook support for push events
- [ ] Configurable commit filtering (by author, file patterns)
- [ ] Integration with CI/CD systems
- [ ] Smart interval adjustment based on commit frequency
- [ ] Batch commit processing for large histories

## See Also

- [Git Sync Documentation](./GIT_SYNC.md)
- [Configuration Guide](./CONFIGURATION.md)
- [API Reference](./API.md)
