#!/bin/bash
# Fast session start hook
# Queues session start data for async processing by MCP server
set -euo pipefail

QUEUE_DIR="${KUZU_MEMORY_QUEUE_DIR:-/tmp/kuzu-memory-queue}"
mkdir -p "$QUEUE_DIR"

# Generate unique filename with timestamp and PID
FILENAME="session_$(date +%s%N)_$$.json"

# Read stdin and queue it (atomic write via temp file)
TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE"
mv "$TEMP_FILE" "$QUEUE_DIR/$FILENAME"

# Return immediately - MCP server processes queue async
echo '{"continue": true}'
