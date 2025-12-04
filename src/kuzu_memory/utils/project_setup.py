"""
Project setup utilities for KuzuMemory.

Handles creation of project-specific memory directories and git integration.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def find_project_root(start_path: Path | None = None, _home_dir: Path | None = None) -> Path | None:
    """
    Find the project root by looking for common project indicators.

    Args:
        start_path: Starting directory (default: current directory)
        _home_dir: Home directory override (for testing only)

    Returns:
        Path to project root or None if not found

    Logic:
        1. Check if current directory has project indicators - if yes, use it
        2. Only walk up if current directory has no indicators
        3. Never use home directory as project root (safety check)
        4. Stop walking at home directory boundary
        5. Fall back to current directory if no valid project root found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = Path(start_path).resolve()

    # Get home directory (allow override for testing)
    if _home_dir is None:
        home_dir = Path.home().resolve()
    else:
        home_dir = Path(_home_dir).resolve()

    # Look for common project root indicators
    project_indicators = [
        ".git",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "composer.json",
        "Gemfile",
        "requirements.txt",
        "setup.py",
        "CMakeLists.txt",
        "Makefile",
    ]

    def has_project_indicator(path: Path) -> str | None:
        """Check if path has any project indicator. Returns indicator name if found."""
        for indicator in project_indicators:
            if (path / indicator).exists():
                return indicator
        return None

    # STEP 1: Check current directory first
    current_indicator = has_project_indicator(current)
    if current_indicator:
        logger.debug(
            f"Found project root at current directory {current} (indicator: {current_indicator})"
        )
        return current

    # STEP 2: Walk up the directory tree, but with safety checks
    for parent in current.parents:
        # Safety check: NEVER use home directory as project root
        if parent == home_dir:
            logger.debug(
                f"Reached home directory {home_dir}, stopping search. Using current directory {current}"
            )
            return current

        # Safety check: Stop if we've gone above home directory
        if home_dir in parent.parents:
            logger.debug(
                f"Passed home directory boundary at {parent}, stopping search. Using current directory {current}"
            )
            return current

        # Check if this parent has project indicators
        parent_indicator = has_project_indicator(parent)
        if parent_indicator:
            logger.debug(f"Found project root at {parent} (indicator: {parent_indicator})")
            return parent

    # STEP 3: No project root found, use current directory
    logger.debug("No project root found, using current directory")
    return current


def get_project_memories_dir(project_root: Path | None = None) -> Path:
    """
    Get the project memories directory path.

    Args:
        project_root: Project root directory (auto-detected if None)

    Returns:
        Path to kuzu-memories directory
    """
    root = project_root if project_root is not None else find_project_root()
    if root is None:
        raise ValueError("Could not determine project root directory")
    return root / "kuzu-memories"


def get_project_db_path(project_root: Path | None = None) -> Path:
    """
    Get the project memory database path.

    Args:
        project_root: Project root directory (auto-detected if None)

    Returns:
        Path to memories.db file
    """
    memories_dir = get_project_memories_dir(project_root)
    return memories_dir / "memories.db"


def create_project_memories_structure(
    project_root: Path | None = None, force: bool = False
) -> dict[str, Any]:
    """
    Create the kuzu-memories directory structure for a project.

    Args:
        project_root: Project root directory (auto-detected if None)
        force: Overwrite existing structure

    Returns:
        Dictionary with creation results
    """
    root = project_root if project_root is not None else find_project_root()
    if root is None:
        raise ValueError("Could not determine project root directory")

    memories_dir = get_project_memories_dir(root)
    db_path = get_project_db_path(root)

    result: dict[str, Any] = {
        "project_root": str(root),
        "memories_dir": str(memories_dir),
        "db_path": str(db_path),
        "created": False,
        "existed": False,
        "files_created": [],
    }

    # Check if directory already exists
    if memories_dir.exists():
        if not force:
            result["existed"] = True
            return result
        else:
            # Remove existing directory
            shutil.rmtree(memories_dir)

    try:
        # Create memories directory
        memories_dir.mkdir(parents=True, exist_ok=True)
        files_created = result["files_created"]
        assert isinstance(files_created, list)
        files_created.append(str(memories_dir))

        # Create README.md
        readme_content = create_memories_readme(root)
        readme_path = memories_dir / "README.md"
        readme_path.write_text(readme_content)
        files_created.append(str(readme_path))

        # Create .gitignore (initially empty - we want to commit the DB)
        gitignore_path = memories_dir / ".gitignore"
        gitignore_content = """# KuzuMemory temporary files
*.tmp
*.log
.DS_Store
"""
        gitignore_path.write_text(gitignore_content)
        files_created.append(str(gitignore_path))

        # Create project_info.md template
        project_info_path = memories_dir / "project_info.md"
        project_info_content = create_project_info_template(root)
        project_info_path.write_text(project_info_content)
        files_created.append(str(project_info_path))

        result["created"] = True
        logger.info(f"Created project memories structure at {memories_dir}")

    except Exception as e:
        logger.error(f"Failed to create project memories structure: {e}")
        result["error"] = str(e)

    return result


def create_memories_readme(project_root: Path) -> str:
    """Create README content for the kuzu-memories directory."""
    project_name = project_root.name

    return f"""# 🧠 Project Memories - {project_name}

This directory contains the KuzuMemory database for the **{project_name}** project.

## 📁 What's Here

- **`memories.db`** - Kuzu graph database containing project memories
- **`project_info.md`** - Project context and documentation
- **`.gitignore`** - Git ignore rules for temporary files

## 🎯 Purpose

This memory database stores:
- **Project context** - Architecture, decisions, patterns
- **Team knowledge** - Preferences, conventions, best practices
- **Development history** - Solutions, learnings, gotchas
- **AI context** - Information for enhanced AI assistance

## 🔄 Git Integration

**✅ COMMIT THIS DIRECTORY TO GIT**

The memories database should be committed to your repository so that:
- All team members share the same project context
- AI assistants have consistent project knowledge
- Project memory persists across environments
- New team members get instant project context

## 🚀 Usage

### Store Project Memories
```bash
# Store project information
kuzu-memory remember "We use FastAPI with PostgreSQL for this microservice"

# Store architectural decisions
kuzu-memory remember "We decided to use Redis for caching to improve API response times"

# Store team conventions
kuzu-memory remember "All API endpoints should include request/response examples in docstrings"
```

### Recall Project Context
```bash
# Get relevant project context
kuzu-memory recall "How is the database configured?"

# Find architectural decisions
kuzu-memory recall "What caching strategy do we use?"

# Get AI-enhanced responses
kuzu-memory auggie enhance "How should I structure this API endpoint?"
```

### Project Statistics
```bash
# View memory statistics
kuzu-memory stats

# See project memory summary
kuzu-memory project-info
```

## 🤖 AI Integration

When using AI assistants (like Auggie), the memories in this database automatically enhance prompts with relevant project context, making AI responses more accurate and project-specific.

## 📊 Database Info

- **Type**: Kuzu Graph Database
- **Schema**: Optimized for memory relationships and fast retrieval
- **Performance**: Sub-10ms memory recall for real-time AI integration
- **Size**: Typically 1-10MB for most projects

## 🆘 Troubleshooting

### Database Issues
```bash
# Check database health
kuzu-memory stats

# Reinitialize if corrupted
kuzu-memory init --force
```

### Performance Issues
```bash
# Optimize database
kuzu-memory optimize

# Clean up old memories
kuzu-memory cleanup
```

---

**This directory is managed by KuzuMemory v1.0.0**
Generated on: {project_root.stat().st_mtime}
"""


def create_project_info_template(project_root: Path) -> str:
    """Create project info template."""
    project_name = project_root.name

    return f"""# 📋 Project Information - {project_name}

This file contains structured information about the project that helps KuzuMemory provide better context.

## 🏗️ Project Overview

**Project Name**: {project_name}
**Type**: [Web App / API / Library / CLI Tool / etc.]
**Language**: [Python / JavaScript / Rust / etc.]
**Framework**: [FastAPI / React / Django / etc.]

## 🎯 Project Purpose

[Describe what this project does and why it exists]

## 🏛️ Architecture

### Tech Stack
- **Backend**: [Framework/Language]
- **Database**: [PostgreSQL / MongoDB / etc.]
- **Cache**: [Redis / Memcached / etc.]
- **Frontend**: [React / Vue / etc.]
- **Deployment**: [Docker / Kubernetes / etc.]

### Key Components
- **[Component 1]**: [Description]
- **[Component 2]**: [Description]
- **[Component 3]**: [Description]

## 📏 Conventions & Standards

### Code Style
- [Formatting rules, linting, etc.]

### API Design
- [REST conventions, response formats, etc.]

### Database
- [Naming conventions, migration patterns, etc.]

### Testing
- [Testing framework, coverage requirements, etc.]

## 🚀 Development Workflow

### Getting Started
1. [Setup steps]
2. [Installation commands]
3. [First run instructions]

### Common Tasks
- **Run tests**: `[command]`
- **Start dev server**: `[command]`
- **Build for production**: `[command]`
- **Deploy**: `[command]`

## 🤝 Team Preferences

### Development
- [Preferred tools, IDEs, extensions]

### Communication
- [How decisions are made, documentation standards]

### Code Review
- [Review process, requirements, standards]

## 📚 Important Resources

- **Documentation**: [Link or location]
- **API Docs**: [Link or location]
- **Design System**: [Link or location]
- **Deployment Guide**: [Link or location]

---

**💡 Tip**: Update this file as the project evolves. KuzuMemory will use this information to provide better context for AI assistance.

**🤖 AI Integration**: This information is automatically included in AI prompts to provide project-specific context.
"""


def is_git_repository(path: Path) -> bool:
    """Check if a directory is a git repository."""
    return (path / ".git").exists()


def should_commit_memories(project_root: Path) -> bool:
    """Determine if memories should be committed to git."""
    # Always commit if it's a git repository
    return is_git_repository(project_root)


def get_project_context_summary(project_root: Path | None = None) -> dict[str, Any]:
    """Get a summary of the project context."""
    root = project_root if project_root is not None else find_project_root()
    if root is None:
        raise ValueError("Could not determine project root directory")

    memories_dir = get_project_memories_dir(root)
    db_path = get_project_db_path(root)

    return {
        "project_name": root.name,
        "project_root": str(root),
        "memories_dir": str(memories_dir),
        "db_path": str(db_path),
        "memories_exist": memories_dir.exists(),
        "db_exists": db_path.exists(),
        "is_git_repo": is_git_repository(root),
        "should_commit": should_commit_memories(root),
        "db_size_mb": db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0,
    }
