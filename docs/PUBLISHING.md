# Publishing Guide

This document describes the release process for kuzu-memory.

## Prerequisites

Before publishing, ensure you have:

1. **PyPI API Token**: Stored in `.env.local` as `PYPI_API_KEY`
   ```bash
   # Create .env.local with your PyPI token
   cat > .env.local <<EOF
   PYPI_API_KEY=pypi-YOUR_TOKEN_HERE
   GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE  # Optional, for GitHub operations
   EOF
   ```
   Get a PyPI token from: https://pypi.org/manage/account/token/

2. **GitHub CLI**: Installed and authenticated with `workflow` scope
   ```bash
   # Check authentication status
   gh auth status

   # If not authenticated or missing workflow scope, run:
   gh auth refresh -s workflow
   ```

3. **Clean Repository**: No uncommitted changes (except `uv.lock` which is auto-handled)
   ```bash
   git status  # Should show clean or only uv.lock
   ```

4. **Main Branch**: Currently on the `main` branch
   ```bash
   git checkout main
   git pull origin main
   ```

5. **All Tests Passing**: Run quality checks before publishing
   ```bash
   make quality test  # Or use make pre-publish if available
   ```

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

## Complete Publishing Flow

```
make publish-patch
    ↓
./scripts/publish.sh patch
    ↓
┌─────────────────────────────────────────┐
│ 1. Validate Environment                 │
│    - Check .env.local (PYPI_API_KEY)   │
│    - Verify main branch                 │
│    - Check working directory clean      │
│    - Confirm tools installed (uv, gh)   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 2. Bump Version                         │
│    - Run manage_version.py bump patch   │
│    - Update VERSION, pyproject.toml,    │
│      __version__.py, CHANGELOG.md       │
│    - Sync uv.lock if needed             │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 3. Build Package                        │
│    - Clean old dist/ artifacts          │
│    - Run uv build                       │
│    - Verify .tar.gz and .whl created    │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 4. Run Sanity Tests (Optional)          │
│    - pytest tests/unit/ -q --tb=no     │
│    - Skip with --no-test flag           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 5. Commit & Tag                         │
│    - git add VERSION pyproject.toml ... │
│    - git commit --no-verify (skip hooks)│
│    - git tag vX.Y.Z                     │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 6. Push to GitHub                       │
│    - git push origin main --tags        │
│    - Disable rollback after push        │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 7. Publish to PyPI (CRITICAL PATH)      │
│    - Export TWINE_PASSWORD=$PYPI_TOKEN  │
│    - twine upload dist/kuzu_memory-*    │
│    - ✅ SUCCESS if this completes       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 8. GitHub Release (Non-Fatal)           │
│    - gh release create vX.Y.Z           │
│    - Warn if fails, don't exit          │
│    - Package already on PyPI ✅         │
└─────────────────────────────────────────┘
    ↓
✅ Release Complete!
   - PyPI: https://pypi.org/project/kuzu-memory/X.Y.Z
   - GitHub: https://github.com/.../releases/tag/vX.Y.Z
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

- Exports `PYPI_API_KEY` from `.env.local` as `TWINE_PASSWORD`
- Uses `twine upload` with token authentication (`__token__` username)
- Uploads both `.tar.gz` and `.whl` to PyPI
- Handles token securely via environment variables (not command line)

### 8. GitHub Release 🎉

- Creates GitHub release with auto-generated notes
- Links to PyPI package
- **Non-fatal**: If this step fails, the package is already on PyPI (critical path succeeded)
- Provides instructions for manual release creation if needed

## Error Handling & Rollback

The script includes robust error handling with automatic rollback:

### Rollback Mechanism

- **Automatic Rollback**: If any step fails **before** GitHub push (Step 6), the version bump is automatically rolled back
- **Rollback Disabled After Push**: Once committed to GitHub, rollback is disabled (you can't rewrite public history)
- **Files Restored on Rollback**:
  - `VERSION`
  - `pyproject.toml`
  - `uv.lock`
  - `src/kuzu_memory/__version__.py`
  - `CHANGELOG.md`

### Error Handling Features

- **Immediate Exit**: Any error stops the process (`set -e`)
- **Clear Error Messages**: Color-coded output (red for errors, yellow for warnings, green for success)
- **Safe Defaults**: Pre-commit hooks skipped with `--no-verify` (code already validated)
- **Non-Fatal GitHub Release**: PyPI publish is the critical path; GitHub release failure only warns

### What Happens on Failure?

**Before GitHub Push (Steps 1-5)**:
- Script exits with error
- Version bump is automatically rolled back
- Working directory restored to pre-publish state
- No remote changes made

**After GitHub Push (Steps 6-8)**:
- Script continues even if GitHub release fails
- PyPI publish is critical path; if it succeeds, release is considered successful
- Manual intervention may be needed for GitHub release

### Manual Recovery

If you need to manually recover from a failed publish:

```bash
# Check what was actually pushed
git log --oneline -5
git tag | grep v

# If version was pushed but PyPI failed
VERSION=$(cat VERSION)
uv run twine upload "dist/kuzu_memory-${VERSION}"* -u __token__ -p "$(grep PYPI_API_KEY .env.local | cut -d= -f2)"

# If GitHub release failed
gh release create "v$VERSION" --generate-notes

# If you need to undo a local version bump (not pushed yet)
git restore VERSION pyproject.toml uv.lock src/kuzu_memory/__version__.py CHANGELOG.md
git clean -fd dist/ build/
```

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
cat > .env.local <<EOF
PYPI_API_KEY=pypi-YOUR_TOKEN_HERE
GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE  # Optional
EOF
```

Get a PyPI token from: https://pypi.org/manage/account/token/

**Important**: Never commit `.env.local` to git! It's already in `.gitignore`.

### "PyPI upload failed: Invalid credentials"

This means the token authentication failed. Verify:

1. **Token format**: Should start with `pypi-` (e.g., `pypi-AgEIcH...`)
2. **Token in .env.local**: Check the file has correct format:
   ```bash
   grep PYPI_API_KEY .env.local
   # Should output: PYPI_API_KEY=pypi-YOUR_TOKEN
   ```
3. **Token permissions**: Ensure token has "Upload packages" scope on PyPI
4. **Token not expired**: Regenerate if necessary at https://pypi.org/manage/account/token/

### "GitHub release creation failed"

The script now handles this gracefully (package is already on PyPI). To fix:

1. **Check authentication**:
   ```bash
   gh auth status
   # Look for "workflow" scope in the output
   ```

2. **Refresh with workflow scope** (if missing):
   ```bash
   gh auth refresh -s workflow
   ```

3. **Manually create release** (if needed):
   ```bash
   VERSION=$(cat VERSION)
   gh release create "v$VERSION" --generate-notes
   ```

### "Working directory has uncommitted changes"

The script now auto-handles `uv.lock` changes. For other files:

```bash
# Check what's uncommitted
git status

# Commit or stash your changes
git add .
git commit -m "your changes"
# or
git stash
```

### "uv.lock is dirty after version bump"

This is now handled automatically by the script. The version bump updates `pyproject.toml`, which can trigger `uv.lock` updates. The script:

1. Detects `uv.lock` changes
2. Runs `uv sync` to update lockfile
3. Includes `uv.lock` in the version bump commit

If you see this issue, the script should auto-resolve it.

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

- ✅ **PyPI token stored in `.env.local`** (not committed to git, in `.gitignore`)
- ✅ **Token used via environment variable** (`TWINE_PASSWORD`, not command line)
- ✅ **Twine upload uses token authentication** (secure, no password visible in logs)
- ✅ **Script validates token exists** (prevents accidental exposure)
- ✅ **Pre-commit hooks skipped** (uses `--no-verify` to avoid sensitive data leaks)

Never commit `.env.local` to version control!

## Quick Reference

### One-Command Publishing

```bash
# Patch release (most common)
make publish-patch

# Minor release (new features)
make publish-minor

# Major release (breaking changes)
make publish-major

# Skip tests (use with caution)
make publish-no-test
```

### Prerequisites Checklist

Before running `make publish-patch`:

- [ ] `.env.local` exists with `PYPI_API_KEY=pypi-...`
- [ ] GitHub CLI authenticated: `gh auth status` (with `workflow` scope)
- [ ] On main branch: `git branch --show-current` → `main`
- [ ] Working directory clean: `git status` → no uncommitted changes
- [ ] Tests passing: `make quality test`

### Environment File Template

```bash
# .env.local (never commit this file!)
PYPI_API_KEY=pypi-YOUR_TOKEN_HERE
GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE  # Optional, for gh CLI
```

### Common Commands

```bash
# Check prerequisites
gh auth status                    # Verify GitHub auth + workflow scope
gh auth refresh -s workflow       # Add workflow scope if missing
cat .env.local | grep PYPI        # Verify PyPI token exists

# Publish
make publish-patch                # Full automated release

# Manual troubleshooting
./scripts/publish.sh patch --no-test  # Skip tests
git restore VERSION pyproject.toml    # Rollback version bump
gh release create vX.Y.Z --generate-notes  # Manual GitHub release
```

## Related Documentation

- [Development Guide (CLAUDE.md)](../CLAUDE.md)
- [Version Management](./VERSION_MANAGEMENT.md)
- [Changelog](../CHANGELOG.md)
- [PyPI Project](https://pypi.org/project/kuzu-memory/)

---

**Last Updated**: 2026-02-19
**Version**: 1.6.37
**Script**: `scripts/publish.sh`
**Make Targets**: `publish-patch`, `publish-minor`, `publish-major`, `publish-no-test`
