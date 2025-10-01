# KuzuMemory - Deployment & Setup Guide

## Quick Start

KuzuMemory stores conversation memories in a local graph database that **should be committed to your git repository** for team collaboration and persistence.

### Installation

```bash
pip install kuzu-memory
```

### Project Setup

```bash
# Initialize memory database in your project
kuzu-memory init

# This creates:
# .kuzu_memory/
#   ├── memories.db      # ← COMMIT THIS TO GIT!
#   ├── config.yaml      # ← COMMIT THIS TOO!
#   └── .gitkeep         # ← Ensures directory is tracked
```

## ⚠️ IMPORTANT: Git Configuration

### Step 1: Update Your .gitignore

By default, many `.gitignore` templates exclude `.db` files. **You need to explicitly include the memories database:**

```gitignore
# .gitignore

# Default database exclusions
*.db
*.sqlite
*.sqlite3

# BUT INCLUDE KuzuMemory database!
!.kuzu_memory/memories.db
!.kuzu_memory/*.jsonl.gz
!.kuzu_memory/config.yaml
```

### Step 2: Initial Commit

```bash
# Add the memory database to git
git add .kuzu_memory/memories.db
git add .kuzu_memory/config.yaml
git commit -m "Add KuzuMemory database for shared team knowledge"
```

### Step 3: Verify It's Tracked

```bash
# Ensure the database is being tracked
git ls-files | grep memories.db
# Should output: .kuzu_memory/memories.db
```

## Why Commit the Database?

### ✅ Benefits of Committing memories.db

1. **Team Knowledge Sharing**: All team members share the same context and memories
2. **Persistence**: Memories survive across machines and deployments  
3. **Small File Size**: Typically only 2-5MB even after months of use
4. **Project Context**: Memories are project-specific knowledge that belongs with the code
5. **Zero Configuration**: New team members get memories automatically with `git clone`

### 📊 File Size Expectations

| Usage Duration | Typical Size | Git Impact |
|---------------|--------------|------------|
| 1 week | 100 KB | Negligible |
| 1 month | 500 KB | Negligible |
| 6 months | 2-3 MB | Small |
| 1 year | 3-5 MB | Small |
| 2+ years | 10-20 MB | Moderate (consider Git LFS) |

## Team Collaboration

### For New Team Members

```bash
# Clone project (memories included!)
git clone https://github.com/yourteam/project
cd project

# Memories are ready to use immediately
python your_app.py
# KuzuMemory automatically loads .kuzu_memory/memories.db
```

### Handling Memory Conflicts

If multiple team members add memories simultaneously:

```bash
# The database is binary, so conflicts need special handling
# Option 1: Accept theirs (recommended for minor conflicts)
git checkout --theirs .kuzu_memory/memories.db
git add .kuzu_memory/memories.db
git commit -m "Resolved memory database conflict"

# Option 2: Merge both (for important memories)
kuzu-memory merge --theirs .kuzu_memory/memories.db --mine .kuzu_memory/memories.db.backup
```

### Daily Workflow

```bash
# Pull latest memories from team
git pull

# Work normally - memories are automatically used and created
python your_app.py

# Commit new memories along with code
git add .
git commit -m "Feature X + learned deployment patterns"
git push
```

## Configuration

### .kuzu_memory/config.yaml

```yaml
# This file should ALWAYS be in git
version: 1.0
project:
  name: "Your Project"
  description: "Project description"

storage:
  # Keep database small by limiting memory types
  memory_types:
    - DECISION    # Architectural decisions
    - PATTERN     # Code patterns
    - SOLUTION    # Problem solutions
    - PREFERENCE  # Team preferences
    # - STATUS    # Exclude ephemeral status updates
    # - CONTEXT   # Exclude temporary context

  # Auto-cleanup old memories
  retention:
    STATUS: 7 days
    CONTEXT: 1 day
    default: 365 days

  # Size management
  max_size_mb: 50  # Warn if database exceeds this
  auto_compact: true
```

## Advanced: Large Databases (>10MB)

### Using Git LFS

If your memory database grows beyond 10MB:

```bash
# Install Git LFS
git lfs install

# Track database files with LFS
git lfs track ".kuzu_memory/*.db"
git add .gitattributes
git commit -m "Track memory database with Git LFS"

# Continue using git normally
git add .kuzu_memory/memories.db
git commit -m "Update memories"
```

### Alternative: JSONL Export

For very large databases or if you want readable diffs:

```bash
# Export memories as text (automatically compressed)
kuzu-memory export --format jsonl --compress

# Creates .kuzu_memory/memories.jsonl.gz (much smaller)
# This file shows readable diffs in git!

# Import on fresh clone
kuzu-memory import .kuzu_memory/memories.jsonl.gz
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/memory-backup.yml
name: Backup Memories

on:
  push:
    paths:
      - '.kuzu_memory/memories.db'

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Export memories as JSONL
        run: |
          pip install kuzu-memory
          kuzu-memory export --format jsonl --output .kuzu_memory/backup.jsonl.gz
      
      - name: Upload backup
        uses: actions/upload-artifact@v3
        with:
          name: memory-backup
          path: .kuzu_memory/backup.jsonl.gz
          retention-days: 30
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11

WORKDIR /app

# Copy memories with the application
COPY .kuzu_memory/ .kuzu_memory/
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Memories are available in container!
CMD ["python", "app.py"]
```

## Troubleshooting

### "memories.db not found"

```bash
# Check if it's in git
git ls-files | grep memories.db

# If missing, initialize
kuzu-memory init
git add .kuzu_memory/memories.db
git commit -m "Add memory database"
```

### "Database corrupted"

```bash
# Restore from git history
git checkout HEAD~1 -- .kuzu_memory/memories.db

# Or restore from JSONL backup
kuzu-memory import .kuzu_memory/memories.jsonl.gz
```

### Database Growing Too Large

```bash
# Check size
du -h .kuzu_memory/memories.db

# Compact database
kuzu-memory compact --remove-old --vacuum

# Archive old memories
kuzu-memory archive --older-than 180d --output archive.jsonl.gz
```

## Best Practices

### ✅ DO

- **DO** commit `memories.db` to git (it's small!)
- **DO** include `config.yaml` in version control
- **DO** regularly export to JSONL as backup
- **DO** use Git LFS for databases over 50MB
- **DO** run `kuzu-memory compact` monthly

### ❌ DON'T

- **DON'T** add `*.db` to `.gitignore` without the exception
- **DON'T** commit embeddings if you don't need semantic search
- **DON'T** store sensitive data (passwords, keys) in memories
- **DON'T** worry about size - it grows very slowly

## Support

- **Documentation**: https://kuzu-memory.readthedocs.io
- **Issues**: https://github.com/kuzu-memory/kuzu-memory/issues
- **Discord**: https://discord.gg/kuzu-memory

---

## Quick Checklist

Before deploying, ensure:

- [ ] `.kuzu_memory/memories.db` is tracked in git
- [ ] `.gitignore` has exception for `!.kuzu_memory/memories.db`
- [ ] `config.yaml` is committed
- [ ] Team members know to pull before starting work
- [ ] CI/CD copies `.kuzu_memory/` directory
- [ ] Backups are configured (JSONL export or Git LFS)

---

*Remember: The memories.db file is your team's shared knowledge. Treat it as part of your codebase!*