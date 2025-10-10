# Changelog Fragments

This directory contains changelog fragments managed by [towncrier](https://towncrier.readthedocs.io/).

## Quick Start

### Create a new fragment

```bash
make changelog-fragment ISSUE=<number> TYPE=<type>
```

**Available types:**
- `feature` → Added
- `enhancement` → Changed
- `bugfix` → Fixed
- `deprecation` → Deprecated
- `removal` → Removed
- `doc` → Documentation
- `performance` → Performance
- `security` → Security
- `misc` → Miscellaneous (not shown in changelog)

### Preview changes

```bash
make changelog-preview
```

### Validate fragments

```bash
make changelog-validate
```

### Build changelog (automatically run on version bump)

```bash
make changelog-build
```

## Fragment Format

Each fragment file should contain a single line describing the change:

```
Brief description of the change
```

The fragment filename format is: `<issue_number>.<type>.md`

Examples:
- `123.feature.md` - New feature for issue #123
- `456.bugfix.md` - Bug fix for issue #456
- `789.doc.md` - Documentation update for issue #789

## Workflow

1. **During development:** Create fragments for each significant change
2. **Before release:** Preview the changelog with `make changelog-preview`
3. **During version bump:** Fragments are automatically built into CHANGELOG.md
4. **After build:** Fragment files are automatically deleted (they're consumed)

## Integration with Version Management

The changelog fragment system is integrated with version bumping:

```bash
make version-patch  # Validates fragments, bumps version, builds changelog
make version-minor  # Validates fragments, bumps version, builds changelog
make version-major  # Validates fragments, bumps version, builds changelog
```

## Template

The `template.md` file defines how fragments are formatted in the final changelog. Don't edit this unless changing the changelog structure.

## Installation

Towncrier is included in the dev dependencies:

```bash
pip install -e ".[dev]"
```

Or install separately:

```bash
pip install towncrier>=23.11.0
```
