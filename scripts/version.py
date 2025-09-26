#!/usr/bin/env python3
"""
Version management utility for KuzuMemory.

This script handles semantic versioning operations including:
- Reading the current version from VERSION file
- Bumping version numbers (patch, minor, major)
- Updating CHANGELOG.md with new version entries
- Creating git tags for releases
- Generating build information
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class VersionManager:
    """Handles all version-related operations for the project."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.version_file = self.project_root / "VERSION"
        self.changelog_file = self.project_root / "CHANGELOG.md"
        self.build_info_file = self.project_root / "BUILD_INFO"
        self.pyproject_file = self.project_root / "pyproject.toml"

    def get_current_version(self) -> str:
        """Read current version from VERSION file."""
        if not self.version_file.exists():
            raise FileNotFoundError(f"VERSION file not found at {self.version_file}")

        version = self.version_file.read_text().strip()
        if not self._is_valid_semver(version):
            raise ValueError(f"Invalid semantic version: {version}")

        return version

    def _is_valid_semver(self, version: str) -> bool:
        """Validate semantic version format."""
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
        return bool(re.match(pattern, version))

    def parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse semantic version into major, minor, patch components."""
        parts = version.split("-")[0].split("+")[0]  # Remove pre-release and build metadata
        major, minor, patch = map(int, parts.split("."))
        return major, minor, patch

    def bump_version(self, bump_type: str) -> str:
        """Bump version according to semantic versioning rules."""
        current = self.get_current_version()
        major, minor, patch = self.parse_version(current)

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid bump type: {bump_type}. Use 'major', 'minor', or 'patch'")

        new_version = f"{major}.{minor}.{patch}"
        self.version_file.write_text(new_version + "\n")
        return new_version

    def get_git_info(self) -> Dict[str, str]:
        """Get current git commit and branch information."""
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=self.project_root, text=True
            ).strip()
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.project_root, text=True
            ).strip()
            return {"commit": commit, "branch": branch}
        except subprocess.CalledProcessError:
            return {"commit": "unknown", "branch": "unknown"}

    def generate_build_info(self) -> Dict[str, str]:
        """Generate build information."""
        version = self.get_current_version()
        git_info = self.get_git_info()

        build_info = {
            "version": version,
            "build_date": datetime.now().isoformat(),
            "git_commit": git_info["commit"],
            "git_branch": git_info["branch"],
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
        }

        # Write to BUILD_INFO file
        self.build_info_file.write_text(json.dumps(build_info, indent=2) + "\n")
        return build_info

    def update_changelog(self, version: str, changes: Optional[List[str]] = None) -> None:
        """Update CHANGELOG.md with new version entry."""
        if not self.changelog_file.exists():
            print(f"Warning: CHANGELOG.md not found at {self.changelog_file}")
            return

        content = self.changelog_file.read_text()
        today = datetime.now().strftime("%Y-%m-%d")

        # Find the [Unreleased] section
        unreleased_pattern = r"## \[Unreleased\]"
        unreleased_match = re.search(unreleased_pattern, content)

        if not unreleased_match:
            print("Warning: [Unreleased] section not found in CHANGELOG.md")
            return

        # Create new version entry
        new_entry = f"\n## [{version}] - {today}\n"
        if changes:
            new_entry += "\n### Changed\n"
            for change in changes:
                new_entry += f"- {change}\n"
        else:
            new_entry += "\n### Changed\n- Version bump\n"

        # Insert new entry after [Unreleased] section
        # Find the end of the unreleased section (next ## or end of file)
        unreleased_end = unreleased_match.end()
        rest_content = content[unreleased_end:]
        next_version_match = re.search(r"\n## \[", rest_content)

        if next_version_match:
            insert_pos = unreleased_end + next_version_match.start()
            new_content = content[:insert_pos] + new_entry + content[insert_pos:]
        else:
            # No other versions, append at end
            new_content = content + new_entry

        # Update version links at the bottom
        new_content = self._update_changelog_links(new_content, version)

        self.changelog_file.write_text(new_content)

    def _update_changelog_links(self, content: str, version: str) -> str:
        """Update the version comparison links at the bottom of CHANGELOG.md."""
        # Find the links section
        links_pattern = r"\[Unreleased\]: (.+?)/compare/v(.+?)\.\.\.HEAD"
        links_match = re.search(links_pattern, content)

        if links_match:
            repo_url = links_match.group(1)
            current_version = links_match.group(2)

            # Update Unreleased link
            new_unreleased_link = f"[Unreleased]: {repo_url}/compare/v{version}...HEAD"
            content = re.sub(
                r"\[Unreleased\]: .+",
                new_unreleased_link,
                content
            )

            # Add new version link
            new_version_link = f"[{version}]: {repo_url}/compare/v{current_version}...v{version}"

            # Insert after the Unreleased link
            unreleased_line_end = content.find(new_unreleased_link) + len(new_unreleased_link)
            content = content[:unreleased_line_end] + f"\n{new_version_link}" + content[unreleased_line_end:]

        return content

    def create_git_tag(self, version: str) -> None:
        """Create a git tag for the version."""
        tag_name = f"v{version}"
        try:
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", f"Release {version}"],
                cwd=self.project_root,
                check=True
            )
            print(f"✅ Created git tag: {tag_name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create git tag: {e}")
            sys.exit(1)

    def validate_clean_working_tree(self) -> None:
        """Ensure git working tree is clean before version operations."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip():
                print("❌ Working tree is not clean. Please commit or stash changes first.")
                print("Modified files:")
                print(result.stdout)
                sys.exit(1)
        except subprocess.CalledProcessError:
            print("Warning: Could not check git status")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="KuzuMemory version management")
    parser.add_argument("action", choices=["current", "bump", "build-info", "tag"],
                       help="Action to perform")
    parser.add_argument("--type", choices=["major", "minor", "patch"],
                       help="Version bump type (for bump action)")
    parser.add_argument("--no-tag", action="store_true",
                       help="Don't create git tag after version bump")
    parser.add_argument("--force", action="store_true",
                       help="Force operation even with dirty working tree")
    parser.add_argument("--changelog", nargs="*",
                       help="Custom changelog entries")

    args = parser.parse_args()

    vm = VersionManager()

    if args.action == "current":
        print(vm.get_current_version())

    elif args.action == "bump":
        if not args.type:
            print("❌ --type is required for bump action")
            sys.exit(1)

        if not args.force:
            vm.validate_clean_working_tree()

        current = vm.get_current_version()
        new_version = vm.bump_version(args.type)
        print(f"🚀 Bumped version: {current} → {new_version}")

        # Update changelog
        vm.update_changelog(new_version, args.changelog)
        print(f"📝 Updated CHANGELOG.md")

        # Create git tag
        if not args.no_tag:
            vm.create_git_tag(new_version)

    elif args.action == "build-info":
        build_info = vm.generate_build_info()
        print(f"🔨 Generated BUILD_INFO:")
        print(json.dumps(build_info, indent=2))

    elif args.action == "tag":
        version = vm.get_current_version()
        vm.create_git_tag(version)


if __name__ == "__main__":
    main()