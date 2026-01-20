# publish.sh - Architecture & Maintenance

Internal documentation for the automated publishing script.

## Script Architecture

### Design Principles

1. **Fail Fast**: Exit immediately on any error (`set -e`)
2. **Safe Rollback**: Automatically rollback version changes if publish fails
3. **Clear Feedback**: Color-coded output for errors, warnings, successes
4. **Idempotent**: Can be safely re-run after fixing issues
5. **Atomic Operations**: Either complete successfully or rollback completely

### Control Flow

```
Start
  ↓
Validate Environment
  ↓
Bump Version (rollback-enabled from here)
  ↓
Build Package
  ↓
Run Tests (optional)
  ↓
Commit & Tag
  ↓
Push to GitHub (rollback-disabled from here)
  ↓
Publish to PyPI
  ↓
Create GitHub Release
  ↓
Print Summary
```

### Rollback Logic

The script uses a `ROLLBACK_NEEDED` flag to control automatic rollback:

```bash
ROLLBACK_NEEDED=false  # Initially disabled

# After version bump
ROLLBACK_NEEDED=true   # Enable rollback

# After successful push
ROLLBACK_NEEDED=false  # Disable rollback (changes are public)
```

**Rollback is enabled between:**
- Version bump ✅
- Package build ✅
- Test execution ✅
- Git commit/tag ✅

**Rollback is disabled after:**
- Git push ❌ (changes are public, cannot be undone)

### Error Handling

```bash
# Global error handler
trap 'rollback_version' ERR

# Rollback function
rollback_version() {
    if [[ "$ROLLBACK_NEEDED" == "true" ]]; then
        warn "Rolling back version bump..."
        echo "$OLD_VERSION" > VERSION
        ./scripts/manage_version.py sync
        git restore VERSION pyproject.toml uv.lock src/kuzu_memory/__version__.py CHANGELOG.md
        warn "Version rolled back to $OLD_VERSION"
    fi
}
```

## File Dependencies

### Required Files

- `VERSION` - Single source of truth for version
- `.env.local` - PyPI credentials (PYPI_API_KEY)
- `scripts/manage_version.py` - Version bump script
- `pyproject.toml` - Package metadata
- `uv.lock` - Dependency lock file

### Generated Files

- `dist/kuzu_memory-X.Y.Z.tar.gz` - Source distribution
- `dist/kuzu_memory-X.Y.Z-py3-none-any.whl` - Binary wheel

## External Dependencies

### Required Tools

- `uv` - Package builder and publisher
- `gh` - GitHub CLI for releases
- `git` - Version control
- `twine` - PyPI upload tool (via uv run)

### Validation Checks

```bash
command -v uv >/dev/null 2>&1 || error "uv is not installed"
command -v gh >/dev/null 2>&1 || error "gh CLI is not installed"
```

## Environment Variables

### Used by Script

- `PYPI_TOKEN` - Extracted from .env.local (PYPI_API_KEY)

### Used by External Tools

- `UV_PUBLISH_TOKEN` - Used by `uv publish` (set from PYPI_TOKEN)

## Security Considerations

### Token Handling

1. **Never in command line**: Token passed via environment variable
2. **Never in logs**: Token not echoed to stdout/stderr
3. **File permissions**: `.env.local` should be 600 (read/write owner only)
4. **Git ignored**: `.env.local` must be in `.gitignore`

### Validation

```bash
# Check token exists (but don't print it)
if [[ -z "$PYPI_TOKEN" ]]; then
    error "PYPI_API_KEY is empty in .env.local"
fi
```

## Testing the Script

### Dry Run (No Side Effects)

```bash
# Test validation steps only
bash -n scripts/publish.sh  # Syntax check

# Test with fake token (will fail at PyPI upload)
echo "PYPI_API_KEY=pypi-fake-token-for-testing" > .env.local.test
```

### Safe Testing

1. Create a test PyPI account: https://test.pypi.org/
2. Get test PyPI token
3. Modify script to use test PyPI URL
4. Run full release to test.pypi.org

### Integration Tests

Located in `tests/integration/test_publish_script.py`:

```python
def test_publish_validation():
    """Test script validates environment correctly."""
    result = subprocess.run(["./scripts/publish.sh"], capture_output=True)
    assert result.returncode != 0  # Should fail without .env.local

def test_version_bump_rollback():
    """Test version bump rollback on failure."""
    # Simulate failure after version bump
    # Verify VERSION file restored
```

## Maintenance Tasks

### Adding New Validation

Add to Step 1 (Validate environment):

```bash
# Check new requirement
if [[ ! -f "some_required_file" ]]; then
    error "some_required_file not found"
fi
```

### Adding New Build Step

Add between existing steps, update step numbers:

```bash
info "Step X/Y: New build step..."
# New logic here
success "New step complete"
```

### Changing PyPI Upload Method

Modify Step 7 (Publish to PyPI):

```bash
# Current: twine upload
uv run twine upload "dist/kuzu_memory-${NEW_VERSION}"* -u __token__ -p "$PYPI_TOKEN"

# Alternative: uv publish (requires UV_PUBLISH_TOKEN)
UV_PUBLISH_TOKEN="$PYPI_TOKEN" uv publish
```

## Common Modifications

### Skip Specific Tests

```bash
# Current: Run all unit tests
if uv run pytest tests/unit/ -q --tb=no; then

# Modified: Run only critical tests
if uv run pytest tests/unit/test_core.py -q --tb=no; then
```

### Add Pre-Publish Hook

```bash
# After Step 4 (tests)
info "Running pre-publish hook..."
./scripts/pre_publish_hook.sh
success "Pre-publish hook complete"
```

### Custom GitHub Release Notes

```bash
# Current: Auto-generated notes
gh release create "v$NEW_VERSION" --generate-notes

# Modified: Custom notes from CHANGELOG
RELEASE_NOTES=$(./scripts/extract_changelog.sh "$NEW_VERSION")
gh release create "v$NEW_VERSION" --notes "$RELEASE_NOTES"
```

## Debugging

### Enable Verbose Mode

```bash
# Add at top of script
set -x  # Print each command before execution
```

### Check Intermediate State

```bash
# After version bump
echo "New version: $NEW_VERSION"
cat VERSION
git diff

# After build
ls -lh dist/
tar -tzf dist/kuzu_memory-*.tar.gz | head
```

### Test Individual Steps

```bash
# Test version bump only
./scripts/manage_version.py bump patch
./scripts/manage_version.py show

# Test build only
uv build
ls -la dist/

# Test upload only (dry run)
uv run twine check dist/*
```

## Performance Optimization

### Current Bottlenecks

1. **Test execution**: ~10-30s (skippable with --no-test)
2. **PyPI upload**: ~5-10s (depends on network)
3. **GitHub release**: ~2-5s (API call)

### Total Runtime

- **With tests**: ~30-60 seconds
- **Without tests**: ~20-30 seconds

### Future Optimizations

- Parallel test execution (pytest-xdist)
- Cached test results (pytest-cache)
- Compressed upload (smaller wheel)

## Error Recovery

### Failed at Version Bump

```bash
# Automatic rollback happens
# Just fix issue and re-run
```

### Failed at Tests

```bash
# Automatic rollback happens
# Fix tests, re-run
pytest tests/unit/ -v  # Debug
./scripts/publish.sh
```

### Failed at PyPI Upload

```bash
# Version bump committed but not pushed
# Rollback not automatic (already committed)

# Option 1: Force re-upload (if version not taken)
./scripts/publish.sh  # Will fail (version exists)

# Option 2: Manual rollback
git reset --hard HEAD~1  # Remove commit
git tag -d vX.Y.Z        # Remove tag
./scripts/publish.sh     # Try again
```

### Failed at GitHub Release

```bash
# Package already on PyPI
# Just create release manually
gh release create "v$(cat VERSION)" --generate-notes
```

## Related Documentation

- [Publishing Guide](../docs/PUBLISHING.md) - User-facing publishing documentation
- [Release Checklist](../docs/RELEASE_CHECKLIST.md) - Quick reference
- [Development Guide](../CLAUDE.md) - Development workflow

---

**Last Updated**: 2025-01-20
