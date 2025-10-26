# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Enhanced Git Commit File References** for better searchability and context
  - Files now listed in searchable content (up to 10 files inline, with count for remainder)
  - New `file_stats` metadata: insertions/deletions per file from git diff
  - New `file_categories` metadata: automatic categorization (source, tests, docs, config, other)
  - File paths fully searchable in memory content for better recall
  - 20 comprehensive tests covering all enhancement features
  - Backward compatible with existing git sync memories

<!-- towncrier release notes start -->

## [1.4.2] - 2025-10-25

### Added

- **Activity-Aware Temporal Decay** for fair recency scoring after project gaps
  - New `project_last_activity` parameter in `calculate_temporal_score()`
  - Memories from before project gaps scored relative to last activity instead of absolute time
  - Prevents old memories from appearing stale when resuming projects after breaks
  - Fully backward compatible (optional parameter)
  - Static helper method `get_project_last_activity()` to automatically detect last activity
  - Enhanced `get_decay_explanation()` with activity-aware context
  - 15 comprehensive tests covering all scenarios
  - Complete documentation in `docs/ACTIVITY_AWARE_TEMPORAL_DECAY.md`

- **Automatic Git Commit Indexing** for seamless commit history tracking
  - New `AutoGitSyncManager` for interval-based and trigger-based git sync
  - Auto-syncs on enhance, learn, and init (configurable)
  - Persistent state tracking in `.kuzu-memory/git_sync_state.json`
  - Incremental sync after first run for performance
  - Configuration options: `auto_sync_enabled`, `auto_sync_on_enhance`, `auto_sync_on_learn`, `auto_sync_interval_hours`, `auto_sync_max_commits`
  - Silent operation with graceful error handling
  - Performance impact <100ms, non-blocking
  - 22 comprehensive tests covering all trigger modes
  - Complete documentation in `docs/AUTO_GIT_SYNC.md`

- **Git Username Tagging** for multi-user memory namespacing
  - New `GitUserProvider` utility for reliable git user detection
  - Auto-populates `user_id` field with git username (email → name → system username fallback)
  - All new memories automatically tagged with current git user
  - Git commits tagged with commit author/committer email
  - New methods: `get_current_user_id()`, `get_users()`, `get_memories_by_user()`
  - User filtering in queries and statistics
  - Configuration options: `auto_tag_git_user`, `user_id_override`, `enable_multi_user`
  - Fully backward compatible (existing memories with `user_id=None` work)
  - Caching for performance (one git call per session)
  - 20 comprehensive tests covering detection, tagging, and filtering
  - Complete documentation in `docs/GIT_USER_TAGGING.md`

### Changed

- Git sync now includes both author and committer information in memory metadata
- Memory statistics now include user breakdown when multi-user features enabled
- Temporal decay explanations now show activity-aware mode when applicable

## [1.4.1] - 2025-10-25

### Added

- **Auggie Integration v2.0.0** with automatic version detection and migration system
  - New `AuggieVersionDetector` for detecting installed versions from `.augment/.kuzu-version` or content patterns
  - New `AuggieRuleMigrator` for seamless upgrades with automatic backup to `.augment/backups/`
  - Enhanced rules incorporating 8 key improvements from Claude Code hooks v1.4.0:
    * Concrete success metrics (2-5 memories per query, <100ms response)
    * Enhanced trigger patterns with negative examples (what NOT to enhance)
    * Decision tree for storage logic (project-specific, different, corrections)
    * Deduplication patterns (SHA256 hashing, TTL caching)
    * Performance optimization (batching, targeted filtering)
    * Real-world examples from v1.4.0 testing
    * Monitoring and health checks
    * Failure recovery protocols (graceful degradation)
  - Backward compatible: Existing `AuggieInstaller` now wraps `AuggieInstallerV2`
  - Automatic migration: Running `kuzu-memory install add auggie` automatically upgrades v1.0.0 to v2.0.0 with backup
  - Comprehensive test suite: 14 tests covering version detection, installation, migration, and backups

## [1.4.0] - 2025-10-25

### Added

- Production-ready Claude Code hooks with comprehensive type hints and mypy configuration for type safety
- Comprehensive test suite with 30+ test cases covering both enhance and learn hooks
- Log rotation infrastructure with both automatic (logrotate) and manual (rotate_logs.sh) options
- Detailed testing and QA documentation in README_TESTING.md

### Fixed

- Critical fix for duplicate memory creation when PostToolUse hook fires multiple times for parallel tool calls. Implemented SHA256-based content deduplication with 5-minute TTL cache to prevent storing the same assistant response multiple times ([#duplicate-memories](https://github.com/bobmatnyc/kuzu-memory/issues/duplicate-memories))

### Changed

- Enhanced kuzu_enhance.py and kuzu_learn.py hooks with full type hints for Python 3.11+ compatibility
- Improved logging infrastructure with configurable log directories and proper error handling
- Added robust transcript file finding logic to handle continued Claude Code sessions

## [1.3.4] - 2025-10-25

### Fixed

- Fixed critical bug in Claude Code hook event names. The v1.3.3 installer used incorrect event names (`user_prompt_submit`, `assistant_response`) that never fired in Claude Code. Updated to correct event names (`UserPromptSubmit`, `Stop`). Users must run `kuzu-memory install add claude-code --force` to update existing configurations. Added diagnostic checks to detect and warn about incorrect event names. ([#claude-hooks-event-fix](https://github.com/bobmatnyc/kuzu-memory/issues/claude-hooks-event-fix))
## [1.3.3] - 2025-10-14

### Added
- Implemented complete automated demo command showcasing all KuzuMemory features in 8 steps: initialization, memory storage (all 6 types), recall, prompt enhancement, statistics, recent memories, and next steps guidance.

### Changed
- Enhanced quickstart command with 3 new interactive steps: view recent memories, try semantic search recall, and learn about the 6 cognitive memory types (SEMANTIC, PROCEDURAL, PREFERENCE, EPISODIC, WORKING, SENSORY).

### Fixed
- Fixed critical JSON serialization bug that prevented memory storage when metadata contained Pydantic Sentinel values. This resolves the "the JSON object must be str, bytes or bytearray, not Sentinel" error that blocked all memory operations.
- Fixed 8 Click Sentinel parameter bugs in demo and quickstart commands that caused crashes when invoking subcommands. All ctx.invoke() calls now provide explicit parameters to prevent Sentinel object propagation.

## [1.3.2] - 2025-10-12

### Fixed

- Fixed concurrent database access errors that occurred when 3+ Claude Desktop sessions accessed the same database simultaneously. The issue was caused by the async connection pool creating separate Database instances per connection, leading to file lock conflicts. Implemented shared Database instance pattern with retry logic (10 attempts, exponential backoff) and corrected Kuzu Python API method names. All concurrent access tests now pass (7/7) with no performance degradation. ([#concurrent-access](https://github.com/bobmatnyc/kuzu-memory/issues/concurrent-access))
## [1.3.1] - 2025-10-10

### Added

- Unified MCP Installer with auto-detection for Cursor, VS Code with Continue, and Windsurf ([#200](https://github.com/bobmatnyc/kuzu-memory/issues/200))
- Implemented towncrier-based changelog fragment management system for better release notes ([#203](https://github.com/bobmatnyc/kuzu-memory/issues/203))

### Fixed

- Fixed installer file tracking logic to correctly populate files_created list ([#201](https://github.com/bobmatnyc/kuzu-memory/issues/201))
- Resolved Git Sync API integration issues including MemoryStore API mismatches ([#202](https://github.com/bobmatnyc/kuzu-memory/issues/202))
## [1.3.0] - 2025-10-09

### Added
- **Unified MCP Installer**: Multi-AI system support for modern coding assistants
  - Auto-detection of Cursor, VS Code with Continue, and Windsurf
  - Smart configuration merging preserves existing MCP server configs
  - CLI commands: `kuzu-memory mcp detect`, `mcp install`, `mcp list`
  - Supports both global and project-specific installations
  - Automatic path resolution and verification
  - Dry-run mode for safe testing before installation

### Fixed
- **Git Sync API Compatibility**: Fixed critical MemoryStore API mismatch (100% → 0% failure rate)
  - Fixed `recall_memories()` → `get_recent_memories()` API call
  - Fixed `store_memory()` → `batch_store_memories()` API call
  - Added deduplication via commit SHA checking
  - All 30 commits now sync successfully
- **Quality Improvements**: Resolved formatting, linting, and installer file tracking issues
  - Fixed code formatting compliance
  - Resolved linting violations
  - Improved installer metadata tracking

### Documentation
- **Git Sync Guide**: Comprehensive documentation for git history synchronization
  - Setup instructions and configuration options
  - Hook installation and auto-sync setup
  - Performance benchmarks and best practices
  - Troubleshooting guide
- **API Fix Summary**: Detailed technical documentation of git sync fixes
- **Hook Examples**: Reference implementations for post-commit hooks

## [1.2.8] - 2025-10-09

### Added
- **Git History Sync**: Automatically import significant git commits as memories
  - Smart sync with initial and incremental modes
  - Commit filtering by semantic prefixes (feat:, fix:, refactor:, perf:)
  - Branch pattern matching with wildcards (main, master, develop, feature/*, bugfix/*)
  - SHA-based deduplication prevents duplicates
  - Post-commit hook for automatic synchronization
  - CLI commands: `git sync`, `git status`, `git install-hooks`, `git uninstall-hooks`

### Fixed
- **Git Sync Compatibility**: Enhanced branch pattern defaults for legacy repositories
  - Bug #1: Added "master" to default branch patterns for legacy git repos
  - Bug #2: Reduced min_message_length from 20 to 5 for concise commits
  - Bug #3: Fixed CLI import errors with get_container()
  - Bug #4: Fixed MemoryStore API mismatch in git sync
  - Bug #5: Fixed ConfigLoader.save() API call
  - Bug #6: Fixed datetime timezone comparison in incremental sync

### Technical Details
- Commits stored as EPISODIC memories (30-day retention)
- Metadata includes: commit_sha, author, timestamp, branch, files
- Deduplication via commit SHA checking
- Performance: <2s incremental sync, 30 commits in first sync
- Test coverage: 88% (22/25 tests passing)
- Production verified: 30/30 commits synced successfully in real testing

## [1.2.7] - 2025-10-08

### Fixed
- **Memory Generation Performance**: Restored optimal performance by disabling NLP classification by default
  - Generation time improved from ~630ms to ~80ms (87% faster)
  - Mean generation time: 3.94ms (within ~8ms target)
  - NLP classification can still be enabled via config: `extraction.enable_nlp_classification: true`
  - Performance now meets documented thresholds: <200ms generation, <100ms recall

## [1.2.6] - 2025-10-08

### Fixed
- **MCP Server Integration**: Fixed installer to detect correct kuzu-memory path with MCP support
  - Added priority-based path detection (pipx → dev → system)
  - Added `_verify_mcp_support()` to check if installation supports MCP server
  - Registered MCP command group in main CLI (7 total command groups)
  - Fixed import paths to use absolute imports following PEP 8 (improved maintainability)
  - Enhanced error messages when MCP server is not available

### Improved
- **Installer Reliability**: Enhanced Claude hooks installer with better path detection
  - Warns when kuzu-memory installation doesn't support MCP server
  - Provides clear guidance for reinstalling with pipx for MCP support
  - Better logging for troubleshooting installation issues
  - Improved development environment detection

## [1.2.5] - 2025-10-07

### Fixed
- **Project Root Detection**: Fixed critical bug where `kuzu-memory init` would incorrectly use home directory as project root
  - Added safety check to never use home directory as project root
  - Stops search at home directory boundary
  - Defaults to current directory when no project root found
  - Added comprehensive test coverage with 18 new tests

## [1.2.4] - 2025-10-06

### Changed
- Version bump

## [1.2.3] - 2025-10-06

### Fixed
- **Claude Code Installer**: Fixed file messaging to correctly show "created" vs "modified"
- **Claude Code Installer**: Added clarity about Claude MPM config purpose with helpful explanation
- **Claude Code Installer**: Fixed command paths to use full pipx path instead of plain command name
  - Added automatic detection of pipx installation using `which kuzu-memory`
  - Commands now use full path (e.g., `/Users/user/.local/bin/kuzu-memory`) when installed via pipx
  - Applied to Claude Code hooks, MCP server config, MPM config, and shell wrapper
- **Installation Output**: Enhanced file listings with contextual information
  - Shows "(Claude MPM integration)" for MPM config files
  - Shows "(merged with existing config)" for modified config files
  - Displays helpful explanation when Claude MPM integration is configured

## [1.2.2] - 2025-10-06

### Fixed
- **Path Bug**: Corrected incorrect path references `kuzu-memory` → `kuzu-memories`
  - Fixed in `mcp/testing/diagnostics.py` for MCP diagnostics
  - Fixed in `installers/claude_hooks.py` for hook installation
- **Doctor Command Enhancement**: Comprehensive checks for all init/install files
  - Added validation for `.kuzu-memories/config.yaml`
  - Added validation for `.claude/config.local.json`
  - Added validation for `.claude-mpm/configuration.yaml`
  - Improved diagnostic accuracy for installation verification

### Breaking Changes
- **CLI Reorganization**: Restructured from 20+ commands to 6 focused command groups
  - `remember` → `memory store`
  - `recall` → `memory recall`
  - `enhance` → `memory enhance`
  - `stats` → `status`
  - `install <system>` → `install add <system>`
  - `list-installers` → `install list`
  - `install-status` → `install status`
  - `uninstall` → `install remove`
  - `mcp diagnose` → `doctor`
  - `mcp health` → `doctor health`
  - `examples` → `help examples`
  - `tips` → `help tips`

### Added
- Type-safe enums for CLI parameters (AISystem, OutputFormat, MemoryType, DiagnosticCheck)
- Hierarchical command structure with 6 top-level groups
- `doctor` command group for diagnostics and health checks
- `help` command group with examples and tips
- `status` command with multiple output formats

### Changed
- Reorganized CLI modules for better maintainability (30% code reduction)
- Improved help text consistency across all commands
- Enhanced error messages with enum validation

### Deprecated
- Old command modules moved to `_deprecated/` directory
- Legacy command names (still work with deprecation warnings in transition period)

### Documentation
- Updated all 8 documentation files with new command structure
- 156+ command reference updates
- Archived previous documentation versions

## [1.2.1] - 2025-10-06

### Changed
- Version bump

## [1.2.0] - 2025-10-06

### Changed
- Version bump

## [1.1.13] - 2025-10-02

### Changed
- Version bump

## [1.1.12] - 2025-10-02

### Changed
- Version bump

## [1.1.11] - 2025-10-01

### Fixed
- **MCP Diagnostics Tool Names**: Corrected tool name mismatch in diagnostics
  - Removed incorrect 'kuzu_' prefix from tool name checks (tools use 'enhance', not 'kuzu_enhance')
  - Added test parameters for all 9 MCP tools (enhance, learn, recall, stats, remember, recent, cleanup, project, init)
  - Fixed 'missing required argument' errors in tool execution tests
  - All 16 diagnostic tests now pass (100% pass rate)
    - tool_execution_enhance: PASSING ✅
    - tool_execution_learn: PASSING ✅
    - tool_execution_recall: PASSING ✅
    - tool_execution_stats: PASSING ✅
    - tool_execution_remember: PASSING ✅
    - tool_execution_recent: PASSING ✅
    - tool_execution_cleanup: PASSING ✅
    - tool_execution_project: PASSING ✅
    - tool_execution_init: PASSING ✅

### Improved
- **Diagnostic Test Coverage**: Comprehensive parameter validation for all tools
- **Error Messages**: Clearer diagnostic output for tool execution failures

## [1.1.10] - 2025-10-01

### Fixed
- **MCP stdio Communication**: Resolved critical text/binary mode mismatches
  - Fixed JSON parsing 'Expecting value: line 1 column 1' errors
  - Implemented text mode with explicit UTF-8 encoding for stdin/stdout
  - Added explicit stderr logging to prevent stdout pollution
  - Improved subprocess communication in connection tester
  - Updated mock clients to use text mode consistently

### Improved
- **Diagnostics Reliability**: Pass rate improved from 66.7% to 81.2%
  - Enhanced connection tester with retry logic
  - Better error handling for subprocess reading
  - More robust MCP protocol communication
  - All 101 unit tests passing (100%)

### Verified
- Core MCP functionality confirmed working
- `kuzu-memory mcp diagnose run` - 13/16 tests passing
- `pytest tests/mcp/unit/` - 101/101 tests passing
- Real-world MCP server communication validated

## [1.1.9] - 2025-10-01

### Added
- **Interactive Fix Prompt**: Diagnostic commands now offer interactive fixing
  - After running diagnostics, users can apply automatic fixes when available
  - User-friendly prompts guide through configuration repairs
  - Enhanced user experience for MCP troubleshooting

### Changed
- **Improved .gitignore**: Updated to exclude Claude MPM session files
  - Added `.claude-mpm/configuration.yaml` exclusion
  - Added `.claude-mpm/memories/` directory exclusion
  - Better separation of session-specific artifacts

### Fixed
- Code formatting applied to test files for consistency

## [1.1.8] - 2025-10-01

### Added - MCP Testing Framework (Phase 5)
- **Comprehensive MCP Testing Suite** (151+ tests across 7 test modules)
  - Unit tests (51+ tests) - Protocol and component validation
  - Integration tests - Multi-step operations and workflows
  - End-to-end tests - Complete user scenarios
  - Performance tests (78 tests) - Latency, throughput, memory profiling
  - Compliance tests (73 tests) - JSON-RPC 2.0 and MCP protocol validation

- **MCP Diagnostic Commands**
  - `kuzu-memory mcp diagnose run` - Complete diagnostic suite
  - `kuzu-memory mcp diagnose config` - Configuration validation with auto-fix
  - `kuzu-memory mcp diagnose connection` - Server connectivity testing
  - `kuzu-memory mcp diagnose tools` - Tool schema and execution validation
  - Support for text, JSON, and HTML report formats
  - Automatic fix capabilities for common configuration issues

- **MCP Health Monitoring**
  - `kuzu-memory mcp health` - Quick health status check
  - `kuzu-memory mcp health --detailed` - Comprehensive health reporting
  - `kuzu-memory mcp health --continuous` - Continuous monitoring mode
  - JSON output for integration with monitoring systems
  - Exit codes for automation and alerting

- **MCP Performance Benchmarking**
  - Latency testing (connection, tool calls, roundtrip) with percentile analysis
  - Throughput testing (sequential, concurrent, sustained load)
  - Memory usage profiling and leak detection
  - Concurrent load testing (50+ concurrent clients)
  - Performance regression detection with baseline tracking
  - pytest-benchmark integration for detailed performance analysis

- **MCP Protocol Compliance Validation**
  - JSON-RPC 2.0 specification compliance (36 tests)
  - MCP protocol compliance (37 tests)
  - Protocol version negotiation (2025-06-18, 2024-11-05)
  - Error code validation
  - Batch request handling
  - Tool discovery and execution validation

- **Documentation**
  - [MCP Testing Guide](docs/MCP_TESTING_GUIDE.md) - Comprehensive testing procedures
  - [MCP Diagnostics Reference](docs/MCP_DIAGNOSTICS.md) - Command reference and troubleshooting
  - [MCP Phase 5 Implementation Report](docs/MCP_PHASE5_IMPLEMENTATION_REPORT.md) - Technical details
  - Updated README.md with MCP testing section
  - Updated CLAUDE.md with MCP testing workflows

- **Makefile Targets**
  - `make mcp-test` - Complete MCP test suite
  - `make mcp-unit` - Unit tests only
  - `make mcp-integration` - Integration tests
  - `make mcp-e2e` - End-to-end tests
  - `make mcp-performance` - Performance tests
  - `make mcp-compliance` - Compliance tests
  - `make mcp-benchmark` - Performance benchmarks
  - `make mcp-diagnose` - Run diagnostics
  - `make mcp-health` - Health check
  - `make mcp-full` - Complete validation suite

### Improved
- **Test Infrastructure**
  - MCPConnectionTester framework for server lifecycle testing
  - MockClientSimulator for realistic client simulation
  - Comprehensive pytest fixtures for test data and scenarios
  - pytest markers for test categorization (unit, integration, e2e, performance, compliance)
  - Benchmark configuration for consistent performance measurement

- **Quality Gates**
  - MCP protocol compliance required for release
  - Performance thresholds enforced (connection <500ms, tool calls <1000ms)
  - Health diagnostics required before deployment
  - Automated regression detection

### Performance Thresholds (MCP)
- Connection latency: 100ms target, 500ms critical
- Tool call latency: 200ms target, 1000ms critical
- Roundtrip latency: 50ms target, 200ms critical
- Throughput: 100 ops/sec target, 50 ops/sec critical
- Memory per connection: 10MB target, 20MB critical
- Concurrent connections: 10 target, 5 critical
- Success rate: 95% target, 90% critical

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

[Unreleased]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.3.5...HEAD
[1.3.5]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.3.4...v1.3.5
[1.3.4]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.3.3...v1.3.4
[1.3.3]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.3.0...v1.3.2
[1.3.0]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.2.5...v1.3.0
[1.2.5]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.2.4...v1.2.5
[1.2.4]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.13...v1.2.0
[1.1.13]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.12...v1.1.13
[1.1.12]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.11...v1.1.12
[1.1.11]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.10...v1.1.11
[1.1.10]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.9...v1.1.10
[1.1.9]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.6...v1.1.9
[1.1.6]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.5...v1.1.6
[1.1.5]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/kuzu-memory/kuzu-memory/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/kuzu-memory/kuzu-memory/releases/tag/v1.0.0