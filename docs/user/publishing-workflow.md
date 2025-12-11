# Publishing Workflow

This document describes the standardized publishing workflow using the modular makefile system.

## Overview

KuzuMemory now uses a modular makefile system from the `python-project-template` submodule. This provides a consistent, well-tested publishing workflow.

## Directory Structure

```
.makefiles/
├── common.mk      # Core infrastructure (colors, ENV system, metadata)
├── deps.mk        # Dependency management
├── quality.mk     # Code quality checks
├── release.mk     # Version bumping and publishing
└── testing.mk     # Test automation
```

## Quick Start

### Full Release Workflow (Recommended)

```bash
# Patch release (1.4.50 → 1.4.51)
make release-patch
make release-publish

# Minor release (1.4.50 → 1.5.0)
make release-minor
make release-publish

# Major release (1.4.50 → 2.0.0)
make release-major
make release-publish
```

### Step-by-Step Commands

#### 1. Check Prerequisites
```bash
make release-check
```

Verifies:
- Required tools installed (git, python3, gh CLI)
- Working directory is clean
- On main branch (or prompts for confirmation)

#### 2. Bump Version
```bash
# Patch: Bug fixes, small changes
make patch

# Minor: New features, backward compatible
make minor

# Major: Breaking changes
make major
```

#### 3. Build Package
```bash
make release-build
```

Runs:
- Pre-publish quality checks (ruff, black, isort, flake8, mypy)
- Package build (`python3 -m build`)
- Package validation (`twine check`)

#### 4. Publish Release
```bash
make release-publish
```

Steps:
- Prompts for confirmation
- Publishes to PyPI (`twine upload`)
- Creates GitHub release (`gh release create`)
- Shows verification links

#### 5. Verify Release
```bash
make release-verify
```

Shows:
- PyPI package URL
- GitHub release URL
- Installation command

## Testing on TestPyPI

Before publishing to production PyPI:

```bash
make release-build
make release-test-pypi
```

Test installation:
```bash
pip install --index-url https://test.pypi.org/simple/ kuzu-memory
```

## Preview Changes (Dry Run)

```bash
make release-dry-run
```

Shows what would happen without making any changes.

## Environment-Specific Builds

```bash
# Development (default): verbose output
make ENV=development release-build

# Staging: balanced settings
make ENV=staging release-build

# Production: strict, fast, minimal output
make ENV=production release-build
```

## Troubleshooting

### Working Directory Not Clean

```bash
# Check what files are modified
git status

# Commit changes
git add .
git commit -m "Description of changes"

# Try again
make release-check
```

### Missing GitHub CLI

Install GitHub CLI:
```bash
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
```

### PyPI Authentication Failed

Ensure you have a PyPI API token configured. The current Makefile expects credentials in `.env.local`:

```bash
# Create .env.local with your PyPI token
echo "PYPI_API_KEY=pypi-your-token-here" > .env.local
```

## Customization

### Version Management

KuzuMemory uses `scripts/version.py` for version management instead of semver. The modular makefiles have been customized to use this script.

### Build Metadata

Build metadata is tracked in `build/metadata.json`:

```json
{
  "version": "1.4.50",
  "build_number": 123,
  "commit": "abc123...",
  "commit_short": "abc123",
  "branch": "main",
  "timestamp": "2025-11-25T05:45:00Z",
  "python_version": "Python 3.11.6",
  "environment": "development"
}
```

## Integration with Existing Workflow

The modular makefiles integrate with KuzuMemory's existing targets:

- `make release` - Unchanged, uses existing workflow
- `make publish` - Unchanged, uses existing PyPI publishing
- `make release-patch` - New, from modular system
- `make release-minor` - New, from modular system
- `make release-major` - New, from modular system

## Best Practices

1. **Always run release-check first** to ensure prerequisites are met
2. **Use release-dry-run** to preview changes before actual release
3. **Test on TestPyPI first** for major releases
4. **Verify the release** after publishing with `make release-verify`
5. **Keep working directory clean** by committing changes before release
6. **Use semantic versioning** correctly:
   - Patch: Bug fixes, documentation updates
   - Minor: New features, backward compatible
   - Major: Breaking changes, API incompatibilities

## Migration from Old Workflow

The old workflow (`make version-patch && make release && make publish`) still works, but the new workflow provides better safety checks and automation:

**Old:**
```bash
make version-patch
make changelog
make release
make publish
```

**New:**
```bash
make release-patch    # Includes checks + version bump + build
make release-publish  # Includes PyPI + GitHub release + verification
```

## Additional Commands

- `make env-info` - Display current environment configuration
- `make build-metadata` - Track build metadata in JSON format
- `make build-info-json` - Display build metadata from JSON

## References

- Python Project Template: `.python-project-template/`
- Release Makefile: `.makefiles/release.mk`
- Version Script: `scripts/version.py`
- Common Infrastructure: `.makefiles/common.mk`
