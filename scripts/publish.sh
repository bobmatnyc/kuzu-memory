#!/usr/bin/env bash
#
# publish.sh - Publish kuzu-memory to PyPI
#
# Usage:
#   ./scripts/publish.sh [patch|minor|major] [--no-test]
#
# Examples:
#   ./scripts/publish.sh              # Patch release (default)
#   ./scripts/publish.sh minor        # Minor release
#   ./scripts/publish.sh patch --no-test  # Skip tests
#
# Requirements:
#   - .env.local with PYPI_API_KEY=pypi-...
#   - Clean working directory on main branch
#   - uv installed
#

set -e
set -u
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() { echo -e "${RED}ERROR: $1${NC}" >&2; exit 1; }
info()  { echo -e "${BLUE}INFO: $1${NC}"; }
success() { echo -e "${GREEN}SUCCESS: $1${NC}"; }
warn()  { echo -e "${YELLOW}WARNING: $1${NC}"; }

# Parse arguments
VERSION_TYPE="${1:-patch}"
RUN_TESTS=true

if [[ "${2:-}" == "--no-test" ]] || [[ "${1:-}" == "--no-test" ]]; then
    RUN_TESTS=false
    VERSION_TYPE="${1:-patch}"
    if [[ "${1:-}" == "--no-test" ]]; then
        VERSION_TYPE="patch"
    fi
fi

if [[ ! "$VERSION_TYPE" =~ ^(patch|minor|major)$ ]]; then
    error "Invalid version type: $VERSION_TYPE. Must be patch, minor, or major."
fi

info "Starting $VERSION_TYPE release..."

# ── Step 1: Validate ──────────────────────────────────────────────
info "Step 1/7: Validating environment..."

[[ -f ".env.local" ]] || error ".env.local not found. Create it with PYPI_API_KEY=pypi-..."
grep -q "^PYPI_API_KEY=" .env.local || error "PYPI_API_KEY not found in .env.local"

PYPI_TOKEN=$(grep "^PYPI_API_KEY=" .env.local | sed 's/PYPI_API_KEY=//')
[[ -n "$PYPI_TOKEN" ]] || error "PYPI_API_KEY is empty in .env.local"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
[[ "$CURRENT_BRANCH" == "main" ]] || error "Must be on main branch (currently on: $CURRENT_BRANCH)"

[[ -z "$(git status --porcelain)" ]] || error "Working directory not clean. Commit or stash first."

command -v uv >/dev/null 2>&1 || error "uv is not installed"

success "Environment OK"

# ── Step 2: Bump version ──────────────────────────────────────────
info "Step 2/7: Bumping version ($VERSION_TYPE)..."

OLD_VERSION=$(cat VERSION)
./scripts/manage_version.py bump --type "$VERSION_TYPE" --no-tag
NEW_VERSION=$(cat VERSION)

[[ "$OLD_VERSION" != "$NEW_VERSION" ]] || error "Version did not change (still $OLD_VERSION)"
success "Version: $OLD_VERSION → $NEW_VERSION"

# Rollback on error (before push)
ROLLBACK_NEEDED=true
rollback_version() {
    if [[ "$ROLLBACK_NEEDED" == "true" ]]; then
        warn "Rolling back version bump..."
        git checkout -- VERSION pyproject.toml src/kuzu_memory/__version__.py CHANGELOG.md uv.lock 2>/dev/null || true
        git tag -d "v$NEW_VERSION" 2>/dev/null || true
        warn "Rolled back to $OLD_VERSION"
    fi
}
trap 'rollback_version' ERR

# ── Step 3: Build ─────────────────────────────────────────────────
info "Step 3/7: Building package..."

rm -rf dist/ build/ *.egg-info
uv build

[[ -f "dist/kuzu_memory-${NEW_VERSION}.tar.gz" ]] || error "Build failed: tar.gz not found"
[[ -f "dist/kuzu_memory-${NEW_VERSION}-py3-none-any.whl" ]] || error "Build failed: wheel not found"
success "Built: kuzu_memory-${NEW_VERSION}"

# ── Step 4: Test (optional) ───────────────────────────────────────
if [[ "$RUN_TESTS" == "true" ]]; then
    info "Step 4/7: Running tests..."
    uv run pytest tests/unit/ -q --tb=no || error "Tests failed."
    success "Tests passed"
else
    warn "Step 4/7: Tests skipped (--no-test)"
fi

# ── Step 5: Commit + tag ─────────────────────────────────────────
info "Step 5/7: Committing version bump..."

# Sync uv.lock if pyproject.toml change dirtied it
if [[ -n "$(git status --porcelain uv.lock 2>/dev/null)" ]]; then
    uv sync --no-progress 2>/dev/null || true
fi

git add VERSION pyproject.toml uv.lock src/kuzu_memory/__version__.py CHANGELOG.md
git diff --staged --quiet && warn "Nothing to commit" || \
    git commit --no-verify -m "chore: bump version to $NEW_VERSION"

git tag "v$NEW_VERSION"
success "Committed and tagged v$NEW_VERSION"

# ── Step 6: Push ──────────────────────────────────────────────────
info "Step 6/7: Pushing to GitHub..."

git push origin main --tags
ROLLBACK_NEEDED=false
success "Pushed to GitHub"

# ── Step 7: Publish to PyPI ───────────────────────────────────────
info "Step 7/7: Publishing to PyPI..."

UV_PUBLISH_TOKEN="$PYPI_TOKEN" uv publish dist/kuzu_memory-${NEW_VERSION}*
success "Published to PyPI"

# ── Done ──────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "kuzu-memory $NEW_VERSION released! 🎉"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  📦 PyPI:   https://pypi.org/project/kuzu-memory/$NEW_VERSION/"
echo "  🏷️  Tag:    v$NEW_VERSION"
echo "  📝 Commit: $(git rev-parse --short HEAD)"
echo ""
echo "  Verify: pip install kuzu-memory==$NEW_VERSION"
echo ""
