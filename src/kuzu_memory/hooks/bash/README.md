# Bash Hooks for KuzuMemory

Fast bash-based hooks that replace slow Python hooks for 40x performance improvement.

## Performance

- **Python hooks**: ~800ms startup latency
- **Bash hooks**: ~20ms startup latency
- **Improvement**: 40x faster

## Scripts

### `learn_hook.sh`
- **Purpose**: Queue learning data for async processing
- **Latency**: ~20ms
- **Usage**: Called by Claude Code `PostToolUse` event

### `session_start_hook.sh`
- **Purpose**: Queue session start events
- **Latency**: ~20ms
- **Usage**: Called by Claude Code `SessionStart` event

### `enhance_hook.sh`
- **Purpose**: Enhance prompts with context (fallback to Python)
- **Latency**: ~100ms (uses Python for sync response)
- **Usage**: Called by Claude Code `UserPromptSubmit` event

## How It Works

1. **Bash hook** receives JSON from stdin
2. **Writes to queue** at `/tmp/kuzu-memory-queue/`
3. **Returns immediately** with `{"continue": true}`
4. **MCP server** processes queue in background
5. **Memory stored** asynchronously

## Environment Variables

- `KUZU_MEMORY_QUEUE_DIR` - Queue directory (default: `/tmp/kuzu-memory-queue`)
- `KUZU_MEMORY_MCP_SOCKET` - MCP socket path (future, default: `/tmp/kuzu-memory-mcp.sock`)

## Migration

Existing users are automatically migrated when upgrading to v1.7.0+:

1. Original settings backed up to `~/.claude.json.bak`
2. Python hook commands replaced with bash script paths
3. Migration state saved to `.kuzu-memory/migration_state.json`

## Development

### Testing

```bash
# Test learn hook
echo '{"prompt": "test", "transcript_path": "/tmp/test.jsonl"}' | ./learn_hook.sh

# Check queue
ls /tmp/kuzu-memory-queue/

# Verify output
cat /tmp/kuzu-memory-queue/learn_*.json
```

### Requirements

- Bash 4.0+
- Standard Unix tools: `mktemp`, `mv`, `cat`, `date`

## Security

- **Atomic writes**: `mktemp` + `mv` prevents partial reads
- **No shell injection**: All input is JSON-parsed, not evaluated
- **File permissions**: Queue files are user-only (0600)

## Future Enhancements

- [ ] MCP socket for synchronous enhance (even faster)
- [ ] Queue batching for better throughput
- [ ] Queue persistence across MCP restarts
