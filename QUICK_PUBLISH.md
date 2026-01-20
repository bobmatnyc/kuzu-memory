# Quick Publish Guide

**TL;DR**: One command to publish a release to PyPI.

## Prerequisites (One-Time Setup)

```bash
# 1. Create .env.local with PyPI token
echo "PYPI_API_KEY=pypi-YOUR_TOKEN_HERE" > .env.local

# Get token from: https://pypi.org/manage/account/token/

# 2. Ensure tools installed
brew install gh  # GitHub CLI (macOS)
pip install uv   # Universal Python package manager
```

## Publish Commands

```bash
# Patch release (1.6.23 → 1.6.24) - Bug fixes
make publish-patch

# Minor release (1.6.23 → 1.7.0) - New features
make publish-minor

# Major release (1.6.23 → 2.0.0) - Breaking changes
make publish-major
```

That's it! ✅

## What Happens

1. ✅ Validates environment (.env.local, main branch, clean state)
2. ✅ Bumps version (VERSION, pyproject.toml, __version__.py, etc.)
3. ✅ Builds package (tar.gz + wheel)
4. ✅ Runs tests (unit tests)
5. ✅ Commits and tags (chore: bump version to X.Y.Z)
6. ✅ Pushes to GitHub (main + tags)
7. ✅ Publishes to PyPI (secure token upload)
8. ✅ Creates GitHub release (auto-generated notes)

## Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUCCESS: Release 1.6.24 completed successfully! 🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Package:  https://pypi.org/project/kuzu-memory/1.6.24/
🏷️  Release: https://github.com/bobmatnyc/kuzu-memory/releases/tag/v1.6.24
📝 Commit:   abc123f
```

## Troubleshooting

**"PYPI_API_KEY not found"**
```bash
echo "PYPI_API_KEY=pypi-..." > .env.local
```

**"Working directory has uncommitted changes"**
```bash
git status
git add . && git commit -m "your changes"
```

**"Tests failed"**
```bash
pytest tests/unit/ -v  # Fix tests first
make publish-patch     # Then publish
```

**Skip tests (emergency only)**
```bash
make publish-no-test
```

## More Details

- [Full Publishing Guide](docs/PUBLISHING.md)
- [Release Checklist](docs/RELEASE_CHECKLIST.md)
- [Implementation Summary](PUBLISHING_SUMMARY.md)

---

**Pro Tip**: Run `make help` to see all available commands.
