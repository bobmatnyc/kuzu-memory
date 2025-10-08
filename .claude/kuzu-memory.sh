#!/bin/bash
# KuzuMemory wrapper for Claude integration

set -e

# Ensure we're in the project directory
cd "$(dirname "$0")/.."

# Execute kuzu-memory with all arguments
exec /Users/masa/Projects/managed/kuzu-memory/.venv/bin/kuzu-memory "$@"
