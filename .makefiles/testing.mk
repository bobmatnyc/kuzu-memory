# ============================================================================
# testing.mk - Test Execution Targets
# ============================================================================
# Provides: test execution, coverage, parallel/serial modes
# Include in main Makefile with: -include .makefiles/testing.mk
#
# Extracted from: claude-mpm production Makefile (97 targets)
# Dependencies: common.mk (for PYTHON, ENV system, PYTEST_ARGS)
# Last updated: 2025-11-21
# ============================================================================

# ============================================================================
# Test Target Declarations
# ============================================================================
.PHONY: test test-serial test-parallel test-fast test-coverage
.PHONY: test-unit test-integration test-e2e

# ============================================================================
# Primary Test Targets
# ============================================================================

test: test-parallel ## Run tests with parallel execution (default, 3-4x faster)

test-parallel: ## Run tests in parallel using all available CPUs
	@echo "$(YELLOW)🧪 Running tests in parallel (using all CPUs)...$(NC)"
	@$(PYTHON) -m pytest $(TESTS_DIR)/ $(PYTEST_ARGS)
	@echo "$(GREEN)✓ Parallel tests completed$(NC)"

test-serial: ## Run tests serially for debugging (disables parallelization)
	@echo "$(YELLOW)🧪 Running tests serially (debugging mode)...$(NC)"
	@$(PYTHON) -m pytest $(TESTS_DIR)/ -n 0 -v
	@echo "$(GREEN)✓ Serial tests completed$(NC)"

# ============================================================================
# Fast Testing (Unit Tests Only)
# ============================================================================

test-fast: ## Run unit tests only in parallel (fastest)
	@echo "$(YELLOW)⚡ Running unit tests in parallel...$(NC)"
	@$(PYTHON) -m pytest $(TESTS_DIR)/ -n auto -m unit -v
	@echo "$(GREEN)✓ Unit tests completed$(NC)"

# ============================================================================
# Coverage Reporting
# ============================================================================

test-coverage: ## Run tests with coverage report (parallel)
	@echo "$(YELLOW)📊 Running tests with coverage...$(NC)"
	@$(PYTHON) -m pytest $(TESTS_DIR)/ -n auto \
		--cov=$(SRC_DIR) \
		--cov-report=html \
		--cov-report=term \
		--cov-report=term-missing
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"
	@echo "$(BLUE)View with: open htmlcov/index.html$(NC)"

# ============================================================================
# Test Category Targets
# ============================================================================

test-unit: ## Run unit tests only
	@echo "$(YELLOW)🧪 Running unit tests...$(NC)"
	@$(PYTHON) -m pytest $(TESTS_DIR)/ -n auto -m unit -v

test-integration: ## Run integration tests only
	@echo "$(YELLOW)🧪 Running integration tests...$(NC)"
	@$(PYTHON) -m pytest $(TESTS_DIR)/integration/ -n auto -v

test-e2e: ## Run end-to-end tests only
	@echo "$(YELLOW)🧪 Running e2e tests...$(NC)"
	@$(PYTHON) -m pytest $(TESTS_DIR)/e2e/ -n auto -v

# ============================================================================
# ENV-Specific Test Configurations
# ============================================================================
# The PYTEST_ARGS variable is configured in common.mk based on ENV:
#
# development (default):
#   PYTEST_ARGS := -n auto -v --tb=long
#   - Parallel execution with all CPUs
#   - Verbose output
#   - Long traceback for debugging
#
# staging:
#   PYTEST_ARGS := -n auto -v --tb=line
#   - Parallel execution
#   - Shorter traceback for CI logs
#
# production:
#   PYTEST_ARGS := -n auto -v --tb=short --strict-markers
#   - Parallel execution
#   - Minimal traceback
#   - Strict marker enforcement
#
# Override with: make ENV=production test
# ============================================================================

# ============================================================================
# Test Markers (requires pytest markers in pytest.ini)
# ============================================================================
# Example markers to configure in pytest.ini:
#
# [pytest]
# markers =
#     unit: Unit tests (fast, isolated)
#     integration: Integration tests (slower, multiple components)
#     e2e: End-to-end tests (slowest, full system)
#     slow: Tests that take >1s to run
#     database: Tests requiring database connection
#     network: Tests requiring network access
# ============================================================================

# ============================================================================
# Usage Examples
# ============================================================================
# Quick test run (parallel, all tests):
#   make test
#
# Debugging failing tests (serial, verbose):
#   make test-serial
#
# Fast feedback loop (unit tests only):
#   make test-fast
#
# Check coverage:
#   make test-coverage
#
# Run specific test categories:
#   make test-unit
#   make test-integration
#   make test-e2e
#
# Environment-specific testing:
#   make ENV=production test         # Strict, minimal output
#   make ENV=staging test             # Balanced settings
#   make ENV=development test         # Verbose, detailed errors
#
# Run specific test file:
#   pytest tests/test_specific.py -v
#
# Run tests matching pattern:
#   pytest -k "test_auth" -v
# ============================================================================
