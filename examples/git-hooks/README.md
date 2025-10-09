# KuzuMemory Git Hooks

This directory contains git hook templates for automatic memory synchronization.

## Available Hooks

### post-commit

Automatically syncs significant commits to the memory system after each commit.

**Installation:**
```bash
# Automatic installation (recommended)
kuzu-memory git install-hooks

# Manual installation
cp examples/git-hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

**Features:**
- Runs after each successful commit
- Only syncs significant commits (feat:, fix:, refactor:, etc.)
- Incremental sync (only new commits)
- Fails silently if kuzu-memory is unavailable
- No performance impact on git operations

**Uninstallation:**
```bash
kuzu-memory git uninstall-hooks
```

## Configuration

Git sync behavior can be configured in your project's `config.yaml`:

```yaml
git_sync:
  enabled: true
  branch_include_patterns:
    - main
    - develop
    - feature/*
    - bugfix/*
  branch_exclude_patterns:
    - tmp/*
    - test/*
    - experiment/*
  significant_prefixes:
    - "feat:"
    - "fix:"
    - "refactor:"
    - "perf:"
    - "BREAKING CHANGE"
  skip_patterns:
    - wip
    - tmp
    - "chore:"
    - "style:"
    - "docs:"
  min_message_length: 20
  include_merge_commits: true
  auto_sync_on_push: true
```

## How It Works

1. **Commit Detection**: Hook triggers after successful commit
2. **Filtering**: Only significant commits are synced based on configuration
3. **Memory Storage**: Commits stored as EPISODIC memories (30-day retention)
4. **Metadata**: Includes commit SHA, author, timestamp, and changed files
5. **State Tracking**: Config updated with last sync timestamp and commit SHA

## Memory Format

Commits are stored with the following format:

**Content**: `{commit_message} | Files: {changed_files}`

**Metadata**:
- `commit_sha`: Full commit SHA
- `commit_author`: Author name and email
- `commit_timestamp`: Commit timestamp (ISO8601)
- `branch`: Branch name
- `changed_files`: List of modified files
- `parent_count`: Number of parent commits (merge detection)

## Troubleshooting

**Hook not running:**
- Verify hook is executable: `chmod +x .git/hooks/post-commit`
- Check kuzu-memory is in PATH: `which kuzu-memory`
- Test manually: `.git/hooks/post-commit`

**Commits not syncing:**
- Check git sync status: `kuzu-memory git status`
- Verify commit matches filter criteria
- Run sync manually: `kuzu-memory git sync --dry-run`

**Performance concerns:**
- Hook runs asynchronously and fails silently
- Typical sync time: <100ms for incremental updates
- No blocking of git operations
