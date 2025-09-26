# MCP JSON-RPC 2.0 Implementation

## Overview

The KuzuMemory MCP server implements the JSON-RPC 2.0 protocol for communication with Claude Code. This ensures full compatibility with the Model Context Protocol (MCP) specification.

## Architecture

### Components

1. **Protocol Handler** (`protocol.py`)
   - Implements JSON-RPC 2.0 message parsing and formatting
   - Handles request/response cycle
   - Manages error codes and notifications
   - Supports batch requests

2. **MCP Server** (`server.py`)
   - Provides memory operations as MCP tools
   - Executes CLI commands via subprocess
   - Formats responses for Claude Code

3. **Run Server** (`run_server.py`)
   - Main entry point for the MCP server
   - Handles stdio communication
   - Routes JSON-RPC requests to appropriate handlers

## JSON-RPC 2.0 Compliance

### Request Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "enhance",
    "arguments": {
      "prompt": "What database are we using?"
    }
  }
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Enhanced prompt with context..."
      }
    ]
  }
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method not found"
  }
}
```

## Supported Methods

### Core MCP Methods
- `initialize` - Initialize the MCP server
- `tools/list` - List available tools
- `tools/call` - Execute a tool
- `notifications/initialized` - Client initialization notification
- `shutdown` - Gracefully shutdown the server
- `ping` - Health check

### KuzuMemory Tools
- `enhance` - Enhance prompts with context
- `learn` - Store learnings asynchronously
- `recall` - Query memories
- `remember` - Store direct memories
- `stats` - Get memory statistics
- `recent` - Get recent memories
- `cleanup` - Clean expired memories
- `project` - Get project information
- `init` - Initialize project

## Error Codes

Standard JSON-RPC 2.0 error codes:
- `-32700` - Parse error
- `-32600` - Invalid request
- `-32601` - Method not found
- `-32602` - Invalid params
- `-32603` - Internal error

Custom MCP error codes:
- `-32001` - Tool execution error
- `-32002` - Initialization error
- `-32003` - Timeout error

## Configuration

### Claude Code Configuration

Add to your Claude Code settings:

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "python",
      "args": ["-m", "kuzu_memory.mcp.run_server"],
      "env": {
        "PYTHONPATH": "src",
        "KUZU_MEMORY_PROJECT": "/path/to/project"
      }
    }
  }
}
```

## Communication Flow

1. **Initialization**
   - Claude Code sends `initialize` request
   - Server responds with capabilities
   - Client sends `notifications/initialized`

2. **Tool Discovery**
   - Claude Code sends `tools/list`
   - Server returns available tools with schemas

3. **Tool Execution**
   - Claude Code sends `tools/call` with tool name and arguments
   - Server executes tool via CLI
   - Response formatted as MCP content blocks

4. **Shutdown**
   - Claude Code sends `shutdown` request
   - Server gracefully closes connections

## Features

### Batch Requests
The server supports JSON-RPC 2.0 batch requests:
```json
[
  {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
  {"jsonrpc": "2.0", "id": 2, "method": "ping"}
]
```

### Notifications
Notifications (requests without `id`) are supported:
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized",
  "params": {}
}
```

### Async Operations
- Learn operations are non-blocking
- CLI commands have configurable timeouts
- Graceful error handling for timeouts

## Testing

### Unit Tests
```bash
# Test JSON-RPC message formatting
python test_jsonrpc_messages.py

# Test MCP server end-to-end
python test_mcp_jsonrpc.py
```

### Manual Testing
```bash
# Start server
python -m kuzu_memory.mcp.run_server

# Send test request (in another terminal)
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python -m kuzu_memory.mcp.run_server
```

## Performance

- Sub-100ms response time for most operations
- Connection pooling via CLI adapter
- Async learning operations (non-blocking)
- Efficient JSON parsing and serialization

## Security

- Input validation on all requests
- Subprocess sandboxing for CLI execution
- No direct database access from MCP layer
- Proper error handling without exposing internals

## Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Monitor JSON-RPC messages:
```bash
# Set environment variable
export MCP_DEBUG=1
python -m kuzu_memory.mcp.run_server
```

## Troubleshooting

### Common Issues

1. **"Method not found" errors**
   - Verify method name matches exactly
   - Check JSON-RPC version is "2.0"

2. **Timeout errors**
   - Increase timeout in server configuration
   - Check database connection

3. **Parse errors**
   - Ensure valid JSON formatting
   - Use line-delimited JSON for stdio

4. **Tool execution failures**
   - Verify CLI is properly installed
   - Check PYTHONPATH environment variable

## Future Improvements

- [ ] WebSocket transport support
- [ ] HTTP transport option
- [ ] Request batching optimization
- [ ] Response streaming for large results
- [ ] Tool parameter validation enhancements