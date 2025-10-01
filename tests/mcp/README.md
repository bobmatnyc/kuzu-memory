# MCP Testing and Diagnostic Framework

Comprehensive testing suite for the KuzuMemory MCP server implementation.

## Phase 1: Foundation & Connection Testing ✅

**Status**: Complete and operational

### What's Implemented

#### 1. Directory Structure

```
tests/mcp/
├── __init__.py
├── README.md (this file)
├── conftest.py                    # Shared pytest fixtures
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_protocol.py          # JSON-RPC protocol tests (40 tests)
│   └── test_connection_tester.py # Connection tester tests (11 tests)
├── integration/                   # Integration tests (Phase 2)
├── e2e/                          # End-to-end tests (Phase 2)
├── performance/                  # Performance benchmarks (Phase 3)
├── compliance/                   # MCP compliance tests (Phase 4)
└── fixtures/
    ├── __init__.py
    └── mock_clients.py           # Mock client simulators
```

#### 2. Core Testing Infrastructure

**MCPConnectionTester** (`src/kuzu_memory/mcp/testing/connection_tester.py`)
- Complete connection testing framework
- Server lifecycle management (start/stop)
- Protocol initialization testing
- Error scenario simulation
- Latency testing
- JSON-RPC compliance validation
- Connection recovery testing

**MockClientSimulator** (`tests/mcp/fixtures/mock_clients.py`)
- Full-featured MCP client simulator
- Session tracking and statistics
- Batch request support
- Concurrent client testing
- Load testing capabilities

#### 3. Test Coverage

**Protocol Tests** (`tests/mcp/unit/test_protocol.py`) - 40 tests
- JSON-RPC 2.0 error codes
- Message parsing and validation
- Request/response handling
- Batch processing
- Protocol compliance
- Error handling

**Connection Tester Tests** (`tests/mcp/unit/test_connection_tester.py`) - 11 tests
- Result and suite data structures
- Status and severity enums
- Tester initialization
- Server path resolution

### Running Tests

```bash
# Run all MCP unit tests
pytest tests/mcp/unit/ -v

# Run specific test file
pytest tests/mcp/unit/test_protocol.py -v

# Run with coverage
pytest tests/mcp/ --cov=src/kuzu_memory/mcp --cov-report=html

# Run with timeout protection
pytest tests/mcp/ --timeout=30
```

### Using the Connection Tester

```python
import asyncio
from kuzu_memory.mcp.testing import MCPConnectionTester

async def test_connection():
    tester = MCPConnectionTester(timeout=5.0)

    # Run complete test suite
    suite = await tester.run_test_suite()

    print(f"Tests: {suite.total}")
    print(f"Passed: {suite.passed}")
    print(f"Failed: {suite.failed}")
    print(f"Success Rate: {suite.success_rate:.2f}%")

    # Individual tests
    await tester.start_server()
    result = await tester.test_stdio_connection()
    print(f"Stdio: {result.success} ({result.duration_ms:.2f}ms)")
    await tester.stop_server()

asyncio.run(test_connection())
```

### Using the Mock Client

```python
import asyncio
from tests.mcp.fixtures.mock_clients import MCPClientSimulator

async def test_client():
    client = MCPClientSimulator()

    # Connect and initialize
    await client.connect()
    response = await client.initialize()

    # Call tools
    result = await client.call_tool("enhance", {
        "prompt": "Test prompt",
        "limit": 5
    })

    # Get statistics
    stats = client.get_session_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Avg duration: {stats['average_duration_ms']:.2f}ms")

    await client.disconnect()

asyncio.run(test_client())
```

### Test Fixtures Available

From `tests/mcp/conftest.py`:

- `project_root` - Project root path
- `mcp_server` - Configured MCP server instance
- `connection_tester` - Connection tester with cleanup
- `sample_requests` - Sample JSON-RPC requests
- `sample_tools` - Sample tool definitions
- `invalid_requests` - Invalid request scenarios
- `protocol_versions` - Supported protocol versions
- `error_codes` - JSON-RPC error code mappings
- `performance_thresholds` - Performance benchmarks
- `running_server` - Pre-started server instance
- `batch_requests` - Batch request samples
- `stress_test_params` - Stress test parameters

### Quality Gates

All code passes:
- ✅ Black formatting (88 char line length)
- ✅ Ruff linting (minimal warnings)
- ✅ Type checking with mypy
- ✅ 51 unit tests passing
- ✅ Comprehensive docstrings
- ✅ Error handling

### Dependencies

Added to `pyproject.toml`:
```toml
pytest-asyncio>=0.23.0  # Async test support
pytest-timeout>=2.2.0   # Test timeout management
pytest-mock>=3.10       # Mock utilities
```

## Next Phases

### Phase 2: Integration & Tool Testing (Upcoming)
- Tool call integration tests
- Multi-step operation testing
- Error propagation testing
- State management validation

### Phase 3: Performance & Load Testing (Upcoming)
- Response time benchmarks
- Memory usage profiling
- Concurrent client load tests
- Throughput measurements

### Phase 4: MCP Protocol Compliance (Upcoming)
- Full protocol version compatibility
- Capability negotiation testing
- Resource and prompt testing
- Standard compliance validation

## Architecture Notes

### Design Principles
- **Isolation**: Unit tests don't require live server
- **Reusability**: Shared fixtures and utilities
- **Completeness**: Comprehensive error scenario coverage
- **Performance**: Fast execution with timeout protection
- **Maintainability**: Clear structure and documentation

### Code Organization
- `src/kuzu_memory/mcp/testing/` - Testing framework (production code)
- `tests/mcp/fixtures/` - Test utilities and mocks
- `tests/mcp/unit/` - Unit tests (no external dependencies)
- `tests/mcp/integration/` - Integration tests (Phase 2)
- `tests/mcp/e2e/` - End-to-end tests (Phase 2)
- `tests/mcp/performance/` - Performance tests (Phase 3)
- `tests/mcp/compliance/` - Compliance tests (Phase 4)

## Contributing

When adding new tests:
1. Follow existing patterns from `test_protocol.py`
2. Use shared fixtures from `conftest.py`
3. Add new fixtures for reusable test data
4. Ensure tests pass `make quality`
5. Document complex test scenarios
6. Use descriptive test names and docstrings

## Troubleshooting

### Server Won't Start
- Check that kuzu-memory is installed: `which kuzu-memory`
- Verify Python path: `python -m kuzu_memory.mcp.run_server --help`
- Check project root detection

### Tests Timeout
- Increase timeout: `pytest --timeout=60`
- Check server process isn't hanging
- Verify no port conflicts

### Import Errors
- Install test dependencies: `pip install -e ".[test]"`
- Check Python path in test files
- Verify src directory structure

## References

- **Design Spec**: See Code Analyzer agent output for complete design
- **MCP Protocol**: JSON-RPC 2.0 specification
- **Project Docs**: See `/docs/` directory
- **Server Implementation**: `src/kuzu_memory/mcp/server.py`
- **Protocol Implementation**: `src/kuzu_memory/mcp/protocol.py`

---

**Version**: Phase 1 Complete
**Last Updated**: 2025-10-01
**Status**: Production Ready ✅
