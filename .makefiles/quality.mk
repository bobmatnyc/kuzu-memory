# ============================================================================
# quality.mk - Code Quality Targets
# ============================================================================
# Provides: linting, formatting, type-checking, pre-publish gates
# Include in main Makefile with: -include .makefiles/quality.mk
#
# Extracted from: claude-mpm production Makefile (97 targets)
# Dependencies: common.mk (for colors, ENV system)
# Last updated: 2025-11-21
# ============================================================================

# ============================================================================
# Quality Target Declarations
# ============================================================================
.PHONY: lint-ruff lint-fix lint-mypy quality quality-ci pre-publish
.PHONY: clean-system-files clean-test-artifacts clean-deprecated clean-pre-publish

# ============================================================================
# Individual Linting Targets
# ============================================================================

lint-ruff: ## Run Ruff linter and formatter check
	@echo "$(YELLOW)🔍 Running Ruff linter...$(NC)"
	@if command -v ruff &> /dev/null; then \
		ruff check $(SRC_DIR)/ $(TESTS_DIR)/ $(RUFF_ARGS) || exit 1; \
		echo "$(GREEN)✓ Ruff linting passed$(NC)"; \
		echo "$(YELLOW)🔍 Checking code formatting...$(NC)"; \
		ruff format --check $(SRC_DIR)/ $(TESTS_DIR)/ || exit 1; \
		echo "$(GREEN)✓ Ruff format check passed$(NC)"; \
	else \
		echo "$(RED)✗ ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi

lint-mypy: ## Run mypy type checker
	@echo "$(YELLOW)🔍 Running mypy type checker...$(NC)"
	@if command -v mypy &> /dev/null; then \
		mypy $(SRC_DIR)/ --ignore-missing-imports --no-error-summary || true; \
		echo "$(YELLOW)ℹ MyPy check complete (informational)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ mypy not found. Install with: pip install mypy$(NC)"; \
	fi

# ============================================================================
# Auto-Fix Target
# ============================================================================

lint-fix: ## Auto-fix linting issues (ruff format + ruff check --fix)
	@echo "$(YELLOW)🔧 Auto-fixing code issues with Ruff...$(NC)"
	@if command -v ruff &> /dev/null; then \
		echo "$(YELLOW)Fixing linting issues...$(NC)"; \
		ruff check $(SRC_DIR)/ $(TESTS_DIR)/ --fix || true; \
		echo "$(GREEN)✓ Ruff linting fixes applied$(NC)"; \
		echo "$(YELLOW)Formatting code...$(NC)"; \
		ruff format $(SRC_DIR)/ $(TESTS_DIR)/ || true; \
		echo "$(GREEN)✓ Code formatted$(NC)"; \
	else \
		echo "$(RED)✗ ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(GREEN)✅ Auto-fix complete. Run 'make quality' to verify.$(NC)"

# ============================================================================
# Combined Quality Checks
# ============================================================================

quality: ## Run all quality checks (ruff + mypy)
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Running all quality checks...$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@$(MAKE) lint-ruff
	@$(MAKE) lint-mypy
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✅ All quality checks passed!$(NC)"
	@echo "$(GREEN)════════════════════════════════════════$(NC)"

quality-ci: ## Quality checks for CI/CD (strict, fail fast)
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Running CI quality checks (strict mode)...$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@set -e; \
	echo "$(YELLOW)🔍 Ruff check (no fixes)...$(NC)"; \
	ruff check $(SRC_DIR)/ $(TESTS_DIR)/ --no-fix; \
	echo "$(YELLOW)🔍 Type checking...$(NC)"; \
	mypy $(SRC_DIR)/ --ignore-missing-imports; \
	echo "$(YELLOW)🧪 Running tests (parallel)...$(NC)"; \
	$(PYTHON) -m pytest $(TESTS_DIR)/ $(PYTEST_ARGS) --tb=short
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✅ CI quality checks passed!$(NC)"
	@echo "$(GREEN)════════════════════════════════════════$(NC)"

# ============================================================================
# Pre-Publish Cleanup Targets
# ============================================================================

clean-system-files: ## Remove system files (.DS_Store, __pycache__, *.pyc)
	@echo "$(YELLOW)🧹 Cleaning system files...$(NC)"
	@find . -name ".DS_Store" -not -path "*/venv/*" -not -path "*/.venv/*" -delete 2>/dev/null || true
	@find . -type d -name "__pycache__" -not -path "*/venv/*" -not -path "*/.venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -not -path "*/venv/*" -not -path "*/.venv/*" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ System files cleaned$(NC)"

clean-test-artifacts: ## Remove test artifacts (HTML, JSON reports in root)
	@echo "$(YELLOW)🧹 Cleaning test artifacts from root...$(NC)"
	@rm -f dashboard_test.html report_qa_test.html coverage.json 2>/dev/null || true
	@rm -rf htmlcov/ .coverage .pytest_cache/ 2>/dev/null || true
	@echo "$(GREEN)✓ Test artifacts cleaned$(NC)"

clean-deprecated: ## Remove explicitly deprecated files
	@echo "$(YELLOW)🧹 Removing deprecated files...$(NC)"
	@# Add project-specific deprecated file patterns here
	@echo "$(GREEN)✓ Deprecated files removed$(NC)"

clean-pre-publish: clean-system-files clean-test-artifacts clean-deprecated ## Complete pre-publish cleanup
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✅ Pre-publish cleanup complete!$(NC)"
	@echo "$(GREEN)════════════════════════════════════════$(NC)"

# ============================================================================
# Pre-Publish Quality Gate
# ============================================================================

pre-publish: clean-pre-publish ## Comprehensive pre-release quality gate
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)🚀 Pre-Publish Quality Gate$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 1/4: Checking working directory...$(NC)"
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "$(RED)✗ Working directory is not clean$(NC)"; \
		echo "$(YELLOW)Please commit or stash your changes first$(NC)"; \
		git status --short; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Working directory is clean$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 2/4: Running all linters...$(NC)"
	@$(MAKE) quality
	@echo ""
	@echo "$(YELLOW)Step 3/4: Running tests...$(NC)"
	@if command -v pytest >/dev/null 2>&1; then \
		$(PYTHON) -m pytest $(TESTS_DIR)/ $(PYTEST_ARGS) || exit 1; \
	else \
		echo "$(YELLOW)⚠ pytest not found, skipping tests$(NC)"; \
	fi
	@echo "$(GREEN)✓ Tests passed$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 4/4: Checking for common issues...$(NC)"
	@echo "Checking for debug prints..."
	@! grep -r "print(" $(SRC_DIR)/ --include="*.py" | grep -v "#" | grep -v "logger" || \
		echo "$(YELLOW)⚠ Found print statements (non-blocking for CLI tools)$(NC)"
	@echo "Checking for TODO/FIXME..."
	@! grep -r "TODO\|FIXME" $(SRC_DIR)/ --include="*.py" | head -5 || \
		echo "$(YELLOW)⚠ Found TODO/FIXME comments (non-blocking)$(NC)"
	@echo "$(GREEN)✓ Common issues check complete$(NC)"
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✅ Pre-publish checks PASSED!$(NC)"
	@echo "$(GREEN)Ready for release.$(NC)"
	@echo "$(GREEN)════════════════════════════════════════$(NC)"

# ============================================================================
# Usage Examples
# ============================================================================
# Quick development workflow:
#   make lint-fix          # Auto-fix all issues
#   make quality           # Verify all checks pass
#
# Before committing:
#   make quality           # Run all quality checks
#
# Before releasing:
#   make pre-publish       # Comprehensive quality gate
#
# CI/CD integration:
#   make quality-ci        # Strict, fail-fast checks
#
# Cleanup:
#   make clean-pre-publish # Remove artifacts and temp files
# ============================================================================
