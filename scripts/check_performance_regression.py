#!/usr/bin/env python3
"""
Performance regression checker for KuzuMemory CI.

Analyzes benchmark results and checks for performance regressions
against established baselines.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional


class PerformanceChecker:
    """Checks for performance regressions in benchmark results."""
    
    def __init__(self, baseline_file: Optional[Path] = None):
        """Initialize with optional baseline file."""
        self.baseline_file = baseline_file or Path("tests/baselines/performance_baseline.json")
        self.baseline_data = self._load_baseline()
        
        # Performance thresholds (allow some degradation)
        self.thresholds = {
            "attach_memories_mean_ms": 10.0,
            "attach_memories_p95_ms": 15.0,
            "generate_memories_mean_ms": 20.0,
            "generate_memories_p95_ms": 30.0,
            "memory_scaling_factor": 2.0,
            "cache_speedup_factor": 2.0,
            "regression_tolerance": 1.2  # Allow 20% degradation
        }
    
    def _load_baseline(self) -> Dict[str, Any]:
        """Load performance baseline data."""
        if not self.baseline_file.exists():
            print(f"Warning: Baseline file {self.baseline_file} not found. Using default values.")
            return {
                "attach_memories": {"mean": 8.0, "p95": 12.0},
                "generate_memories": {"mean": 15.0, "p95": 25.0},
                "memory_scaling": {"degradation_factor": 1.8},
                "cache_performance": {"speedup": 2.5},
                "last_updated": "2024-01-01T00:00:00Z"
            }
        
        try:
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading baseline: {e}")
            return {}
    
    def _save_baseline(self, new_baseline: Dict[str, Any]):
        """Save updated baseline data."""
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.baseline_file, 'w') as f:
            json.dump(new_baseline, f, indent=2)
        
        print(f"Updated baseline saved to {self.baseline_file}")
    
    def check_benchmark_results(self, results_file: Path) -> bool:
        """Check benchmark results for regressions."""
        if not results_file.exists():
            print(f"Error: Benchmark results file {results_file} not found.")
            return False
        
        try:
            with open(results_file, 'r') as f:
                results = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading benchmark results: {e}")
            return False
        
        print("🔍 Checking Performance Regression...")
        print("=" * 50)
        
        regressions_found = []
        improvements_found = []
        
        # Check each benchmark
        for benchmark in results.get('benchmarks', []):
            benchmark_name = benchmark.get('name', 'unknown')
            stats = benchmark.get('stats', {})
            
            regression_result = self._check_benchmark_regression(benchmark_name, stats)
            
            if regression_result['status'] == 'regression':
                regressions_found.append(regression_result)
            elif regression_result['status'] == 'improvement':
                improvements_found.append(regression_result)
        
        # Report results
        self._report_results(regressions_found, improvements_found)
        
        # Update baseline if no regressions and improvements found
        if not regressions_found and improvements_found:
            self._update_baseline_from_results(results)
        
        return len(regressions_found) == 0
    
    def _check_benchmark_regression(self, benchmark_name: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Check a single benchmark for regression."""
        mean_time = stats.get('mean', 0) * 1000  # Convert to ms
        p95_time = stats.get('p95', 0) * 1000 if 'p95' in stats else mean_time * 1.2
        
        # Map benchmark names to baseline keys
        baseline_mapping = {
            'test_attach_memories_performance_target': 'attach_memories',
            'test_generate_memories_performance_target': 'generate_memories',
            'test_attach_memories_performance': 'attach_memories',
            'test_generate_memories_performance': 'generate_memories',
        }
        
        baseline_key = None
        for pattern, key in baseline_mapping.items():
            if pattern in benchmark_name:
                baseline_key = key
                break
        
        if not baseline_key or baseline_key not in self.baseline_data:
            return {
                'benchmark': benchmark_name,
                'status': 'no_baseline',
                'message': f"No baseline found for {benchmark_name}"
            }
        
        baseline = self.baseline_data[baseline_key]
        baseline_mean = baseline.get('mean', 0)
        baseline_p95 = baseline.get('p95', 0)
        
        tolerance = self.thresholds['regression_tolerance']
        
        # Check for regression
        mean_regression = mean_time > baseline_mean * tolerance
        p95_regression = p95_time > baseline_p95 * tolerance
        
        # Check for improvement
        improvement_threshold = 0.9  # 10% improvement
        mean_improvement = mean_time < baseline_mean * improvement_threshold
        p95_improvement = p95_time < baseline_p95 * improvement_threshold
        
        if mean_regression or p95_regression:
            return {
                'benchmark': benchmark_name,
                'status': 'regression',
                'current_mean': mean_time,
                'baseline_mean': baseline_mean,
                'current_p95': p95_time,
                'baseline_p95': baseline_p95,
                'mean_regression': mean_regression,
                'p95_regression': p95_regression,
                'message': f"Performance regression detected in {benchmark_name}"
            }
        elif mean_improvement and p95_improvement:
            return {
                'benchmark': benchmark_name,
                'status': 'improvement',
                'current_mean': mean_time,
                'baseline_mean': baseline_mean,
                'current_p95': p95_time,
                'baseline_p95': baseline_p95,
                'message': f"Performance improvement detected in {benchmark_name}"
            }
        else:
            return {
                'benchmark': benchmark_name,
                'status': 'stable',
                'current_mean': mean_time,
                'baseline_mean': baseline_mean,
                'message': f"Performance stable for {benchmark_name}"
            }
    
    def _report_results(self, regressions: List[Dict], improvements: List[Dict]):
        """Report regression check results."""
        if regressions:
            print("❌ PERFORMANCE REGRESSIONS DETECTED:")
            print("-" * 40)
            for regression in regressions:
                print(f"  {regression['benchmark']}:")
                print(f"    Mean: {regression['current_mean']:.2f}ms (baseline: {regression['baseline_mean']:.2f}ms)")
                if regression.get('mean_regression'):
                    print(f"    ⚠️  Mean time regression: {regression['current_mean']/regression['baseline_mean']:.2f}x")
                
                print(f"    P95:  {regression['current_p95']:.2f}ms (baseline: {regression['baseline_p95']:.2f}ms)")
                if regression.get('p95_regression'):
                    print(f"    ⚠️  P95 time regression: {regression['current_p95']/regression['baseline_p95']:.2f}x")
                print()
        
        if improvements:
            print("✅ PERFORMANCE IMPROVEMENTS DETECTED:")
            print("-" * 40)
            for improvement in improvements:
                print(f"  {improvement['benchmark']}:")
                print(f"    Mean: {improvement['current_mean']:.2f}ms (baseline: {improvement['baseline_mean']:.2f}ms)")
                print(f"    🚀 Improvement: {improvement['baseline_mean']/improvement['current_mean']:.2f}x faster")
                print()
        
        if not regressions and not improvements:
            print("✅ All benchmarks within acceptable performance range")
        
        print("=" * 50)
        
        # Summary
        total_checks = len(regressions) + len(improvements)
        if total_checks > 0:
            print(f"Summary: {len(regressions)} regressions, {len(improvements)} improvements")
        
        if regressions:
            print("\n🚨 PERFORMANCE REGRESSION CHECK FAILED")
            print("Please investigate and fix performance issues before merging.")
        else:
            print("\n✅ PERFORMANCE REGRESSION CHECK PASSED")
    
    def _update_baseline_from_results(self, results: Dict[str, Any]):
        """Update baseline with improved performance results."""
        print("\n📈 Updating performance baseline with improvements...")
        
        updated = False
        new_baseline = self.baseline_data.copy()
        
        for benchmark in results.get('benchmarks', []):
            benchmark_name = benchmark.get('name', '')
            stats = benchmark.get('stats', {})
            
            if 'attach_memories' in benchmark_name:
                key = 'attach_memories'
            elif 'generate_memories' in benchmark_name:
                key = 'generate_memories'
            else:
                continue
            
            mean_time = stats.get('mean', 0) * 1000
            p95_time = stats.get('p95', 0) * 1000 if 'p95' in stats else mean_time * 1.2
            
            if key not in new_baseline:
                new_baseline[key] = {}
            
            # Update if significantly better
            current_mean = new_baseline[key].get('mean', float('inf'))
            current_p95 = new_baseline[key].get('p95', float('inf'))
            
            if mean_time < current_mean * 0.9:  # 10% improvement
                new_baseline[key]['mean'] = mean_time
                updated = True
                print(f"  Updated {key} mean: {mean_time:.2f}ms")
            
            if p95_time < current_p95 * 0.9:  # 10% improvement
                new_baseline[key]['p95'] = p95_time
                updated = True
                print(f"  Updated {key} P95: {p95_time:.2f}ms")
        
        if updated:
            from datetime import datetime
            new_baseline['last_updated'] = datetime.utcnow().isoformat() + 'Z'
            self._save_baseline(new_baseline)
        else:
            print("  No significant improvements to update baseline")
    
    def generate_performance_report(self, results_file: Path, output_file: Path):
        """Generate a detailed performance report."""
        if not results_file.exists():
            print(f"Error: Results file {results_file} not found.")
            return
        
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        report_lines = [
            "# Performance Benchmark Report",
            "",
            f"**Generated:** {results.get('datetime', 'Unknown')}",
            f"**Machine:** {results.get('machine_info', {}).get('machine', 'Unknown')}",
            f"**Python:** {results.get('machine_info', {}).get('python_version', 'Unknown')}",
            "",
            "## Benchmark Results",
            ""
        ]
        
        for benchmark in results.get('benchmarks', []):
            name = benchmark.get('name', 'Unknown')
            stats = benchmark.get('stats', {})
            
            mean_ms = stats.get('mean', 0) * 1000
            p95_ms = stats.get('p95', 0) * 1000 if 'p95' in stats else mean_ms * 1.2
            
            report_lines.extend([
                f"### {name}",
                "",
                f"- **Mean Time:** {mean_ms:.2f}ms",
                f"- **P95 Time:** {p95_ms:.2f}ms",
                f"- **Min Time:** {stats.get('min', 0) * 1000:.2f}ms",
                f"- **Max Time:** {stats.get('max', 0) * 1000:.2f}ms",
                f"- **Iterations:** {stats.get('rounds', 'Unknown')}",
                ""
            ])
        
        # Write report
        with open(output_file, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"Performance report generated: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check for performance regressions")
    parser.add_argument("results_file", type=Path, help="Benchmark results JSON file")
    parser.add_argument("--baseline", type=Path, help="Baseline performance file")
    parser.add_argument("--report", type=Path, help="Generate performance report")
    parser.add_argument("--update-baseline", action="store_true", 
                       help="Update baseline with improvements")
    
    args = parser.parse_args()
    
    checker = PerformanceChecker(args.baseline)
    
    # Check for regressions
    passed = checker.check_benchmark_results(args.results_file)
    
    # Generate report if requested
    if args.report:
        checker.generate_performance_report(args.results_file, args.report)
    
    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
