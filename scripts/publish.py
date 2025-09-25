#!/usr/bin/env python3
"""
KuzuMemory PyPI Publishing Script

This script handles building and publishing KuzuMemory to PyPI.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(cmd, description, check=True):
    """Run a command with status output."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True, result.stdout
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False, str(e)

def check_prerequisites():
    """Check if all prerequisites are installed."""
    print("🔍 Checking prerequisites...")
    
    # Check if build tools are installed
    tools = ["build", "twine"]
    missing_tools = []
    
    for tool in tools:
        success, _ = run_command(f"python -m {tool} --help", f"Checking {tool}", check=False)
        if not success:
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"❌ Missing tools: {', '.join(missing_tools)}")
        print("📦 Installing missing tools...")
        for tool in missing_tools:
            success, _ = run_command(f"pip install {tool}", f"Installing {tool}")
            if not success:
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
    """Build the package."""
    print("📦 Building package...")
    
    success, output = run_command("python -m build", "Building wheel and source distribution")
    if not success:
        return False
    
    # List built files
    dist_files = list(Path("dist").glob("*"))
    if dist_files:
        print("📋 Built files:")
        for file in dist_files:
            print(f"  - {file}")
    
    return True

def check_package():
    """Check the built package."""
    print("🔍 Checking package...")
    
    success, output = run_command("python -m twine check dist/*", "Checking package with twine")
    return success

def upload_to_testpypi():
    """Upload to Test PyPI first."""
    print("🧪 Uploading to Test PyPI...")
    
    success, output = run_command(
        "python -m twine upload --repository testpypi dist/*",
        "Uploading to Test PyPI"
    )
    
    if success:
        print("✅ Successfully uploaded to Test PyPI")
        print("🔗 Check at: https://test.pypi.org/project/kuzu-memory/")
        return True
    else:
        print("❌ Failed to upload to Test PyPI")
        return False

def upload_to_pypi():
    """Upload to PyPI."""
    print("🚀 Uploading to PyPI...")
    
    print("⚠️  This will publish to the real PyPI!")
    print("🤔 Are you sure you want to continue? (y/N): ", end="")
    response = input().strip().lower()
    
    if response not in ['y', 'yes']:
        print("❌ Upload cancelled")
        return False
    
    success, output = run_command(
        "python -m twine upload dist/*",
        "Uploading to PyPI"
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
    
    try:
        # Step 1: Check prerequisites
        if not check_prerequisites():
            sys.exit(1)
        
        # Step 2: Clean build
        clean_build()
        
        # Step 3: Run tests (unless skipped)
        if not skip_tests:
            if not run_tests():
                sys.exit(1)
        else:
            print("⚠️  Skipping tests (--skip-tests flag)")
        
        # Step 4: Build package
        if not build_package():
            sys.exit(1)
        
        # Step 5: Check package
        if not check_package():
            sys.exit(1)
        
        # Step 6: Upload
        if test_only:
            print("🧪 Test mode - uploading to Test PyPI only")
            if not upload_to_testpypi():
                sys.exit(1)
        else:
            # Upload to Test PyPI first
            print("🧪 Uploading to Test PyPI first...")
            if upload_to_testpypi():
                print("\n" + "=" * 50)
                print("🤔 Test PyPI upload successful. Upload to real PyPI? (y/N): ", end="")
                response = input().strip().lower()
                
                if response in ['y', 'yes']:
                    if not upload_to_pypi():
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
