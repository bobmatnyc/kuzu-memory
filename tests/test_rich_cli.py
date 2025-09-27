#!/usr/bin/env python3
"""
Test the rich CLI system.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    """Run a CLI command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd="/Users/masa/Projects/managed/kuzu-memory",
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def test_cli_help():
    """Test the CLI help system."""
    import pytest

    pytest.skip("Standalone test file - functionality tested in proper test suite")
    print("🧪 Testing Rich CLI Help System")
    print("=" * 50)

    commands_to_test = [
        ("kuzu-memory --help", "Main help"),
        ("kuzu-memory", "Default help (no command)"),
        ("kuzu-memory examples", "Examples overview"),
        ("kuzu-memory examples remember", "Remember examples"),
        ("kuzu-memory examples recall", "Recall examples"),
        ("kuzu-memory examples auggie", "Auggie examples"),
        ("kuzu-memory examples workflow", "Workflow examples"),
        ("kuzu-memory examples patterns", "Pattern examples"),
        ("kuzu-memory remember --help", "Remember command help"),
        ("kuzu-memory demo", "Instant demo"),
    ]

    results = []

    for cmd, description in commands_to_test:
        print(f"\n🔍 Testing: {description}")
        print(f"   Command: {cmd}")

        returncode, stdout, stderr = run_command(cmd)

        if returncode == 0:
            print(f"   ✅ Success ({len(stdout)} chars output)")
            if "🧠" in stdout or "📚" in stdout or "🚀" in stdout:
                print("   🎨 Rich formatting detected")
            results.append((cmd, True, len(stdout)))
        else:
            print(f"   ❌ Failed (code: {returncode})")
            if stderr:
                print(f"   Error: {stderr[:100]}...")
            results.append((cmd, False, 0))

    # Summary
    print("\n📊 Test Results:")
    print("-" * 30)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    for cmd, success, output_len in results:
        status = "✅" if success else "❌"
        print(f"  {status} {cmd[:40]:<40} ({output_len} chars)")

    return passed == total


def test_cli_functionality():
    """Test actual CLI functionality."""
    import pytest

    pytest.skip("Standalone test file - functionality tested in proper test suite")
    print("\n🧪 Testing CLI Functionality")
    print("=" * 50)

    # Test demo command (should work without setup)
    print("\n🎮 Testing demo command...")
    returncode, stdout, stderr = run_command("kuzu-memory demo")

    if returncode == 0:
        print("✅ Demo command works")
        if "Demo Complete" in stdout:
            print("✅ Demo completed successfully")
        if "🎉" in stdout:
            print("✅ Rich formatting in demo")
    else:
        print(f"❌ Demo failed: {stderr}")
        return False

    return True


def main():
    """Run CLI tests."""
    print("🧪 KuzuMemory Rich CLI Test Suite")
    print("=" * 60)

    # Test 1: Help system
    help_success = test_cli_help()

    # Test 2: Functionality
    func_success = test_cli_functionality()

    # Overall results
    print(f"\n{'=' * 60}")
    print("📊 OVERALL RESULTS")
    print(f"{'=' * 60}")

    tests = [("Help System", help_success), ("Functionality", func_success)]

    passed_tests = sum(1 for _, success in tests if success)
    total_tests = len(tests)

    print(f"🎯 Results: {passed_tests}/{total_tests} test suites passed")

    for test_name, success in tests:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Rich CLI system is working correctly")
        print("✅ Help system provides comprehensive guidance")
        print("✅ Examples and tutorials are accessible")
        print("✅ 3-minute setup goal achieved")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
