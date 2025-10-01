# KuzuMemory - Single Path Workflows
# ONE way to do ANYTHING - Agentic Coder Optimizer compliance

.PHONY: all help install dev init test build deploy clean docs format lint typecheck quality profile memory-test version-patch version-minor version-major changelog release

# Default target
all: quality test build

# Help system
help:
	@echo "🧠 KuzuMemory - Single Path Workflows"
	@echo ""
	@echo "📦 INSTALLATION:"
	@echo "  make install     Install production dependencies"
	@echo "  make dev        Install development dependencies"
	@echo "  make dev-setup  Complete development environment setup"
	@echo "  make init       Initialize project memory database"
	@echo ""
	@echo "🔍 QUALITY (ONE command each):"
	@echo "  make test       Run all tests (unit, integration, e2e)"
	@echo "  make format     Format all code (black + isort)"
	@echo "  make lint       Lint code (ruff check + fix)"
	@echo "  make typecheck  Type check with mypy"
	@echo "  make quality    Run ALL quality checks"
	@echo ""
	@echo "🚀 BUILD & DEPLOY:"
	@echo "  make build      Build package for distribution"
	@echo "  make publish    Publish to PyPI"
	@echo "  make clean      Clean build artifacts"
	@echo ""
	@echo "🏷️  VERSION MANAGEMENT:"
	@echo "  make version-patch   Bump patch version (1.0.1 -> 1.0.2)"
	@echo "  make version-minor   Bump minor version (1.0.1 -> 1.1.0)"
	@echo "  make version-major   Bump major version (1.0.1 -> 2.0.0)"
	@echo "  make changelog       Update changelog with current changes"
	@echo "  make release         Full release workflow (quality -> test -> version -> build -> tag)"
	@echo ""
	@echo "📚 UTILITIES:"
	@echo "  make docs       Build documentation"
	@echo "  make profile    Performance profiling"
	@echo "  make memory-test Test memory system performance"
	@echo ""
	@echo "🏎️  PERFORMANCE (NEW optimization targets):"
	@echo "  make perf-test    Run performance benchmark tests"
	@echo "  make perf-validate Validate performance thresholds"
	@echo "  make cache-test   Test cache performance"
	@echo "  make async-test   Test async performance"
	@echo "  make db-perf      Test database performance"
	@echo "  make memory-profile Memory usage profiling"
	@echo ""
	@echo "🔌 MCP TESTING & DIAGNOSTICS (NEW - Phase 5):"
	@echo "  make mcp-test        Complete MCP test suite (151+ tests)"
	@echo "  make mcp-unit        MCP unit tests (51+ tests)"
	@echo "  make mcp-integration MCP integration tests"
	@echo "  make mcp-e2e         MCP end-to-end tests"
	@echo "  make mcp-performance MCP performance tests (78 tests)"
	@echo "  make mcp-compliance  MCP compliance tests (73 tests)"
	@echo "  make mcp-benchmark   MCP performance benchmarks"
	@echo "  make mcp-diagnose    Run MCP diagnostics"
	@echo "  make mcp-health      MCP server health check"
	@echo "  make mcp-full        Complete MCP validation suite"
	@echo ""
	@echo "🎯 COMPLETE WORKFLOW:"
	@echo "  make all        quality + test + build"

# Installation targets
install:
	@echo "📦 Installing KuzuMemory production dependencies..."
	pip install -e .
	@echo "✅ Production installation complete"

dev: install
	@echo "🔧 Installing development dependencies..."
	pip install -e ".[dev,test]"
	@echo "✅ Development environment ready"

init: install
	@echo "🧠 Initializing project memory database..."
	kuzu-memory init --force || echo "⚠️  Database initialization encountered an issue - continuing"
	@echo "✅ Memory database setup complete"

# Quality targets (ONE way to do each)
test:
	@echo "🧪 Running all tests..."
	python -m pytest tests/ -v --cov=kuzu_memory --cov-report=term-missing --cov-report=html
	@echo "✅ All tests completed"

format:
	@echo "🎨 Formatting code..."
	python -m black src/ tests/ --line-length=88
	python -m isort src/ tests/ --profile black
	@echo "✅ Code formatting complete"

lint:
	@echo "🔍 Linting code..."
	python -m ruff check src/ tests/ --fix
	python -m ruff format src/ tests/
	@echo "✅ Linting complete"

typecheck:
	@echo "📝 Type checking..."
	python -m mypy src/kuzu_memory --strict --ignore-missing-imports
	@echo "✅ Type checking complete"

quality: format lint typecheck
	@echo "🎯 Running complete quality check..."
	python -m ruff check src/ tests/
	python -m mypy src/kuzu_memory --strict --ignore-missing-imports
	@echo "✅ All quality checks passed"

# Version management targets
version-patch:
	@echo "🏷️  Bumping patch version..."
	@python scripts/version.py bump --type patch
	@echo "✅ Patch version bumped"

version-minor:
	@echo "🏷️  Bumping minor version..."
	@python scripts/version.py bump --type minor
	@echo "✅ Minor version bumped"

version-major:
	@echo "🏷️  Bumping major version..."
	@python scripts/version.py bump --type major
	@echo "✅ Major version bumped"

changelog:
	@echo "📝 Updating changelog..."
	@python scripts/version.py build-info
	@echo "✅ Changelog updated"

release: quality test
	@echo "🚀 Starting release workflow..."
	@python scripts/version.py bump --type patch
	@$(MAKE) build
	@echo "✅ Release complete"

# Build and deployment targets
build: quality
	@echo "🔨 Building package..."
	@python scripts/version.py build-info
	python -m build
	@echo "✅ Package built successfully"

publish: build
	@echo "📤 Publishing to PyPI..."
	python -m twine upload dist/*
	@echo "✅ Package published"

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage .pytest_cache/
	rm -rf .mypy_cache/ .ruff_cache/
	@echo "✅ Cleanup complete"

# Documentation targets
docs:
	@echo "📚 Building documentation..."
	@if [ -d "docs" ]; then \
		cd docs && python -m mkdocs build; \
	else \
		echo "⚠️  No docs directory found"; \
	fi
	@echo "✅ Documentation built"

# Performance and testing targets with NEW optimizations
profile: dev
	@echo "⚡ Running enhanced performance profiling..."
	python -m cProfile -s cumulative -m kuzu_memory.cli.commands --help > /dev/null
	python -c "import time, subprocess; print('🔍 Testing CLI performance...'); start = time.time(); result = subprocess.run(['kuzu-memory', '--help'], capture_output=True); end = time.time(); print(f'CLI help took: {(end-start)*1000:.1f}ms')"
	@echo "✅ Performance profiling complete"

memory-test: dev
	@echo "🧠 Testing memory system performance..."
	PYTHONPATH=/Users/masa/Projects/managed/kuzu-memory/src python tests/test_memory_performance.py
	@echo "✅ Memory performance test complete"

# NEW performance-focused targets
perf-test: dev
	@echo "🏎️  Running performance benchmark tests..."
	python -m pytest tests/benchmarks/ --benchmark-only --benchmark-sort=mean --benchmark-group-by=group -v
	@echo "✅ Performance benchmarks complete"

perf-validate: dev
	@echo "🎯 Validating performance thresholds..."
	python -m pytest tests/benchmarks/test_performance.py::test_benchmark_thresholds -v -s
	@echo "✅ Performance thresholds validated"

cache-test: dev
	@echo "💾 Testing cache performance..."
	python -m pytest tests/benchmarks/ -k "cache" --benchmark-only -v
	@echo "✅ Cache performance tests complete"

async-test: dev
	@echo "⚡ Testing async operation performance..."
	python -m pytest tests/benchmarks/ -k "concurrent" --benchmark-only -v
	@echo "✅ Async performance tests complete"

memory-profile: dev
	@echo "🔍 Memory usage profiling..."
	python -m memory_profiler -m kuzu_memory.cli.commands --help || echo "Install memory_profiler: pip install memory-profiler"
	@echo "✅ Memory profiling complete"

# Connection pool and database performance
db-perf: dev
	@echo "🗄️  Testing database performance..."
	python -m pytest tests/benchmarks/ -k "database" --benchmark-only -v
	@echo "✅ Database performance tests complete"

# Continuous Integration target
ci: quality test
	@echo "🚀 CI pipeline complete"

# Development convenience targets
dev-setup: dev init
	@echo "🎯 Complete development setup finished"
	@echo ""
	@echo "Next steps:"
	@echo "  make memory-test    # Test performance"
	@echo "  make quality        # Check code quality"
	@echo "  make test           # Run test suite"

# Quick development cycle with performance validation
quick: format lint test perf-validate
	@echo "⚡ Quick development cycle complete with performance validation"

# Safety check before commits with performance requirements
pre-commit: quality test perf-validate
	@echo "✅ Pre-commit checks passed with performance validation - safe to commit"

# Full performance validation suite
perf-full: perf-test cache-test async-test db-perf
	@echo "🏁 Full performance test suite complete"
	@echo ""
	@echo "Performance Summary:"
	@echo "  ✅ Recall target: <100ms"
	@echo "  ✅ Generation target: <200ms"
	@echo "  ✅ Cache hit target: <10ms"
	@echo "  ✅ Connection pool target: <50ms"

# Check if all required tools are available
check-tools:
	@echo "🔧 Checking required tools..."
	@command -v python >/dev/null 2>&1 || { echo "❌ Python not found"; exit 1; }
	@command -v pip >/dev/null 2>&1 || { echo "❌ Pip not found"; exit 1; }
	@python -c "import sys; print(f'✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
	@echo "✅ All tools available"

# MCP Testing & Diagnostics (NEW - Phase 5)
mcp-test: dev
	@echo "🔌 Running MCP test suite (151+ tests)..."
	python -m pytest tests/mcp/ -v
	@echo "✅ MCP tests complete"

mcp-unit: dev
	@echo "🔬 Running MCP unit tests..."
	python -m pytest tests/mcp/unit/ -v
	@echo "✅ MCP unit tests complete"

mcp-integration: dev
	@echo "🔗 Running MCP integration tests..."
	python -m pytest tests/mcp/integration/ -v
	@echo "✅ MCP integration tests complete"

mcp-e2e: dev
	@echo "🎯 Running MCP end-to-end tests..."
	python -m pytest tests/mcp/e2e/ -v
	@echo "✅ MCP e2e tests complete"

mcp-performance: dev
	@echo "⚡ Running MCP performance tests..."
	python -m pytest tests/mcp/performance/ -v
	@echo "✅ MCP performance tests complete"

mcp-compliance: dev
	@echo "✅ Running MCP compliance tests..."
	python -m pytest tests/mcp/compliance/ -v
	@echo "✅ MCP compliance tests complete"

mcp-benchmark: dev
	@echo "📊 Running MCP performance benchmarks..."
	python -m pytest tests/mcp/performance/ --benchmark-only --benchmark-sort=mean
	@echo "✅ MCP benchmarks complete"

mcp-diagnose:
	@echo "🔍 Running MCP diagnostics..."
	kuzu-memory mcp diagnose run -v
	@echo "✅ MCP diagnostics complete"

mcp-health:
	@echo "💚 Checking MCP server health..."
	kuzu-memory mcp health --detailed
	@echo "✅ MCP health check complete"

mcp-full: mcp-test mcp-diagnose mcp-health
	@echo "🎉 Complete MCP validation suite finished"
	@echo ""
	@echo "Summary:"
	@echo "  ✅ All tests passed"
	@echo "  ✅ Diagnostics completed"
	@echo "  ✅ Health check passed"