# Root Cause Analysis: Missing `click` Module in Homebrew Installation

**Date:** 2025-11-25
**Issue:** ModuleNotFoundError: No module named 'click'
**Context:** kuzu-memory v1.5.1 installed via Homebrew
**Investigated by:** Research Agent

## Executive Summary

The root cause of the missing `click` module is that the Homebrew formula for kuzu-memory is incomplete. While the formula uses `virtualenv_install_with_resources`, it does **not declare any resource blocks** for the package dependencies. This causes Homebrew to install only the kuzu-memory package itself into the virtualenv, without any of its required dependencies.

## Evidence

### 1. Package Dependencies are Correctly Declared in Source

**File:** `/Users/masa/Projects/kuzu-memory/pyproject.toml` (lines 27-40)

```toml
dependencies = [
    "kuzu>=0.4.0",           # Graph database
    "pydantic>=2.0",         # Data validation
    "click>=8.1.0",          # CLI ← CORRECTLY DECLARED
    "pyyaml>=6.0",          # Configuration
    "python-dateutil>=2.8",  # Date handling
    "typing-extensions>=4.5", # Python 3.11+ compatibility
    "rich>=13.0.0",         # Rich CLI formatting
    "psutil>=5.9.0",        # System and process utilities
    "gitpython>=3.1.0",     # Git repository integration
    "mcp>=1.0.0",           # Model Context Protocol SDK
    "packaging>=20.0",      # Version comparison
    "tomli-w>=1.0.0",       # TOML writing support
]
```

**Finding:** `click>=8.1.0` is properly declared in the project's dependency list.

### 2. Homebrew Formula is Missing Resource Declarations

**File:** `/Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb`

```ruby
class KuzuMemory < Formula
  include Language::Python::Virtualenv

  desc "Lightweight, embedded graph-based memory system for AI applications"
  homepage "https://github.com/bobmatnyc/kuzu-memory"
  url "https://files.pythonhosted.org/packages/2c/ae/d417c7c299f20b8cd71f07e0b499224a5588ae4a15f15bb012e91f9918e7/kuzu_memory-1.5.1.tar.gz"
  sha256 "a29d0c11b526d8ee932b99f71ee56f0d8d7f2183b3b938a17fc177a2a55e01c4"
  license "MIT"
  version "1.5.1"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources  # ← PROBLEM: No resources declared!
  end

  test do
    system bin/"kuzu-memory", "--version"
  end
end
```

**Finding:** The formula uses `virtualenv_install_with_resources` but declares **zero resource blocks**. This method expects each dependency to be explicitly listed as a `resource` block.

### 3. Installed Package Contains Only kuzu-memory

**Verification:**
```bash
$ ls -la /opt/homebrew/Cellar/kuzu-memory/1.5.1/libexec/lib/python3.11/site-packages/
drwxr-xr-x@ 21 masa  admin  672 Nov 25 16:41 kuzu_memory
drwxr-xr-x@  8 masa  admin  256 Nov 25 16:41 kuzu_memory-1.5.1.dist-info
```

**Finding:** Only `kuzu_memory` and its metadata are installed. No dependencies (click, rich, pydantic, etc.) are present.

### 4. Comparison with Working Formulas

**Example:** `python-yq` formula (working correctly)

```ruby
class PythonYq < Formula
  include Language::Python::Virtualenv

  # ... metadata ...

  resource "argcomplete" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "d0519b1bc867f5f4f4713c41ad0aba73a4a5f007449716b16f385f2166dc6adf"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f"
  end

  # ... more resources ...

  def install
    virtualenv_install_with_resources
  end
end
```

**Finding:** Working formulas explicitly declare each dependency as a `resource` block with PyPI URL and SHA256 hash.

## Root Cause

**The Homebrew formula is incomplete.**

When using `virtualenv_install_with_resources`, Homebrew's Python language module expects:
1. Each dependency to be declared as a `resource` block
2. Each resource must include the PyPI download URL and SHA256 hash
3. The method then downloads and installs all resources into the virtualenv

Without resource declarations, `virtualenv_install_with_resources` only installs the main package (kuzu-memory) and ignores all dependencies listed in `pyproject.toml` or `setup.py`.

## Required Dependencies (12 Total)

Based on `pyproject.toml`, the following resources need to be declared:

1. **click** (>=8.1.0) - CLI framework ← **MISSING, causing the error**
2. **kuzu** (>=0.4.0) - Graph database backend
3. **pydantic** (>=2.0) - Data validation
4. **pyyaml** (>=6.0) - YAML configuration
5. **python-dateutil** (>=2.8) - Date handling
6. **typing-extensions** (>=4.5) - Type hints
7. **rich** (>=13.0.0) - Rich terminal formatting
8. **psutil** (>=5.9.0) - System utilities
9. **gitpython** (>=3.1.0) - Git integration
10. **mcp** (>=1.0.0) - Model Context Protocol
11. **packaging** (>=20.0) - Version comparison
12. **tomli-w** (>=1.0.0) - TOML writing

### Transitive Dependencies Required

Several of these packages have their own dependencies that must also be declared:

**pydantic** requires:
- annotated-types>=0.6.0
- pydantic-core==2.41.5
- typing-inspection>=0.4.2

**rich** requires:
- pygments>=2.13.0
- markdown-it-py>=2.2.0

**gitpython** requires:
- gitdb>=4.0.1

**mcp** requires (extensive):
- anyio>=4.5
- httpx-sse>=0.4
- httpx>=0.27.1
- jsonschema>=4.20.0
- pydantic-settings>=2.5.2
- pyjwt[crypto]>=2.10.1
- python-multipart>=0.0.9
- sse-starlette>=1.6.1
- starlette>=0.27
- uvicorn>=0.31.1

**Total:** Approximately **30+ packages** need to be declared as resources (including transitive dependencies).

## Recommended Fix Approaches

### Option 1: Manual Resource Declaration (Most Control)

**Pros:**
- Full control over versions
- Follows Homebrew best practices
- Reproducible builds
- Works offline after initial download

**Cons:**
- Time-consuming to maintain (~30 resource blocks)
- Must manually track transitive dependencies
- Requires updating for every dependency version change

**Implementation:** Add resource blocks for all dependencies to `kuzu-memory.rb`

### Option 2: Use `pip_install_and_link` (Simpler, Less Robust)

**Pros:**
- Minimal formula changes
- pip automatically resolves dependencies
- Less maintenance burden

**Cons:**
- Not recommended by Homebrew for production formulas
- Requires internet connection at install time
- Less reproducible (dependency versions can drift)
- May conflict with other Homebrew packages

**Implementation:**
```ruby
def install
  virtualenv_create(libexec, "python3.11")
  system libexec/"bin/pip", "install", "--no-binary", ":all:", buildpath
end
```

### Option 3: Hybrid Approach (Recommended)

**Pros:**
- Declare only direct dependencies as resources
- Let pip resolve transitive dependencies
- Balance between control and maintainability

**Cons:**
- Still requires ~12 resource declarations
- Transitive dependencies less controlled

**Implementation:**
```ruby
# Declare 12 direct dependencies as resources
resource "click" do
  url "https://files.pythonhosted.org/packages/..."
  sha256 "12ff4785d337a1bb490bb7e9c2b1ee5da3112e94a8622f26a6c77f5d2fc6842a"
end

# ... 11 more resources ...

def install
  virtualenv_install_with_resources
end
```

### Option 4: Automated Resource Generation (Best Long-term)

Use `homebrew-pypi-poet` to automatically generate resource blocks:

```bash
# Install poet
brew install homebrew-pypi-poet

# Generate resources
poet kuzu-memory==1.5.1 > resources.txt

# Copy resource blocks into kuzu-memory.rb
```

## Specific Files Requiring Changes

### 1. `/Users/masa/Projects/homebrew-tools/Formula/kuzu-memory.rb`

**Current state:** Incomplete (8 lines)
**Required change:** Add 12+ resource blocks (approximately 50-70 lines)
**Priority:** CRITICAL - Blocks package functionality

### 2. Repository: `bobmatnyc/homebrew-tools`

**Location:** `Formula/kuzu-memory.rb`
**Action:** Update formula and push to GitHub
**Impact:** All future Homebrew installations will work correctly

## Immediate Workaround for Users

Until the formula is fixed, users can work around the issue:

**Option A: Install dependencies manually**
```bash
/opt/homebrew/Cellar/kuzu-memory/1.5.1/libexec/bin/pip install click kuzu pydantic pyyaml python-dateutil typing-extensions rich psutil gitpython mcp packaging tomli-w
```

**Option B: Use pip instead of Homebrew**
```bash
brew uninstall kuzu-memory
pip install kuzu-memory
```

**Option C: Use pipx (recommended for CLI tools)**
```bash
brew install pipx
pipx install kuzu-memory
```

## Prevention Recommendations

1. **Add CI/CD Testing:** Test Homebrew formula installations in CI to catch missing dependencies
2. **Automated Formula Generation:** Use `homebrew-pypi-poet` for initial formula creation
3. **Installation Verification:** Add test cases that import key modules (not just `--version`)
4. **Documentation:** Include formula update process in release checklist

## Related Issues Found

While investigating, no other dependency issues were found. The `pyproject.toml` configuration is correct and complete. The issue is isolated to the Homebrew formula.

## Severity Assessment

**Severity:** HIGH
**Impact:** Complete package failure - `kuzu-memory setup` cannot run
**Scope:** All Homebrew installations (v1.5.1)
**Workaround available:** Yes (manual pip install or use pip/pipx instead)

## Next Steps

1. **Immediate:** Generate complete resource blocks for all 12 direct dependencies
2. **Short-term:** Update `kuzu-memory.rb` formula in `bobmatnyc/homebrew-tools`
3. **Medium-term:** Add formula testing to CI/CD pipeline
4. **Long-term:** Consider automated formula generation on release

---

## Appendix A: Generated Resource Blocks (Direct Dependencies)

```ruby
resource "click" do
  url "https://files.pythonhosted.org/packages/3d/fa/656b739db8587d7b5dfa22e22ed02566950fbfbcdc20311993483657a5c0/click-8.3.1.tar.gz"
  sha256 "12ff4785d337a1bb490bb7e9c2b1ee5da3112e94a8622f26a6c77f5d2fc6842a"
end

resource "kuzu" do
  url "https://files.pythonhosted.org/packages/96/0c/f141a81485729a072dc527b474e7580d5632309c68ad1a5aa6ed9ac45387/kuzu-0.11.3.tar.gz"
  sha256 "e7bea3ca30c4bb462792eedcaa7f2125c800b243bb4a872e1eedc16917c1967a"
end

resource "pydantic" do
  url "https://files.pythonhosted.org/packages/96/ad/a17bc283d7d81837c061c49e3eaa27a45991759a1b7eae1031921c6bd924/pydantic-2.12.4.tar.gz"
  sha256 "0f8cb9555000a4b5b617f66bfd2566264c4984b27589d3b845685983e8ea85ac"
end

resource "pyyaml" do
  url "https://files.pythonhosted.org/packages/05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/pyyaml-6.0.3.tar.gz"
  sha256 "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f"
end

resource "python-dateutil" do
  url "https://files.pythonhosted.org/packages/66/c0/0c8b6ad9f17a802ee498c46e004a0eb49bc148f2fd230864601a86dcf6db/python-dateutil-2.9.0.post0.tar.gz"
  sha256 "37dd54208da7e1cd875388217d5e00ebd4179249f90fb72437e91a35459a0ad3"
end

resource "typing-extensions" do
  url "https://files.pythonhosted.org/packages/72/94/1a15dd82efb362ac84269196e94cf00f187f7ed21c242792a923cdb1c61f/typing_extensions-4.15.0.tar.gz"
  sha256 "0cea48d173cc12fa28ecabc3b837ea3cf6f38c6d1136f85cbaaf598984861466"
end

resource "rich" do
  url "https://files.pythonhosted.org/packages/fb/d2/8920e102050a0de7bfabeb4c4614a49248cf8d5d7a8d01885fbb24dc767a/rich-14.2.0.tar.gz"
  sha256 "73ff50c7c0c1c77c8243079283f4edb376f0f6442433aecb8ce7e6d0b92d1fe4"
end

resource "psutil" do
  url "https://files.pythonhosted.org/packages/e1/88/bdd0a41e5857d5d703287598cbf08dad90aed56774ea52ae071bae9071b6/psutil-7.1.3.tar.gz"
  sha256 "6c86281738d77335af7aec228328e944b30930899ea760ecf33a4dba66be5e74"
end

resource "gitpython" do
  url "https://files.pythonhosted.org/packages/9a/c8/dd58967d119baab745caec2f9d853297cec1989ec1d63f677d3880632b88/gitpython-3.1.45.tar.gz"
  sha256 "85b0ee964ceddf211c41b9f27a49086010a190fd8132a24e21f362a4b36a791c"
end

resource "mcp" do
  url "https://files.pythonhosted.org/packages/a3/a2/c5ec0ab38b35ade2ae49a90fada718fbc76811dc5aa1760414c6aaa6b08a/mcp-1.22.0.tar.gz"
  sha256 "769b9ac90ed42134375b19e777a2858ca300f95f2e800982b3e2be62dfc0ba01"
end

resource "packaging" do
  url "https://files.pythonhosted.org/packages/a1/d4/1fc4078c65507b51b96ca8f8c3ba19e6a61c8253c72794544580a7b6c24d/packaging-25.0.tar.gz"
  sha256 "d443872c98d677bf60f6a1f2f8c1cb748e8fe762d2bf9d3148b5599295b0fc4f"
end

resource "tomli-w" do
  url "https://files.pythonhosted.org/packages/19/75/241269d1da26b624c0d5e110e8149093c759b7a286138f4efd61a60e75fe/tomli_w-1.2.0.tar.gz"
  sha256 "2dd14fac5a47c27be9cd4c976af5a12d87fb1f0b4512f81d69cce3b35ae25021"
end
```

**Note:** These are only the 12 direct dependencies. Transitive dependencies (~18 additional packages) should also be added for a complete, robust formula.

## Appendix B: Memory Usage Statistics

This research analysis was conducted using strategic sampling techniques:
- Files read: 5 (pyproject.toml, setup.py, 3 formula examples)
- Total file size analyzed: ~15KB
- No large files loaded into memory
- Pattern-based search used extensively
- Research methodology: grep-first, targeted reading

**Research approach:** Efficient, memory-conscious investigation suitable for embedded graph-based memory systems.
