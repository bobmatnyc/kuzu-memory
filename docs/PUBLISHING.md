# Publishing Guide

This document describes the release process for kuzu-memory.

## Prerequisites

Before publishing, ensure you have:

1. **PyPI API Token**: Stored in `.env.local` as `PYPI_API_KEY`
2. **GitHub CLI**: Installed and authenticated (`gh auth status`)
3. **Clean Repository**: No uncommitted changes
4. **Main Branch**: Currently on the `main` branch
5. **All Tests Passing**: Run `make pre-publish` to verify

## Quick Start

The simplest way to publish a new release:

```bash
# Patch release (1.6.23 → 1.6.24)
./scripts/publish.sh

# Minor release (1.6.23 → 1.7.0)
./scripts/publish.sh minor

# Major release (1.6.23 → 2.0.0)
./scripts/publish.sh major

# Skip tests (use with caution)
./scripts/publish.sh patch --no-test
```

## What the Script Does

The `publish.sh` script automates the entire release process:

### 1. Environment Validation ✅

- Checks `.env.local` exists with valid `PYPI_API_KEY`
- Verifies you're on the `main` branch
- Ensures working directory is clean (no uncommitted changes)
- Confirms required tools are installed (`uv`, `gh`)

### 2. Version Bump 📝

- Runs `./scripts/manage_version.py bump <type>`
- Updates `VERSION`, `pyproject.toml`, `uv.lock`, `__version__.py`, and `CHANGELOG.md`
- Validates version changed successfully

### 3. Package Build 📦

- Cleans old build artifacts (`dist/`, `build/`)
- Runs `uv build` to create `.tar.gz` and `.whl`
- Verifies build artifacts exist

### 4. Sanity Tests 🧪

- Runs `pytest tests/unit/ -q --tb=no` for quick validation
- Skippable with `--no-test` flag
- Prevents publishing broken code

### 5. Git Commit and Tag 🏷️

- Commits version bump with message: `"chore: bump version to X.Y.Z"`
- Creates git tag: `vX.Y.Z`
- Prepares for GitHub push

### 6. Push to GitHub 🚀

- Pushes commits and tags to `origin main`
- Makes version bump public

### 7. Publish to PyPI 📤

- Uses `twine upload` with PyPI token authentication
- Uploads both `.tar.gz` and `.whl` to PyPI
- Handles token securely from `.env.local`

### 8. GitHub Release 🎉

- Creates GitHub release with auto-generated notes
- Links to PyPI package
- Completes the release process

## Error Handling

The script includes robust error handling:

- **Immediate Exit**: Any error stops the process (`set -e`)
- **Rollback on Failure**: Version bump is rolled back if publish fails
- **Clear Error Messages**: Color-coded output explains what went wrong
- **Safe Defaults**: Requires explicit confirmation for destructive actions

## Manual Publishing (Not Recommended)

If you need to publish manually:

```bash
# 1. Bump version
./scripts/manage_version.py bump patch

# 2. Build package
uv build

# 3. Run tests
uv run pytest tests/unit/

# 4. Commit and tag
git add VERSION pyproject.toml uv.lock src/kuzu_memory/__version__.py CHANGELOG.md
git commit -m "chore: bump version to $(cat VERSION)"
git tag "v$(cat VERSION)"
git push origin main --tags

# 5. Publish to PyPI
PYPI_TOKEN=$(grep "^PYPI_API_KEY=" .env.local | sed 's/PYPI_API_KEY=//')
uv run twine upload dist/kuzu_memory-$(cat VERSION)* -u __token__ -p "$PYPI_TOKEN"

# 6. Create GitHub release
gh release create "v$(cat VERSION)" --generate-notes
```

## Troubleshooting

### "PYPI_API_KEY not found in .env.local"

Create `.env.local` with your PyPI token:

```bash
echo "PYPI_API_KEY=pypi-YOUR_TOKEN_HERE" > .env.local
```

Get a token from: https://pypi.org/manage/account/token/

### "Must be on main branch"

Switch to main and pull latest:

```bash
git checkout main
git pull origin main
```

### "Working directory has uncommitted changes"

Commit or stash your changes:

```bash
git status
git add .
git commit -m "your changes"
# or
git stash
```

### "Tests failed"

Fix failing tests before publishing:

```bash
pytest tests/unit/ -v
# Fix issues
pytest tests/unit/ -v
```

Or skip tests (not recommended):

```bash
./scripts/publish.sh patch --no-test
```

### "Version did not change after bump"

Check `VERSION` file and ensure `manage_version.py` is working:

```bash
cat VERSION
./scripts/manage_version.py show
```

### "Build failed: tar.gz not found"

Clean and rebuild:

```bash
rm -rf dist/ build/
uv build
ls -la dist/
```

## Post-Release Checklist

After a successful release:

- [ ] Verify package on PyPI: https://pypi.org/project/kuzu-memory/
- [ ] Test installation: `pip install kuzu-memory==X.Y.Z`
- [ ] Check GitHub release: https://github.com/bobmatnyc/kuzu-memory/releases
- [ ] Verify CLI version: `kuzu-memory --version`
- [ ] Update documentation if API changed
- [ ] Announce release (if major/minor)

## Semantic Versioning

Follow semantic versioning (semver):

- **Patch** (1.6.23 → 1.6.24): Bug fixes, minor improvements
- **Minor** (1.6.23 → 1.7.0): New features, backward-compatible
- **Major** (1.6.23 → 2.0.0): Breaking changes, incompatible API

## Release Frequency

- **Patch releases**: As needed for bug fixes (weekly)
- **Minor releases**: Monthly for new features
- **Major releases**: Rarely, only for breaking changes

## Security

- ✅ **PyPI token stored in `.env.local`** (not committed to git)
- ✅ **Token used via environment variable** (not command line)
- ✅ **Twine upload uses token authentication** (secure)
- ✅ **Script validates token exists** (prevents accidental exposure)

Never commit `.env.local` to version control!

## Related Documentation

- [Development Guide (CLAUDE.md)](../CLAUDE.md)
- [Version Management](./VERSION_MANAGEMENT.md)
- [Changelog](../CHANGELOG.md)
- [PyPI Project](https://pypi.org/project/kuzu-memory/)

---

**Last Updated**: 2025-01-20
