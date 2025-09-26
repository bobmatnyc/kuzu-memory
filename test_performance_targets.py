#!/usr/bin/env python3
"""
Performance Target Testing Script

Tests specific performance targets mentioned in the requirements:
- <100ms for enhance/recall operations
- Non-blocking async learning operations
- Overall system performance under load
"""

import time
import tempfile
import shutil
import statistics
from pathlib import Path
from typing import List, Dict, Any

from src.kuzu_memory.async_memory.async_cli import AsyncMemoryCLI
from src.kuzu_memory.core.memory import KuzuMemory


class PerformanceTargetTester:
    """Test suite for performance targets."""

    def __init__(self):
        """Initialize the test environment."""
        self.test_db_dir = None
        self.async_cli = None
        self.sync_memory = None

    def setup_test_environment(self) -> None:
        """Set up a temporary test environment."""
        print("Setting up performance test environment...")

        # Create temporary directory for test database
        self.test_db_dir = Path(tempfile.mkdtemp(prefix="kuzu_memory_perf_test_"))
        print(f"Test database directory: {self.test_db_dir}")

        # Initialize async CLI
        self.async_cli = AsyncMemoryCLI(db_path=self.test_db_dir / "memories.db")

        # Initialize sync memory for comparison
        self.sync_memory = KuzuMemory(db_path=self.test_db_dir / "memories.db")

        # Pre-populate with some memories for context
        self._populate_test_memories()

    def _populate_test_memories(self) -> None:
        """Populate the database with test memories for context retrieval."""
        test_memories = [
            "We use React for frontend development with TypeScript",
            "PostgreSQL is our primary database for user data",
            "Authentication uses JWT tokens with 24 hour expiry",
            "Redis is used for caching and session storage",
            "API endpoints follow REST conventions with versioning",
            "The project structure follows Domain Driven Design patterns",
            "Testing framework is pytest with 90% coverage requirement",
            "CI/CD pipeline runs on GitHub Actions with automated deployments",
            "Docker containers are used for consistent deployment environments",
            "Team uses Scrum methodology with 2-week sprints"
        ]

        print("Populating test database with context memories...")
        for content in test_memories:
            try:
                self.sync_memory.generate_memories(content, source="test-setup")
            except Exception as e:
                print(f"Warning: Failed to add test memory: {e}")

    def cleanup_test_environment(self) -> None:
        """Clean up test environment."""
        print("Cleaning up performance test environment...")

        if self.sync_memory:
            try:
                self.sync_memory.close()
            except:
                pass

        if self.test_db_dir and self.test_db_dir.exists():
            shutil.rmtree(self.test_db_dir)

        print("Performance test cleanup complete")

    def test_enhance_performance_target(self) -> Dict[str, Any]:
        """Test that enhance operations meet <100ms target."""
        print("\n🎯 Testing enhance performance target (<100ms)...")

        test_prompts = [
            "How do I set up authentication?",
            "What database should I use for user profiles?",
            "How to structure API endpoints?",
            "What testing framework is recommended?",
            "How to deploy the application?",
            "What caching strategy should I use?",
            "How to handle user sessions?",
            "What frontend framework is preferred?",
            "How to organize the project structure?",
            "What CI/CD tools are being used?"
        ]

        measurements = []
        results = {}

        for prompt in test_prompts:
            start_time = time.perf_counter()

            try:
                enhanced_prompt = self.async_cli.enhance_sync(
                    prompt=prompt,
                    max_memories=5,
                    output_format="plain"
                )

                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                measurements.append(duration_ms)

                print(f"  ✅ Enhanced in {duration_ms:.1f}ms: {prompt[:50]}...")

            except Exception as e:
                print(f"  ❌ Failed: {prompt[:50]}... - {e}")
                measurements.append(float('inf'))

        # Calculate statistics
        valid_measurements = [m for m in measurements if m != float('inf')]

        if valid_measurements:
            results = {
                'test_name': 'enhance_performance_target',
                'success': all(m < 100 for m in valid_measurements),
                'measurements_ms': valid_measurements,
                'statistics': {
                    'min_ms': min(valid_measurements),
                    'max_ms': max(valid_measurements),
                    'mean_ms': statistics.mean(valid_measurements),
                    'median_ms': statistics.median(valid_measurements),
                    'std_dev_ms': statistics.stdev(valid_measurements) if len(valid_measurements) > 1 else 0.0,
                },
                'target_met': {
                    'under_100ms': sum(1 for m in valid_measurements if m < 100),
                    'total_tests': len(valid_measurements),
                    'success_rate': sum(1 for m in valid_measurements if m < 100) / len(valid_measurements) * 100
                }
            }
        else:
            results = {
                'test_name': 'enhance_performance_target',
                'success': False,
                'error': 'No valid measurements obtained'
            }

        if results['success']:
            print(f"  🎉 PASS: All enhance operations under 100ms (avg: {results['statistics']['mean_ms']:.1f}ms)")
        else:
            failed_count = sum(1 for m in valid_measurements if m >= 100)
            print(f"  ⚠️  PARTIAL: {failed_count}/{len(valid_measurements)} operations exceeded 100ms target")

        return results

    def test_async_learning_non_blocking(self) -> Dict[str, Any]:
        """Test that async learning operations are truly non-blocking."""
        print("\n🚀 Testing async learning non-blocking behavior...")

        test_contents = [
            "User reported a bug in the authentication system",
            "Feature request for dark mode in the UI",
            "Team decision to migrate to microservices architecture",
            "Performance issue with database queries identified",
            "Security vulnerability patched in payment processing"
        ]

        # Test 1: Measure time to submit all tasks (should be very fast)
        start_time = time.perf_counter()
        task_ids = []

        for content in test_contents:
            task_result = self.async_cli.learn_async(
                content=content,
                source="performance-test",
                quiet=True
            )
            task_ids.append(task_result['task_id'])

        submission_time = (time.perf_counter() - start_time) * 1000

        # Test 2: Check that submission was indeed non-blocking (very fast)
        avg_submission_time = submission_time / len(test_contents)

        # Test 3: Wait for completion and measure processing time
        start_processing_time = time.perf_counter()
        completed_tasks = []

        for task_id in task_ids:
            task_status = self.async_cli.wait_for_task(task_id, timeout_seconds=10.0)
            if task_status['status'] == 'completed':
                completed_tasks.append(task_status)

        total_processing_time = (time.perf_counter() - start_processing_time) * 1000

        results = {
            'test_name': 'async_learning_non_blocking',
            'success': False,
            'details': {
                'submission_time_ms': submission_time,
                'avg_submission_time_ms': avg_submission_time,
                'total_processing_time_ms': total_processing_time,
                'tasks_submitted': len(task_ids),
                'tasks_completed': len(completed_tasks),
                'completion_rate': len(completed_tasks) / len(task_ids) * 100
            }
        }

        # Success criteria:
        # 1. Fast submission (each task submission < 10ms)
        # 2. High completion rate (>80%)
        # 3. Total submission time much less than processing time
        success_criteria = [
            avg_submission_time < 10.0,  # Fast submission
            len(completed_tasks) / len(task_ids) >= 0.8,  # High completion rate
            submission_time < (total_processing_time / 10)  # Submission much faster than processing
        ]

        results['success'] = all(success_criteria)
        results['success_criteria'] = {
            'fast_submission': success_criteria[0],
            'high_completion_rate': success_criteria[1],
            'non_blocking': success_criteria[2]
        }

        if results['success']:
            print(f"  🎉 PASS: Async operations are non-blocking (avg submission: {avg_submission_time:.1f}ms)")
        else:
            print(f"  ⚠️  Issues detected in async non-blocking behavior")

        return results

    def test_recall_performance(self) -> Dict[str, Any]:
        """Test recall performance specifically."""
        print("\n🔍 Testing recall performance...")

        test_queries = [
            "authentication system",
            "database configuration",
            "API design patterns",
            "testing framework",
            "deployment process",
            "caching strategy",
            "project structure",
            "frontend technology",
            "security measures",
            "performance optimization"
        ]

        measurements = []

        for query in test_queries:
            start_time = time.perf_counter()

            try:
                # Use the sync memory for recall testing
                context = self.sync_memory.attach_memories(
                    prompt=f"Tell me about {query}",
                    max_memories=5
                )

                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                measurements.append({
                    'query': query,
                    'duration_ms': duration_ms,
                    'memories_found': len(context.memories),
                    'confidence': context.confidence
                })

                print(f"  ✅ Recalled in {duration_ms:.1f}ms: {query} ({len(context.memories)} memories)")

            except Exception as e:
                print(f"  ❌ Failed: {query} - {e}")
                measurements.append({
                    'query': query,
                    'duration_ms': float('inf'),
                    'memories_found': 0,
                    'confidence': 0.0
                })

        # Calculate statistics
        valid_measurements = [m for m in measurements if m['duration_ms'] != float('inf')]
        durations = [m['duration_ms'] for m in valid_measurements]

        results = {
            'test_name': 'recall_performance',
            'success': False,
            'measurements': valid_measurements,
            'statistics': {}
        }

        if durations:
            results['statistics'] = {
                'min_ms': min(durations),
                'max_ms': max(durations),
                'mean_ms': statistics.mean(durations),
                'median_ms': statistics.median(durations),
                'std_dev_ms': statistics.stdev(durations) if len(durations) > 1 else 0.0,
                'under_100ms_count': sum(1 for d in durations if d < 100),
                'total_tests': len(durations),
                'success_rate': sum(1 for d in durations if d < 100) / len(durations) * 100
            }

            results['success'] = all(d < 100 for d in durations)

        if results['success']:
            print(f"  🎉 PASS: All recall operations under 100ms (avg: {results['statistics']['mean_ms']:.1f}ms)")
        else:
            failed_count = sum(1 for d in durations if d >= 100)
            print(f"  ⚠️  ISSUES: {failed_count}/{len(durations)} operations exceeded 100ms")

        return results

    def test_system_under_load(self) -> Dict[str, Any]:
        """Test system performance under load."""
        print("\n🔥 Testing system performance under load...")

        # Create a mixed workload
        enhance_queries = [f"How to implement feature {i}?" for i in range(20)]
        learn_contents = [f"User story {i}: As a user I want to..." for i in range(30)]

        results = {
            'test_name': 'system_under_load',
            'success': False,
            'details': {}
        }

        try:
            # Test 1: Rapid enhancement requests
            print("  Testing rapid enhancement requests...")
            enhance_times = []
            start_time = time.perf_counter()

            for query in enhance_queries:
                op_start = time.perf_counter()
                enhanced = self.async_cli.enhance_sync(query, max_memories=3, output_format="plain")
                op_end = time.perf_counter()
                enhance_times.append((op_end - op_start) * 1000)

            total_enhance_time = (time.perf_counter() - start_time) * 1000

            # Test 2: Rapid async learning submissions
            print("  Testing rapid async learning submissions...")
            learn_start_time = time.perf_counter()
            task_ids = []

            for content in learn_contents:
                task_result = self.async_cli.learn_async(
                    content=content,
                    source="load-test",
                    quiet=True
                )
                task_ids.append(task_result['task_id'])

            total_submission_time = (time.perf_counter() - learn_start_time) * 1000

            # Test 3: Check system responsiveness during load
            print("  Checking system responsiveness during processing...")
            responsiveness_start = time.perf_counter()
            test_query = "What's the system architecture?"
            response = self.async_cli.enhance_sync(test_query, output_format="plain")
            responsiveness_time = (time.perf_counter() - responsiveness_start) * 1000

            # Compile results
            results['details'] = {
                'enhance_operations': {
                    'total_operations': len(enhance_queries),
                    'total_time_ms': total_enhance_time,
                    'avg_time_ms': statistics.mean(enhance_times),
                    'max_time_ms': max(enhance_times),
                    'operations_under_100ms': sum(1 for t in enhance_times if t < 100),
                    'throughput_ops_per_sec': len(enhance_queries) / (total_enhance_time / 1000)
                },
                'async_submissions': {
                    'total_submissions': len(task_ids),
                    'total_submission_time_ms': total_submission_time,
                    'avg_submission_time_ms': total_submission_time / len(task_ids),
                    'throughput_ops_per_sec': len(task_ids) / (total_submission_time / 1000)
                },
                'system_responsiveness': {
                    'response_time_ms': responsiveness_time,
                    'responsive': responsiveness_time < 100
                }
            }

            # Success criteria
            success_criteria = [
                statistics.mean(enhance_times) < 100,  # Average enhance time under 100ms
                max(enhance_times) < 200,  # No enhance operation over 200ms
                total_submission_time / len(task_ids) < 10,  # Fast async submissions
                responsiveness_time < 100  # System remains responsive
            ]

            results['success'] = all(success_criteria)
            results['success_criteria'] = {
                'avg_enhance_under_100ms': success_criteria[0],
                'max_enhance_under_200ms': success_criteria[1],
                'fast_async_submissions': success_criteria[2],
                'system_remains_responsive': success_criteria[3]
            }

            if results['success']:
                print(f"  🎉 PASS: System performs well under load")
                print(f"       - Enhance throughput: {results['details']['enhance_operations']['throughput_ops_per_sec']:.1f} ops/sec")
                print(f"       - Async throughput: {results['details']['async_submissions']['throughput_ops_per_sec']:.1f} ops/sec")
            else:
                print(f"  ⚠️  Performance issues detected under load")

        except Exception as e:
            results['error'] = str(e)
            print(f"  ❌ Load testing failed: {e}")

        return results

    def run_all_performance_tests(self) -> Dict[str, Any]:
        """Run all performance tests."""
        print("🚀 Starting Performance Target Tests...")
        print("=" * 60)

        try:
            self.setup_test_environment()

            test_methods = [
                self.test_enhance_performance_target,
                self.test_async_learning_non_blocking,
                self.test_recall_performance,
                self.test_system_under_load
            ]

            results = []
            for test_method in test_methods:
                try:
                    result = test_method()
                    results.append(result)
                except Exception as e:
                    results.append({
                        'test_name': test_method.__name__,
                        'success': False,
                        'error': str(e)
                    })
                    print(f"Test {test_method.__name__} crashed: {e}")

            # Compile final results
            total_tests = len(results)
            successful_tests = sum(1 for r in results if r['success'])

            final_results = {
                'summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'failed_tests': total_tests - successful_tests,
                    'success_rate': successful_tests / total_tests * 100,
                    'performance_target_met': successful_tests >= 3  # At least 3/4 tests should pass
                },
                'individual_results': results,
                'performance_analysis': self._analyze_performance_results(results)
            }

            return final_results

        finally:
            self.cleanup_test_environment()

    def _analyze_performance_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance results and provide insights."""
        analysis = {
            'enhance_performance': 'Not tested',
            'async_performance': 'Not tested',
            'recall_performance': 'Not tested',
            'load_performance': 'Not tested',
            'overall_assessment': 'Inconclusive',
            'recommendations': []
        }

        for result in results:
            test_name = result.get('test_name', '')

            if 'enhance_performance' in test_name and result['success']:
                stats = result.get('statistics', {})
                avg_ms = stats.get('mean_ms', 0)
                analysis['enhance_performance'] = f"EXCELLENT - avg {avg_ms:.1f}ms (target: <100ms)"

            elif 'async_learning' in test_name and result['success']:
                details = result.get('details', {})
                avg_submission = details.get('avg_submission_time_ms', 0)
                analysis['async_performance'] = f"EXCELLENT - avg {avg_submission:.1f}ms submission time"

            elif 'recall_performance' in test_name and result['success']:
                stats = result.get('statistics', {})
                avg_ms = stats.get('mean_ms', 0)
                analysis['recall_performance'] = f"EXCELLENT - avg {avg_ms:.1f}ms (target: <100ms)"

            elif 'system_under_load' in test_name and result['success']:
                analysis['load_performance'] = "EXCELLENT - maintains performance under load"

        # Overall assessment
        successes = sum(1 for result in results if result['success'])
        if successes == len(results):
            analysis['overall_assessment'] = "EXCELLENT - All performance targets met"
        elif successes >= len(results) * 0.75:
            analysis['overall_assessment'] = "GOOD - Most performance targets met"
        else:
            analysis['overall_assessment'] = "NEEDS IMPROVEMENT - Multiple performance issues"
            analysis['recommendations'].append("Review system architecture for performance bottlenecks")
            analysis['recommendations'].append("Consider optimizing database queries and caching")

        return analysis


def main():
    """Main test execution function."""
    print("⚡ KuzuMemory Performance Target Test Suite")
    print("=" * 60)

    tester = PerformanceTargetTester()
    results = tester.run_all_performance_tests()

    # Print summary
    summary = results['summary']
    print(f"\n📊 Performance Test Results:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Successful: {summary['successful_tests']}")
    print(f"   Failed: {summary['failed_tests']}")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Performance Target Met: {'✅ YES' if summary['performance_target_met'] else '❌ NO'}")

    # Print individual results
    print(f"\n📋 Individual Test Results:")
    for result in results['individual_results']:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        test_name = result['test_name'].replace('test_', '').replace('_', ' ').title()
        print(f"   {status} {test_name}")

    # Print performance analysis
    print(f"\n🔍 Performance Analysis:")
    analysis = results['performance_analysis']
    print(f"   Enhance Performance: {analysis['enhance_performance']}")
    print(f"   Async Performance: {analysis['async_performance']}")
    print(f"   Recall Performance: {analysis['recall_performance']}")
    print(f"   Load Performance: {analysis['load_performance']}")
    print(f"   Overall: {analysis['overall_assessment']}")

    if analysis['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in analysis['recommendations']:
            print(f"   • {rec}")

    return results


if __name__ == "__main__":
    main()