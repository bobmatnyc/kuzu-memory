# ============================================================================
# deps.mk - Dependency Management
# ============================================================================
# Provides: Poetry lock file management, installation, export
# Include in main Makefile with: -include .makefiles/deps.mk
#
# Extracted from: claude-mpm production Makefile (97 targets)
# Dependencies: common.mk (for colors, PYTHON)
# Last updated: 2025-11-21
# ============================================================================
#
# Workflow for updating dependencies:
#   1. make lock-check         - Verify current lock state
#   2. make lock-update        - Update to latest compatible versions
#   3. make test               - Test with updated deps
#   4. git diff poetry.lock    - Review changes
#   5. git add poetry.lock     - Commit if tests pass
#
# For reproducible installs:
#   make lock-install          - Install exact versions from lock file
#
# For CI/CD integration:
#   make lock-check            - Fail if lock file is outdated
#   make lock-export           - Generate requirements.txt for Docker
# ============================================================================

# ============================================================================
# Dependency Management Target Declarations
# ============================================================================
.PHONY: lock-deps lock-update lock-check lock-install lock-export lock-info
.PHONY: install install-prod install-dev

# ============================================================================
# Lock File Management
# ============================================================================

lock-deps: ## Lock dependencies without updating (poetry.lock)
	@echo "$(YELLOW)🔒 Locking dependencies...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry lock --no-update; \
		echo "$(GREEN)✓ Dependencies locked in poetry.lock$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-update: ## Update all dependencies to latest compatible versions
	@echo "$(YELLOW)⬆️  Updating dependencies...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry update; \
		echo "$(GREEN)✓ Dependencies updated$(NC)"; \
		echo "$(YELLOW)📋 Review changes with: git diff poetry.lock$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-check: ## Check if poetry.lock is up to date with pyproject.toml
	@echo "$(YELLOW)🔍 Checking lock file consistency...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry check; \
		poetry lock --check; \
		echo "$(GREEN)✓ Lock file is up to date$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-install: ## Install dependencies from lock file (reproducible)
	@echo "$(YELLOW)📦 Installing from lock file...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install --sync; \
		echo "$(GREEN)✓ Dependencies installed from poetry.lock$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-export: ## Export locked dependencies to requirements.txt format
	@echo "$(YELLOW)📤 Exporting dependencies...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry export -f requirements.txt --output requirements.txt --without-hashes; \
		poetry export -f requirements.txt --output requirements-dev.txt --with dev --without-hashes; \
		echo "$(GREEN)✓ Exported to requirements.txt and requirements-dev.txt$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-info: ## Display dependency lock information
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Dependency Lock Information$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@if [ -f poetry.lock ]; then \
		echo "$(GREEN)✓ poetry.lock exists$(NC)"; \
		echo ""; \
		echo "Lock file modified: $$(stat -f %Sm -t '%Y-%m-%d %H:%M:%S' poetry.lock 2>/dev/null || stat -c %y poetry.lock 2>/dev/null || echo 'unknown')"; \
		echo "Lock file size: $$(du -h poetry.lock | cut -f1)"; \
		echo ""; \
		if command -v poetry >/dev/null 2>&1; then \
			echo "$(YELLOW)Direct dependencies:$(NC)"; \
			poetry show --tree --only main | head -20; \
		fi; \
	else \
		echo "$(RED)✗ poetry.lock not found$(NC)"; \
		echo "$(YELLOW)  Run: make lock-deps$(NC)"; \
	fi

# ============================================================================
# Installation Targets
# ============================================================================

install: ## Install project in development mode with all dependencies
	@echo "$(YELLOW)📦 Installing project in development mode...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install; \
		echo "$(GREEN)✓ Project installed with all dependencies$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Poetry not found, falling back to pip...$(NC)"; \
		$(PYTHON) -m pip install -e ".[dev]"; \
		echo "$(GREEN)✓ Project installed with pip$(NC)"; \
	fi

install-prod: ## Install production dependencies only (no dev deps)
	@echo "$(YELLOW)📦 Installing production dependencies...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install --only main; \
		echo "$(GREEN)✓ Production dependencies installed$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Poetry not found, falling back to pip...$(NC)"; \
		$(PYTHON) -m pip install -e .; \
		echo "$(GREEN)✓ Production dependencies installed with pip$(NC)"; \
	fi

install-dev: install ## Alias for development installation

# ============================================================================
# Virtual Environment Management
# ============================================================================
# Note: Poetry manages its own virtual environments.
# If you need manual venv management, add these targets:
#
# .PHONY: venv venv-clean
#
# venv: ## Create virtual environment
# 	@echo "$(YELLOW)Creating virtual environment...$(NC)"
# 	@$(PYTHON) -m venv .venv
# 	@echo "$(GREEN)✓ Virtual environment created in .venv/$(NC)"
# 	@echo "$(BLUE)Activate with: source .venv/bin/activate$(NC)"
#
# venv-clean: ## Remove virtual environment
# 	@echo "$(YELLOW)Removing virtual environment...$(NC)"
# 	@rm -rf .venv
# 	@echo "$(GREEN)✓ Virtual environment removed$(NC)"
# ============================================================================

# ============================================================================
# Dependency Management Best Practices
# ============================================================================
# 1. Lock before committing:
#    Always run `make lock-check` before committing changes
#
# 2. Update dependencies regularly:
#    Run `make lock-update` weekly to get security patches
#
# 3. Review dependency changes:
#    Use `git diff poetry.lock` to review what changed
#
# 4. Test after updates:
#    Always run `make test` after `make lock-update`
#
# 5. CI/CD integration:
#    Add `make lock-check` to your CI pipeline
#
# 6. Docker builds:
#    Use `make lock-export` to generate requirements.txt for Docker
#
# 7. Reproducible builds:
#    Use `make lock-install` for deterministic installations
# ============================================================================

# ============================================================================
# Usage Examples
# ============================================================================
# Initial setup:
#   make install               # Install all dependencies (dev + prod)
#
# Production deployment:
#   make install-prod          # Install production dependencies only
#
# Update dependencies:
#   make lock-update           # Update to latest compatible versions
#   make test                  # Test with updated dependencies
#   git add poetry.lock        # Commit if tests pass
#
# CI/CD pipeline:
#   make lock-check            # Verify lock file is current
#   make lock-install          # Install from lock file
#   make test                  # Run tests
#
# Docker integration:
#   make lock-export           # Generate requirements.txt
#   # Use requirements.txt in Dockerfile
#
# Troubleshooting:
#   make lock-info             # View dependency tree
#   poetry show <package>      # Check specific package
#   poetry why <package>       # See why package is installed
# ============================================================================
