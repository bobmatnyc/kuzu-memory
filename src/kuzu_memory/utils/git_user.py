"""
Git user identification for memory namespacing.

Provides automatic detection of git user identity for tagging memories
with author information, enabling multi-user memory separation.
"""

import getpass
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GitUserInfo:
    """Git user information."""

    user_id: str  # Primary identifier (email, name, or system username)
    email: str | None = None
    name: str | None = None
    source: str = "unknown"  # "git_email", "git_name", "system_user"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metadata storage."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "source": self.source,
        }


class GitUserProvider:
    """
    Provides git user identification for memory namespacing.

    Detection priority:
    1. git config user.email (most reliable, globally unique)
    2. git config user.name (fallback)
    3. system username (last resort)

    All results are cached for performance.
    """

    _cache: dict[str, GitUserInfo] = {}

    @staticmethod
    def _run_git_command(args: list[str], cwd: Path | None = None) -> str | None:
        """
        Run git command and return output.

        Args:
            args: Git command arguments
            cwd: Working directory for command

        Returns:
            Command output or None if failed
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    logger.debug(f"Git command {' '.join(args)} returned: {output}")
                    return output

            # Log non-zero exit codes for debugging
            if result.returncode != 0:
                logger.debug(
                    f"Git command {' '.join(args)} failed with code {result.returncode}: {result.stderr.strip()}"
                )

            return None

        except subprocess.TimeoutExpired:
            logger.warning(f"Git command {' '.join(args)} timed out")
            return None
        except FileNotFoundError:
            logger.debug("Git command not found")
            return None
        except Exception as e:
            logger.debug(f"Git command {' '.join(args)} failed: {e}")
            return None

    @staticmethod
    def _get_system_username() -> str:
        """
        Get system username as last resort.

        Returns:
            System username
        """
        try:
            username = getpass.getuser()
            logger.debug(f"Using system username: {username}")
            return username
        except Exception as e:
            logger.warning(f"Failed to get system username: {e}")
            return "unknown_user"

    @classmethod
    def get_git_user_info(cls, project_root: Path | None = None) -> GitUserInfo:
        """
        Get complete git user information.

        Args:
            project_root: Optional project root for git config lookup

        Returns:
            GitUserInfo with user_id, email, name, and source
        """
        # Check cache
        cache_key = str(project_root) if project_root else "_default"
        if cache_key in cls._cache:
            logger.debug("Using cached git user info")
            return cls._cache[cache_key]

        # Try to get git email (priority 1)
        git_email = cls._run_git_command(["config", "user.email"], cwd=project_root)

        # Try to get git name (priority 2)
        git_name = cls._run_git_command(["config", "user.name"], cwd=project_root)

        # Determine user_id and source
        if git_email:
            user_id = git_email
            source = "git_email"
            logger.info(f"Using git email as user_id: {user_id}")
        elif git_name:
            user_id = git_name
            source = "git_name"
            logger.info(f"Using git name as user_id: {user_id}")
        else:
            user_id = cls._get_system_username()
            source = "system_user"
            logger.info(f"Using system username as user_id: {user_id}")

        # Create GitUserInfo object
        user_info = GitUserInfo(
            user_id=user_id,
            email=git_email,
            name=git_name,
            source=source,
        )

        # Cache result
        cls._cache[cache_key] = user_info

        return user_info

    @classmethod
    def get_git_user_id(cls, project_root: Path | None = None) -> str:
        """
        Get git user identifier for namespacing memories.

        This is the primary method to use for tagging memories.

        Args:
            project_root: Optional project root for git config lookup

        Returns:
            User identifier string (email, name, or username)
        """
        return cls.get_git_user_info(project_root).user_id

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached user information (for testing)."""
        cls._cache.clear()
        logger.debug("Cleared git user cache")

    @classmethod
    def is_git_available(cls, project_root: Path | None = None) -> bool:
        """
        Check if git is available and configured.

        Args:
            project_root: Optional project root for git config lookup

        Returns:
            True if git user email or name is configured
        """
        git_email = cls._run_git_command(["config", "user.email"], cwd=project_root)
        git_name = cls._run_git_command(["config", "user.name"], cwd=project_root)
        return bool(git_email or git_name)
