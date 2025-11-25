# Homebrew Installation Fix - Quick Guide

**Issue:** `ModuleNotFoundError: No module named 'click'` when running `kuzu-memory` commands

**Status:** ✅ **FIXED** - Corrected formula available in `bobmatnyc/homebrew-tools`

---

## If You Already Installed v1.5.1 (Broken)

### Quick Fix (Recommended - 2 minutes)

Run this one command to fix your existing installation:

```bash
/opt/homebrew/Cellar/kuzu-memory/1.5.1/libexec/bin/python3.11 -m pip install \
  --target=/opt/homebrew/Cellar/kuzu-memory/1.5.1/libexec/lib/python3.11/site-packages \
  click kuzu pydantic pyyaml python-dateutil typing-extensions \
  rich psutil gitpython mcp packaging tomli-w
```

**Verify it works:**
```bash
kuzu-memory --version
kuzu-memory setup --help
```

You should see:
```
kuzu-memory, version 1.5.1
```

✅ **Done!** You can now use `kuzu-memory` normally.

---

### Clean Reinstall (Alternative - 5 minutes)

If you prefer a clean reinstall with the corrected formula:

```bash
# Uninstall broken version
brew uninstall kuzu-memory

# Update tap to get corrected formula
brew update

# Reinstall with corrected formula
brew install bobmatnyc/tools/kuzu-memory

# Verify installation
kuzu-memory --version
kuzu-memory setup
```

---

## If You're Installing Fresh

✅ The corrected formula is already available. Just install normally:

```bash
brew tap bobmatnyc/tools
brew install kuzu-memory
kuzu-memory setup
```

---

## What Was Wrong?

The original Homebrew formula was missing all 42 Python dependency resource blocks. This caused only the `kuzu-memory` package to be installed, without its required dependencies like `click`, `pydantic`, `rich`, etc.

The corrected formula now includes all required dependencies and installs correctly.

---

## Verification

You can verify your installation is working by running:

```bash
# Should show version without errors
kuzu-memory --version

# Should display help without import errors
kuzu-memory --help

# Should show commands list
kuzu-memory setup --help
```

If any of these fail with `ModuleNotFoundError`, use the Quick Fix above.

---

## Need Help?

- **Report Issues:** https://github.com/bobmatnyc/kuzu-memory/issues
- **Full Verification Report:** See `HOMEBREW_VERIFICATION_REPORT.md`
- **Formula Source:** https://github.com/bobmatnyc/homebrew-tools/blob/main/Formula/kuzu-memory.rb

---

**Last Updated:** 2025-11-25
**Fixed in:** Formula commit `a68d81f`
