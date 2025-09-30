# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.6] - 2025-09-29

### Fixed
- Updated MCP protocol version from "2024-11-05" to "2025-06-18" for Claude Code compatibility
  - Maintains backward compatibility with legacy protocol version
  - Fixes version negotiation to prefer latest supported version
  - Resolves MCP server connection issues with Claude Desktop

### Changed
- Improved CLI syntax: `kuzu-memory recent --limit N` replaces `--recent N`
  - Eliminates redundant "recent --recent" syntax
  - Maintains backward compatibility with deprecation warning
  - Follows common CLI conventions for result limiting

## [1.1.5] - 2025-09-29

### Fixed
- Fixed MCP server stdout contamination issue for proper protocol compliance
  - Redirected startup message "Starting MCP server for project: ..." from stdout to stderr
  - MCP protocol requires stdout to contain only JSON-RPC messages
  - All logging and status messages now correctly output to stderr
  - Resolves integration issues with Claude Desktop and other MCP clients
  - Added comprehensive unit tests to prevent regression of this issue

## [1.1.4] - 2025-09-29

### Fixed
- Fixed MCP server async stdin issue on macOS by implementing thread-based synchronous reading
  - Resolves "can't register file descriptor 0" RuntimeError when running MCP server
  - Enables proper Claude Desktop integration through stable stdin communication
  - MCP server now uses synchronous stdin reading in a separate thread to avoid async event loop conflicts
- MCP server `remember` command parameters now correctly match CLI arguments (source, session_id instead of type, priority)

## [1.1.3] - 2025-09-27

### Fixed
- Critical memory recall functionality that was returning empty results due to overly restrictive agent_id filtering
- MCP server parameter names now correctly match CLI command arguments (--max-memories, --format)
- MCPServer now properly detects homebrew installations on macOS

### Changed
- KeywordRecallStrategy, EntityRecallStrategy, and TemporalRecallStrategy now only filter by agent_id when explicitly provided
- MCP server is fully integrated into main CLI as `kuzu-memory mcp serve` (no separate script needed)

## [1.1.2] - 2025-09-27

### Changed
- Version bump

## [1.1.1] - 2025-09-27

### Changed
- Version bump

## [1.1.0] - 2025-09-26

### Added
- Claude Desktop MCP installer with automatic pipx detection and configuration
- Semantic versioning and build tracking system
- VERSION file for single source of truth version management
- Automated version bumping with `make version-*` commands
- Build tracking with BUILD_INFO file generation
- Git tagging for releases
- PyPI package publication for production use
- Ready-to-use claude-mpm hook compatibility

### Fixed
- Async learning queue now properly processes and stores memories
- DateTime comparison errors in relationships and models preventing proper memory storage
- Memory extraction patterns now properly handle cognitive type classification
- F-string syntax errors in version management files

### Improved
- Performance thresholds for async operations to reduce unnecessary processing
- Help text with pattern matching examples for better user guidance
- Async learning reliability and error handling
- Performance metrics verified: ~3ms recall, ~8ms generation
- 5-second default wait behavior for async operations

### Released
- **Production Ready**: KuzuMemory v1.1.0 published to PyPI
- **Verified Performance**: All benchmarks passing with Kuzu database
- **MCP Integration**: Stable Claude Desktop integration available

## [1.0.1] - 2024-09-26

### Changed
- Version bump for project standardization

### Fixed
- Minor improvements and bug fixes

## [1.0.0] - 2024-09-24

### Added
- Initial release of KuzuMemory
- Lightweight, embedded graph-based memory system for AI applications
- Cognitive memory types: SEMANTIC, PROCEDURAL, EPISODIC, WORKING, SENSORY, PREFERENCE
- CLI interface with `kuzu-memory` command
- Python API for memory operations
- Integration with Claude Desktop via MCP (Memory Context Protocol)
- Async memory operations for background learning
- Memory recall with temporal decay
- Pattern extraction and relationship management
- NLP enhancements with sentiment analysis and classification
- Comprehensive test suite with performance benchmarks
- Development tooling with linting, formatting, and type checking
- Documentation and examples

### Features
- **Memory System**: Graph-based storage using Kuzu database
- **Cognitive Types**: Human-psychology inspired memory categorization
- **CLI Tools**: Complete command-line interface for memory management
- **MCP Integration**: Seamless integration with Claude Desktop
- **Performance**: Optimized for speed with <100ms recall targets
- **Async Operations**: Background learning and memory processing
- **NLP Support**: Advanced text processing and classification
- **Testing**: Comprehensive test coverage with benchmarks

[Unreleased]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.6...HEAD
[1.1.6]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.5...v1.1.6
[1.1.5]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/kuzu-memory/kuzu-memory/releases/tag/v1.0.0