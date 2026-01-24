#!/bin/bash
# Fast learn hook - queues data for async MCP processing
# Replaces slow Python hook (~800ms) with fast bash hook (~20ms)
set -euo pipefail

QUEUE_DIR="${KUZU_MEMORY_QUEUE_DIR:-/tmp/kuzu-memory-queue}"
mkdir -p "$QUEUE_DIR"

# Generate unique filename with timestamp and PID
FILENAME="learn_$(date +%s%N)_$$.json"

# Read stdin and queue it (atomic write via temp file)
TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE"
mv "$TEMP_FILE" "$QUEUE_DIR/$FILENAME"

# Return immediately - MCP server processes queue async
echo '{"continue": true}'
