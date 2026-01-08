#!/usr/bin/env python3
"""Automated publish script for kuzu-memory.

Usage:
    python scripts/publish.py [--bump patch|minor|major] [--dry-run] [--skip-tests] [--skip-github]
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


class Publisher:
    """Handles the complete publish workflow."""

    def __init__(self, project_root: Path, dry_run: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.version_file = project_root / "VERSION"
        self.pyproject_file = project_root / "pyproject.toml"
        self.version_py = project_root / "src" / "kuzu_memory" / "__version__.py"

    def get_current_version(self) -> str:
        """Read current version from VERSION file."""
        if not self.version_file.exists():
            raise FileNotFoundError(f"VERSION file not found: {self.version_file}")
        return self.version_file.read_text().strip()

    def bump_version(self, bump_type: str) -> str:
        """Bump version and return new version string."""
        current = self.get_current_version()

        # Validate current version format
        if not re.match(r'^\d+\.\d+\.\d+$', current):
            raise ValueError(f"Invalid version format: {current}")

        major, minor, patch = map(int, current.split("."))

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        new_version = f"{major}.{minor}.{patch}"

        if not self.dry_run:
            # Update VERSION file
            self.version_file.write_text(new_version + "\n")

            # Update pyproject.toml
            if self.pyproject_file.exists():
                content = self.pyproject_file.read_text()
                content = re.sub(
                    r'version\s*=\s*"[^"]*"',
                    f'version = "{new_version}"',
                    content,
                    count=1
                )
                self.pyproject_file.write_text(content)

            # Update __version__.py
            if self.version_py.exists():
                content = self.version_py.read_text()
                content = re.sub(
                    r'__version__\s*=\s*"[^"]*"',
                    f'__version__ = "{new_version}"',
                    content
                )
                self.version_py.write_text(content)

        return new_version

    def get_pypi_token(self) -> str:
        """Get PyPI token from env or .env.local file."""
        # Check environment variable first (both UV_PUBLISH_TOKEN and PYPI_API_KEY)
        token = os.environ.get("UV_PUBLISH_TOKEN") or os.environ.get("PYPI_API_KEY")
        if token:
            return token

        # Fall back to .env.local
        env_file = self.project_root / ".env.local"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("PYPI_API_KEY=") or line.startswith("UV_PUBLISH_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

        raise ValueError(
            "No PyPI token found. Set UV_PUBLISH_TOKEN or PYPI_API_KEY env var, "
            "or add to .env.local file"
        )

    def run(
        self, cmd: list[str], check: bool = True, capture: bool = False
    ) -> subprocess.CompletedProcess:
        """Run a command."""
        print(f"  $ {' '.join(cmd)}")

        # Always execute read-only commands
        read_only_commands = {"git", "cat", "grep", "ls", "find"}
        if self.dry_run and cmd[0] not in read_only_commands:
            print("    [DRY RUN - skipped]")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        return subprocess.run(
            cmd, cwd=self.project_root, check=check, capture_output=capture, text=True
        )

    def run_quality_checks(self) -> bool:
        """Run linting and tests."""
        print("\n📋 Running quality checks...")

        checks = [
            (["uv", "run", "ruff", "check", "src/"], "Ruff linting"),
            (
                ["uv", "run", "mypy", "src/kuzu_memory", "--ignore-missing-imports"],
                "Type checking",
            ),
            (["uv", "run", "pytest", "tests/", "-x", "-q"], "Tests"),
        ]

        for cmd, name in checks:
            print(f"\n  {name}...")
            result = self.run(cmd, check=False)
            if result.returncode != 0:
                print(f"  ❌ {name} failed!")
                return False
            print(f"  ✅ {name} passed")

        return True

    def build(self) -> bool:
        """Build distribution files."""
        print("\n📦 Building distribution...")

        # Clean old builds
        dist_dir = self.project_root / "dist"
        if dist_dir.exists() and not self.dry_run:
            print("  Cleaning old builds...")
            for f in dist_dir.glob("*"):
                f.unlink()

        result = self.run(["uv", "build"], check=False)
        if result.returncode != 0:
            return False

        # Verify build artifacts exist
        if not self.dry_run:
            whl_files = list(dist_dir.glob("*.whl"))
            tar_files = list(dist_dir.glob("*.tar.gz"))
            if not whl_files or not tar_files:
                print("  ❌ Build artifacts not found!")
                return False
            print(f"  Built: {whl_files[0].name}")
            print(f"  Built: {tar_files[0].name}")

        return True

    def publish_pypi(self) -> bool:
        """Publish to PyPI."""
        print("\n🚀 Publishing to PyPI...")

        try:
            token = self.get_pypi_token()
        except ValueError as e:
            print(f"  ❌ {e}")
            return False

        if self.dry_run:
            print("  [DRY RUN - would publish to PyPI]")
            return True

        # Use uv publish with token
        result = self.run(["uv", "publish", "--token", token], check=False)
        return result.returncode == 0

    def git_commit_and_tag(self, version: str) -> bool:
        """Commit version bump and create tag."""
        print(f"\n🏷️  Git commit and tag v{version}...")

        if self.dry_run:
            print("  [DRY RUN - would commit and tag]")
            return True

        # Check for uncommitted changes (excluding version files)
        status = self.run(["git", "status", "--porcelain"], capture=True)
        if status.stdout:
            # Filter out version files
            other_changes = [
                line for line in status.stdout.splitlines()
                if not any(f in line for f in ["VERSION", "pyproject.toml", "__version__.py"])
            ]
            if other_changes:
                print("  ⚠️  Warning: Uncommitted changes detected:")
                for line in other_changes[:5]:  # Show first 5
                    print(f"    {line}")

        # Stage version files
        files_to_add = ["VERSION", "pyproject.toml", "src/kuzu_memory/__version__.py"]
        self.run(["git", "add"] + files_to_add)

        # Commit
        commit_result = self.run(
            ["git", "commit", "-m", f"chore: bump version to {version}", "--no-verify"],
            check=False,
        )
        if commit_result.returncode != 0:
            print("  ⚠️  Commit failed (files may already be committed)")

        # Tag
        tag_result = self.run(["git", "tag", f"v{version}"], check=False)
        if tag_result.returncode != 0:
            print(f"  ⚠️  Tag v{version} may already exist")

        # Push commit and tag
        self.run(["git", "push", "origin", "main"], check=False)
        self.run(["git", "push", "origin", f"v{version}"], check=False)

        return True

    def create_github_release(self, version: str) -> bool:
        """Create GitHub release."""
        print(f"\n📣 Creating GitHub release v{version}...")

        if self.dry_run:
            print("  [DRY RUN - would create GitHub release]")
            return True

        # Check if gh CLI is available
        gh_check = subprocess.run(
            ["which", "gh"], capture_output=True, text=True
        )
        if gh_check.returncode != 0:
            print("  ⚠️  gh CLI not found. Skipping GitHub release.")
            print("     Install: https://cli.github.com/")
            return False

        result = self.run(
            ["gh", "release", "create", f"v{version}", "--generate-notes"], check=False
        )

        return result.returncode == 0

    def publish(
        self, bump_type: str = "patch", skip_tests: bool = False, skip_github: bool = False
    ) -> bool:
        """Run the complete publish workflow."""
        print(f"🚀 Publishing kuzu-memory ({bump_type} release)")
        if self.dry_run:
            print("   [DRY RUN MODE]")

        # 1. Quality checks
        if not skip_tests:
            if not self.run_quality_checks():
                print("\n❌ Quality checks failed. Aborting.")
                return False
        else:
            print("\n⚠️  Skipping quality checks")

        # 2. Bump version
        current = self.get_current_version()
        new_version = self.bump_version(bump_type)
        print(f"\n📝 Version: {current} → {new_version}")

        # 3. Build
        if not self.build():
            print("\n❌ Build failed. Aborting.")
            return False
        print("  ✅ Build successful")

        # 4. Git commit and tag
        if not self.git_commit_and_tag(new_version):
            print("\n⚠️  Git operations had issues (continuing...)")

        # 5. Publish to PyPI
        if not self.publish_pypi():
            print("\n❌ PyPI publish failed.")
            return False
        print("  ✅ Published to PyPI")

        # 6. GitHub release
        if not skip_github:
            if not self.create_github_release(new_version):
                print("\n⚠️  GitHub release creation had issues")
            else:
                print("  ✅ GitHub release created")
        else:
            print("\n⚠️  Skipping GitHub release")

        print(f"\n✅ Successfully published kuzu-memory v{new_version}!")
        print(f"   PyPI: https://pypi.org/project/kuzu-memory/{new_version}/")
        if not skip_github:
            print(
                f"   GitHub: https://github.com/bobmatnyc/kuzu-memory/releases/tag/v{new_version}"
            )

        return True


def main():
    parser = argparse.ArgumentParser(description="Publish kuzu-memory to PyPI")
    parser.add_argument(
        "--bump",
        "-b",
        choices=["patch", "minor", "major"],
        default="patch",
        help="Version bump type (default: patch)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without doing it",
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip quality checks"
    )
    parser.add_argument(
        "--skip-github", action="store_true", help="Skip GitHub release creation"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    publisher = Publisher(project_root, dry_run=args.dry_run)

    try:
        success = publisher.publish(
            bump_type=args.bump, skip_tests=args.skip_tests, skip_github=args.skip_github
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
