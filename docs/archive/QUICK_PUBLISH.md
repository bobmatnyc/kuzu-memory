# Quick Publish Reference

**One command to publish kuzu-memory to PyPI.**

## TL;DR

```bash
make publish-patch  # Most common: patch release (1.6.37 → 1.6.38)
```

## Prerequisites (One-Time Setup)

### 1. Create `.env.local` with PyPI Token

```bash
cat > .env.local <<EOF
PYPI_API_KEY=pypi-YOUR_TOKEN_HERE
GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE  # Optional, for GitHub operations
EOF
```

Get token from: https://pypi.org/manage/account/token/

### 2. Authenticate GitHub CLI with Workflow Scope

```bash
# Check authentication status
gh auth status

# If not authenticated or missing workflow scope
gh auth refresh -s workflow
```

### 3. Ensure Tools Installed

```bash
# macOS
brew install gh uv

# Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Publishing Commands

```bash
# Patch release (1.6.37 → 1.6.38) - Bug fixes
make publish-patch

# Minor release (1.6.37 → 1.7.0) - New features
make publish-minor

# Major release (1.6.37 → 2.0.0) - Breaking changes
make publish-major

# Skip tests (use with caution)
make publish-no-test
```

## What Happens

1. ✅ Validates environment (token, branch, clean repo)
2. ✅ Bumps version and updates files (VERSION, pyproject.toml, etc.)
3. ✅ Builds package (tar.gz + wheel)
4. ✅ Runs tests (skippable with `--no-test`)
5. ✅ Commits version bump (uses `--no-verify` to skip pre-commit hooks)
6. ✅ Syncs `uv.lock` if modified by version bump (auto-handled)
7. ✅ Creates git tag (`vX.Y.Z`)
8. ✅ Pushes to GitHub (main + tags)
9. ✅ Publishes to PyPI (critical path - token via `TWINE_PASSWORD`)
10. ⚠️  Creates GitHub release (non-fatal, warns if fails)

## Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUCCESS: Release 1.6.38 completed successfully! 🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Package:  https://pypi.org/project/kuzu-memory/1.6.38/
🏷️  Release: https://github.com/bobmatnyc/kuzu-memory/releases/tag/v1.6.38
📝 Commit:   abc123f
```

## Troubleshooting

### "PYPI_API_KEY not found in .env.local"
```bash
echo "PYPI_API_KEY=pypi-YOUR_TOKEN_HERE" > .env.local
```

### "PyPI upload failed: Invalid credentials"
Verify token format and permissions:
```bash
grep PYPI_API_KEY .env.local  # Should output: PYPI_API_KEY=pypi-...
```
Get a new token: https://pypi.org/manage/account/token/

### "GitHub release creation failed"
The script now handles this gracefully (package is already on PyPI). To fix:
```bash
# Check authentication and add workflow scope
gh auth status
gh auth refresh -s workflow

# Or manually create release
VERSION=$(cat VERSION)
gh release create "v$VERSION" --generate-notes
```

### "Working directory has uncommitted changes"
```bash
git status
git add . && git commit -m "your changes"
# or
git stash
```

### "uv.lock is dirty after version bump"
This is now auto-handled by the script. The version bump updates `pyproject.toml`, which triggers `uv.lock` changes. The script automatically:
1. Detects `uv.lock` changes
2. Runs `uv sync` to update lockfile
3. Includes `uv.lock` in the version bump commit

### "Tests failed"
Fix tests first, then publish:
```bash
pytest tests/unit/ -v
make publish-patch
```

Or skip tests (use with caution):
```bash
make publish-no-test
```

## Manual Recovery

```bash
# Undo local version bump (not pushed yet)
git restore VERSION pyproject.toml uv.lock src/kuzu_memory/__version__.py CHANGELOG.md

# Republish if PyPI failed (already pushed to GitHub)
VERSION=$(cat VERSION)
export TWINE_PASSWORD=$(grep PYPI_API_KEY .env.local | cut -d= -f2)
uv run twine upload "dist/kuzu_memory-${VERSION}"* -u __token__

# Create GitHub release manually
gh release create "v$VERSION" --generate-notes
```

## Verification

After publishing:

```bash
# Check PyPI
VERSION=$(cat VERSION)
echo "https://pypi.org/project/kuzu-memory/$VERSION/"

# Check GitHub
echo "https://github.com/bobmatnyc/kuzu-memory/releases/tag/v$VERSION"

# Test installation
pip install kuzu-memory==$VERSION
kuzu-memory --version
```

## Security

- ✅ **Never commit `.env.local`** (already in `.gitignore`)
- ✅ **Token passed via environment variable** (`TWINE_PASSWORD`), not command line
- ✅ **Pre-commit hooks skipped** (`--no-verify`) to avoid leaking sensitive data
- ✅ **Script validates token format** before use

## More Details

- [Full Publishing Guide](docs/PUBLISHING.md) - Comprehensive documentation
- [Version Management](docs/VERSION_MANAGEMENT.md) - Semantic versioning guide
- [Development Guide](CLAUDE.md) - Complete development documentation

---

**Last Updated**: 2026-02-19
**Script**: `scripts/publish.sh`
**Make Targets**: `publish-patch`, `publish-minor`, `publish-major`, `publish-no-test`
