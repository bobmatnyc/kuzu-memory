#!/usr/bin/env python3
"""
Complete setup verification test.

Tests both development (shell script) and production (pipx) installations.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, timeout=30):
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True, result.stdout
        else:
            print(f"❌ {description} - FAILED")
            print(f"   Error: {result.stderr[:100]}...")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False, "Timeout"
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False, str(e)


def test_development_setup():
    """Test the development shell script setup."""
    import pytest

    pytest.skip("Standalone test file - functionality tested in proper test suite")
    print("\n🔧 Testing Development Setup")
    print("=" * 50)

    # Check if shell script exists
    if not Path("kuzu-memory.sh").exists():
        print("❌ kuzu-memory.sh not found")
        return False

    # Check if executable
    if not os.access("kuzu-memory.sh", os.X_OK):
        print("❌ kuzu-memory.sh not executable")
        return False

    tests = [
        ("./kuzu-memory.sh --help-dev", "Development help"),
        ("./kuzu-memory.sh --venv-info", "Virtual environment info"),
        ("./kuzu-memory.sh --help", "CLI help via shell script"),
        ("./kuzu-memory.sh demo", "Demo via shell script"),
    ]

    passed = 0
    for cmd, desc in tests:
        success, output = run_command(cmd, desc, timeout=60)
        if success:
            passed += 1

        # Special checks
        if "demo" in cmd and success:
            if "Demo Complete" in output:
                print("   ✅ Demo completed successfully")
            else:
                print("   ⚠️  Demo may not have completed fully")

    print(f"\n📊 Development Setup: {passed}/{len(tests)} tests passed")
    return passed == len(tests)


def test_production_installation():
    """Test the pipx production installation."""
    import pytest

    pytest.skip("Standalone test file - functionality tested in proper test suite")
    print("\n📦 Testing Production Installation")
    print("=" * 50)

    # Check if pipx is available
    success, _ = run_command("pipx --version", "Checking pipx availability")
    if not success:
        print("❌ pipx not available - skipping production tests")
        return False

    # Check if kuzu-memory is installed
    success, output = run_command("pipx list", "Checking installed packages")
    if not success or "kuzu-memory" not in output:
        print("❌ kuzu-memory not installed via pipx")
        return False

    tests = [
        ("kuzu-memory --version", "Version command"),
        ("kuzu-memory --help", "Help command"),
        ("kuzu-memory examples", "Examples command"),
        ("kuzu-memory demo", "Demo command"),
    ]

    passed = 0
    for cmd, desc in tests:
        success, output = run_command(cmd, desc, timeout=60)
        if success:
            passed += 1

        # Special checks
        if "version" in cmd and success:
            if "1.0.0" in output:
                print("   ✅ Correct version detected")
        elif "demo" in cmd and success:
            if "Demo Complete" in output:
                print("   ✅ Demo completed successfully")

    print(f"\n📊 Production Installation: {passed}/{len(tests)} tests passed")
    return passed == len(tests)


def test_functionality():
    """Test core functionality with both installations."""
    import pytest

    pytest.skip("Standalone test file - functionality tested in proper test suite")
    print("\n🧪 Testing Core Functionality")
    print("=" * 50)

    # Test development version
    print("\n🔧 Testing development functionality...")
    dev_tests = [
        (
            "./kuzu-memory.sh remember 'I am testing the development setup' --user-id test-dev",
            "Store memory (dev)",
        ),
        (
            "./kuzu-memory.sh recall 'What am I testing?' --user-id test-dev",
            "Recall memory (dev)",
        ),
        ("./kuzu-memory.sh optimize", "Optimize command (dev)"),
    ]

    dev_passed = 0
    for cmd, desc in dev_tests:
        success, _output = run_command(cmd, desc, timeout=60)
        if success:
            dev_passed += 1

    # Test production version
    print("\n📦 Testing production functionality...")
    prod_tests = [
        (
            "kuzu-memory remember 'I am testing the production setup' --user-id test-prod",
            "Store memory (prod)",
        ),
        (
            "kuzu-memory recall 'What am I testing?' --user-id test-prod",
            "Recall memory (prod)",
        ),
        ("kuzu-memory optimize", "Optimize command (prod)"),
    ]

    prod_passed = 0
    for cmd, desc in prod_tests:
        success, _output = run_command(cmd, desc, timeout=60)
        if success:
            prod_passed += 1

    total_tests = len(dev_tests) + len(prod_tests)
    total_passed = dev_passed + prod_passed

    print(f"\n📊 Functionality Tests: {total_passed}/{total_tests} tests passed")
    print(f"   Development: {dev_passed}/{len(dev_tests)}")
    print(f"   Production: {prod_passed}/{len(prod_tests)}")

    return total_passed >= (total_tests * 0.8)  # 80% pass rate


def main():
    """Run complete setup verification."""
    print("🧪 KuzuMemory Complete Setup Verification")
    print("=" * 70)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Must be run from KuzuMemory project root")
        sys.exit(1)

    # Run all tests
    tests = [
        ("Development Setup", test_development_setup),
        ("Production Installation", test_production_installation),
        ("Core Functionality", test_functionality),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n{'=' * 70}")
    print("📊 COMPLETE SETUP VERIFICATION SUMMARY")
    print(f"{'=' * 70}")

    passed_tests = sum(1 for _, success in results if success)
    total_tests = len(results)

    print(f"🎯 Overall Results: {passed_tests}/{total_tests} test suites passed")

    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")

    if passed_tests == total_tests:
        print("\n🎉 ALL SETUP VERIFICATION TESTS PASSED!")
        print("✅ Development environment working correctly")
        print("✅ Production installation working correctly")
        print("✅ Core functionality verified")
        print("✅ Both shell script and pipx installations ready")

        print("\n🚀 Setup Summary:")
        print("  • Development: ./kuzu-memory.sh [command]")
        print("  • Production:  kuzu-memory [command]")
        print("  • Help:        kuzu-memory --help")
        print("  • Demo:        kuzu-memory demo")

        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed")
        print("💡 Check the detailed output above for issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
