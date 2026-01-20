# Release Checklist

Quick reference for releasing kuzu-memory to PyPI.

## Prerequisites ✅

Before running any release command, ensure:

- [ ] You're on the `main` branch
- [ ] Working directory is clean (no uncommitted changes)
- [ ] `.env.local` exists with `PYPI_API_KEY=pypi-...`
- [ ] All tests are passing (`make test`)
- [ ] Code quality checks pass (`make quality`)

## Quick Release Commands

### Option 1: Makefile Targets (Recommended)

```bash
# Patch release (1.6.23 → 1.6.24)
make publish-patch

# Minor release (1.6.23 → 1.7.0)
make publish-minor

# Major release (1.6.23 → 2.0.0)
make publish-major

# Skip tests (use with caution)
make publish-no-test
```

### Option 2: Direct Script

```bash
# Patch release
./scripts/publish.sh

# Minor release
./scripts/publish.sh minor

# Major release
./scripts/publish.sh major

# Skip tests
./scripts/publish.sh patch --no-test
```

## What Gets Published

### Automated Steps (All Handled by Script)

1. ✅ Environment validation
2. ✅ Version bump (VERSION, pyproject.toml, __version__.py)
3. ✅ Package build (tar.gz + wheel)
4. ✅ Test execution (unit tests)
5. ✅ Git commit + tag
6. ✅ Push to GitHub
7. ✅ PyPI upload
8. ✅ GitHub release creation

### Manual Steps (You Handle)

- Updating documentation for breaking changes
- Writing release announcements
- Notifying users of major releases

## Post-Release Verification

After a successful release, verify:

```bash
# Check PyPI
open https://pypi.org/project/kuzu-memory/

# Test installation
pip install --upgrade kuzu-memory
kuzu-memory --version

# Check GitHub release
open https://github.com/bobmatnyc/kuzu-memory/releases
```

## Common Release Scenarios

### Bug Fix Release

```bash
# Fix the bug, commit changes
git add .
git commit -m "fix: resolve database connection issue"

# Run quality checks
make quality test

# Publish patch release
make publish-patch
```

### New Feature Release

```bash
# Implement feature, write tests
git add .
git commit -m "feat: add new recall algorithm"

# Run quality checks
make quality test

# Publish minor release
make publish-minor
```

### Emergency Hotfix

```bash
# Fix critical issue
git add .
git commit -m "fix: critical security vulnerability"

# Skip tests if absolutely necessary
make publish-no-test

# Follow up with full test suite
make test
```

## Rollback Procedure

If you need to rollback a failed release:

```bash
# The script automatically rolls back version changes on failure
# If you need to manually rollback:

# 1. Delete the tag
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z

# 2. Revert the version commit
git revert HEAD
git push origin main

# 3. Contact PyPI to yank the release (cannot delete)
# Visit: https://pypi.org/manage/project/kuzu-memory/releases/
```

## Semantic Versioning Guide

Choose the right version bump:

### Patch (1.6.23 → 1.6.24)

- Bug fixes
- Documentation updates
- Performance improvements
- Internal refactoring
- Dependency updates (non-breaking)

### Minor (1.6.23 → 1.7.0)

- New features (backward-compatible)
- New CLI commands
- New API methods
- Deprecation warnings (not removals)

### Major (1.6.23 → 2.0.0)

- Breaking API changes
- Removed deprecated features
- Changed CLI interface
- Database schema changes requiring migration

## Troubleshooting

### "PYPI_API_KEY not found"

```bash
# Create .env.local
echo "PYPI_API_KEY=pypi-YOUR_TOKEN_HERE" > .env.local
```

### "Working directory has uncommitted changes"

```bash
# Commit or stash changes
git status
git add .
git commit -m "your changes"
```

### "Tests failed"

```bash
# Fix tests first
pytest tests/unit/ -v

# Then publish
make publish-patch
```

### "Authentication failed to PyPI"

```bash
# Check token is valid
grep PYPI_API_KEY .env.local

# Get new token from: https://pypi.org/manage/account/token/
```

## Release Frequency

- **Patch releases**: As needed (weekly for bug fixes)
- **Minor releases**: Monthly for new features
- **Major releases**: Rarely, only for breaking changes

## Related Documentation

- [Publishing Guide](./PUBLISHING.md) - Detailed publishing documentation
- [Development Guide (CLAUDE.md)](../CLAUDE.md) - Development workflow
- [Changelog](../CHANGELOG.md) - Version history
- [PyPI Project](https://pypi.org/project/kuzu-memory/)

---

**Last Updated**: 2025-01-20
