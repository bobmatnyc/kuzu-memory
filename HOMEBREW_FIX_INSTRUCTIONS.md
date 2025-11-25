# Homebrew Formula Fix Instructions

## Issue Summary

The Homebrew installation of kuzu-memory v1.5.1 is missing the `click` dependency (and all other dependencies) because the formula does not declare resource blocks for dependencies.

**Error:** `ModuleNotFoundError: No module named 'click'`

## Root Cause

The formula at `/Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb` uses `virtualenv_install_with_resources` but declares **zero resource blocks**. This causes only the main package to be installed without any dependencies.

## Quick Fix for Current Users

**Option 1: Install dependencies manually**
```bash
/opt/homebrew/Cellar/kuzu-memory/1.5.1/libexec/bin/pip install click kuzu pydantic pyyaml python-dateutil typing-extensions rich psutil gitpython mcp packaging tomli-w
```

**Option 2: Use pipx instead (recommended)**
```bash
brew uninstall kuzu-memory
brew install pipx
pipx install kuzu-memory
```

**Option 3: Use pip**
```bash
brew uninstall kuzu-memory
pip install kuzu-memory
```

## Permanent Fix (Update Homebrew Formula)

### Step 1: Replace Formula File

Replace `/Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb` with the corrected version:

**Source:** `/Users/masa/Projects/kuzu-memory/Formula-corrected/kuzu-memory.rb`

**Destination:** `/Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb`

```bash
# Copy corrected formula
cp /Users/masa/Projects/kuzu-memory/Formula-corrected/kuzu-memory.rb /Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb

# Or symlink for development
ln -sf /Users/masa/Projects/kuzu-memory/Formula-corrected/kuzu-memory.rb /Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb
```

### Step 2: Test Formula Locally

```bash
# Audit formula
brew audit --strict --online kuzu-memory

# Test installation locally
brew uninstall kuzu-memory
brew install --build-from-source kuzu-memory

# Verify all dependencies are installed
/opt/homebrew/Cellar/kuzu-memory/1.5.1/libexec/bin/python -c "import click, kuzu, pydantic, yaml, rich"

# Test CLI command
kuzu-memory --version
kuzu-memory setup
```

### Step 3: Commit and Push to Tap

```bash
cd /Users/masa/Projects/homebrew-tools

# Add the updated formula
git add Formula/kuzu-memory.rb

# Commit with descriptive message
git commit -m "fix: add all dependency resources to kuzu-memory formula

Fixes ModuleNotFoundError for click and other dependencies.

The formula was using virtualenv_install_with_resources but did not
declare any resource blocks, causing only kuzu-memory to be installed
without its dependencies.

Changes:
- Added 12 direct dependency resources (click, kuzu, pydantic, etc.)
- Added ~30 transitive dependency resources for full functionality
- Updated test to verify click module is importable

Resolves issue where 'kuzu-memory setup' would fail with:
ModuleNotFoundError: No module named 'click'"

# Push to GitHub
git push origin main
```

### Step 4: Update Tap and Test End-to-End

```bash
# Update tap
brew update

# Reinstall from tap
brew uninstall kuzu-memory
brew install bobmatnyc/tools/kuzu-memory

# Verify installation
kuzu-memory --version
kuzu-memory setup
```

## What Changed in the Formula

### Before (8 lines, broken)
```ruby
class KuzuMemory < Formula
  include Language::Python::Virtualenv

  desc "Lightweight, embedded graph-based memory system for AI applications"
  homepage "https://github.com/bobmatnyc/kuzu-memory"
  url "https://files.pythonhosted.org/packages/.../kuzu_memory-1.5.1.tar.gz"
  sha256 "a29d0c11b526d8ee932b99f71ee56f0d8d7f2183b3b938a17fc177a2a55e01c4"
  license "MIT"
  version "1.5.1"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources  # ← No resources declared!
  end

  test do
    system bin/"kuzu-memory", "--version"
  end
end
```

### After (~180 lines, working)
```ruby
class KuzuMemory < Formula
  include Language::Python::Virtualenv

  desc "Lightweight, embedded graph-based memory system for AI applications"
  homepage "https://github.com/bobmatnyc/kuzu-memory"
  url "https://files.pythonhosted.org/packages/.../kuzu_memory-1.5.1.tar.gz"
  sha256 "a29d0c11b526d8ee932b99f71ee56f0d8d7f2183b3b938a17fc177a2a55e01c4"
  license "MIT"
  version "1.5.1"

  depends_on "python@3.11"

  # Direct dependencies from pyproject.toml
  resource "click" do
    url "https://files.pythonhosted.org/packages/.../click-8.3.1.tar.gz"
    sha256 "12ff4785d337a1bb490bb7e9c2b1ee5da3112e94a8622f26a6c77f5d2fc6842a"
  end

  # ... 41 more resource blocks for all dependencies ...

  def install
    virtualenv_install_with_resources
  end

  test do
    system libexec/"bin/python", "-c", "import kuzu_memory; import click"
    assert_match version.to_s, shell_output("#{bin}/kuzu-memory --version")
  end
end
```

## Dependencies Declared (42 Total)

### Direct Dependencies (12)
1. click (CLI framework) ← **This was missing and caused the error**
2. kuzu (graph database)
3. pydantic (data validation)
4. pyyaml (YAML support)
5. python-dateutil (date handling)
6. typing-extensions (type hints)
7. rich (terminal formatting)
8. psutil (system utilities)
9. gitpython (git integration)
10. mcp (Model Context Protocol)
11. packaging (version handling)
12. tomli-w (TOML writing)

### Transitive Dependencies (30)
- pydantic dependencies: annotated-types, pydantic-core, typing-inspection
- rich dependencies: pygments, markdown-it-py, mdurl
- gitpython dependencies: gitdb, smmap
- mcp dependencies: anyio, httpx, httpx-sse, jsonschema, pydantic-settings, pyjwt, cryptography, python-multipart, sse-starlette, starlette, uvicorn
- httpx dependencies: idna, certifi, httpcore, h11, sniffio
- jsonschema dependencies: jsonschema-specifications, referencing, rpds-py, attrs
- Other: six, click-plugins

## Files Modified

1. **Main Formula:** `/Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb`
   - **Before:** 20 lines (8 effective)
   - **After:** ~180 lines
   - **Change:** Added 42 resource blocks

2. **Research Documentation:** `/Users/masa/Projects/kuzu-memory/docs/research/homebrew-click-dependency-issue-2025-11-25.md`
   - **Created:** Comprehensive root cause analysis
   - **Size:** 14KB

3. **Corrected Formula (reference):** `/Users/masa/Projects/kuzu-memory/Formula-corrected/kuzu-memory.rb`
   - **Created:** Working formula template
   - **Size:** ~6KB

## Verification Checklist

- [ ] Formula passes `brew audit --strict --online`
- [ ] Installation creates virtualenv with all dependencies
- [ ] `kuzu-memory --version` works
- [ ] `kuzu-memory setup` runs without ModuleNotFoundError
- [ ] Python imports work: `import click, kuzu, pydantic, yaml, rich`
- [ ] Formula committed to homebrew-tools repository
- [ ] Tap updated on GitHub
- [ ] End-to-end installation test from tap succeeds

## Future Prevention

1. **Add CI/CD Testing:** Test formula installations in GitHub Actions
2. **Automated Formula Generation:** Use `homebrew-pypi-poet` for future updates
3. **Enhanced Tests:** Import key modules, not just version check
4. **Release Checklist:** Include formula update verification

## Related Files

- **Root Cause Analysis:** `docs/research/homebrew-click-dependency-issue-2025-11-25.md`
- **Corrected Formula:** `Formula-corrected/kuzu-memory.rb`
- **Current Formula:** `/Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb`
- **Tap Repository:** `https://github.com/bobmatnyc/homebrew-tools`

## Need Help?

If you encounter issues:

1. Check formula audit: `brew audit --strict kuzu-memory`
2. View installation logs: `brew install --verbose --debug kuzu-memory`
3. Verify virtualenv contents: `ls /opt/homebrew/Cellar/kuzu-memory/1.5.1/libexec/lib/python3.11/site-packages/`
4. Test Python imports directly: `/opt/homebrew/Cellar/kuzu-memory/1.5.1/libexec/bin/python -c "import click"`

## Summary

**Problem:** Missing click module (and all other dependencies)
**Cause:** Formula missing resource declarations
**Solution:** Add 42 resource blocks to formula
**Status:** Fixed formula created at `Formula-corrected/kuzu-memory.rb`
**Next Step:** Copy to tap repository and commit

**Estimated Time to Fix:** 5 minutes (copy + commit + push)
**Users Affected:** All Homebrew installations of kuzu-memory v1.5.1
