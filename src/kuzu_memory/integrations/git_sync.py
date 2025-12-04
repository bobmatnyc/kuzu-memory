"""
Git history synchronization for KuzuMemory.

Provides functionality to import git commit history as EPISODIC memories,
with intelligent filtering and incremental updates.
"""

from __future__ import annotations

import fnmatch
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.config import GitSyncConfig
from ..core.models import Memory, MemoryType

logger = logging.getLogger(__name__)


class GitSyncError(Exception):
    """Git synchronization error."""

    pass


class GitSyncManager:
    """
    Manages synchronization of git commit history to memory system.

    Features:
    - Smart filtering of significant commits
    - Incremental updates
    - Branch pattern matching
    - Commit deduplication
    """

    # Type annotations for instance variables
    repo_path: Path
    config: GitSyncConfig
    memory_store: Any
    _repo: Any  # git.Repo if available
    _git_available: bool

    def __init__(
        self,
        repo_path: str | Path,
        config: GitSyncConfig,
        memory_store: Any = None,
    ) -> None:
        """
        Initialize git sync manager.

        Args:
            repo_path: Path to git repository
            config: Git sync configuration
            memory_store: Memory store instance (optional)
        """
        self.repo_path = Path(repo_path).resolve()
        self.config = config
        self.memory_store = memory_store
        self._repo = None
        self._git_available = self._check_git_available()

    def _check_git_available(self) -> bool:
        """Check if git and gitpython are available."""
        try:
            import git

            # Check if path is a git repository
            try:
                self._repo = git.Repo(  # type: ignore[assignment]  # GitPython stubs incomplete for Repo type
                    self.repo_path, search_parent_directories=True
                )
                return True
            except git.InvalidGitRepositoryError:
                logger.warning(f"Not a git repository: {self.repo_path}")
                return False
            except Exception as e:
                logger.warning(f"Git repository error: {e}")
                return False
        except ImportError:
            logger.warning("GitPython not installed. Git sync disabled.")
            return False

    def is_available(self) -> bool:
        """Check if git sync is available."""
        return self._git_available and self.config.enabled

    def _matches_pattern(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any of the glob patterns."""
        for pattern in patterns:
            if fnmatch.fnmatch(text, pattern):
                return True
        return False

    def _filter_branches(self, branches: list[Any]) -> list[Any]:
        """
        Filter branches based on include/exclude patterns.

        Args:
            branches: List of git branch objects

        Returns:
            Filtered list of branches
        """
        filtered = []
        for branch in branches:
            branch_name = str(branch.name) if hasattr(branch, "name") else str(branch)

            # Check exclusion patterns first
            if self._matches_pattern(branch_name, self.config.branch_exclude_patterns):
                logger.debug(f"Excluding branch: {branch_name}")
                continue

            # Check inclusion patterns
            if self._matches_pattern(branch_name, self.config.branch_include_patterns):
                logger.debug(f"Including branch: {branch_name}")
                filtered.append(branch)

        return filtered

    def _is_significant_commit(self, commit: Any) -> bool:
        """
        Check if commit is significant based on message patterns.

        Args:
            commit: Git commit object

        Returns:
            True if commit should be synced
        """
        message = commit.message.strip()

        # Check message length
        if len(message) < self.config.min_message_length:
            logger.debug(f"Skipping short message: {message[:50]}...")
            return False

        # Check skip patterns (WIP, tmp, etc.)
        for skip_pattern in self.config.skip_patterns:
            if skip_pattern.lower() in message.lower():
                logger.debug(f"Skipping pattern '{skip_pattern}': {message[:50]}...")
                return False

        # Check merge commits FIRST (before prefix matching)
        # This ensures merge commits are included even without conventional prefixes
        if self.config.include_merge_commits and len(commit.parents) > 1:
            logger.debug(f"Including merge commit: {message[:50]}...")
            return True

        # Then check significant prefixes
        for prefix in self.config.significant_prefixes:
            if message.lower().startswith(prefix.lower()):
                logger.debug(f"Significant commit '{prefix}': {message[:50]}...")
                return True

        return False

    def _get_changed_files(self, commit: Any) -> list[str]:
        """Get list of changed files in commit."""
        try:
            if not commit.parents:
                # Initial commit
                return [item.path for item in commit.tree.traverse()]
            else:
                # Regular commit - get diff from first parent
                parent = commit.parents[0]
                diffs = parent.diff(commit)
                return [diff.b_path or diff.a_path for diff in diffs]
        except Exception as e:
            logger.warning(f"Failed to get changed files: {e}")
            return []

    def _get_file_stats(self, commit: Any) -> dict[str, dict[str, int]]:
        """
        Get diff statistics for each changed file.

        Args:
            commit: Git commit object

        Returns:
            Dict mapping file paths to {"insertions": int, "deletions": int}
        """
        stats: dict[str, dict[str, int]] = {}
        try:
            if not commit.parents:
                # Initial commit - no diff stats available
                return stats

            parent = commit.parents[0]
            diffs = parent.diff(commit, create_patch=True)

            for diff in diffs:
                file_path = diff.b_path or diff.a_path
                if file_path:
                    # Count insertions and deletions from diff text
                    insertions = 0
                    deletions = 0
                    if hasattr(diff, "diff") and diff.diff:
                        diff_text = diff.diff.decode("utf-8", errors="ignore")
                        for line in diff_text.split("\n"):
                            if line.startswith("+") and not line.startswith("+++"):
                                insertions += 1
                            elif line.startswith("-") and not line.startswith("---"):
                                deletions += 1

                    stats[file_path] = {
                        "insertions": insertions,
                        "deletions": deletions,
                    }
        except Exception as e:
            logger.warning(f"Failed to get file stats: {e}")

        return stats

    def _categorize_files(self, file_paths: list[str]) -> dict[str, list[str]]:
        """
        Categorize files by type.

        Args:
            file_paths: List of file paths

        Returns:
            Dict with categories: source, tests, docs, config, other
        """
        categories: dict[str, list[str]] = {
            "source": [],
            "tests": [],
            "docs": [],
            "config": [],
            "other": [],
        }

        for path in file_paths:
            path_lower = path.lower()

            # Categorization rules
            if any(
                test_pattern in path_lower
                for test_pattern in [
                    "test_",
                    "tests/",
                    "_test.",
                    "spec/",
                    "__tests__/",
                ]
            ):
                categories["tests"].append(path)
            elif any(
                doc_pattern in path_lower
                for doc_pattern in [
                    ".md",
                    "readme",
                    "changelog",
                    "docs/",
                    "documentation/",
                ]
            ):
                categories["docs"].append(path)
            elif any(
                config_pattern in path_lower
                for config_pattern in [
                    ".json",
                    ".yaml",
                    ".yml",
                    ".toml",
                    ".ini",
                    ".cfg",
                    "config",
                    ".env",
                    "dockerfile",
                    "makefile",
                ]
            ):
                categories["config"].append(path)
            elif any(
                path_lower.endswith(ext)
                for ext in [
                    ".py",
                    ".js",
                    ".ts",
                    ".jsx",
                    ".tsx",
                    ".java",
                    ".go",
                    ".rs",
                    ".php",
                    ".rb",
                    ".c",
                    ".cpp",
                    ".h",
                    ".hpp",
                ]
            ):
                categories["source"].append(path)
            else:
                categories["other"].append(path)

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def _commit_to_memory(self, commit: Any) -> Memory:
        """
        Convert git commit to Memory object.

        Args:
            commit: Git commit object

        Returns:
            Memory object
        """
        message = commit.message.strip()
        changed_files = self._get_changed_files(commit)

        # Enhanced content format with searchable file list
        if changed_files:
            files_list = "\n".join(f"- {file}" for file in changed_files[:10])
            if len(changed_files) > 10:
                files_list += f"\n... and {len(changed_files) - 10} more files"
            content = f"{message}\n\nChanged files:\n{files_list}"
        else:
            content = message

        # Get file statistics and categories
        file_stats = self._get_file_stats(commit)
        file_categories = self._categorize_files(changed_files)

        # Get branch name safely
        branch_name = "unknown"
        if self._repo:
            if hasattr(self._repo, "active_branch"):
                try:
                    branch_name = self._repo.active_branch.name
                except Exception:
                    pass

        # Use commit author's email as user_id for namespacing
        # Priority: committer.email > author.email
        # (committer is who actually committed, author is who wrote the code)
        user_id = None
        try:
            # Prefer committer email (who actually committed)
            if hasattr(commit, "committer") and hasattr(commit.committer, "email"):
                user_id = commit.committer.email
            # Fallback to author email (who wrote the code)
            elif hasattr(commit, "author") and hasattr(commit.author, "email"):
                user_id = commit.author.email
        except Exception as e:
            logger.debug(f"Failed to extract user_id from commit: {e}")

        # Create memory with EPISODIC type (30-day retention)
        # Note: valid_to is auto-set by Memory model based on memory_type
        memory = Memory(
            content=content,
            memory_type=MemoryType.EPISODIC,
            source_type="git_sync",
            user_id=user_id,  # Tag with commit author/committer
            metadata={
                "commit_sha": commit.hexsha,
                "commit_author": f"{commit.author.name} <{commit.author.email}>",
                "commit_committer": (
                    f"{commit.committer.name} <{commit.committer.email}>"
                    if hasattr(commit, "committer")
                    else None
                ),
                "commit_timestamp": commit.committed_datetime.isoformat(),
                "branch": branch_name,
                "changed_files": changed_files,
                "parent_count": len(commit.parents),
                "file_stats": file_stats,
                "file_categories": file_categories,
            },
        )

        # Override created_at with commit timestamp
        memory.created_at = commit.committed_datetime.replace(tzinfo=None)

        return memory

    def get_significant_commits(
        self, since: datetime | None = None, branch_name: str | None = None
    ) -> list[Any]:
        """
        Get significant commits from repository.

        Args:
            since: Only get commits after this timestamp
            branch_name: Specific branch to scan (default: all included branches)

        Returns:
            List of significant git commit objects
        """
        if not self.is_available() or not self._repo:
            return []

        try:
            import git

            significant_commits = []

            # Get branches to scan
            if branch_name:
                branches = [b for b in self._repo.branches if str(b.name) == branch_name]
            else:
                branches = self._filter_branches(list(self._repo.branches))

            logger.info(f"Scanning {len(branches)} branches for commits")

            # Collect commits from all branches
            seen_shas = set()

            for branch in branches:
                try:
                    # Get commits from this branch (iter_commits returns newest first)
                    # Reverse to process oldest first for stable chronological ordering
                    commits = list(reversed(list(self._repo.iter_commits(branch))))

                    for commit in commits:
                        # Skip if already processed
                        if commit.hexsha in seen_shas:
                            continue

                        # Check timestamp filter
                        commit_time = commit.committed_datetime.replace(tzinfo=None)
                        if since and commit_time <= since:
                            continue

                        # Check significance
                        if self._is_significant_commit(commit):
                            significant_commits.append(commit)
                            seen_shas.add(commit.hexsha)

                except git.GitCommandError as e:
                    logger.warning(f"Error reading branch {branch.name}: {e}")
                    continue

            # Sort by timestamp (oldest first)
            significant_commits.sort(key=lambda c: c.committed_datetime)

            logger.info(
                f"Found {len(significant_commits)} significant commits "
                f"(out of {len(seen_shas)} total unique commits)"
            )

            return significant_commits

        except Exception as e:
            logger.error(f"Failed to get commits: {e}")
            raise GitSyncError(f"Failed to get commits: {e}")

    def _commit_already_stored(self, commit_sha: str) -> bool:
        """
        Check if commit SHA already exists in memory store.

        Args:
            commit_sha: Git commit SHA to check

        Returns:
            True if commit already stored
        """
        if not self.memory_store:
            return False

        try:
            # Search for memories with this commit SHA by querying recent git_sync memories
            # and checking their metadata
            recent_memories = self.memory_store.get_recent_memories(
                limit=1000,
                source_type="git_sync",  # Check last 1000 git_sync memories
            )

            # Check if any memory has this commit SHA
            for memory in recent_memories:
                if memory.metadata and memory.metadata.get("commit_sha") == commit_sha:
                    logger.debug(f"Commit {commit_sha[:8]} already stored, skipping")
                    return True

            return False
        except Exception as e:
            logger.warning(f"Error checking duplicate commit {commit_sha[:8]}: {e}")
            return False  # Proceed with storage on error to avoid blocking sync

    def store_commit_as_memory(self, commit: Any) -> Memory | None:
        """
        Store a single commit as a memory with deduplication.

        Args:
            commit: Git commit object

        Returns:
            Created Memory object, or None if commit already exists
        """
        # Check if commit already stored (deduplication)
        if self._commit_already_stored(commit.hexsha):
            logger.debug(f"Skipping duplicate commit: {commit.hexsha[:8]}")
            return None

        memory = self._commit_to_memory(commit)

        if self.memory_store:
            try:
                # Store using batch_store_memories API (stores a list of Memory objects)
                stored_ids = self.memory_store.batch_store_memories([memory])
                if stored_ids:
                    logger.debug(f"Stored commit {commit.hexsha[:8]} as memory {stored_ids[0][:8]}")
                    # Memory was stored, return it with the ID
                    memory.id = stored_ids[0]
                    return memory
                else:
                    logger.warning(f"No ID returned when storing commit {commit.hexsha[:8]}")
                    return None
            except Exception as e:
                logger.error(f"Failed to store memory: {e}")
                raise GitSyncError(f"Failed to store memory: {e}")

        return memory

    def sync(self, mode: str = "auto", dry_run: bool = False) -> dict[str, Any]:
        """
        Synchronize git commits to memory.

        Args:
            mode: Sync mode - 'auto', 'initial', or 'incremental'
            dry_run: If True, don't actually store memories

        Returns:
            Sync statistics dictionary
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Git sync not available",
                "commits_synced": 0,
            }

        # Determine sync timestamp
        since = None
        if mode == "incremental" or (mode == "auto" and self.config.last_sync_timestamp):
            if self.config.last_sync_timestamp:
                since = datetime.fromisoformat(self.config.last_sync_timestamp).replace(tzinfo=None)
                logger.info(f"Incremental sync since {since}")
            else:
                logger.info("No previous sync, performing initial sync")
        else:
            logger.info("Performing initial/full sync")

        # Get significant commits
        commits = self.get_significant_commits(since=since)

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "commits_found": len(commits),
                "commits_synced": 0,
                "commits": [
                    {
                        "sha": c.hexsha[:8],
                        "message": c.message.strip()[:80],
                        "timestamp": c.committed_datetime.isoformat(),
                    }
                    for c in commits[:10]  # Preview first 10
                ],
            }

        # Store commits as memories
        synced_count = 0
        skipped_count = 0
        last_commit_sha = None
        last_timestamp = None

        for commit in commits:
            try:
                result = self.store_commit_as_memory(commit)
                if result is not None:
                    synced_count += 1
                else:
                    skipped_count += 1

                # Always track last processed commit, even if duplicate
                # This ensures state updates correctly on subsequent syncs
                last_commit_sha = commit.hexsha
                last_timestamp = commit.committed_datetime

            except Exception as e:
                logger.error(f"Failed to sync commit {commit.hexsha[:8]}: {e}")
                # Continue with other commits

        # Update sync state - always update if we processed commits, even if all were duplicates
        if last_timestamp:
            self.config.last_sync_timestamp = last_timestamp.isoformat()
            if last_commit_sha:  # Only update SHA if we processed commits
                self.config.last_commit_sha = last_commit_sha

        return {
            "success": True,
            "mode": mode,
            "commits_found": len(commits),
            "commits_synced": synced_count,
            "commits_skipped": skipped_count,
            "last_sync_timestamp": self.config.last_sync_timestamp,
            "last_commit_sha": (
                self.config.last_commit_sha[:8] if self.config.last_commit_sha else None
            ),
        }

    def get_sync_status(self) -> dict[str, Any]:
        """
        Get current sync status.

        Returns:
            Status information dictionary
        """
        if not self.is_available():
            return {
                "available": False,
                "enabled": self.config.enabled,
                "reason": "Git not available or not a git repository",
            }

        return {
            "available": True,
            "enabled": self.config.enabled,
            "last_sync_timestamp": self.config.last_sync_timestamp,
            "last_commit_sha": self.config.last_commit_sha,
            "repo_path": str(self.repo_path),
            "branch_include_patterns": self.config.branch_include_patterns,
            "branch_exclude_patterns": self.config.branch_exclude_patterns,
            "auto_sync_on_push": self.config.auto_sync_on_push,
        }
