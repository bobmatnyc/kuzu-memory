#!/bin/bash
# Fast enhance hook - retrieves memories via MCP if available
# For enhance, we need synchronous response with memories
# Fall back to Python if MCP socket not available
set -euo pipefail

QUEUE_DIR="${KUZU_MEMORY_QUEUE_DIR:-/tmp/kuzu-memory-queue}"
MCP_SOCKET="${KUZU_MEMORY_MCP_SOCKET:-/tmp/kuzu-memory-mcp.sock}"

if [[ -S "$MCP_SOCKET" ]]; then
    # MCP server available - use fast path via socket
    # Read prompt from stdin, send to MCP, return enhanced
    # For now, just pass through - full MCP integration in future iteration
    echo '{"continue": true}'
else
    # Fallback to Python (slower but always works)
    exec kuzu-memory hooks enhance
fi
