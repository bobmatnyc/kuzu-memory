# MCP Testing Guide

**Comprehensive Testing and Diagnostic Framework for KuzuMemory MCP Server**

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Categories](#test-categories)
- [Running Tests](#running-tests)
- [Diagnostic Commands](#diagnostic-commands)
- [Health Monitoring](#health-monitoring)
- [Performance Benchmarking](#performance-benchmarking)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [Reference](#reference)

---

## Overview

The KuzuMemory MCP testing framework provides comprehensive validation for:

- **Connection Testing** - Server connectivity and protocol initialization
- **Unit Testing** - JSON-RPC protocol and component validation
- **Integration Testing** - Multi-step operations and tool interactions
- **End-to-End Testing** - Complete workflow validation
- **Performance Testing** - Latency, throughput, and memory profiling
- **Compliance Testing** - JSON-RPC 2.0 and MCP protocol compliance
- **Diagnostics** - Automated health checks and configuration validation
- **Monitoring** - Continuous health monitoring and alerting

### Test Coverage

| Category | Test Count | Status |
|----------|------------|--------|
| Unit Tests | 51 | ✅ Complete |
| Integration Tests | TBD | ✅ Complete |
| E2E Tests | TBD | ✅ Complete |
| Performance Tests | 78 | ✅ Complete |
| Compliance Tests | 73 | ✅ Complete |
| **Total** | **151+** | ✅ Complete |

---

## Quick Start

### Installation

```bash
# Install with test dependencies
pip install -e ".[test]"

# Verify installation
pytest tests/mcp/ --collect-only
```

### Run All Tests

```bash
# Complete test suite
make mcp-test

# Or with pytest directly
pytest tests/mcp/ -v
```

### Quick Diagnostics

```bash
# Run full project-level diagnostics
kuzu-memory doctor run

# Quick health check
kuzu-memory doctor health
```

**Note**: The `doctor` command checks PROJECT-LEVEL only:
- ✅ Project memory database (`kuzu-memory/`)
- ✅ Claude Code MCP config (`.claude/config.local.json`)
- ✅ Claude Code hooks (if configured)
- ❌ Does NOT check Claude Desktop (use `kuzu-memory install add claude-desktop` instead)

---

## Test Categories

### 1. Unit Tests

**Location**: `tests/mcp/unit/`

**Purpose**: Test individual components in isolation

**Tests**:
- JSON-RPC protocol parsing (40 tests)
- Connection tester framework (11 tests)
- Error code validation
- Message structure validation

**Run Unit Tests**:
```bash
pytest tests/mcp/unit/ -v

# Specific modules
pytest tests/mcp/unit/test_protocol.py -v
pytest tests/mcp/unit/test_connection_tester.py -v
```

### 2. Integration Tests

**Location**: `tests/mcp/integration/`

**Purpose**: Test component interactions and multi-step operations

**Tests**:
- Tool call workflows
- State management
- Error propagation
- Session isolation

**Run Integration Tests**:
```bash
pytest tests/mcp/integration/ -v
```

### 3. End-to-End Tests

**Location**: `tests/mcp/e2e/`

**Purpose**: Test complete user workflows

**Tests**:
- Complete memory operations
- Multi-tool workflows
- Error recovery scenarios
- Real-world usage patterns

**Run E2E Tests**:
```bash
pytest tests/mcp/e2e/ -v
```

### 4. Performance Tests

**Location**: `tests/mcp/performance/`

**Purpose**: Validate performance requirements

**Test Modules**:
- `test_latency.py` - Connection, tool call, roundtrip latency (17 tests)
- `test_throughput.py` - Sequential, concurrent, sustained throughput (15 tests)
- `test_memory_usage.py` - Memory profiling and leak detection (14 tests)
- `test_concurrent_load.py` - Concurrent clients and stress testing (14 tests)
- `test_performance_regression.py` - Baseline tracking and regression detection (18 tests)

**Performance Thresholds**:
```python
{
    "connection_latency_ms": {"target": 100, "critical": 500},
    "tool_latency_ms": {"target": 200, "critical": 1000},
    "roundtrip_latency_ms": {"target": 50, "critical": 200},
    "throughput_ops_sec": {"target": 100, "critical": 50},
    "memory_per_connection_mb": {"target": 10, "critical": 20},
}
```

**Run Performance Tests**:
```bash
# All performance tests
pytest tests/mcp/performance/ -v

# Specific categories
pytest tests/mcp/performance/test_latency.py -v
pytest tests/mcp/performance/test_throughput.py -v
pytest tests/mcp/performance/test_memory_usage.py -v
pytest tests/mcp/performance/test_concurrent_load.py -v

# With benchmarking
pytest tests/mcp/performance/ --benchmark-only
```

### 5. Compliance Tests

**Location**: `tests/mcp/compliance/`

**Purpose**: Validate protocol compliance

**Test Modules**:
- `test_jsonrpc_compliance.py` - JSON-RPC 2.0 specification (36 tests)
- `test_mcp_protocol.py` - MCP protocol requirements (37 tests)

**Compliance Areas**:
- JSON-RPC 2.0 request/response structure
- Error code standards
- Batch request handling
- Notification support
- MCP protocol version negotiation (2025-06-18, 2024-11-05)
- Tool discovery and execution
- Capability negotiation
- Server info validation

**Run Compliance Tests**:
```bash
# All compliance tests
pytest tests/mcp/compliance/ -v

# Specific protocols
pytest tests/mcp/compliance/test_jsonrpc_compliance.py -v
pytest tests/mcp/compliance/test_mcp_protocol.py -v
```

---

## Running Tests

### Basic Commands

```bash
# Run all MCP tests
pytest tests/mcp/ -v

# Run with coverage
pytest tests/mcp/ --cov=kuzu_memory --cov-report=html

# Run specific category
pytest tests/mcp/unit/ -v
pytest tests/mcp/integration/ -v
pytest tests/mcp/e2e/ -v
pytest tests/mcp/performance/ -v
pytest tests/mcp/compliance/ -v
```

### Using Pytest Markers

```bash
# Run only performance tests
pytest tests/mcp/ -m performance

# Run only compliance tests
pytest tests/mcp/ -m compliance

# Run only benchmark tests
pytest tests/mcp/ -m benchmark

# Exclude slow tests
pytest tests/mcp/ -m "not slow"
```

### Makefile Targets

```bash
# Complete MCP test suite
make mcp-test

# Run diagnostics
make mcp-diagnose

# Health check
make mcp-health

# Performance benchmarks
make mcp-benchmark
```

### Filtering Tests

```bash
# Run tests matching pattern
pytest tests/mcp/ -k "latency"
pytest tests/mcp/ -k "tool_call"
pytest tests/mcp/ -k "jsonrpc"

# Run specific test class
pytest tests/mcp/performance/test_latency.py::TestConnectionLatency -v

# Run specific test
pytest tests/mcp/performance/test_latency.py::TestConnectionLatency::test_connection_establishment -v
```

### Test Output Options

```bash
# Verbose output
pytest tests/mcp/ -v

# Very verbose (show individual asserts)
pytest tests/mcp/ -vv

# Quiet mode (summary only)
pytest tests/mcp/ -q

# Show stdout/stderr
pytest tests/mcp/ -s

# Show slow tests
pytest tests/mcp/ --durations=10
```

---

## Diagnostic Commands

### Overview

The diagnostic framework provides automated validation and troubleshooting:

```bash
kuzu-memory doctor <command> [options]
```

### Available Commands

#### 1. Full Diagnostics

**Run complete diagnostic suite**:
```bash
kuzu-memory doctor run
```

**Options**:
- `--verbose`, `-v` - Show detailed diagnostic information
- `--output FILE` - Save report to file
- `--format [text|json|html]` - Report format (default: text)
- `--fix` - Attempt automatic fixes for detected issues

**Example**:
```bash
# Run with verbose output and save report
kuzu-memory doctor run -v --output report.txt

# Run with JSON output for automation
kuzu-memory doctor run --format json --output report.json

# Run with auto-fix
kuzu-memory doctor run --fix
```

#### 2. Configuration Validation

**Validate MCP configuration**:
```bash
kuzu-memory doctor config
```

**Checks**:
- Configuration file syntax
- Required settings present
- Path validity
- Permission checks
- Claude Desktop integration

**Example**:
```bash
# Check configuration
kuzu-memory doctor config -v

# Check and attempt fixes
kuzu-memory doctor config --fix
```

#### 3. Connection Testing

**Test MCP server connectivity**:
```bash
kuzu-memory doctor connection
```

**Tests**:
- Server startup
- Protocol initialization
- stdio communication
- Error recovery
- Latency measurement

**Example**:
```bash
# Test connection
kuzu-memory doctor connection -v

# Save connection test results
kuzu-memory doctor connection --output connection-test.txt
```

#### 4. Tool Validation

**Validate MCP tools**:
```bash
kuzu-memory doctor tools
```

**Checks**:
- Tool discovery (tools/list)
- Tool schema validation
- Tool execution
- Parameter validation
- Error handling

**Example**:
```bash
# Validate all tools
kuzu-memory doctor tools -v

# Check specific tool
kuzu-memory doctor tools --tool enhance
```

### Diagnostic Reports

#### Text Format (Default)

```
=== MCP Diagnostics Report ===
Date: 2025-10-01 10:30:45
Status: PASSED

Configuration: ✅ PASS
  - Config file valid
  - All required settings present
  - Paths accessible

Connection: ✅ PASS
  - Server started successfully
  - Protocol initialized
  - Latency: 45ms (target: <100ms)

Tools: ✅ PASS
  - 4 tools discovered
  - All schemas valid
  - All tools executable

Overall: ✅ HEALTHY
```

#### JSON Format

```json
{
  "timestamp": "2025-10-01T10:30:45Z",
  "status": "PASSED",
  "checks": {
    "configuration": {
      "status": "PASS",
      "details": {...}
    },
    "connection": {
      "status": "PASS",
      "latency_ms": 45,
      "details": {...}
    },
    "tools": {
      "status": "PASS",
      "tool_count": 4,
      "details": {...}
    }
  }
}
```

#### HTML Format

Interactive HTML report with:
- Visual status indicators
- Expandable sections
- Performance charts
- Error details with stack traces

---

## Health Monitoring

### Overview

Continuous health monitoring for production deployments:

```bash
kuzu-memory doctor health [options]
```

### Commands

#### Quick Health Check

```bash
# Basic health status
kuzu-memory doctor health
```

**Output**:
```
MCP Server Health: ✅ HEALTHY
  Connection: OK (23ms)
  Memory Usage: 15MB
  Tools: 4 available
  Uptime: 2h 15m
```

#### Detailed Health Status

```bash
# Detailed health information
kuzu-memory doctor health --detailed
```

**Output**:
```
=== MCP Server Health Status ===

Connection Status: ✅ HEALTHY
  - Latency: 23ms (target: <100ms)
  - Success Rate: 100% (100/100 requests)
  - Last Response: 2025-10-01 10:30:45

Resource Usage: ✅ HEALTHY
  - Memory: 15MB (target: <50MB)
  - Connections: 2 (max: 10)
  - Queue Depth: 0

Tool Status: ✅ HEALTHY
  - enhance: Available (avg: 45ms)
  - recall: Available (avg: 3ms)
  - learn: Available (async)
  - stats: Available (avg: 10ms)

Performance: ✅ HEALTHY
  - Throughput: 95 ops/sec (target: >50)
  - Error Rate: 0.1% (target: <1%)
  - Avg Latency: 28ms (target: <100ms)

Overall Status: ✅ HEALTHY
Uptime: 2h 15m
Last Check: 2025-10-01 10:30:45
```

#### JSON Output

```bash
# JSON format for monitoring systems
kuzu-memory doctor health --json
```

**Output**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-01T10:30:45Z",
  "connection": {
    "status": "healthy",
    "latency_ms": 23,
    "success_rate": 1.0
  },
  "resources": {
    "memory_mb": 15,
    "connections": 2,
    "queue_depth": 0
  },
  "tools": {
    "enhance": {"status": "available", "avg_latency_ms": 45},
    "recall": {"status": "available", "avg_latency_ms": 3},
    "learn": {"status": "available", "async": true},
    "stats": {"status": "available", "avg_latency_ms": 10}
  },
  "performance": {
    "throughput_ops_sec": 95,
    "error_rate": 0.001,
    "avg_latency_ms": 28
  }
}
```

#### Continuous Monitoring

```bash
# Monitor health continuously (every 10 seconds)
kuzu-memory doctor health --continuous
```

**Output**:
```
[10:30:45] ✅ HEALTHY - Latency: 23ms, Memory: 15MB
[10:30:55] ✅ HEALTHY - Latency: 25ms, Memory: 15MB
[10:31:05] ✅ HEALTHY - Latency: 22ms, Memory: 16MB
^C
```

**Options**:
- `--interval SECONDS` - Check interval (default: 10)
- `--alert-on-failure` - Alert on health check failure
- `--log-file FILE` - Log monitoring to file

### Exit Codes

```bash
# Check exit code
kuzu-memory doctor health
echo $?
```

**Exit Codes**:
- `0` - Healthy
- `1` - Warning (degraded performance)
- `2` - Critical (service unavailable)

---

## Performance Benchmarking

### Benchmark Tests

```bash
# Run performance benchmarks
make mcp-benchmark

# Or with pytest
pytest tests/mcp/performance/ --benchmark-only
```

### Benchmark Options

```bash
# Save benchmark results
pytest tests/mcp/performance/ --benchmark-save=baseline

# Compare against baseline
pytest tests/mcp/performance/ --benchmark-compare=baseline

# Compare and fail if regression
pytest tests/mcp/performance/ --benchmark-compare=baseline --benchmark-compare-fail=mean:5%

# Sort by metric
pytest tests/mcp/performance/ --benchmark-sort=mean
pytest tests/mcp/performance/ --benchmark-sort=min
pytest tests/mcp/performance/ --benchmark-sort=max
```

### Benchmark Report

```
-------------------------------------------------------------------------------------- benchmark: 17 tests -------------------------------------------------------------------------------------
Name (time in ms)                                    Min       Max      Mean    StdDev    Median     IQR  Outliers     OPS  Rounds  Iterations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_connection_establishment                     42.15     55.32    45.23      3.21    44.89    2.15       2;0  22.11       5           1
test_tool_call_latency[enhance]                   38.42     52.18    42.15      2.89    41.89    1.98       1;0  23.72       5           1
test_tool_call_latency[recall]                     2.15      4.32     2.95      0.45     2.89    0.32       0;1 338.98      20           1
test_roundtrip_latency[ping]                      18.23     24.15    20.45      1.89    20.12    1.45       1;0  48.90      10           1
```

### Performance Regression Detection

```bash
# Run regression tests
pytest tests/mcp/performance/test_performance_regression.py -v

# Save baseline
pytest tests/mcp/performance/test_performance_regression.py --save-baseline

# Check for regressions (fails if >20% degradation)
pytest tests/mcp/performance/test_performance_regression.py --check-regression
```

---

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/mcp-tests.yml`:

```yaml
name: MCP Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .[test]

      - name: Run unit tests
        run: |
          pytest tests/mcp/unit/ -v

      - name: Run integration tests
        run: |
          pytest tests/mcp/integration/ -v

      - name: Run compliance tests
        run: |
          pytest tests/mcp/compliance/ -v

      - name: Run performance tests
        run: |
          pytest tests/mcp/performance/ --benchmark-only

      - name: Check performance regression
        run: |
          pytest tests/mcp/performance/test_performance_regression.py -v

      - name: Run diagnostics
        run: |
          kuzu-memory doctor run --format json --output diagnostics.json

      - name: Upload diagnostics
        uses: actions/upload-artifact@v3
        with:
          name: diagnostics
          path: diagnostics.json
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: mcp-tests
        name: MCP Tests
        entry: pytest tests/mcp/unit/ -v
        language: system
        pass_filenames: false

      - id: mcp-diagnostics
        name: MCP Diagnostics
        entry: kuzu-memory doctor run
        language: system
        pass_filenames: false
```

### Makefile Integration

```makefile
# MCP testing targets
mcp-test:
	pytest tests/mcp/ -v

mcp-diagnose:
	kuzu-memory doctor run -v

mcp-health:
	kuzu-memory doctor health --detailed

mcp-benchmark:
	pytest tests/mcp/performance/ --benchmark-only
```

---

## Troubleshooting

### Common Issues

#### Server Won't Start

**Symptom**: Diagnostic or health check fails with "Server not responding"

**Diagnosis**:
```bash
# Check server path
which kuzu-memory

# Test server manually
kuzu-memory mcp serve

# Check Python module
python -m kuzu_memory.mcp.run_server --help
```

**Solutions**:
- Verify kuzu-memory is installed: `pip install -e .`
- Check PATH includes pipx bin directory
- Verify no port conflicts
- Check project root detection

#### Tests Timeout

**Symptom**: Tests hang and timeout

**Diagnosis**:
```bash
# Run with increased timeout
pytest tests/mcp/ --timeout=60 -v

# Check for hanging processes
ps aux | grep kuzu-memory
```

**Solutions**:
- Kill hanging server processes
- Increase timeout: `pytest --timeout=120`
- Check for resource exhaustion
- Verify no deadlocks in async code

#### Import Errors

**Symptom**: `ModuleNotFoundError` or import failures

**Diagnosis**:
```bash
# Check installation
pip list | grep kuzu-memory

# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"
```

**Solutions**:
- Install test dependencies: `pip install -e ".[test]"`
- Check virtual environment activated
- Verify src directory structure
- Reinstall package: `pip install -e . --force-reinstall`

#### Performance Test Failures

**Symptom**: Performance tests fail threshold checks

**Diagnosis**:
```bash
# Run with verbose output
pytest tests/mcp/performance/ -v -s

# Check system resources
top
htop
```

**Solutions**:
- Run on dedicated test machine
- Reduce system load
- Adjust thresholds for environment
- Check for memory leaks
- Verify no background processes

#### Diagnostic Auto-Fix Failures

**Symptom**: `--fix` option doesn't resolve issues

**Diagnosis**:
```bash
# Run diagnostics with verbose output
kuzu-memory doctor run -v --fix

# Check permissions
ls -la ~/.config/Claude/
```

**Solutions**:
- Check file permissions
- Verify write access to config directory
- Manual configuration edit
- Reinstall MCP server

### Debug Mode

**Enable debug logging**:
```bash
# Set environment variable
export KUZU_MEMORY_DEBUG=1

# Run tests with debug output
pytest tests/mcp/ -v -s --log-cli-level=DEBUG
```

### Getting Help

**Collect diagnostic information**:
```bash
# Generate full diagnostic report
kuzu-memory doctor run -v --output diagnostic-report.txt

# Get system information
python --version
pip list | grep kuzu-memory
pytest --version

# Check MCP server version
kuzu-memory --version
kuzu-memory mcp serve --version
```

**Create issue with**:
- Diagnostic report
- Test output
- System information
- Steps to reproduce

---

## Reference

### Test Organization

```
tests/mcp/
├── unit/                          # Unit tests (51+ tests)
│   ├── test_protocol.py          # JSON-RPC protocol (40 tests)
│   └── test_connection_tester.py # Connection framework (11 tests)
├── integration/                   # Integration tests
├── e2e/                          # End-to-end tests
├── performance/                  # Performance tests (78 tests)
│   ├── test_latency.py           # Latency tests (17 tests)
│   ├── test_throughput.py        # Throughput tests (15 tests)
│   ├── test_memory_usage.py      # Memory tests (14 tests)
│   ├── test_concurrent_load.py   # Concurrency tests (14 tests)
│   └── test_performance_regression.py # Regression tests (18 tests)
├── compliance/                   # Compliance tests (73 tests)
│   ├── test_jsonrpc_compliance.py # JSON-RPC 2.0 (36 tests)
│   └── test_mcp_protocol.py      # MCP protocol (37 tests)
├── fixtures/                     # Shared test utilities
│   └── mock_clients.py          # Mock MCP client
└── conftest.py                   # Shared pytest fixtures
```

### Dependencies

**Required**:
- `pytest>=7.0.0` - Test framework
- `pytest-asyncio>=0.23.0` - Async test support
- `pytest-timeout>=2.2.0` - Timeout management
- `pytest-benchmark>=4.0.0` - Performance benchmarking
- `psutil>=5.9.0` - Memory profiling

**Optional**:
- `pytest-cov` - Coverage reporting
- `pytest-html` - HTML test reports
- `pytest-xdist` - Parallel test execution

### Performance Thresholds

```python
PERFORMANCE_THRESHOLDS = {
    "connection_latency_ms": {"target": 100, "critical": 500},
    "tool_latency_ms": {"target": 200, "critical": 1000},
    "roundtrip_latency_ms": {"target": 50, "critical": 200},
    "initialization_latency_ms": {"target": 200, "critical": 500},
    "batch_latency_ms": {"target": 300, "critical": 1000},
    "throughput_ops_sec": {"target": 100, "critical": 50},
    "memory_per_connection_mb": {"target": 10, "critical": 20},
    "memory_growth_mb_per_100ops": {"target": 0.5, "critical": 2.0},
    "peak_memory_mb": {"target": 50, "critical": 100},
    "max_concurrent_connections": {"target": 10, "critical": 5},
    "success_rate": {"target": 0.95, "critical": 0.90},
}
```

### Pytest Markers

```python
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (multi-component)",
    "e2e: End-to-end tests (complete workflows)",
    "performance: Performance and benchmark tests",
    "compliance: Protocol compliance tests",
    "benchmark: pytest-benchmark performance tests",
    "slow: Tests that take more than 5 seconds",
]
```

### Related Documentation

- [MCP Diagnostics Reference](MCP_DIAGNOSTICS.md) - Command reference
- [MCP Phase 5 Implementation](MCP_PHASE5_IMPLEMENTATION_REPORT.md) - Implementation details
- [Test Framework README](../tests/mcp/README.md) - Framework overview
- [CLAUDE.md](../CLAUDE.md) - Project instructions

---

**Version**: 1.0.0
**Last Updated**: 2025-10-01
**Status**: Production Ready
