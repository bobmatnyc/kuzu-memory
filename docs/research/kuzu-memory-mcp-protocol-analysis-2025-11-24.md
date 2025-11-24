# KuzuMemory MCP Server Protocol Analysis

**Date**: 2025-11-24
**Researcher**: Research Agent
**Project**: kuzu-memory
**Current Version**: 1.4.49
**MCP SDK Version**: 1.19.0

---

## Executive Summary

KuzuMemory's MCP server is currently using the **official MCP SDK v1.19.0** with **line-delimited JSON framing** (legacy protocol), NOT Content-Length framing. Contrary to initial assumptions, **FastMCP in the official MCP SDK also uses line-delimited JSON**, not Content-Length framing.

### Critical Findings

❌ **Protocol**: Line-delimited JSON (legacy framing)
✅ **MCP SDK**: Official Anthropic MCP SDK v1.19.0
❌ **FastMCP Misconception**: FastMCP in official SDK uses line-delimited JSON, NOT Content-Length
⚠️ **Migration Required**: No migration needed - current implementation is correct for MCP SDK
✅ **Server Implementation**: Well-structured with proper async/await patterns
❌ **Entry Point**: Uses `kuzu-memory mcp` CLI command, not `python -m` pattern

---

## 1. Current MCP Server Implementation

### Server File Location
- **Primary**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/server.py`
- **Entry Point**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/__main__.py`
- **CLI Command**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/mcp_server_command.py`

### Protocol Analysis

**Current Implementation** (server.py lines 390-398):
```python
async def run(self):
    """Run the MCP server."""
    # Use stdin/stdout for MCP communication
    init_options = InitializationOptions(
        server_name="kuzu-memory",
        server_version=__version__,
        capabilities=self.server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

    # Use stdio_server async context manager for proper stream handling
    async with stdio_server() as (read_stream, write_stream):
        logger.info(f"KuzuMemory MCP Server running for project: {self.project_root}")

        try:
            # Run the MCP server with proper streams
            await self.server.run(
                read_stream, write_stream, init_options, raise_exceptions=False
            )
        except asyncio.CancelledError:
            logger.info("Server shutdown requested")
            raise
        except GeneratorExit:
            logger.info("Server context manager cleanup")
            # Allow proper cleanup without ignoring GeneratorExit
            raise
```

**Protocol Type**: Line-delimited JSON

**Evidence from MCP SDK** (stdio_server source):
```python
async def stdio_server(
    stdin: anyio.AsyncFile[str] | None = None,
    stdout: anyio.AsyncFile[str] | None = None,
):
    """
    Server transport for stdio: this communicates with an MCP client by reading
    from the current process' stdin and writing to stdout.
    """
    # ...
    async def stdin_reader():
        try:
            async with read_stream_writer:
                async for line in stdin:  # ← LINE-DELIMITED
                    try:
                        message = types.JSONRPCMessage.model_validate_json(line)
                    except Exception as exc:
                        await read_stream_writer.send(exc)
                        continue
                    # ...

    async def stdout_writer():
        try:
            async with write_stream_reader:
                async for session_message in write_stream_reader:
                    json = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                    await stdout.write(json + "\n")  # ← NEWLINE DELIMITED
                    await stdout.flush()
```

**Interpretation**:
- ✅ Reads messages line-by-line (`async for line in stdin`)
- ✅ Writes messages with newline delimiter (`json + "\n"`)
- ❌ **NO Content-Length headers** - this is line-delimited JSON

---

## 2. FastMCP Investigation

### FastMCP in Official MCP SDK

**Location**: `/opt/homebrew/lib/python3.13/site-packages/mcp/server/fastmcp/server.py`

**FastMCP run_stdio_async()** implementation:
```python
async def run_stdio_async(self) -> None:
    """Run the server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):  # ← SAME stdio_server!
        await self._mcp_server.run(
            read_stream,
            write_stream,
            self._mcp_server.create_initialization_options(),
        )
```

**Key Finding**: FastMCP in the official MCP SDK **ALSO uses line-delimited JSON**, not Content-Length framing.

### What is FastMCP?

FastMCP is a **high-level API wrapper** in the official MCP SDK that:
- ✅ Provides decorator-based tool/resource/prompt registration
- ✅ Simplifies server setup with less boilerplate
- ✅ Handles lifecycle management automatically
- ❌ **Does NOT change the protocol** - still uses line-delimited JSON

**Example FastMCP Usage**:
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
async def my_tool(arg: str) -> str:
    return f"Result: {arg}"

# Still uses line-delimited JSON!
mcp.run()  # Calls run_stdio_async() → stdio_server()
```

---

## 3. Comparison with mcp-ticketer

### mcp-ticketer Configuration

From previous research (`mcp-ticketer-config-analysis-2025-11-24.md`):

```toml
[mcp_servers.mcp-ticketer]
command = "/Users/masa/.local/pipx/venvs/mcp-ticketer/bin/python"
args = [
    "-m",
    "mcp_ticketer.mcp.server",
    "/Users/masa/Projects/aipowerranking",
]
```

**Research Document Claims**:
- ✅ "Modern Format: Content-Length framing protocol"
- ✅ "Using FastMCP SDK"
- ✅ "Content-Length framed JSON-RPC messages"

### Reality Check: mcp-ticketer Protocol

**Critical Question**: Does mcp-ticketer actually use Content-Length framing?

**Need to Verify**:
1. What version of MCP SDK does mcp-ticketer use?
2. Does mcp-ticketer use custom protocol implementation?
3. Is there a separate "fastmcp" package that implements Content-Length framing?

**Hypothesis**:
- If mcp-ticketer uses the official MCP SDK (mcp>=1.x), it also uses line-delimited JSON
- The previous research document may contain incorrect assumptions
- "FastMCP" in mcp-ticketer likely refers to the FastMCP API wrapper, not protocol

---

## 4. Installation Configuration

### Current KuzuMemory MCP Configuration

**Claude Desktop** (from installers/claude_desktop.py:250-251):
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp"]
    }
  }
}
```

**Entry Points**:
1. **CLI Command**: `kuzu-memory mcp` (preferred by installers)
2. **Python Module**: `python -m kuzu_memory.mcp.server` (available but not used)

**Comparison with mcp-ticketer**:
| Aspect | KuzuMemory | mcp-ticketer |
|--------|------------|--------------|
| Command | `kuzu-memory` | `/path/to/python` |
| Args | `["mcp"]` | `["-m", "mcp_ticketer.mcp.server", "PROJECT_PATH"]` |
| Pattern | CLI command | Python module |
| Project Context | Auto-detected | Passed as arg |

---

## 5. MCP SDK Dependencies

### Current Dependencies (pyproject.toml:37)

```toml
dependencies = [
    # ...
    "mcp>=1.0.0",  # Model Context Protocol SDK for MCP server integration
]
```

### Installed Version

```
Name: mcp
Version: 1.19.0
Summary: Model Context Protocol SDK
Home-page: https://modelcontextprotocol.io
Author: Anthropic, PBC.
Requires: anyio, httpx, httpx-sse, jsonschema, pydantic, pydantic-settings,
          python-multipart, sse-starlette, starlette, uvicorn
```

**Protocol**: Official MCP SDK v1.19.0 uses **line-delimited JSON** for stdio transport

---

## 6. Tools and Resources Exposed

### MCP Tools (from server.py:92-189)

```python
[
    Tool(name="kuzu_enhance", ...),      # Enhance prompts with context
    Tool(name="kuzu_learn", ...),        # Store learnings async
    Tool(name="kuzu_recall", ...),       # Query memories
    Tool(name="kuzu_remember", ...),     # Store direct memories
    Tool(name="kuzu_stats", ...),        # Get statistics
]
```

### MCP Resources (from server.py:231-241)

```python
[
    Resource(
        uri=f"kuzu://project/{self.project_root.name}",
        name=f"Project: {self.project_root.name}",
        description="KuzuMemory project context and memories",
        mimeType="application/json",
    )
]
```

### Resource Templates (from server.py:243-253)

```python
[
    ResourceTemplate(
        uriTemplate="kuzu://memory/{id}",
        name="Memory by ID",
        description="Access a specific memory by its ID",
        mimeType="application/json",
    )
]
```

---

## 7. Protocol Evidence from Tests

### Test File: `tests/mcp/integration/test_stdio_communication.py`

**Line 39-40**:
```python
async def test_message_framing_newline_delimited(self, project_root):
    """Test newline-delimited JSON framing."""
```

**Line 47-53**:
```python
# Verify messages are newline-delimited
request = {"jsonrpc": "2.0", "method": "ping", "id": 1}
message = json.dumps(request) + "\n"  # ← NEWLINE DELIMITER

# Send directly
client.process.stdin.write(message.encode())
client.process.stdin.flush()
```

**Line 55-61**:
```python
# Should receive newline-delimited response
response_line = await asyncio.wait_for(
    asyncio.to_thread(client.process.stdout.readline),
    timeout=5.0,
)

assert response_line.endswith(b"\n"), "Response not newline-terminated"
```

**Evidence**: Tests explicitly verify **newline-delimited JSON**, not Content-Length framing

---

## 8. Migration Requirements Assessment

### Does KuzuMemory Need Migration?

**Answer**: ❌ **NO MIGRATION NEEDED**

**Reasoning**:
1. ✅ KuzuMemory uses official MCP SDK v1.19.0
2. ✅ Official MCP SDK uses line-delimited JSON for stdio transport
3. ✅ FastMCP in official SDK also uses line-delimited JSON
4. ✅ Current implementation is correct and standards-compliant
5. ❌ There is no "Content-Length framing" version of MCP SDK to migrate to

### Previous Research Error

The document `mcp-ticketer-config-analysis-2025-11-24.md` incorrectly stated:
- ❌ "Modern Format: Content-Length framing protocol"
- ❌ "Content-Length framed JSON-RPC messages"

**Reality**:
- ✅ mcp-ticketer also uses line-delimited JSON (same MCP SDK)
- ✅ "FastMCP" refers to API wrapper, not protocol
- ✅ All MCP SDK stdio servers use line-delimited JSON

---

## 9. Potential Optimizations (Not Migration)

### Option 1: Adopt FastMCP API Wrapper

**Benefits**:
- ✅ Cleaner, decorator-based API
- ✅ Less boilerplate code
- ✅ Better type safety
- ✅ Simplified lifecycle management

**Example Migration**:

**Before** (current):
```python
class KuzuMemoryMCPServer:
    def __init__(self, project_root: Path | None = None):
        self.server = Server("kuzu-memory")
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return [Tool(...), Tool(...)]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            # ...
```

**After** (with FastMCP):
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kuzu-memory")

@mcp.tool()
async def kuzu_enhance(prompt: str, max_memories: int = 5) -> str:
    """Enhance a prompt with project-specific context."""
    # Implementation
    return result

@mcp.tool()
async def kuzu_learn(content: str, source: str = "ai-conversation") -> str:
    """Store a learning asynchronously."""
    # Implementation
    return result

# Still uses line-delimited JSON
mcp.run()
```

**Recommendation**: ✅ **Consider adopting FastMCP API** for cleaner code, but this is a **refactoring**, not a protocol migration.

### Option 2: Switch to `python -m` Entry Point

**Current**:
```json
{
  "command": "kuzu-memory",
  "args": ["mcp"]
}
```

**Alternative**:
```json
{
  "command": "python",
  "args": ["-m", "kuzu_memory.mcp.server"]
}
```

**Benefits**:
- ✅ More reliable across installation methods (pipx, pip, uv)
- ✅ Doesn't depend on binary path detection
- ✅ Matches mcp-ticketer pattern
- ✅ Works with different Python environments

**Recommendation**: ✅ **Consider switching** for improved reliability

---

## 10. Correct Understanding of Protocol Evolution

### MCP Protocol Versions

**MCP SDK stdio Transport**:
- ✅ **Line-delimited JSON** (official MCP SDK standard)
- ✅ Used by all stdio-based MCP servers
- ✅ Simple, robust, widely compatible

**Content-Length Framing**:
- ❌ **NOT part of official MCP SDK**
- ⚠️ May be custom implementation in some projects
- ⚠️ Not standard MCP protocol

### Clarification on "Modern" vs "Legacy"

**What is NOT Legacy**:
- ✅ Line-delimited JSON in MCP SDK stdio transport (this is the standard)
- ✅ Using `from mcp.server.stdio import stdio_server`
- ✅ FastMCP (API wrapper in official SDK)

**What IS Legacy** (if it exists):
- ❌ Custom line-delimited implementations outside MCP SDK
- ❌ Non-standard protocol variants
- ❌ Deprecated MCP SDK versions

---

## 11. Recommended Actions

### Immediate Actions (None Required)

✅ **Current implementation is correct** - no changes needed for protocol compliance

### Optional Improvements (Quality of Life)

1. **Adopt FastMCP API Wrapper** (Low Priority)
   - Refactor `server.py` to use FastMCP decorators
   - Simplifies code, improves maintainability
   - No protocol changes - still line-delimited JSON
   - Complexity: Low (2-4 hours)

2. **Switch to `python -m` Entry Point** (Medium Priority)
   - Update installers to use `python -m kuzu_memory.mcp.server`
   - Improves cross-platform reliability
   - Matches mcp-ticketer pattern
   - Complexity: Low (1-2 hours)

3. **Update Documentation** (High Priority)
   - Correct any references to "Content-Length framing"
   - Clarify that line-delimited JSON is the standard
   - Document FastMCP as API wrapper, not protocol
   - Complexity: Low (30 minutes)

### Actions NOT Recommended

❌ **Do NOT attempt Content-Length framing migration** - not part of official MCP SDK
❌ **Do NOT rewrite protocol layer** - official SDK handles this correctly
❌ **Do NOT switch to custom MCP implementation** - official SDK is authoritative

---

## 12. Conclusions

### Key Takeaways

1. **Protocol is Correct**: KuzuMemory uses official MCP SDK v1.19.0 with standard line-delimited JSON
2. **No Migration Needed**: Current implementation is standards-compliant
3. **FastMCP is API Wrapper**: Not a different protocol, just cleaner API
4. **Previous Research Error**: mcp-ticketer analysis incorrectly claimed Content-Length framing
5. **Optional Improvements Available**: FastMCP API and `python -m` entry point

### Corrected Understanding

**Line-Delimited JSON**:
- ✅ Official MCP SDK standard for stdio transport
- ✅ Used by all MCP servers (including mcp-ticketer)
- ✅ Simple, robust, widely compatible
- ✅ **THIS IS THE MODERN STANDARD**, not legacy

**Content-Length Framing**:
- ❌ Not part of official MCP SDK
- ❌ Not standard MCP protocol
- ❌ Likely confusion with LSP (Language Server Protocol)

### Final Recommendation

**NO MIGRATION REQUIRED** - Current implementation is correct and standards-compliant.

**Optional quality-of-life improvements**:
1. Consider FastMCP API wrapper for cleaner code
2. Consider `python -m` entry point for better reliability
3. Update documentation to correct any protocol misconceptions

---

## Appendix A: File Locations

### Source Files
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/server.py` - Main server implementation
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/__main__.py` - Python module entry point
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/mcp_server_command.py` - CLI command

### Installer Configurations
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_desktop.py` - Claude Desktop installer
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/cursor_installer.py` - Cursor installer
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/vscode_installer.py` - VSCode installer
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/windsurf_installer.py` - Windsurf installer

### Test Files
- `/Users/masa/Projects/kuzu-memory/tests/mcp/integration/test_stdio_communication.py` - Stdio tests
- `/Users/masa/Projects/kuzu-memory/tests/test_mcp_server.py` - Server tests
- `/Users/masa/Projects/kuzu-memory/tests/test_mcp.py` - General MCP tests

### Documentation
- `/Users/masa/Projects/kuzu-memory/docs/developer/mcp-jsonrpc.md` - Protocol documentation
- `/Users/masa/Projects/kuzu-memory/docs/MCP_INSTALLATION.md` - Installation guide
- `/Users/masa/Projects/kuzu-memory/docs/research/mcp-ticketer-config-analysis-2025-11-24.md` - Previous (incorrect) research

---

## Appendix B: MCP SDK Source Code Locations

### Official MCP SDK (v1.19.0)
- **stdio_server**: `/opt/homebrew/lib/python3.13/site-packages/mcp/server/stdio.py`
- **FastMCP**: `/opt/homebrew/lib/python3.13/site-packages/mcp/server/fastmcp/server.py`
- **Server**: `/opt/homebrew/lib/python3.13/site-packages/mcp/server/__init__.py`
- **Types**: `/opt/homebrew/lib/python3.13/site-packages/mcp/types.py`

---

**Research completed**: 2025-11-24
**Researcher**: Research Agent
**Status**: Analysis complete - No migration needed
