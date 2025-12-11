"""
Update checker and upgrade commands for KuzuMemory CLI.

Provides functionality to check for and install updates from PyPI.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import click

from ..__version__ import __version__
from .cli_utils import rich_confirm, rich_panel, rich_print

logger = logging.getLogger(__name__)


class VersionChecker:
    """Handles version checking against PyPI."""

    PYPI_API_URL = "https://pypi.org/pypi/kuzu-memory/json"
    TIMEOUT = 10  # seconds

    def __init__(self) -> None:
        self.current_version = __version__

    def get_latest_version(self, include_pre: bool = False) -> dict[str, Any]:
        """
        Fetch latest version from PyPI.

        Args:
            include_pre: If True, include pre-release versions

        Returns:
            dict with keys:
                - version: str (e.g., "1.4.50")
                - release_date: str
                - release_url: str
                - error: str (if failed)
        """
        try:
            # Create request with timeout
            request = Request(self.PYPI_API_URL)
            request.add_header("User-Agent", f"kuzu-memory/{self.current_version}")

            # Fetch PyPI JSON
            with urlopen(request, timeout=self.TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Extract version information
            info = data.get("info", {})
            releases = data.get("releases", {})

            # Get latest version
            if include_pre:
                latest = info.get("version", "0.0.0")
            else:
                # Filter out pre-release versions
                stable_versions = [
                    v
                    for v in releases.keys()
                    if not any(pre in v for pre in ["a", "b", "rc", "dev", "alpha", "beta"])
                ]
                if stable_versions:
                    # Sort versions properly using packaging if available
                    try:
                        from packaging.version import Version

                        latest = str(max(stable_versions, key=Version))
                    except ImportError:
                        # Fallback to simple string sorting
                        latest = max(stable_versions)
                else:
                    latest = info.get("version", "0.0.0")

            # Get release info
            release_info = releases.get(latest, [{}])[0]
            release_date = release_info.get("upload_time", "unknown")

            return {
                "version": latest,
                "release_date": (
                    release_date.split("T")[0] if "T" in release_date else release_date
                ),
                "release_url": f"https://pypi.org/project/kuzu-memory/{latest}/",
                "error": None,
            }

        except HTTPError as e:
            if e.code == 404:
                return {"error": "Package not found on PyPI"}
            return {"error": f"HTTP error {e.code}: {e.reason}"}
        except URLError as e:
            return {"error": f"Network error: {e.reason}"}
        except json.JSONDecodeError:
            return {"error": "Failed to parse PyPI response"}
        except Exception as e:
            return {"error": f"Unexpected error: {e!s}"}

    def compare_versions(self, latest: str) -> dict[str, Any]:
        """
        Compare current vs latest version.

        Args:
            latest: Latest version string from PyPI

        Returns:
            dict with keys:
                - current: str
                - latest: str
                - update_available: bool
                - version_type: str ("major"|"minor"|"patch"|"none")
        """
        try:
            # Try using packaging library for proper version comparison
            from packaging.version import Version

            current_ver = Version(self.current_version)
            latest_ver = Version(latest)

            update_available = latest_ver > current_ver

            # Determine update type
            if not update_available:
                version_type = "none"
            else:
                # Parse version parts
                current_parts = current_ver.base_version.split(".")
                latest_parts = latest_ver.base_version.split(".")

                if len(current_parts) >= 3 and len(latest_parts) >= 3:
                    if current_parts[0] != latest_parts[0]:
                        version_type = "major"
                    elif current_parts[1] != latest_parts[1]:
                        version_type = "minor"
                    else:
                        version_type = "patch"
                else:
                    version_type = "unknown"

        except ImportError:
            # Fallback to simple string comparison
            update_available = latest != self.current_version
            version_type = "unknown" if update_available else "none"

        return {
            "current": self.current_version,
            "latest": latest,
            "update_available": update_available,
            "version_type": version_type,
        }

    def get_upgrade_command(self) -> str:
        """Return pip command to upgrade."""
        return "pip install --upgrade kuzu-memory"


def _run_upgrade() -> dict[str, Any]:
    """
    Execute pip upgrade command.

    Returns:
        dict with keys:
            - success: bool
            - output: str
            - error: str (if failed)
    """
    try:
        # Run pip upgrade
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "kuzu-memory"],
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute timeout
        )

        if result.returncode == 0:
            return {
                "success": True,
                "output": result.stdout,
                "error": None,
            }
        else:
            return {
                "success": False,
                "output": result.stdout,
                "error": result.stderr,
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Upgrade timed out after 60 seconds",
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
        }


def _format_text_output(
    check_result: dict[str, Any],
    comparison: dict[str, Any],
    upgrade_result: dict[str, Any] | None = None,
) -> None:
    """Format and print text output using rich."""
    # Handle errors
    if check_result.get("error"):
        rich_panel(
            f"Failed to check for updates:\n{check_result['error']}\n\n"
            "Please check your internet connection and try again.",
            title="⚠️  Update Check Failed",
            style="yellow",
        )
        return

    # Version comparison
    current = comparison["current"]
    latest = comparison["latest"]
    update_available = comparison["update_available"]
    version_type = comparison["version_type"]

    if not update_available:
        # Already on latest
        rich_panel(
            f"Current version: {current}\n"
            f"Latest version:  {latest}\n\n"
            "✅ You are running the latest version!",
            title="📦 Version Check",
            style="green",
        )
        return

    # Update available
    version_type_emoji = {
        "major": "🚀",
        "minor": "✨",
        "patch": "🔧",
        "unknown": "📦",
    }
    emoji = version_type_emoji.get(version_type, "📦")

    release_date = check_result.get("release_date", "unknown")
    release_url = check_result.get("release_url", "")

    message = (
        f"Current version: {current}\n"
        f"Latest version:  {latest}\n"
        f"Update type:     {emoji} {version_type.title()}\n"
        f"Released:        {release_date}"
    )

    if release_url:
        message += f"\n\nRelease notes:   {release_url}"

    # Show upgrade result if available
    if upgrade_result:
        if upgrade_result["success"]:
            rich_panel(
                f"{message}\n\n"
                "✅ Successfully upgraded to the latest version!\n"
                "Please restart kuzu-memory to use the new version.",
                title="🎉 Upgrade Complete",
                style="green",
            )
        else:
            error_msg = upgrade_result.get("error", "Unknown error")
            rich_panel(
                f"{message}\n\n"
                f"❌ Upgrade failed:\n{error_msg}\n\n"
                "Try running manually:\n"
                f"  {VersionChecker().get_upgrade_command()}",
                title="⚠️  Upgrade Failed",
                style="red",
            )
    else:
        # Just showing update availability
        upgrade_cmd = VersionChecker().get_upgrade_command()
        rich_panel(
            f"{message}\n\n"
            f"To upgrade, run:\n"
            f"  {upgrade_cmd}\n\n"
            "Or use: kuzu-memory update (without --check-only)",
            title="📦 Update Available",
            style="blue",
        )


def _format_json_output(
    check_result: dict[str, Any],
    comparison: dict[str, Any],
    upgrade_result: dict[str, Any] | None = None,
) -> None:
    """Format and print JSON output."""
    output = {
        "current_version": comparison["current"],
        "latest_version": comparison.get("latest"),
        "update_available": comparison.get("update_available", False),
        "version_type": comparison.get("version_type"),
        "release_date": check_result.get("release_date"),
        "release_url": check_result.get("release_url"),
        "error": check_result.get("error"),
    }

    if upgrade_result:
        output["upgrade"] = {
            "success": upgrade_result["success"],
            "error": upgrade_result.get("error"),
        }

    rich_print(json.dumps(output, indent=2))


@click.command(name="update")
@click.option(
    "--check-only",
    is_flag=True,
    help="Only check for updates without upgrading",
)
@click.option(
    "--pre",
    is_flag=True,
    help="Include pre-release versions",
)
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Only output if update is available",
)
@click.pass_context
def update(ctx: click.Context, check_only: bool, pre: bool, format: str, quiet: bool) -> None:
    """
    🔄 Check for and install kuzu-memory updates.

    Queries PyPI for the latest version and optionally upgrades
    the installed package using pip.

    \b
    🎮 EXAMPLES:
      # Check and prompt to upgrade
      kuzu-memory update

      # Just check, don't upgrade
      kuzu-memory update --check-only

      # Include pre-releases
      kuzu-memory update --pre

      # JSON output for scripts
      kuzu-memory update --format json

      # Silent mode (for cron jobs)
      kuzu-memory update --quiet --check-only
    """
    try:
        # Create version checker
        checker = VersionChecker()

        # Show progress indicator (unless quiet or json)
        if not quiet and format == "text":
            rich_print("🔍 Checking for updates...", style="dim")

        # Fetch latest version from PyPI
        check_result = checker.get_latest_version(include_pre=pre)

        # Handle errors
        if check_result.get("error"):
            if format == "json":
                _format_json_output(check_result, {"current": checker.current_version}, None)
            else:
                _format_text_output(check_result, {"current": checker.current_version}, None)
            sys.exit(1)

        # Compare versions
        comparison = checker.compare_versions(check_result["version"])

        # No update available
        if not comparison["update_available"]:
            if not quiet:
                if format == "json":
                    _format_json_output(check_result, comparison, None)
                else:
                    _format_text_output(check_result, comparison, None)
            sys.exit(0)

        # Update available
        if check_only:
            # Just show availability
            if not quiet:
                if format == "json":
                    _format_json_output(check_result, comparison, None)
                else:
                    _format_text_output(check_result, comparison, None)
            sys.exit(2)  # Exit code 2 = update available but not installed

        # Prompt to upgrade (text mode only)
        if format == "text":
            # Show what's available
            _format_text_output(check_result, comparison, None)

            # Confirm upgrade
            if not rich_confirm("\n🚀 Upgrade now?", default=False):
                rich_print("Upgrade cancelled.", style="dim")
                sys.exit(0)

        # Perform upgrade
        if format == "text":
            rich_print("\n📦 Upgrading kuzu-memory...", style="dim")

        upgrade_result = _run_upgrade()

        # Show results
        if format == "json":
            _format_json_output(check_result, comparison, upgrade_result)
        else:
            _format_text_output(check_result, comparison, upgrade_result)

        # Exit with appropriate code
        sys.exit(0 if upgrade_result["success"] else 1)

    except KeyboardInterrupt:
        rich_print("\n\nUpgrade cancelled by user.", style="yellow")
        sys.exit(130)
    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Update failed: {e}", style="red")
        logger.exception("Update command failed")
        sys.exit(1)


__all__ = ["VersionChecker", "update"]
