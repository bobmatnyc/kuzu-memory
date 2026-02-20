#!/usr/bin/env bash
#
# publish.sh - Robust publishing script for kuzu-memory
#
# Usage:
#   ./scripts/publish.sh [patch|minor|major] [--no-test]
#
# Examples:
#   ./scripts/publish.sh              # Patch release (default)
#   ./scripts/publish.sh minor        # Minor release
#   ./scripts/publish.sh major        # Major release
#   ./scripts/publish.sh patch --no-test  # Skip tests
#
# Requirements:
#   - .env.local with PYPI_API_KEY
#   - Clean working directory on main branch
#   - uv, gh CLI tools installed
#

set -e  # Exit immediately on error
set -u  # Exit on undefined variables
set -o pipefail  # Catch errors in pipelines

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${BLUE}INFO: $1${NC}"
}

success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

warn() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

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

# Validate version type
if [[ ! "$VERSION_TYPE" =~ ^(patch|minor|major)$ ]]; then
    error "Invalid version type: $VERSION_TYPE. Must be patch, minor, or major."
fi

info "Starting $VERSION_TYPE release process..."

# Step 1: Validate environment
info "Step 1/8: Validating environment..."

# Check .env.local exists
if [[ ! -f ".env.local" ]]; then
    error ".env.local file not found. Create it with PYPI_API_KEY=your_token"
fi

# Check PYPI_API_KEY exists in .env.local
if ! grep -q "^PYPI_API_KEY=" .env.local; then
    error "PYPI_API_KEY not found in .env.local"
fi

PYPI_TOKEN=$(grep "^PYPI_API_KEY=" .env.local | sed 's/PYPI_API_KEY=//')
if [[ -z "$PYPI_TOKEN" ]]; then
    error "PYPI_API_KEY is empty in .env.local"
fi

# Check we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    error "Must be on main branch (currently on: $CURRENT_BRANCH)"
fi

# Check working directory is clean
if [[ -n "$(git status --porcelain)" ]]; then
    error "Working directory has uncommitted changes. Commit or stash them first."
fi

# Check required tools
command -v uv >/dev/null 2>&1 || error "uv is not installed"
command -v gh >/dev/null 2>&1 || error "gh CLI is not installed"

success "Environment validation passed"

# Step 2: Bump version
info "Step 2/8: Bumping version ($VERSION_TYPE)..."

OLD_VERSION=$(cat VERSION)
./scripts/manage_version.py bump --type "$VERSION_TYPE" --no-tag
NEW_VERSION=$(cat VERSION)

if [[ "$OLD_VERSION" == "$NEW_VERSION" ]]; then
    error "Version did not change after bump (still $OLD_VERSION)"
fi

success "Version bumped: $OLD_VERSION → $NEW_VERSION"

# Store the old version for potential rollback
ROLLBACK_NEEDED=false

# Function to rollback version bump
rollback_version() {
    if [[ "$ROLLBACK_NEEDED" == "true" ]]; then
        warn "Rolling back version bump..."
        git restore VERSION pyproject.toml uv.lock src/kuzu_memory/__version__.py CHANGELOG.md
        warn "Version rolled back to $OLD_VERSION"
    fi
}

# Trap errors and rollback if needed
trap 'rollback_version' ERR

ROLLBACK_NEEDED=true  # Enable rollback from this point

# Step 3: Build package
info "Step 3/8: Building package..."

# Clean old builds
rm -rf dist/ build/ *.egg-info

uv build

# Verify build artifacts exist
if [[ ! -f "dist/kuzu_memory-${NEW_VERSION}.tar.gz" ]]; then
    error "Build failed: tar.gz not found"
fi

if [[ ! -f "dist/kuzu_memory-${NEW_VERSION}-py3-none-any.whl" ]]; then
    error "Build failed: wheel not found"
fi

success "Package built successfully"

# Step 4: Run tests (optional)
if [[ "$RUN_TESTS" == "true" ]]; then
    info "Step 4/8: Running sanity tests..."

    if uv run pytest tests/unit/ -q --tb=no; then
        success "Tests passed"
    else
        error "Tests failed. Fix tests before publishing."
    fi
else
    warn "Step 4/8: Skipping tests (--no-test flag used)"
fi

# Step 5: Commit and tag
info "Step 5/8: Committing version bump..."

# Check if uv.lock was modified by version bump (pyproject.toml update triggers lock)
if [[ -n "$(git status --porcelain uv.lock 2>/dev/null)" ]]; then
    info "uv.lock was updated by version bump, syncing dependencies..."
    uv sync --no-progress
fi

git add VERSION pyproject.toml uv.lock src/kuzu_memory/__version__.py CHANGELOG.md

if git diff --staged --quiet; then
    warn "No changes to commit (VERSION files may not have changed)"
else
    # Use --no-verify to skip pre-commit hooks (code already validated)
    git commit --no-verify -m "chore: bump version to $NEW_VERSION"
    success "Version bump committed"
fi

info "Creating git tag v$NEW_VERSION..."
git tag "v$NEW_VERSION"
success "Tag created"

# Step 6: Push to GitHub
info "Step 6/8: Pushing to GitHub..."

git push origin main --tags
success "Pushed to GitHub with tags"

# We've successfully pushed, so disable rollback
ROLLBACK_NEEDED=false

# Step 7: Publish to PyPI
info "Step 7/8: Publishing to PyPI..."

# Export PYPI_TOKEN as TWINE_PASSWORD for twine to use
export TWINE_USERNAME=__token__
export TWINE_PASSWORD="$PYPI_TOKEN"

uv run twine upload "dist/kuzu_memory-${NEW_VERSION}"*
success "Published to PyPI"

# Step 8: Create GitHub release
info "Step 8/8: Creating GitHub release..."

# Attempt GitHub release, but don't fail if it errors (PyPI publish is critical path)
if gh release create "v$NEW_VERSION" --generate-notes 2>&1; then
    success "GitHub release created"
else
    warn "GitHub release creation failed. You may need to:"
    warn "  1. Check 'gh auth status' and ensure 'workflow' scope is enabled"
    warn "  2. Re-authenticate with: gh auth refresh -s workflow"
    warn "  3. Manually create release: gh release create v$NEW_VERSION --generate-notes"
    warn "Package is already on PyPI, so this is non-critical."
fi

# Print summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Release $NEW_VERSION completed successfully! 🎉"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Package:  https://pypi.org/project/kuzu-memory/$NEW_VERSION/"
echo "🏷️  Release: https://github.com/bobmatnyc/kuzu-memory/releases/tag/v$NEW_VERSION"
echo "📝 Commit:   $(git rev-parse --short HEAD)"
echo ""
echo "Next steps:"
echo "  1. Verify package on PyPI: pip install kuzu-memory==$NEW_VERSION"
echo "  2. Test installation: kuzu-memory --version"
echo "  3. Update documentation if needed"
echo ""
