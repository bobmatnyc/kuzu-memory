# ============================================================================
# common.mk - Core Makefile Infrastructure
# ============================================================================
# Provides: strict error handling, colors, ENV system, build metadata
# Include in main Makefile with: -include .makefiles/common.mk
#
# Extracted from: claude-mpm production Makefile (tested with 97 targets)
# Last updated: 2025-11-21
# ============================================================================

# ============================================================================
# Strict Error Handling
# ============================================================================
# Enable bash strict mode for safer shell execution
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# ============================================================================
# Terminal Colors
# ============================================================================
# ANSI color codes for terminal output formatting
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m  # No Color

# ============================================================================
# Environment Detection & Configuration
# ============================================================================
# Environment-based configuration system
# Supports: development (default), staging, production
# Override with: make ENV=production <target>
ENV ?= development
export ENV

# Detect user's shell for compatibility
DETECTED_SHELL := $(shell echo $$SHELL | grep -o '[^/]*$$')

# ENV-specific configurations
# Customize these for your project's needs
ifeq ($(ENV),production)
    # Production: strict, fast, minimal output
    PYTEST_ARGS := -n auto -v --tb=short --strict-markers
    BUILD_FLAGS := --no-isolation
    RUFF_ARGS := --quiet
else ifeq ($(ENV),staging)
    # Staging: balanced settings for pre-production testing
    PYTEST_ARGS := -n auto -v --tb=line
    BUILD_FLAGS :=
    RUFF_ARGS :=
else
    # Development (default): verbose, helpful errors
    PYTEST_ARGS := -n auto -v --tb=long
    BUILD_FLAGS :=
    RUFF_ARGS := --verbose
endif

# ============================================================================
# Build Metadata (optional - customize for your project)
# ============================================================================
# Version and build tracking files
VERSION_FILE ?= VERSION
BUILD_NUMBER_FILE ?= BUILD_NUMBER

# ============================================================================
# Directory Variables
# ============================================================================
# Standard Python project directories
BUILD_DIR := build
DIST_DIR := dist
SRC_DIR := src
TESTS_DIR := tests

# ============================================================================
# Utility Functions
# ============================================================================
# Check if command exists in PATH
command-exists = $(shell command -v $(1) 2>/dev/null)

# Get Python binary (prefer python3 over python)
PYTHON := $(or $(call command-exists,python3),$(call command-exists,python))

# Get current version (if VERSION file exists)
ifneq (,$(wildcard $(VERSION_FILE)))
    VERSION := $(shell cat $(VERSION_FILE))
endif

# Get current build number (if BUILD_NUMBER file exists)
ifneq (,$(wildcard $(BUILD_NUMBER_FILE)))
    BUILD_NUMBER := $(shell cat $(BUILD_NUMBER_FILE))
endif

# ============================================================================
# Environment Information Target
# ============================================================================
.PHONY: env-info

env-info: ## Display current environment configuration
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Environment Configuration$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "Environment: $(ENV)"
	@echo "Python: $$($(PYTHON) --version 2>&1)"
	@echo "Shell: $(DETECTED_SHELL)"
	@echo "Version: $(or $(VERSION),unknown)"
	@echo "Build: $(or $(BUILD_NUMBER),unknown)"
	@echo ""
	@echo "$(YELLOW)Environment-Specific Settings:$(NC)"
	@echo "Pytest Args: $(PYTEST_ARGS)"
	@echo "Build Flags: $(BUILD_FLAGS)"
	@echo "Ruff Args: $(RUFF_ARGS)"
	@echo ""
	@echo "$(GREEN)To change environment:$(NC)"
	@echo "  make ENV=production <target>"
	@echo "  make ENV=staging <target>"

# ============================================================================
# Usage Examples
# ============================================================================
# Include in your main Makefile:
#   -include .makefiles/common.mk
#
# Override variables:
#   VERSION_FILE := VERSION.txt
#   SRC_DIR := lib
#
# Use colors in targets:
#   @echo "$(GREEN)✓ Success!$(NC)"
#   @echo "$(YELLOW)⚠ Warning$(NC)"
#   @echo "$(RED)✗ Error$(NC)"
#
# Use ENV system:
#   make ENV=production build
#   make ENV=staging test
# ============================================================================
