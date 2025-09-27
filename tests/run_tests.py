#!/usr/bin/env python3
"""
Enhanced test runner for KuzuMemory following best practices.

Provides comprehensive test execution with proper configuration,
reporting, and CI/CD integration.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class TestRunner:
    """Enhanced test runner with comprehensive features."""

    def __init__(self):
        """Initialize the test runner."""
        self.start_time = time.time()
        self.results = {}
        self.failed_suites = []

    def run_command(
        self, cmd: list[str], description: str, timeout: int | None = None
    ) -> bool:
        """Run a command with enhanced error handling and reporting."""
        print(f"\n{'=' * 60}")
        print(f"🚀 Running: {description}")
        print(f"📝 Command: {' '.join(cmd)}")
        print("=" * 60)

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd, check=True, capture_output=False, timeout=timeout
            )

            duration = time.time() - start_time
            print(f"✅ {description} completed successfully in {duration:.1f}s")

            self.results[description] = {
                "status": "success",
                "duration": duration,
                "exit_code": result.returncode,
            }
            return True

        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            print(
                f"❌ {description} failed with exit code {e.returncode} after {duration:.1f}s"
            )

            self.results[description] = {
                "status": "failed",
                "duration": duration,
                "exit_code": e.returncode,
            }
            self.failed_suites.append(description)
            return False

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {description} timed out after {duration:.1f}s")

            self.results[description] = {
                "status": "timeout",
                "duration": duration,
                "exit_code": -1,
            }
            self.failed_suites.append(description)
            return False

        except FileNotFoundError:
            print(f"❌ Command not found: {cmd[0]}")
            print(
                "💡 Make sure pytest is installed: pip install -r requirements-dev.txt"
            )

            self.results[description] = {
                "status": "command_not_found",
                "duration": 0,
                "exit_code": -1,
            }
            self.failed_suites.append(description)
            return False

    def build_pytest_command(self, args) -> list[str]:
        """Build pytest command with appropriate options."""
        cmd = ["python", "-m", "pytest"]

        # Verbosity
        if args.verbose:
            cmd.extend(["-v", "--tb=long"])
        else:
            cmd.extend(["-q", "--tb=short"])

        # Coverage
        if args.coverage:
            cmd.extend(
                [
                    "--cov=kuzu_memory",
                    "--cov-report=html:htmlcov",
                    "--cov-report=term-missing",
                    "--cov-report=xml",
                ]
            )

        # Parallel execution
        if args.parallel:
            cmd.extend(["-n", str(args.parallel)])

        # Test filtering
        if args.fast:
            cmd.extend(["-m", "not slow"])

        if args.markers:
            cmd.extend(["-m", args.markers])

        # Output formats
        cmd.extend(
            [
                "--junit-xml=test-results.xml",
                "--html=test-report.html",
                "--self-contained-html",
            ]
        )

        # Timeouts
        if args.timeout:
            cmd.extend(["--timeout", str(args.timeout)])

        return cmd

    def get_test_suites(self, suite_name: str) -> list[tuple]:
        """Get test suite configurations."""
        all_suites = [
            ("tests/unit/", "Unit Tests", 300),
            ("tests/integration/", "Integration Tests", 600),
            ("tests/e2e/", "End-to-End Tests", 1200),
            ("tests/benchmarks/", "Performance Benchmarks", 900),
            ("tests/regression/", "Regression Tests", 1800),
        ]

        if suite_name == "all":
            return all_suites
        elif suite_name == "unit":
            return [all_suites[0]]
        elif suite_name == "integration":
            return [all_suites[1]]
        elif suite_name == "e2e":
            return [all_suites[2]]
        elif suite_name == "benchmark":
            return [all_suites[3]]
        elif suite_name == "regression":
            return [all_suites[4]]
        elif suite_name == "ci":
            # CI suite excludes regression tests
            return all_suites[:4]
        else:
            return []

    def run_test_suite(
        self, test_path: str, description: str, timeout: int, args
    ) -> bool:
        """Run a single test suite."""
        if not Path(test_path).exists():
            print(f"⏭️  Skipping {description} - directory not found: {test_path}")
            return True

        cmd = [*self.build_pytest_command(args), test_path]
        return self.run_command(cmd, description, timeout)

    def print_summary(self):
        """Print comprehensive test summary."""
        total_duration = time.time() - self.start_time

        print(f"\n{'=' * 60}")
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 60)

        success_count = sum(
            1 for r in self.results.values() if r["status"] == "success"
        )
        total_count = len(self.results)

        print(f"⏱️  Total Duration: {total_duration:.1f}s")
        print(
            f"📈 Success Rate: {success_count}/{total_count} ({success_count / total_count * 100:.1f}%)"
        )
        print()

        # Detailed results
        for description, result in self.results.items():
            status_icon = {
                "success": "✅",
                "failed": "❌",
                "timeout": "⏰",
                "command_not_found": "❓",
            }.get(result["status"], "❓")

            print(f"{status_icon} {description}: {result['duration']:.1f}s")

        print("=" * 60)

        if self.failed_suites:
            print("❌ FAILED SUITES:")
            for suite in self.failed_suites:
                print(f"   • {suite}")
            print("\n💡 Check the detailed output above for error information")
            print("🔧 Consider running individual suites for easier debugging")
        else:
            print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
            print("✅ KuzuMemory is ready for use")

        print("=" * 60)


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced KuzuMemory Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --suite unit --coverage          # Run unit tests with coverage
  %(prog)s --suite all --parallel 4         # Run all tests with 4 workers
  %(prog)s --fast --markers "not slow"      # Run fast tests only
  %(prog)s --suite benchmark --timeout 300  # Run benchmarks with timeout
        """,
    )

    parser.add_argument(
        "--suite",
        choices=["unit", "integration", "e2e", "benchmark", "regression", "ci", "all"],
        default="ci",
        help="Test suite to run (default: ci)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output with detailed test information",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage reporting"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests (excludes tests marked as 'slow')",
    )
    parser.add_argument(
        "--parallel",
        "-n",
        type=int,
        help="Number of parallel workers for test execution",
    )
    parser.add_argument(
        "--markers", "-m", help="Run tests matching given mark expression"
    )
    parser.add_argument(
        "--timeout", type=int, help="Timeout for individual tests in seconds"
    )
    parser.add_argument(
        "--fail-fast", "-x", action="store_true", help="Stop on first failure"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = TestRunner()

    print("🧪 KuzuMemory Enhanced Test Runner")
    print(f"📅 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Suite: {args.suite}")

    # Get test suites to run
    test_suites = runner.get_test_suites(args.suite)

    if not test_suites:
        print(f"❌ Unknown test suite: {args.suite}")
        return 1

    # Run test suites
    overall_success = True

    for test_path, description, default_timeout in test_suites:
        timeout = args.timeout or default_timeout
        success = runner.run_test_suite(test_path, description, timeout, args)

        if not success:
            overall_success = False
            if args.fail_fast:
                print("🛑 Stopping on first failure (--fail-fast)")
                break

    # Print summary
    runner.print_summary()

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
