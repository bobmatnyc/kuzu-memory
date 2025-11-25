# ============================================================================
# release.mk - Version & Publishing Management
# ============================================================================
# Provides: version bumping, build, publish to PyPI, GitHub releases
# Include in main Makefile with: -include .makefiles/release.mk
#
# Extracted from: claude-mpm production Makefile (97 targets)
# Dependencies: common.mk (for colors, VERSION, PYTHON, ENV)
#               quality.mk (for pre-publish checks)
# Last updated: 2025-11-21
# ============================================================================

# ============================================================================
# Release Target Declarations
# ============================================================================
.PHONY: release-check release-patch release-minor release-major
.PHONY: release-build release-publish release-verify
.PHONY: release-dry-run release-test-pypi
.PHONY: build-metadata build-info-json
.PHONY: patch minor major

# ============================================================================
# Release Prerequisites Check
# ============================================================================

release-check: ## Check if environment is ready for release
	@echo "$(YELLOW)🔍 Checking release prerequisites...$(NC)"
	@echo "Checking required tools..."
	@command -v git >/dev/null 2>&1 || (echo "$(RED)✗ git not found$(NC)" && exit 1)
	@command -v $(PYTHON) >/dev/null 2>&1 || (echo "$(RED)✗ python not found$(NC)" && exit 1)
	@command -v gh >/dev/null 2>&1 || (echo "$(RED)✗ GitHub CLI not found. Install from: https://cli.github.com/$(NC)" && exit 1)
	@echo "$(GREEN)✓ All required tools found$(NC)"
	@echo "Checking working directory..."
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "$(RED)✗ Working directory is not clean$(NC)"; \
		git status --short; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Working directory is clean$(NC)"
	@echo "Checking current branch..."
	@BRANCH=$$(git branch --show-current); \
	if [ "$$BRANCH" != "main" ]; then \
		echo "$(YELLOW)⚠ Currently on branch '$$BRANCH', not 'main'$(NC)"; \
		read -p "Continue anyway? [y/N]: " confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo "$(RED)Aborted$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(GREEN)✓ On main branch$(NC)"; \
	fi
	@echo "$(GREEN)✓ Release prerequisites check passed$(NC)"

# ============================================================================
# Build Metadata Tracking
# ============================================================================

build-metadata: ## Track build metadata in JSON format
	@echo "$(YELLOW)📋 Tracking build metadata...$(NC)"
	@mkdir -p $(BUILD_DIR)
	@VERSION=$$(cat $(VERSION_FILE) 2>/dev/null || echo "0.0.0"); \
	BUILD_NUM=$$(cat $(BUILD_NUMBER_FILE) 2>/dev/null || echo "0"); \
	COMMIT=$$(git rev-parse HEAD 2>/dev/null || echo "unknown"); \
	SHORT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown"); \
	BRANCH=$$(git branch --show-current 2>/dev/null || echo "unknown"); \
	TIMESTAMP=$$(date -u +%Y-%m-%dT%H:%M:%SZ); \
	PYTHON_VER=$$($(PYTHON) --version 2>&1); \
	echo "{" > $(BUILD_DIR)/metadata.json; \
	echo '  "version": "'$$VERSION'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "build_number": '$$BUILD_NUM',' >> $(BUILD_DIR)/metadata.json; \
	echo '  "commit": "'$$COMMIT'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "commit_short": "'$$SHORT_COMMIT'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "branch": "'$$BRANCH'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "timestamp": "'$$TIMESTAMP'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "python_version": "'$$PYTHON_VER'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "environment": "'$${ENV:-development}'"' >> $(BUILD_DIR)/metadata.json; \
	echo "}" >> $(BUILD_DIR)/metadata.json
	@echo "$(GREEN)✓ Build metadata saved to $(BUILD_DIR)/metadata.json$(NC)"

build-info-json: build-metadata ## Display build metadata from JSON
	@if [ -f $(BUILD_DIR)/metadata.json ]; then \
		cat $(BUILD_DIR)/metadata.json; \
	else \
		echo "$(YELLOW)No build metadata found. Run 'make build-metadata' first.$(NC)"; \
	fi

# ============================================================================
# Version Bumping (requires VERSION file)
# ============================================================================
# NOTE: These targets assume a VERSION file exists.
# Customize the version bumping logic for your project's needs.
# Example: Use `bump2version`, `python-semantic-release`, or custom script.
# ============================================================================

patch: ## Bump patch version (X.Y.Z+1)
	@echo "$(YELLOW)🔧 Bumping patch version...$(NC)"
	@python3 scripts/version.py bump --type patch
	@echo "$(GREEN)✓ Version bumped$(NC)"

minor: ## Bump minor version (X.Y+1.0)
	@echo "$(YELLOW)✨ Bumping minor version...$(NC)"
	@python3 scripts/version.py bump --type minor
	@echo "$(GREEN)✓ Version bumped$(NC)"

major: ## Bump major version (X+1.0.0)
	@echo "$(YELLOW)💥 Bumping major version...$(NC)"
	@python3 scripts/version.py bump --type major
	@echo "$(GREEN)✓ Version bumped$(NC)"

# ============================================================================
# Release Build
# ============================================================================

release-build: pre-publish ## Build Python package for release (runs quality checks first)
	@echo "$(YELLOW)📦 Building package...$(NC)"
	@$(MAKE) build-metadata
	@rm -rf $(DIST_DIR)/ $(BUILD_DIR)/ *.egg-info
	@$(PYTHON) -m build $(BUILD_FLAGS)
	@if command -v twine >/dev/null 2>&1; then \
		twine check $(DIST_DIR)/*; \
		echo "$(GREEN)✓ Package validation passed$(NC)"; \
	else \
		echo "$(YELLOW)⚠ twine not found, skipping package validation$(NC)"; \
	fi
	@echo "$(GREEN)✓ Package built successfully$(NC)"
	@ls -la $(DIST_DIR)/

# ============================================================================
# Release Workflow Shortcuts
# ============================================================================

release-patch: release-check patch release-build ## Create a patch release (X.Y.Z+1)
	@echo "$(GREEN)✓ Patch release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

release-minor: release-check minor release-build ## Create a minor release (X.Y+1.0)
	@echo "$(GREEN)✓ Minor release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

release-major: release-check major release-build ## Create a major release (X+1.0.0)
	@echo "$(GREEN)✓ Major release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

# ============================================================================
# Publishing to PyPI
# ============================================================================

release-publish: ## Publish release to PyPI and create GitHub release
	@echo "$(YELLOW)🚀 Publishing release...$(NC)"
	@VERSION=$$(cat $(VERSION_FILE)); \
	echo "Publishing version: $$VERSION"; \
	read -p "Continue with publishing? [y/N]: " confirm; \
	if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
		echo "$(RED)Publishing aborted$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📤 Publishing to PyPI...$(NC)"
	@if command -v twine >/dev/null 2>&1; then \
		$(PYTHON) -m twine upload $(DIST_DIR)/*; \
		echo "$(GREEN)✓ Published to PyPI$(NC)"; \
	else \
		echo "$(RED)✗ twine not found. Install with: pip install twine$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📤 Creating GitHub release...$(NC)"
	@VERSION=$$(cat $(VERSION_FILE)); \
	gh release create "v$$VERSION" \
		--title "v$$VERSION" \
		--generate-notes \
		$(DIST_DIR)/* || echo "$(YELLOW)⚠ GitHub release creation failed$(NC)"
	@echo "$(GREEN)✓ GitHub release created$(NC)"
	@$(MAKE) release-verify

release-test-pypi: release-build ## Publish to TestPyPI for testing
	@echo "$(YELLOW)🧪 Publishing to TestPyPI...$(NC)"
	@if command -v twine >/dev/null 2>&1; then \
		$(PYTHON) -m twine upload --repository testpypi $(DIST_DIR)/*; \
		echo "$(GREEN)✓ Published to TestPyPI$(NC)"; \
		echo "$(BLUE)Test install: pip install --index-url https://test.pypi.org/simple/ <package-name>$(NC)"; \
	else \
		echo "$(RED)✗ twine not found. Install with: pip install twine$(NC)"; \
		exit 1; \
	fi

# ============================================================================
# Release Verification
# ============================================================================

release-verify: ## Verify release across all channels
	@echo "$(YELLOW)🔍 Verifying release...$(NC)"
	@VERSION=$$(cat $(VERSION_FILE)); \
	echo "Verifying version: $$VERSION"; \
	echo ""; \
	echo "$(BLUE)📦 PyPI:$(NC) https://pypi.org/project/kuzu-memory/$$VERSION/"; \
	echo "$(BLUE)🏷️  GitHub:$(NC) https://github.com/KuzuDB/kuzu-memory/releases/tag/v$$VERSION"; \
	echo ""; \
	echo "$(GREEN)✓ Release verification links generated$(NC)"
	@echo "$(BLUE)💡 Test installation with:$(NC)"
	@echo "  pip install kuzu-memory==$$(cat $(VERSION_FILE))"

# ============================================================================
# Dry Run
# ============================================================================

release-dry-run: ## Show what a patch release would do (dry run)
	@echo "$(YELLOW)🔍 DRY RUN: Patch release preview$(NC)"
	@echo "This would:"
	@echo "  1. Check prerequisites and working directory"
	@echo "  2. Bump patch version"
	@echo "  3. Run pre-publish quality checks"
	@echo "  4. Build Python package"
	@echo "  5. Wait for confirmation to publish"
	@echo "  6. Publish to PyPI and create GitHub release"
	@echo "  7. Show verification links"
	@echo ""
	@echo "$(BLUE)Current version:$(NC) $$(cat $(VERSION_FILE) 2>/dev/null || echo 'unknown')"
	@if [ -f "$(VERSION_FILE)" ]; then \
		python3 scripts/version.py preview-changelog --type patch 2>/dev/null | head -1 || echo "$(YELLOW)Use 'python3 scripts/version.py bump patch' to see next version$(NC)"; \
	fi

# ============================================================================
# Usage Examples
# ============================================================================
# Full release workflow (patch):
#   make release-patch         # Bump version, run checks, build
#   make release-publish       # Publish to PyPI + GitHub
#
# Full release workflow (minor):
#   make release-minor         # Bump version, run checks, build
#   make release-publish       # Publish to PyPI + GitHub
#
# Full release workflow (major):
#   make release-major         # Bump version, run checks, build
#   make release-publish       # Publish to PyPI + GitHub
#
# Test release on TestPyPI:
#   make release-build
#   make release-test-pypi
#
# Preview release:
#   make release-dry-run
#
# Verify published release:
#   make release-verify
#
# IMPORTANT: Customize package name in release-verify target!
# Replace <package-name>, <owner>, <repo> with actual values.
# ============================================================================
