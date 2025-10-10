# Towncrier Quick Start Guide

## 🚀 Quick Reference

### Create a Fragment (Most Common)

```bash
# For a new feature
make changelog-fragment ISSUE=123 TYPE=feature

# For a bug fix
make changelog-fragment ISSUE=124 TYPE=bugfix

# For documentation
make changelog-fragment ISSUE=125 TYPE=doc
```

### Preview Changelog

```bash
make changelog-preview
```

### Validate Fragments

```bash
make changelog-validate
```

### Version Bump (Auto-builds Changelog)

```bash
make version-patch  # 1.3.0 → 1.3.1
make version-minor  # 1.3.0 → 1.4.0
make version-major  # 1.3.0 → 2.0.0
```

## 📝 Fragment Types

| Command | Description | Changelog Section |
|---------|-------------|-------------------|
| `TYPE=feature` | New features | Added |
| `TYPE=enhancement` | Improvements | Changed |
| `TYPE=bugfix` | Bug fixes | Fixed |
| `TYPE=deprecation` | Deprecated features | Deprecated |
| `TYPE=removal` | Removed features | Removed |
| `TYPE=doc` | Documentation | Documentation |
| `TYPE=performance` | Performance improvements | Performance |
| `TYPE=security` | Security fixes | Security |
| `TYPE=misc` | Other changes | (not shown) |

## 🔄 Workflow

1. **Make changes** to code
2. **Create fragment** describing the change
3. **Commit fragment** with your PR
4. **Preview** (optional): `make changelog-preview`
5. **Release time**: `make version-patch` (auto-builds changelog)

## 💡 Tips

- **One fragment per issue/PR** - Keep changes focused
- **Clear descriptions** - Explain what changed from user perspective
- **No technical details** - Focus on impact, not implementation
- **Present tense** - "Add feature" not "Added feature"

## 📖 Examples

### Good Fragment Content

```markdown
# 123.feature.md
Add support for async memory operations with connection pooling
```

```markdown
# 124.bugfix.md
Fix race condition in concurrent memory recall operations
```

```markdown
# 125.performance.md
Improve memory recall speed by 50% through query optimization
```

### Bad Fragment Content

```markdown
# 123.feature.md
Updated the MemoryStore class to use async/await patterns
```
^ Too technical, focuses on implementation

```markdown
# 124.bugfix.md
Fixed it
```
^ Too vague, doesn't explain what was fixed

## 🎯 First Time Setup

When ready to use towncrier features:

```bash
pip install -e ".[dev]"
```

Or separately:

```bash
pip install towncrier>=23.11.0
```

## 📚 Full Documentation

- Detailed guide: `changelog.d/README.md`
- Implementation report: `TOWNCRIER_IMPLEMENTATION_SUMMARY.md`
- Official docs: https://towncrier.readthedocs.io/

## ✅ Quick Checklist

- [ ] Create fragment for your change
- [ ] Use descriptive, user-focused language
- [ ] Choose correct fragment type
- [ ] Commit fragment with your PR
- [ ] Preview before release (optional)
- [ ] Version bump auto-builds changelog
