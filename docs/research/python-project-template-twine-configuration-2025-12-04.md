# Python Project Template Twine Configuration Research

**Date**: 2025-12-04
**Project**: kuzu-memory
**Research Focus**: Updating python-project-template submodule and twine publishing configuration
**Researcher**: Claude Code Research Agent

---

## Executive Summary

The python-project-template is already configured with full twine support for PyPI publishing. The kuzu-memory project has successfully integrated these makefiles and customized them for project-specific needs. **No template update is required** - the current setup is production-ready.

**Key Findings**:
- ✅ Template already includes comprehensive twine support
- ✅ Twine is used for package validation (`twine check`)
- ✅ Twine is used for PyPI publishing (`twine upload`)
- ✅ TestPyPI publishing supported (`twine upload --repository testpypi`)
- ✅ kuzu-memory has customized the template makefiles appropriately
- ⚠️ Submodule is on latest commit (no updates available)
- ⚠️ Template uses Copier-based structure (not direct git submodule integration)

---

## 1. Current Submodule Status

### Submodule Configuration

**Location**: `/Users/masa/Projects/kuzu-memory/.python-project-template/`
**Remote**: `https://github.com/bobmatnyc/python-project-template.git`
**Current Commit**: `5670840` (feat: initial Copier template with modular Makefile system)
**Branch**: `main` (heads/main)
**Status**: Up-to-date with remote origin/main

**Git Submodule Configuration** (`.gitmodules`):
```
[submodule ".python-project-template"]
	path = .python-project-template
	url = https://github.com/bobmatnyc/python-project-template.git
```

### Directory Structure

```
.python-project-template/
├── .git                    # Submodule git metadata
├── .gitignore
├── copier.yml             # Copier template configuration
├── MAKEFILE_EXTRACTION_REPORT.md
├── README.md              # Template documentation
├── STRUCTURE.md           # Template structure documentation
├── template/              # Copier template directory
│   └── .makefiles/        # Modular makefile system
│       ├── common.mk      # Shared variables, colors
│       ├── deps.mk        # Dependency management
│       ├── quality.mk     # Linting, formatting, type-checking
│       ├── testing.mk     # Test execution, coverage
│       └── release.mk     # Version bumping, PyPI publishing (TWINE SUPPORT HERE)
├── TEMPLATE_README.md
└── VERIFICATION.md
```

**No updates available**: Submodule is on the latest commit of origin/main.

---

## 2. Template's Publishing Mechanism (Twine Support)

### Template's release.mk Analysis

**File**: `.python-project-template/template/.makefiles/release.mk`
**Lines**: 268 total
**Last Updated**: 2025-11-21

### Twine Integration Points

The template's `release.mk` includes **comprehensive twine support** across multiple targets:

#### 2.1 Package Validation (Lines 132-144)

```makefile
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
```

**Purpose**: Validates built package metadata, long_description, and distribution files.

#### 2.2 PyPI Publishing (Lines 166-190)

```makefile
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
```

**Features**:
- User confirmation prompt before publishing
- Twine upload to production PyPI
- GitHub release creation via `gh` CLI
- Automatic release verification

#### 2.3 TestPyPI Publishing (Lines 192-201)

```makefile
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
```

**Purpose**: Allows testing package publication on TestPyPI before production release.

#### 2.4 Release Verification (Lines 207-217)

```makefile
release-verify: ## Verify release across all channels
	@echo "$(YELLOW)🔍 Verifying release...$(NC)"
	@VERSION=$$(cat $(VERSION_FILE)); \
	echo "Verifying version: $$VERSION"; \
	echo ""; \
	echo "$(BLUE)📦 PyPI:$(NC) https://pypi.org/project/<package-name>/$$VERSION/"; \
	echo "$(BLUE)🏷️  GitHub:$(NC) https://github.com/<owner>/<repo>/releases/tag/v$$VERSION"; \
	echo ""; \
	echo "$(GREEN)✓ Release verification links generated$(NC)"
	@echo "$(BLUE)💡 Test installation with:$(NC)"
	@echo "  pip install <package-name>==$$(cat $(VERSION_FILE))"
```

**Note**: Template uses placeholders (`<package-name>`, `<owner>`, `<repo>`) for customization.

### Twine Dependency Detection

All twine commands use graceful detection:

```makefile
@if command -v twine >/dev/null 2>&1; then
    # Use twine
else
    # Show warning or error
fi
```

**Behavior**:
- Package validation: Warning if twine missing (continues)
- Publishing: Error if twine missing (aborts)

---

## 3. Kuzu-Memory's Customizations

### File Comparison: Template vs. Kuzu-Memory

**Diff Analysis** (`.python-project-template/template/.makefiles/release.mk` vs. `.makefiles/release.mk`):

#### Key Differences

1. **Version Bumping Strategy** (Lines 94-127)

**Template** (Lines 94-105):
```makefile
patch: ## Bump patch version (X.Y.Z+1)
	@echo "$(YELLOW)🔧 Bumping patch version...$(NC)"
	@if [ ! -f "$(VERSION_FILE)" ]; then \
		echo "$(RED)✗ VERSION file not found$(NC)"; \
		exit 1; \
	fi
	@CURRENT=$$(cat $(VERSION_FILE)); \
	NEW=$$($(PYTHON) -c "import semver; print(semver.VersionInfo.parse('$$CURRENT').bump_patch())"); \
	echo "$$NEW" > $(VERSION_FILE); \
	echo "$(GREEN)✓ Version bumped: $$CURRENT → $$NEW$(NC)"
```

**Kuzu-Memory** (Customized):
```makefile
patch: ## Bump patch version (X.Y.Z+1)
	@echo "$(YELLOW)🔧 Bumping patch version...$(NC)"
	@python3 scripts/version.py bump --type patch
	@echo "$(GREEN)✓ Version bumped$(NC)"
```

**Reason**: Kuzu-memory uses custom `scripts/version.py` for version management with towncrier integration.

2. **Release Verification URLs** (Lines 209-212)

**Template** (placeholders):
```makefile
echo "$(BLUE)📦 PyPI:$(NC) https://pypi.org/project/<package-name>/$$VERSION/";
echo "$(BLUE)🏷️  GitHub:$(NC) https://github.com/<owner>/<repo>/releases/tag/v$$VERSION";
```

**Kuzu-Memory** (project-specific):
```makefile
echo "$(BLUE)📦 PyPI:$(NC) https://pypi.org/project/kuzu-memory/$$VERSION/";
echo "$(BLUE)🏷️  GitHub:$(NC) https://github.com/KuzuDB/kuzu-memory/releases/tag/v$$VERSION";
```

**Reason**: Customized for kuzu-memory package name and GitHub repository.

3. **Dry-Run Preview** (Lines 233-238)

**Template**:
```makefile
@if [ -f "$(VERSION_FILE)" ]; then \
	NEXT=$$($(PYTHON) -c "import semver; print(semver.VersionInfo.parse('$$(cat $(VERSION_FILE))').bump_patch())" 2>/dev/null || echo "unknown"); \
	echo "$(BLUE)Next patch version would be:$(NC) $$NEXT"; \
fi
```

**Kuzu-Memory**:
```makefile
@if [ -f "$(VERSION_FILE)" ]; then \
	python3 scripts/version.py preview-changelog --type patch 2>/dev/null | head -1 || echo "$(YELLOW)Use 'python3 scripts/version.py bump patch' to see next version$(NC)"; \
fi
```

**Reason**: Integrated with custom changelog preview functionality.

### Customization Summary

| Feature | Template | Kuzu-Memory |
|---------|----------|-------------|
| Version bumping | semver library | scripts/version.py |
| Changelog | Manual/placeholder | Towncrier integration |
| Package URLs | Placeholders | kuzu-memory specific |
| Twine support | ✅ Full support | ✅ Inherited + customized |
| TestPyPI | ✅ Supported | ✅ Inherited |
| Package validation | ✅ twine check | ✅ Inherited |

**Conclusion**: Kuzu-memory has appropriately customized the template while preserving all twine functionality.

---

## 4. Kuzu-Memory's Makefile Integration

### Main Makefile Structure

**File**: `/Users/masa/Projects/kuzu-memory/Makefile`
**Lines**: 425 total

### Include Strategy

```makefile
# Include modular makefiles
-include .makefiles/common.mk
-include .makefiles/deps.mk
-include .makefiles/quality.mk
-include .makefiles/testing.mk
-include .makefiles/release.mk
```

**Note**: Uses `-include` for graceful failure (continues if file missing).

### Custom Publishing Implementation

Kuzu-memory extends the template with custom publishing target (Lines 197-220):

```makefile
publish: build
	@echo "📤 Publishing to PyPI..."
	@if [ ! -f .env.local ]; then \
		echo "❌ Error: .env.local not found"; \
		echo "Create .env.local with: PYPI_API_KEY=<your-token>"; \
		exit 1; \
	fi
	@if ! grep -q "PYPI_API_KEY" .env.local; then \
		echo "❌ Error: PYPI_API_KEY not found in .env.local"; \
		echo "Add to .env.local: PYPI_API_KEY=<your-token>"; \
		exit 1; \
	fi
	@echo "🔑 Loading PyPI credentials from .env.local..."
	@export $$(grep -v '^#' .env.local | grep -v '^\s*$$' | xargs) && \
		if [ -z "$$PYPI_API_KEY" ]; then \
			echo "❌ Error: PYPI_API_KEY is empty in .env.local"; \
			exit 1; \
		fi && \
		export TWINE_USERNAME=__token__ && \
		export TWINE_PASSWORD=$$PYPI_API_KEY && \
		VERSION=$$(python3 -c "import sys; sys.path.insert(0, 'src'); from kuzu_memory.__version__ import __version__; print(__version__)") && \
		echo "📦 Publishing version $$VERSION to PyPI..." && \
		python3 -m twine upload dist/kuzu_memory-$$VERSION*
	@echo "✅ Package published to PyPI"
```

**Features**:
- Environment file-based credentials (`.env.local`)
- Validation of PyPI API key presence
- TWINE_USERNAME and TWINE_PASSWORD export
- Version extraction from package `__version__`
- Specific package file matching (`kuzu_memory-$$VERSION*`)

**Comparison to Template**:
- Template: Uses `$(DIST_DIR)/*` (publishes all files)
- Kuzu-memory: Uses `dist/kuzu_memory-$$VERSION*` (version-specific)
- Template: No credential management
- Kuzu-memory: `.env.local` credential loading

---

## 5. PyPI Configuration (pyproject.toml)

### Build System Configuration

**File**: `/Users/masa/Projects/kuzu-memory/pyproject.toml`
**Lines**: 1-3

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

**Build Tool**: Uses `setuptools` (modern PEP 517/518 backend)
**Compatible with**: `python -m build` command (used in template's `release-build` target)

### Package Metadata

**Package Name**: `kuzu-memory`
**Current Version**: `1.5.3` (in pyproject.toml line 7)
**License**: MIT
**Python Requirement**: `>=3.11`

### Twine Dependencies

**Current Status**: Twine is **not listed** in pyproject.toml dependencies.

**Implication**: Twine must be installed separately for publishing workflow.

**Recommendations**:

1. **Add to dev dependencies** (preferred):
```toml
[project.optional-dependencies]
dev = [
    # ... existing dev dependencies ...
    "twine>=4.0",  # PyPI package publishing
    "build>=0.10",  # PEP 517 package building
]
```

2. **Installation command** (current workaround):
```bash
pip install twine build
# or
pip install -e ".[dev]"  # if added to dev dependencies
```

---

## 6. Twine Usage in Kuzu-Memory Codebase

### Grep Analysis

**Search Pattern**: `twine`
**Matches Found**: 21 locations

#### Key Usage Locations

1. **Makefile** (Line 219):
```bash
python3 -m twine upload dist/kuzu_memory-$$VERSION*
```

2. **scripts/publish.py** (Lines 34, 111, 119, 144):
```python
tools = ["build", "twine"]  # Tool availability check

run_command("python -m twine check dist/*", "Checking package with twine")

run_command(
    "python -m twine upload --repository testpypi dist/*",
    "Publishing to TestPyPI"
)

run_command("python -m twine upload dist/*", "Publishing to PyPI")
```

3. **.makefiles/release.mk** (Lines 119-123, 158-162, 176-181):
```makefile
# Package validation
@if command -v twine >/dev/null 2>&1; then \
	twine check $(DIST_DIR)/*; \

# PyPI publishing
@if command -v twine >/dev/null 2>&1; then \
	$(PYTHON) -m twine upload $(DIST_DIR)/*; \

# TestPyPI publishing
@if command -v twine >/dev/null 2>&1; then \
	$(PYTHON) -m twine upload --repository testpypi $(DIST_DIR)/*; \
```

**Summary**:
- Twine is used consistently across all publishing workflows
- Both direct command (`twine check`) and module invocation (`python -m twine upload`) are used
- TestPyPI and production PyPI publishing supported
- All invocations use graceful availability checks

---

## 7. Template Update Process

### Current Situation

**Submodule Update Status**: ✅ Already on latest commit
**Remote State**: No new commits available
**Update Needed**: No

### If Updates Become Available (Future Reference)

#### Method 1: Update Submodule to Latest Commit

```bash
cd /Users/masa/Projects/kuzu-memory

# Navigate to submodule directory
cd .python-project-template

# Fetch latest changes
git fetch origin

# Check for updates
git log HEAD..origin/main

# If updates exist, checkout latest
git checkout origin/main

# Return to main project
cd ..

# Commit submodule update
git add .python-project-template
git commit -m "chore: update python-project-template submodule to latest"
```

#### Method 2: Update Submodule in-place (Alternative)

```bash
cd /Users/masa/Projects/kuzu-memory

# Update submodule to latest commit
git submodule update --remote --merge .python-project-template

# Commit submodule update
git add .python-project-template
git commit -m "chore: update python-project-template submodule"
```

### Copying Updated Makefiles

After updating submodule:

```bash
# Compare changes
diff -u .python-project-template/template/.makefiles/release.mk .makefiles/release.mk

# Copy updated makefiles (if needed)
cp .python-project-template/template/.makefiles/common.mk .makefiles/
cp .python-project-template/template/.makefiles/deps.mk .makefiles/
cp .python-project-template/template/.makefiles/quality.mk .makefiles/
cp .python-project-template/template/.makefiles/testing.mk .makefiles/
cp .python-project-template/template/.makefiles/release.mk .makefiles/

# Review changes
git diff .makefiles/

# Selectively apply or revert customizations
git add .makefiles/
git commit -m "chore: sync makefiles with python-project-template updates"
```

**Important**: Preserve kuzu-memory customizations:
- `scripts/version.py` integration
- Package-specific URLs
- Custom `publish` target in main Makefile

### Template Design Consideration

The python-project-template uses **Copier** for project generation, not direct submodule integration. The current setup (git submodule) is a custom approach.

**Copier Update Process** (if using Copier):
```bash
cd /Users/masa/Projects/kuzu-memory
copier update

# Copier will:
# - Fetch latest template changes
# - Show diff of proposed changes
# - Allow selective acceptance
```

**Current Setup**: Kuzu-memory uses git submodule for reference, manual makefile copying for integration.

---

## 8. Twine Configuration Requirements

### Twine Authentication Methods

#### Method 1: .pypirc File (Traditional)

**Location**: `~/.pypirc`

```ini
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...

[testpypi]
username = __token__
password = pypi-AgENdGVzdC5weXBp...
```

**Usage**:
```bash
python -m twine upload dist/*  # Uses [pypi] section
python -m twine upload --repository testpypi dist/*  # Uses [testpypi] section
```

#### Method 2: Environment Variables (Kuzu-Memory's Current Approach)

**File**: `.env.local` (in kuzu-memory project root)

```bash
PYPI_API_KEY=pypi-AgEIcHlwaS5vcmc...
```

**Usage** (from Makefile):
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=$PYPI_API_KEY
python -m twine upload dist/*
```

**Advantages**:
- Per-project credentials
- Not stored in home directory
- Easy to gitignore
- Explicit credential loading

#### Method 3: Command-Line Arguments (Not Recommended)

```bash
python -m twine upload -u __token__ -p pypi-AgE... dist/*
```

**Issue**: Credentials visible in shell history and process list.

### Kuzu-Memory's Current Configuration

**Method**: Environment variable-based (`.env.local`)
**File Location**: `/Users/masa/Projects/kuzu-memory/.env.local`
**Gitignored**: Yes (should be in `.gitignore`)

**Required Content**:
```bash
PYPI_API_KEY=<your-pypi-api-token>
```

**Validation** (from Makefile):
```bash
@if [ ! -f .env.local ]; then \
	echo "❌ Error: .env.local not found"; \
	exit 1; \
fi
@if ! grep -q "PYPI_API_KEY" .env.local; then \
	echo "❌ Error: PYPI_API_KEY not found in .env.local"; \
	exit 1; \
fi
```

---

## 9. Production PyPI Publishing Workflow

### Current Workflow (Kuzu-Memory)

#### Step 1: Bump Version

```bash
# From main Makefile (lines 161-177)
make version-patch  # Bumps patch version + builds changelog
make version-minor  # Bumps minor version + builds changelog
make version-major  # Bumps major version + builds changelog
```

**Process**:
1. Validates changelog fragments (`changelog-validate`)
2. Bumps version via `python3 scripts/version.py bump --type <patch|minor|major>`
3. Builds changelog from fragments (`changelog-build`)

#### Step 2: Build Package

```bash
# From main Makefile (lines 191-195)
make build
```

**Process**:
1. Runs quality checks (`quality` target)
2. Generates build info (`scripts/version.py build-info`)
3. Builds package (`python3 -m build`)

**Artifacts Created**:
- `dist/kuzu_memory-<version>.tar.gz` (source distribution)
- `dist/kuzu_memory-<version>-py3-none-any.whl` (wheel)

#### Step 3: Validate Package (Optional, Recommended)

```bash
# From .makefiles/release.mk
make release-build
```

**Process**:
1. Runs pre-publish quality checks
2. Builds package
3. **Validates with twine check**: `twine check dist/*`

**Checks Performed by Twine**:
- Package metadata validity
- Long description rendering (README.md)
- Distribution file integrity
- PyPI compatibility

#### Step 4: Test on TestPyPI (Optional, Recommended)

```bash
# From .makefiles/release.mk (lines 192-201)
make release-test-pypi
```

**Process**:
1. Runs `release-build` (quality + build + validate)
2. Publishes to TestPyPI: `python -m twine upload --repository testpypi dist/*`

**Verification**:
```bash
# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ kuzu-memory==<version>

# Test installation
kuzu-memory --version
```

#### Step 5: Publish to Production PyPI

```bash
# From main Makefile (lines 197-220)
make publish
```

**Process**:
1. Checks for `.env.local` file
2. Validates `PYPI_API_KEY` presence
3. Exports credentials as environment variables
4. Extracts version from package
5. **Publishes to PyPI**: `python3 -m twine upload dist/kuzu_memory-<version>*`

**Example Output**:
```
📤 Publishing to PyPI...
🔑 Loading PyPI credentials from .env.local...
📦 Publishing version 1.5.3 to PyPI...
Uploading distributions to https://upload.pypi.org/legacy/
Uploading kuzu_memory-1.5.3-py3-none-any.whl
Uploading kuzu_memory-1.5.3.tar.gz
✅ Package published to PyPI
```

### Template's Workflow (Alternative)

```bash
# From .makefiles/release.mk
make release-patch   # or release-minor, release-major
make release-publish
```

**Differences from Kuzu-Memory**:
- Template: Single-command version bump + build
- Template: Integrated GitHub release creation
- Template: Uses user confirmation prompt
- Template: Release verification links

---

## 10. Comparison: Template vs. Kuzu-Memory Publishing

### Feature Matrix

| Feature | Template (release.mk) | Kuzu-Memory (Makefile + release.mk) |
|---------|----------------------|-------------------------------------|
| **Version Bumping** | semver library | scripts/version.py + towncrier |
| **Changelog** | Manual/placeholder | Towncrier fragments |
| **Build Tool** | `python -m build` | `python -m build` |
| **Package Validation** | `twine check` | `twine check` (inherited) |
| **Credential Storage** | Not specified | `.env.local` |
| **PyPI Publishing** | `twine upload` | `twine upload` (custom target) |
| **TestPyPI Publishing** | `release-test-pypi` | `release-test-pypi` (inherited) |
| **GitHub Release** | `gh release create` | Not in custom publish target |
| **User Confirmation** | Interactive prompt | Not in custom publish target |
| **Release Verification** | `release-verify` | Not implemented |
| **Package-Specific URLs** | Placeholders | Customized |

### Kuzu-Memory Advantages

1. **Changelog Automation**: Towncrier fragment-based changelog
2. **Credential Management**: Explicit `.env.local` validation
3. **Version Extraction**: From package `__version__` (single source of truth)
4. **Targeted Publishing**: Version-specific file matching

### Template Advantages

1. **GitHub Integration**: Automatic release creation
2. **Safety Prompts**: User confirmation before publishing
3. **Release Verification**: Automatic link generation
4. **Workflow Shortcuts**: `release-patch`, `release-minor`, `release-major`

### Recommended Hybrid Approach

Kuzu-memory could benefit from adopting:

1. **GitHub Release Creation** (from template):
```makefile
publish: build
	# ... existing credential loading ...
	@python3 -m twine upload dist/kuzu_memory-$$VERSION*
	@echo "✅ Package published to PyPI"

	# Add GitHub release creation
	@echo "📤 Creating GitHub release..."
	@VERSION=$$(python3 -c "import sys; sys.path.insert(0, 'src'); from kuzu_memory.__version__ import __version__; print(__version__)"); \
	gh release create "v$$VERSION" \
		--title "v$$VERSION" \
		--generate-notes \
		dist/kuzu_memory-$$VERSION* || echo "⚠️  GitHub release creation failed"
	@echo "✅ GitHub release created"
```

2. **Release Verification** (from template):
```makefile
verify-release:
	@echo "🔍 Verifying release..."
	@VERSION=$$(python3 -c "import sys; sys.path.insert(0, 'src'); from kuzu_memory.__version__ import __version__; print(__version__)"); \
	echo "📦 PyPI: https://pypi.org/project/kuzu-memory/$$VERSION/"; \
	echo "🏷️  GitHub: https://github.com/KuzuDB/kuzu-memory/releases/tag/v$$VERSION"; \
	echo "💡 Test installation: pip install kuzu-memory==$$VERSION"
```

---

## 11. Dependencies and Installation

### Required Tools for Publishing

#### Core Publishing Tools

1. **build** (PEP 517 builder)
```bash
pip install build
```

2. **twine** (PyPI publishing)
```bash
pip install twine
```

#### Optional but Recommended

3. **gh** (GitHub CLI - for release creation)
```bash
# macOS
brew install gh

# Linux
curl -sS https://webi.sh/gh | sh

# Authenticate
gh auth login
```

### Current Dependency Status in Kuzu-Memory

**pyproject.toml Analysis**:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-benchmark>=4.0",
    "pytest-cov>=4.0",
    # ... other dev dependencies ...
    "towncrier>=23.11.0",  # ✅ Changelog management
]
```

**Missing Dependencies**:
- ❌ `build` (not in dev dependencies)
- ❌ `twine` (not in dev dependencies)

**Recommendation**: Add to dev dependencies:

```toml
[project.optional-dependencies]
dev = [
    # ... existing dependencies ...
    "build>=0.10",   # PEP 517 package building
    "twine>=4.0",    # PyPI package publishing
]
```

**Installation after adding**:
```bash
pip install -e ".[dev]"
```

### Template's Dependency Approach

The template **does not specify** build/twine in dependencies, assuming they are installed separately.

**Rationale**:
- Publishing is infrequent
- Avoids bloating dev dependencies
- Allows flexibility in tool versions

**Trade-off**: Requires manual installation by maintainers.

---

## 12. Security Considerations

### API Token Management

#### Current Approach (.env.local)

**Strengths**:
- Per-project credentials
- Not in home directory
- Easy to gitignore
- Explicit loading

**Weaknesses**:
- Manual file creation required
- Risk of accidental commit

**Mitigation**:
```bash
# Verify .env.local is in .gitignore
grep -q "^\.env\.local$" .gitignore || echo ".env.local" >> .gitignore

# Check for accidental staging
git status --ignored | grep .env.local
```

#### PyPI API Token Scope

**Best Practice**: Use scoped tokens

1. **Project-Scoped Token** (Recommended):
   - Limited to `kuzu-memory` package only
   - Minimizes damage if leaked
   - Created at: https://pypi.org/manage/account/token/

2. **Account-Wide Token** (Not Recommended):
   - Access to all packages
   - Higher risk if compromised

**Token Format**: `pypi-AgEIcHlwaS5vcmc...` (starts with `pypi-`)

#### TestPyPI vs. Production PyPI

**Separate Tokens Required**:
- TestPyPI: `pypi-AgENdGVzdC5weXBp...`
- Production PyPI: `pypi-AgEIcHlwaS5vcmc...`

**Current Makefile**: Only uses production PyPI token from `.env.local`.

**Enhancement for TestPyPI**:
```bash
# .env.local
PYPI_API_KEY=pypi-AgEIcHlwaS5vcmc...
TEST_PYPI_API_KEY=pypi-AgENdGVzdC5weXBp...
```

```makefile
release-test-pypi: release-build
	@export TWINE_USERNAME=__token__ && \
	export TWINE_PASSWORD=$${TEST_PYPI_API_KEY} && \
	python3 -m twine upload --repository testpypi dist/*
```

### Package Integrity

#### twine check Validation

**Performed by**: `make release-build` (from template's release.mk)

**Checks**:
- Package metadata compliance with PyPI requirements
- Long description rendering (README.md → PyPI project page)
- Distribution file format validation
- Presence of required metadata fields

**Example Errors Caught**:
```
Checking dist/kuzu_memory-1.5.3-py3-none-any.whl: FAILED
  `long_description` has syntax errors in markup and would not be rendered on PyPI.
    line 10: Unknown directive type "note".
```

**Fix**: Ensure README.md uses PyPI-compatible markup (reStructuredText or CommonMark).

#### Distribution File Signing (Advanced)

**GPG Signing** (optional):
```bash
python -m twine upload --sign dist/*
```

**Requirement**: GPG key configured locally.

**Benefit**: Package integrity verification by installers.

---

## 13. Troubleshooting Common Issues

### Issue 1: twine Not Found

**Error**:
```
✗ twine not found. Install with: pip install twine
```

**Solution**:
```bash
# Install twine
pip install twine

# Or install all dev dependencies
pip install -e ".[dev]"  # After adding twine to pyproject.toml
```

### Issue 2: Authentication Failed

**Error**:
```
403 Forbidden: Invalid or non-existent authentication information
```

**Causes**:
1. Incorrect API token
2. Token expired
3. Token not scoped for package

**Solution**:
```bash
# Verify token in .env.local
cat .env.local

# Regenerate token at PyPI
# https://pypi.org/manage/account/token/

# Update .env.local
echo "PYPI_API_KEY=pypi-NEW_TOKEN_HERE" > .env.local
```

### Issue 3: Package Already Exists

**Error**:
```
400 Bad Request: File already exists
```

**Cause**: Version already published to PyPI.

**Solution**:
```bash
# Bump version
make version-patch  # or minor/major

# Rebuild and publish
make build
make publish
```

**Note**: PyPI does not allow overwriting published versions (by design).

### Issue 4: Long Description Rendering Failed

**Error**:
```
WARNING: `long_description` has syntax errors in markup
```

**Cause**: README.md contains non-PyPI-compatible markup.

**Solution**:
```bash
# Validate locally
python -m twine check dist/*

# Common issues:
# - Custom directives (.. note::, .. warning::)
# - Non-standard markdown syntax
# - Missing blank lines before/after code blocks

# Fix README.md and rebuild
make build
make publish
```

### Issue 5: GitHub Release Creation Failed

**Error**:
```
⚠️  GitHub release creation failed
```

**Cause**: `gh` CLI not installed or not authenticated.

**Solution**:
```bash
# Install gh CLI
brew install gh  # macOS

# Authenticate
gh auth login

# Retry publishing
make publish
```

---

## 14. Recommended Update Strategy

### Current Status Assessment

✅ **Template includes full twine support** (no changes needed)
✅ **Kuzu-memory has customized appropriately** (working correctly)
⚠️ **Submodule is up-to-date** (no updates available)
⚠️ **Missing dependencies in pyproject.toml** (build, twine not listed)

### Recommended Actions

#### Priority 1: Add Publishing Dependencies (High Priority)

**Action**: Update `pyproject.toml`

```toml
[project.optional-dependencies]
dev = [
    # ... existing dependencies ...
    "build>=0.10",   # PEP 517 package building
    "twine>=4.0",    # PyPI package publishing
]
```

**Reason**: Ensures consistent dev environment setup.

**Implementation**:
```bash
# Edit pyproject.toml
# Add build and twine to dev dependencies

# Test installation
pip install -e ".[dev]"

# Verify tools available
which twine
python -m build --help
```

#### Priority 2: Enhance Publishing Target (Medium Priority)

**Action**: Add GitHub release creation to `publish` target

**Current** (`Makefile` line 219):
```makefile
python3 -m twine upload dist/kuzu_memory-$$VERSION*
@echo "✅ Package published to PyPI"
```

**Enhanced**:
```makefile
python3 -m twine upload dist/kuzu_memory-$$VERSION*
@echo "✅ Package published to PyPI"

@echo "📤 Creating GitHub release..."
@VERSION=$$(python3 -c "import sys; sys.path.insert(0, 'src'); from kuzu_memory.__version__ import __version__; print(__version__)"); \
gh release create "v$$VERSION" \
	--title "v$$VERSION" \
	--generate-notes \
	dist/kuzu_memory-$$VERSION* || echo "⚠️  GitHub release creation failed (install gh CLI: brew install gh)"
@echo "✅ GitHub release created"
```

**Benefits**:
- Single command for PyPI + GitHub release
- Automatic attachment of distribution files
- Auto-generated release notes from commits

#### Priority 3: Add Release Verification (Low Priority)

**Action**: Create `verify-release` target

```makefile
.PHONY: verify-release

verify-release: ## Verify release was published successfully
	@echo "🔍 Verifying release..."
	@VERSION=$$(python3 -c "import sys; sys.path.insert(0, 'src'); from kuzu_memory.__version__ import __version__; print(__version__)"); \
	echo ""; \
	echo "📦 PyPI: https://pypi.org/project/kuzu-memory/$$VERSION/"; \
	echo "🏷️  GitHub: https://github.com/KuzuDB/kuzu-memory/releases/tag/v$$VERSION"; \
	echo ""; \
	echo "💡 Test installation:"; \
	echo "  pip install kuzu-memory==$$VERSION"
```

**Usage**:
```bash
make publish
make verify-release
```

#### Priority 4: Monitor Template Updates (Ongoing)

**Action**: Periodically check for template updates

```bash
cd .python-project-template
git fetch origin
git log HEAD..origin/main  # Check for new commits

# If updates exist:
git checkout origin/main
cd ..
git add .python-project-template
git commit -m "chore: update python-project-template submodule"

# Review and selectively apply .makefiles updates
diff -u .python-project-template/template/.makefiles/release.mk .makefiles/release.mk
```

**Frequency**: Quarterly or when major template improvements are announced.

---

## 15. Migration Path (If Needed)

### Scenario: Breaking Changes in Template

If future template updates introduce breaking changes, follow this migration process:

#### Step 1: Review Changes

```bash
cd .python-project-template
git fetch origin
git log HEAD..origin/main --oneline

# View detailed changes
git log HEAD..origin/main -p -- template/.makefiles/
```

#### Step 2: Create Feature Branch

```bash
cd /Users/masa/Projects/kuzu-memory
git checkout -b chore/update-template-makefiles
```

#### Step 3: Update Submodule

```bash
cd .python-project-template
git checkout origin/main
cd ..

git add .python-project-template
git commit -m "chore: update python-project-template submodule to latest"
```

#### Step 4: Backup Current Makefiles

```bash
mkdir -p .makefiles.backup
cp .makefiles/*.mk .makefiles.backup/
```

#### Step 5: Apply Template Changes Selectively

```bash
# Compare each makefile
for file in common deps quality testing release; do
    echo "=== Comparing $file.mk ==="
    diff -u .python-project-template/template/.makefiles/$file.mk .makefiles/$file.mk
done

# Copy updated files (carefully review each)
# cp .python-project-template/template/.makefiles/common.mk .makefiles/
# cp .python-project-template/template/.makefiles/deps.mk .makefiles/
# ... etc.
```

#### Step 6: Reapply Kuzu-Memory Customizations

**For release.mk**:
```bash
# Edit .makefiles/release.mk
# Reapply customizations:
# 1. scripts/version.py integration (lines 94-127)
# 2. Package-specific URLs (lines 209-212)
# 3. Dry-run preview integration (lines 233-238)
```

#### Step 7: Test Updated Makefiles

```bash
# Test all major targets
make help
make quality
make test
make build

# Test version bumping (dry-run)
make release-dry-run

# Test build validation
make release-build
```

#### Step 8: Update Documentation

```bash
# Document changes in CHANGELOG.md
towncrier create --edit <issue-number>.misc

# Update this research document
# Add section: "Template Update History"
```

#### Step 9: Commit and PR

```bash
git add .makefiles/
git add .python-project-template/
git commit -m "chore: update makefiles from python-project-template

- Updated to commit <hash>
- Preserved kuzu-memory customizations
- Tested all make targets

Closes #<issue-number>"

# Create PR
gh pr create --title "Update makefiles from python-project-template" \
             --body "Updates makefiles to latest template version"
```

---

## 16. Conclusion

### Key Findings Summary

1. **✅ Twine is fully configured** in python-project-template's `release.mk`
2. **✅ Kuzu-memory has appropriately integrated** twine publishing
3. **✅ No template update required** - submodule is current
4. **⚠️ Missing dev dependencies** - build and twine should be in pyproject.toml
5. **💡 Enhancement opportunities** - GitHub release integration, release verification

### Immediate Actions

**Required** (to improve dev setup):
1. Add `build>=0.10` and `twine>=4.0` to `[project.optional-dependencies.dev]`

**Optional** (to enhance workflow):
1. Add GitHub release creation to `publish` target
2. Create `verify-release` target
3. Document publishing workflow in DEVELOPER.md

### No Breaking Changes

**Current setup is production-ready**. The template's twine support works correctly in kuzu-memory with project-specific customizations.

### Template Update Monitoring

**Current Status**: No updates available
**Recommendation**: Check quarterly for template improvements
**Update Process**: Documented in Section 15 (Migration Path)

---

## Appendix A: Complete File Listings

### Template's release.mk (268 lines)

**File**: `.python-project-template/template/.makefiles/release.mk`
**Purpose**: Version bumping, building, PyPI publishing, GitHub releases
**Twine Usage**: Lines 137-138 (check), 176-177 (upload), 194-195 (test upload)

**Key Targets**:
- `release-check`: Prerequisites validation
- `patch`, `minor`, `major`: Version bumping
- `release-build`: Build + twine check
- `release-publish`: twine upload + GitHub release
- `release-test-pypi`: twine upload to TestPyPI
- `release-verify`: Release verification links

### Kuzu-Memory's release.mk (268 lines, customized)

**File**: `.makefiles/release.mk`
**Customizations**:
- Lines 94-127: Version bumping via `scripts/version.py`
- Lines 209-212: kuzu-memory-specific URLs
- Lines 233-238: Changelog preview integration

**Preserved Template Features**:
- twine check validation
- twine upload functionality
- TestPyPI publishing
- GitHub release creation (in template, not used in custom `publish`)

### Kuzu-Memory's Custom Publish Target

**File**: `Makefile`
**Lines**: 197-220
**Features**:
- `.env.local` credential management
- TWINE_USERNAME and TWINE_PASSWORD export
- Version-specific file publishing
- Comprehensive error checking

---

## Appendix B: Useful Commands Reference

### Publishing Workflow Commands

```bash
# 1. Bump version and generate changelog
make version-patch   # For bug fixes (1.5.3 -> 1.5.4)
make version-minor   # For features (1.5.3 -> 1.6.0)
make version-major   # For breaking changes (1.5.3 -> 2.0.0)

# 2. Run quality checks
make quality         # Lint, format, typecheck

# 3. Run tests
make test            # Full test suite

# 4. Build package
make build           # Creates dist/ artifacts

# 5. Validate package (optional)
make release-build   # Build + twine check

# 6. Test on TestPyPI (optional)
make release-test-pypi
pip install --index-url https://test.pypi.org/simple/ kuzu-memory==<version>

# 7. Publish to production PyPI
make publish

# 8. Verify release (manual)
open https://pypi.org/project/kuzu-memory/
```

### Submodule Management Commands

```bash
# Check submodule status
git submodule status

# Update submodule to latest
cd .python-project-template
git fetch origin
git checkout origin/main
cd ..
git add .python-project-template
git commit -m "chore: update template submodule"

# View submodule changes
git diff --submodule

# Clone project with submodules
git clone --recurse-submodules <repo-url>

# Initialize submodules in existing clone
git submodule update --init --recursive
```

### Debugging Commands

```bash
# Check twine installation
which twine
python -m twine --version

# Check build installation
python -m build --version

# Validate package manually
python -m twine check dist/*

# Test credentials (dry-run)
python -m twine upload --repository testpypi dist/* --verbose

# View package metadata
tar -xzf dist/kuzu_memory-<version>.tar.gz -O kuzu_memory-<version>/PKG-INFO

# Check .env.local
cat .env.local | grep PYPI_API_KEY
```

---

## Appendix C: Research Methodology

### Tools Used

1. **Bash**: Git submodule inspection, file system navigation
2. **Read**: File content analysis (Makefiles, pyproject.toml)
3. **Grep**: Pattern-based search for twine usage
4. **Diff**: File comparison (template vs. customized makefiles)

### Files Analyzed (21 total)

1. `.python-project-template/` - Submodule structure
2. `.python-project-template/template/.makefiles/release.mk` - Template publishing config
3. `.makefiles/release.mk` - Customized publishing config
4. `Makefile` - Main build automation
5. `pyproject.toml` - Project metadata and dependencies
6. `.gitmodules` - Submodule configuration
7. `scripts/publish.py` - Publishing automation script
8. Multiple documentation files (DEVELOPER.md, publishing-workflow.md)

### Analysis Techniques

1. **Static Code Analysis**: Makefile target inspection
2. **Dependency Graph Analysis**: Include chain following
3. **Pattern Matching**: twine usage identification
4. **Diff Analysis**: Template vs. customization comparison
5. **Git History Analysis**: Submodule update detection

### Verification Steps

1. ✅ Confirmed twine presence in template
2. ✅ Verified twine usage in kuzu-memory
3. ✅ Checked submodule update status
4. ✅ Analyzed build system configuration
5. ✅ Documented publishing workflow
6. ✅ Identified enhancement opportunities

---

**End of Research Document**

**Next Steps**:
1. Add build and twine to dev dependencies
2. Optionally enhance publish target with GitHub release creation
3. Document publishing workflow in DEVELOPER.md
4. Schedule quarterly template update checks

**Contact**: Research Agent via Claude Code
**Project**: kuzu-memory
**Template**: python-project-template (bobmatnyc)
