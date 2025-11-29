# Workflow Integration Guide

## Overview

This project uses the [python-project-template](https://github.com/bobmatnyc/python-project-template) as a Git submodule to provide a modular, enterprise-grade Makefile system. The template provides 5 specialized modules with proven automation patterns.

## Submodule Structure

```
kuzu-memory/
├── .python-project-template/       # Git submodule (template source)
│   └── template/
│       └── .makefiles/             # Template makefile modules
│           ├── common.mk           # Variables, colors, helpers
│           ├── deps.mk             # Dependency management
│           ├── quality.mk          # Linting, formatting, type-checking
│           ├── release.mk          # Version bumping, publishing
│           └── testing.mk          # Testing, coverage, benchmarks
├── .makefiles/                     # Project makefile modules (copied from template)
│   ├── common.mk                   # ✅ Identical to template
│   ├── deps.mk                     # ✅ Identical to template
│   ├── quality.mk                  # ✅ Identical to template
│   ├── release.mk                  # ⚠️ CUSTOMIZED for kuzu-memory version management
│   └── testing.mk                  # ✅ Identical to template
└── Makefile                        # Main Makefile (includes .makefiles/*.mk)
```

## Workflow Modules

### 1. common.mk - Shared Infrastructure
**Purpose**: Variables, colors, utility functions used by all modules

**Key Features**:
- Color output for better readability
- Environment detection (dev/staging/prod)
- Python path configuration
- Standard directory variables

**No customization needed** - used as-is from template.

### 2. quality.mk - Code Quality
**Purpose**: Linting, formatting, type-checking

**Key Targets**:
```bash
make lint           # Run Ruff linter
make lint-fix       # Auto-fix linting issues
make format         # Format code with Ruff
make type-check     # Run mypy type checking
make quality        # Run all quality checks (lint + type-check)
```

**No customization needed** - Ruff configuration in `pyproject.toml`.

### 3. testing.mk - Test Automation
**Purpose**: Test execution, coverage, benchmarks

**Key Targets**:
```bash
make test           # Run test suite with coverage
make test-fast      # Run tests without coverage
make test-watch     # Watch mode for TDD
make coverage       # Generate coverage report
make benchmark      # Run performance benchmarks
```

**No customization needed** - pytest configuration in `pyproject.toml`.

### 4. deps.mk - Dependency Management
**Purpose**: Installation, updates, synchronization

**Key Targets**:
```bash
make install        # Install in development mode
make deps-install   # Install dependencies
make deps-update    # Update dependencies
make deps-sync      # Sync lockfile with pyproject.toml
make deps-clean     # Clean dependency cache
```

**No customization needed** - works with pip, Poetry, or uv.

### 5. release.mk - Release Automation
**Purpose**: Version management, changelog, publishing

**Key Targets**:
```bash
make patch          # Bump patch version (0.1.0 -> 0.1.1)
make minor          # Bump minor version (0.1.0 -> 0.2.0)
make major          # Bump major version (0.1.0 -> 1.0.0)
make pre-release    # Run quality + test + build (no publish)
make release        # Full release pipeline with publishing
```

**⚠️ CUSTOMIZED for kuzu-memory**:
- Uses `scripts/version.py` for version management
- Custom PyPI package name configuration
- GitHub release automation

## Customization Strategy

### What's Customized

Only **release.mk** has been customized for this project:

**Template approach** (semver-based):
```makefile
patch:
    @CURRENT=$$(cat $(VERSION_FILE)); \
    NEW=$$($(PYTHON) -c "import semver; print(semver.VersionInfo.parse('$$CURRENT').bump_patch())"); \
    echo "$$NEW" > $(VERSION_FILE)
```

**kuzu-memory approach** (script-based):
```makefile
patch:
    @python3 scripts/version.py bump --type patch
```

**Why customized**:
- kuzu-memory has a sophisticated Python-based version management system
- Handles VERSION file, pyproject.toml, and __init__.py synchronization
- Provides preview, changelog generation, and conventional commit integration

### What Stays Identical

The other 4 modules remain **identical to the template**:
- ✅ **common.mk** - No project-specific variables needed
- ✅ **deps.mk** - Standard Python dependency management
- ✅ **quality.mk** - Ruff configuration lives in pyproject.toml
- ✅ **testing.mk** - pytest configuration lives in pyproject.toml

**Benefit**: Easy to update from template without merge conflicts.

## Updating Workflow Modules

### Step 1: Update Template Submodule

```bash
# Fetch latest template changes
git submodule update --remote .python-project-template

# Check what changed
cd .python-project-template
git log --oneline -5
cd ..
```

### Step 2: Review Template Changes

```bash
# Check for differences in each module
for file in common.mk deps.mk quality.mk testing.mk; do
    diff -u .python-project-template/template/.makefiles/$file .makefiles/$file
done

# Check release.mk separately (we expect differences)
diff -u .python-project-template/template/.makefiles/release.mk .makefiles/release.mk
```

### Step 3: Sync Non-Customized Modules

If template updates common.mk, deps.mk, quality.mk, or testing.mk:

```bash
# Copy updated modules (these should have no local changes)
cp .python-project-template/template/.makefiles/common.mk .makefiles/
cp .python-project-template/template/.makefiles/deps.mk .makefiles/
cp .python-project-template/template/.makefiles/quality.mk .makefiles/
cp .python-project-template/template/.makefiles/testing.mk .makefiles/

# Verify changes
git diff .makefiles/
```

### Step 4: Manually Merge release.mk

For release.mk (which is customized):

```bash
# Review template changes
diff -u .python-project-template/template/.makefiles/release.mk .makefiles/release.mk

# Manually apply desired changes while preserving kuzu-memory customizations
# Focus on sections that don't conflict with version management
```

### Step 5: Test Changes

```bash
# Verify all targets still work
make help
make quality
make test
make pre-release
```

### Step 6: Commit Updates

```bash
git add .python-project-template .makefiles/
git commit -m "chore: update workflow modules from python-project-template"
```

## Development Workflow

### Daily Development

```bash
# Install dependencies
make install

# Run quality checks before committing
make quality

# Run tests
make test

# Auto-fix formatting issues
make lint-fix
```

### Release Workflow

```bash
# 1. Ensure all changes committed
git status

# 2. Run pre-release checks
make pre-release

# 3. Bump version (choose one)
make patch          # Bug fixes
make minor          # New features
make major          # Breaking changes

# 4. Build and publish
make release
```

## Troubleshooting

### Submodule Not Initialized

```bash
git submodule init
git submodule update
```

### Submodule Out of Date

```bash
git submodule update --remote .python-project-template
```

### Make Targets Not Found

Check that `.makefiles/*.mk` files exist:
```bash
ls -la .makefiles/
# Should show: common.mk, deps.mk, quality.mk, release.mk, testing.mk
```

### Version Management Issues

The custom `scripts/version.py` handles version bumping. If issues occur:

```bash
# Check current version
cat VERSION

# Preview next version
python3 scripts/version.py bump --type patch --dry-run

# Manually sync version files
python3 scripts/version.py sync
```

## Benefits of This Approach

### ✅ **Modular Design**
- Each .mk file has single responsibility
- Easy to understand and maintain
- Changes isolated to specific concerns

### ✅ **Template Updates**
- 4 of 5 modules can be updated automatically
- Only release.mk needs careful merging
- Low maintenance overhead

### ✅ **Project Customization**
- release.mk customized for kuzu-memory needs
- Other modules use standard configurations
- Clear separation of generic vs. specific

### ✅ **Battle-Tested**
- Derived from production codebases
- 97+ targets proven in real-world use
- Enterprise-grade automation patterns

### ✅ **Consistency**
- Same workflow across all projects using template
- Familiar targets for new contributors
- Standardized quality and release processes

## See Also

- **Template Documentation**: `.python-project-template/README.md`
- **Template Structure**: `.python-project-template/STRUCTURE.md`
- **Makefile Extraction Report**: `.python-project-template/MAKEFILE_EXTRACTION_REPORT.md`
- **Project Makefile**: `Makefile`
- **Version Management**: `scripts/version.py`
