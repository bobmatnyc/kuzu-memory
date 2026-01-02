#!/usr/bin/env python3
"""
KuzuMemory PyPI Publishing Script

This script handles building and publishing KuzuMemory to PyPI using uv.

Requirements:
- uv package manager installed
- .env.local file with UV_PUBLISH_TOKEN or PYPI_API_KEY

Example usage:
    # Automated (CI-friendly)
    ./scripts/publish.py --yes

    # Interactive (default)
    ./scripts/publish.py

    # Test PyPI only
    ./scripts/publish.py --test --yes
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import Optional

def run_command(cmd, description, check=True, env=None):
    """Run a command with status output.

    Args:
        cmd: Command to run
        description: Human-readable description
        check: If True, raise on non-zero exit
        env: Optional environment variables dict
    """
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=True,
            text=True,
            env=env or os.environ.copy()
        )
        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True, result.stdout
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False, str(e)

def load_env_credentials() -> Optional[str]:
    """Load PyPI credentials from .env.local file.

    Supports both UV_PUBLISH_TOKEN and PYPI_API_KEY environment variables.

    Returns:
        PyPI API token if found, None otherwise
    """
    env_file = Path(".env.local")

    if not env_file.exists():
        print("⚠️  No .env.local file found")
        return None

    print("🔑 Loading credentials from .env.local...")

    # Parse .env.local file
    env_vars = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")

    # Check for credentials (prefer UV_PUBLISH_TOKEN)
    token = env_vars.get("UV_PUBLISH_TOKEN") or env_vars.get("PYPI_API_KEY")

    if token:
        print("✅ Credentials loaded successfully")
        return token
    else:
        print("❌ No UV_PUBLISH_TOKEN or PYPI_API_KEY found in .env.local")
        return None

def check_prerequisites():
    """Check if uv is installed."""
    print("🔍 Checking prerequisites...")

    # Check if uv is installed
    success, _ = run_command("uv --version", "Checking uv", check=False)
    if not success:
        print("❌ uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False

    print("✅ All prerequisites available")
    return True

def clean_build():
    """Clean previous build artifacts."""
    print("🧹 Cleaning build artifacts...")
    
    dirs_to_clean = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  Removed directory: {path}")
            elif path.is_file():
                path.unlink()
                print(f"  Removed file: {path}")
    
    print("✅ Build artifacts cleaned")

def run_tests():
    """Run tests before publishing."""
    print("🧪 Running tests...")
    
    # Check if pytest is available
    success, _ = run_command("python -m pytest --version", "Checking pytest", check=False)
    if not success:
        print("⚠️  pytest not available, skipping tests")
        return True
    
    # Run tests
    success, output = run_command("python -m pytest tests/ -v", "Running test suite", check=False)
    if success:
        print("✅ All tests passed")
        return True
    else:
        print("❌ Tests failed")
        print("🤔 Continue anyway? (y/N): ", end="")
        response = input().strip().lower()
        return response in ['y', 'yes']

def build_package():
    """Build the package using uv."""
    print("📦 Building package...")

    success, output = run_command("uv build", "Building wheel and source distribution")
    if not success:
        return False

    # List built files
    dist_files = list(Path("dist").glob("*"))
    if dist_files:
        print("📋 Built files:")
        for file in dist_files:
            print(f"  - {file}")

    return True

def upload_to_testpypi(token: str, skip_confirmation: bool = False):
    """Upload to Test PyPI using uv.

    Args:
        token: PyPI API token
        skip_confirmation: If True, skip confirmation prompts
    """
    print("🧪 Uploading to Test PyPI...")

    if not skip_confirmation:
        print("🤔 Upload to Test PyPI? (y/N): ", end="")
        response = input().strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Upload cancelled")
            return False

    # Set environment variable for uv publish
    env = os.environ.copy()
    env['UV_PUBLISH_TOKEN'] = token

    success, output = run_command(
        "uv publish --publish-url https://test.pypi.org/legacy/",
        "Uploading to Test PyPI",
        env=env
    )

    if success:
        print("✅ Successfully uploaded to Test PyPI")
        print("🔗 Check at: https://test.pypi.org/project/kuzu-memory/")
        return True
    else:
        print("❌ Failed to upload to Test PyPI")
        return False

def upload_to_pypi(token: str, skip_confirmation: bool = False):
    """Upload to PyPI using uv.

    Args:
        token: PyPI API token
        skip_confirmation: If True, skip confirmation prompts
    """
    print("🚀 Uploading to PyPI...")

    if not skip_confirmation:
        print("⚠️  This will publish to the real PyPI!")
        print("🤔 Are you sure you want to continue? (y/N): ", end="")
        response = input().strip().lower()

        if response not in ['y', 'yes']:
            print("❌ Upload cancelled")
            return False

    # Set environment variable for uv publish
    env = os.environ.copy()
    env['UV_PUBLISH_TOKEN'] = token

    success, output = run_command(
        "uv publish",
        "Uploading to PyPI",
        env=env
    )

    if success:
        print("🎉 Successfully published to PyPI!")
        print("🔗 Available at: https://pypi.org/project/kuzu-memory/")
        return True
    else:
        print("❌ Failed to upload to PyPI")
        return False

def main():
    """Main publishing workflow."""
    print("🚀 KuzuMemory PyPI Publishing")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Must be run from project root (pyproject.toml not found)")
        sys.exit(1)

    # Parse command line arguments
    test_only = "--test" in sys.argv
    skip_tests = "--skip-tests" in sys.argv
    skip_confirmation = "--yes" in sys.argv

    try:
        # Step 1: Check prerequisites
        if not check_prerequisites():
            sys.exit(1)

        # Step 2: Load credentials
        token = load_env_credentials()
        if not token:
            print("❌ No credentials found. Please add UV_PUBLISH_TOKEN or PYPI_API_KEY to .env.local")
            sys.exit(1)

        # Step 3: Clean build
        clean_build()

        # Step 4: Run tests (unless skipped)
        if not skip_tests:
            if not run_tests():
                if not skip_confirmation:
                    # Allow override in interactive mode
                    pass
                else:
                    # Fail immediately in automated mode
                    sys.exit(1)
        else:
            print("⚠️  Skipping tests (--skip-tests flag)")

        # Step 5: Build package
        if not build_package():
            sys.exit(1)

        # Step 6: Upload
        if test_only:
            print("🧪 Test mode - uploading to Test PyPI only")
            if not upload_to_testpypi(token, skip_confirmation):
                sys.exit(1)
        else:
            # Upload to Test PyPI first
            print("🧪 Uploading to Test PyPI first...")
            if upload_to_testpypi(token, skip_confirmation):
                if skip_confirmation:
                    # In automated mode, always continue to PyPI after Test PyPI
                    print("\n" + "=" * 50)
                    print("✅ Test PyPI upload successful. Continuing to PyPI...")
                    if not upload_to_pypi(token, skip_confirmation):
                        sys.exit(1)
                else:
                    # Interactive mode - ask for confirmation
                    print("\n" + "=" * 50)
                    print("🤔 Test PyPI upload successful. Upload to real PyPI? (y/N): ", end="")
                    response = input().strip().lower()

                    if response in ['y', 'yes']:
                        if not upload_to_pypi(token, skip_confirmation):
                            sys.exit(1)
                    else:
                        print("✅ Stopped at Test PyPI")
            else:
                sys.exit(1)

        print("\n" + "=" * 50)
        print("🎉 Publishing complete!")

        if not test_only:
            print("\n📦 Installation commands:")
            print("  pip install kuzu-memory")
            print("  pipx install kuzu-memory")

    except KeyboardInterrupt:
        print("\n❌ Publishing cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Publishing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
