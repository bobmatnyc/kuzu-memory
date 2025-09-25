#!/usr/bin/env python3
"""
Test summary generator for KuzuMemory CI.

Aggregates test results from multiple test suites and generates
comprehensive HTML and markdown reports.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import glob


class TestSummaryGenerator:
    """Generates comprehensive test summaries from multiple test suites."""
    
    def __init__(self):
        """Initialize the test summary generator."""
        self.summary_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'suites': {},
            'overall': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'skipped_tests': 0,
                'error_tests': 0,
                'total_time': 0.0,
                'success_rate': 0.0
            },
            'performance': {},
            'coverage': {}
        }
    
    def parse_junit_xml(self, xml_file: Path, suite_name: str) -> Dict[str, Any]:
        """Parse JUnit XML test results."""
        if not xml_file.exists():
            return {
                'name': suite_name,
                'status': 'missing',
                'tests': 0,
                'failures': 0,
                'errors': 0,
                'skipped': 0,
                'time': 0.0,
                'test_cases': []
            }
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Handle different JUnit XML formats
            if root.tag == 'testsuites':
                testsuite = root.find('testsuite')
                if testsuite is None:
                    testsuite = root
            else:
                testsuite = root
            
            suite_data = {
                'name': suite_name,
                'status': 'completed',
                'tests': int(testsuite.get('tests', 0)),
                'failures': int(testsuite.get('failures', 0)),
                'errors': int(testsuite.get('errors', 0)),
                'skipped': int(testsuite.get('skipped', 0)),
                'time': float(testsuite.get('time', 0.0)),
                'test_cases': []
            }
            
            # Parse individual test cases
            for testcase in testsuite.findall('testcase'):
                case_data = {
                    'name': testcase.get('name', 'unknown'),
                    'classname': testcase.get('classname', ''),
                    'time': float(testcase.get('time', 0.0)),
                    'status': 'passed'
                }
                
                # Check for failures, errors, or skips
                if testcase.find('failure') is not None:
                    case_data['status'] = 'failed'
                    failure = testcase.find('failure')
                    case_data['failure_message'] = failure.get('message', '')
                    case_data['failure_text'] = failure.text or ''
                elif testcase.find('error') is not None:
                    case_data['status'] = 'error'
                    error = testcase.find('error')
                    case_data['error_message'] = error.get('message', '')
                    case_data['error_text'] = error.text or ''
                elif testcase.find('skipped') is not None:
                    case_data['status'] = 'skipped'
                    skipped = testcase.find('skipped')
                    case_data['skip_message'] = skipped.get('message', '')
                
                suite_data['test_cases'].append(case_data)
            
            return suite_data
            
        except ET.ParseError as e:
            return {
                'name': suite_name,
                'status': 'parse_error',
                'error': str(e),
                'tests': 0,
                'failures': 0,
                'errors': 0,
                'skipped': 0,
                'time': 0.0,
                'test_cases': []
            }
    
    def parse_benchmark_results(self, benchmark_file: Path) -> Dict[str, Any]:
        """Parse benchmark results JSON."""
        if not benchmark_file.exists():
            return {'status': 'missing', 'benchmarks': []}
        
        try:
            with open(benchmark_file, 'r') as f:
                data = json.load(f)
            
            performance_data = {
                'status': 'completed',
                'benchmarks': [],
                'machine_info': data.get('machine_info', {}),
                'commit_info': data.get('commit_info', {})
            }
            
            for benchmark in data.get('benchmarks', []):
                bench_data = {
                    'name': benchmark.get('name', 'unknown'),
                    'mean_time_ms': benchmark.get('stats', {}).get('mean', 0) * 1000,
                    'p95_time_ms': benchmark.get('stats', {}).get('p95', 0) * 1000,
                    'min_time_ms': benchmark.get('stats', {}).get('min', 0) * 1000,
                    'max_time_ms': benchmark.get('stats', {}).get('max', 0) * 1000,
                    'iterations': benchmark.get('stats', {}).get('rounds', 0)
                }
                performance_data['benchmarks'].append(bench_data)
            
            return performance_data
            
        except (json.JSONDecodeError, IOError) as e:
            return {
                'status': 'parse_error',
                'error': str(e),
                'benchmarks': []
            }
    
    def aggregate_results(self, unit_results: List[Path], integration_results: Optional[Path],
                         e2e_results: Optional[Path], benchmark_results: Optional[Path]):
        """Aggregate all test results."""
        
        # Process unit test results (multiple Python versions)
        unit_suite_data = {
            'name': 'Unit Tests',
            'status': 'completed',
            'tests': 0,
            'failures': 0,
            'errors': 0,
            'skipped': 0,
            'time': 0.0,
            'python_versions': []
        }
        
        for unit_file in unit_results:
            if unit_file.exists():
                suite_data = self.parse_junit_xml(unit_file, f"Unit Tests ({unit_file.stem})")
                unit_suite_data['tests'] += suite_data['tests']
                unit_suite_data['failures'] += suite_data['failures']
                unit_suite_data['errors'] += suite_data['errors']
                unit_suite_data['skipped'] += suite_data['skipped']
                unit_suite_data['time'] += suite_data['time']
                unit_suite_data['python_versions'].append(suite_data)
        
        self.summary_data['suites']['unit'] = unit_suite_data
        
        # Process integration test results
        if integration_results and integration_results.exists():
            integration_data = self.parse_junit_xml(integration_results, 'Integration Tests')
            self.summary_data['suites']['integration'] = integration_data
        
        # Process E2E test results
        if e2e_results and e2e_results.exists():
            e2e_data = self.parse_junit_xml(e2e_results, 'End-to-End Tests')
            self.summary_data['suites']['e2e'] = e2e_data
        
        # Process benchmark results
        if benchmark_results and benchmark_results.exists():
            perf_data = self.parse_benchmark_results(benchmark_results)
            self.summary_data['performance'] = perf_data
        
        # Calculate overall statistics
        self._calculate_overall_stats()
    
    def _calculate_overall_stats(self):
        """Calculate overall test statistics."""
        overall = self.summary_data['overall']
        
        for suite_name, suite_data in self.summary_data['suites'].items():
            if suite_data.get('status') == 'completed':
                overall['total_tests'] += suite_data.get('tests', 0)
                overall['failed_tests'] += suite_data.get('failures', 0)
                overall['error_tests'] += suite_data.get('errors', 0)
                overall['skipped_tests'] += suite_data.get('skipped', 0)
                overall['total_time'] += suite_data.get('time', 0.0)
        
        overall['passed_tests'] = (overall['total_tests'] - 
                                 overall['failed_tests'] - 
                                 overall['error_tests'] - 
                                 overall['skipped_tests'])
        
        if overall['total_tests'] > 0:
            overall['success_rate'] = overall['passed_tests'] / overall['total_tests']
        else:
            overall['success_rate'] = 0.0
    
    def generate_html_report(self, output_file: Path):
        """Generate HTML test summary report."""
        html_content = self._generate_html_content()
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"HTML test summary generated: {output_file}")
    
    def _generate_html_content(self) -> str:
        """Generate HTML content for the test report."""
        overall = self.summary_data['overall']
        
        # Determine overall status
        if overall['failed_tests'] > 0 or overall['error_tests'] > 0:
            status_class = 'failed'
            status_icon = '❌'
            status_text = 'FAILED'
        elif overall['total_tests'] == 0:
            status_class = 'unknown'
            status_icon = '❓'
            status_text = 'NO TESTS'
        else:
            status_class = 'passed'
            status_icon = '✅'
            status_text = 'PASSED'
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KuzuMemory Test Summary</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header .timestamp {{ opacity: 0.8; margin-top: 10px; }}
        .status-badge {{ display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-top: 15px; }}
        .status-badge.passed {{ background: #d4edda; color: #155724; }}
        .status-badge.failed {{ background: #f8d7da; color: #721c24; }}
        .status-badge.unknown {{ background: #fff3cd; color: #856404; }}
        .content {{ padding: 30px; }}
        .overview {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #495057; }}
        .metric-label {{ color: #6c757d; margin-top: 5px; }}
        .suite {{ margin-bottom: 30px; border: 1px solid #dee2e6; border-radius: 8px; }}
        .suite-header {{ background: #e9ecef; padding: 15px; border-radius: 8px 8px 0 0; font-weight: bold; }}
        .suite-content {{ padding: 20px; }}
        .test-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .test-stat {{ text-align: center; }}
        .test-stat-value {{ font-size: 1.5em; font-weight: bold; }}
        .test-stat.passed {{ color: #28a745; }}
        .test-stat.failed {{ color: #dc3545; }}
        .test-stat.skipped {{ color: #ffc107; }}
        .test-stat.error {{ color: #fd7e14; }}
        .performance {{ margin-top: 30px; }}
        .benchmark {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 6px; }}
        .benchmark-name {{ font-weight: bold; margin-bottom: 10px; }}
        .benchmark-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }}
        .benchmark-stat {{ text-align: center; }}
        .benchmark-stat-label {{ font-size: 0.8em; color: #6c757d; }}
        .benchmark-stat-value {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 KuzuMemory Test Summary</h1>
            <div class="timestamp">Generated: {self.summary_data['timestamp']}</div>
            <div class="status-badge {status_class}">{status_icon} {status_text}</div>
        </div>
        
        <div class="content">
            <div class="overview">
                <div class="metric">
                    <div class="metric-value">{overall['total_tests']}</div>
                    <div class="metric-label">Total Tests</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{overall['passed_tests']}</div>
                    <div class="metric-label">Passed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{overall['failed_tests']}</div>
                    <div class="metric-label">Failed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{overall['success_rate']:.1%}</div>
                    <div class="metric-label">Success Rate</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{overall['total_time']:.1f}s</div>
                    <div class="metric-label">Total Time</div>
                </div>
            </div>
        """
        
        # Add test suites
        for suite_name, suite_data in self.summary_data['suites'].items():
            if suite_data.get('status') == 'completed':
                html += f"""
            <div class="suite">
                <div class="suite-header">{suite_data['name']}</div>
                <div class="suite-content">
                    <div class="test-grid">
                        <div class="test-stat passed">
                            <div class="test-stat-value">{suite_data.get('tests', 0) - suite_data.get('failures', 0) - suite_data.get('errors', 0) - suite_data.get('skipped', 0)}</div>
                            <div>Passed</div>
                        </div>
                        <div class="test-stat failed">
                            <div class="test-stat-value">{suite_data.get('failures', 0)}</div>
                            <div>Failed</div>
                        </div>
                        <div class="test-stat error">
                            <div class="test-stat-value">{suite_data.get('errors', 0)}</div>
                            <div>Errors</div>
                        </div>
                        <div class="test-stat skipped">
                            <div class="test-stat-value">{suite_data.get('skipped', 0)}</div>
                            <div>Skipped</div>
                        </div>
                        <div class="test-stat">
                            <div class="test-stat-value">{suite_data.get('time', 0):.1f}s</div>
                            <div>Duration</div>
                        </div>
                    </div>
                </div>
            </div>
                """
        
        # Add performance results
        perf_data = self.summary_data.get('performance', {})
        if perf_data.get('status') == 'completed' and perf_data.get('benchmarks'):
            html += """
            <div class="performance">
                <h2>📊 Performance Benchmarks</h2>
            """
            
            for benchmark in perf_data['benchmarks']:
                html += f"""
                <div class="benchmark">
                    <div class="benchmark-name">{benchmark['name']}</div>
                    <div class="benchmark-stats">
                        <div class="benchmark-stat">
                            <div class="benchmark-stat-label">Mean</div>
                            <div class="benchmark-stat-value">{benchmark['mean_time_ms']:.2f}ms</div>
                        </div>
                        <div class="benchmark-stat">
                            <div class="benchmark-stat-label">P95</div>
                            <div class="benchmark-stat-value">{benchmark['p95_time_ms']:.2f}ms</div>
                        </div>
                        <div class="benchmark-stat">
                            <div class="benchmark-stat-label">Min</div>
                            <div class="benchmark-stat-value">{benchmark['min_time_ms']:.2f}ms</div>
                        </div>
                        <div class="benchmark-stat">
                            <div class="benchmark-stat-label">Max</div>
                            <div class="benchmark-stat-value">{benchmark['max_time_ms']:.2f}ms</div>
                        </div>
                        <div class="benchmark-stat">
                            <div class="benchmark-stat-label">Iterations</div>
                            <div class="benchmark-stat-value">{benchmark['iterations']}</div>
                        </div>
                    </div>
                </div>
                """
            
            html += "</div>"
        
        html += """
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def generate_markdown_report(self, output_file: Path):
        """Generate markdown test summary report."""
        overall = self.summary_data['overall']
        
        # Determine overall status
        if overall['failed_tests'] > 0 or overall['error_tests'] > 0:
            status_icon = '❌'
            status_text = 'FAILED'
        elif overall['total_tests'] == 0:
            status_icon = '❓'
            status_text = 'NO TESTS'
        else:
            status_icon = '✅'
            status_text = 'PASSED'
        
        markdown_lines = [
            "# 🧪 KuzuMemory Test Summary",
            "",
            f"**Status:** {status_icon} {status_text}",
            f"**Generated:** {self.summary_data['timestamp']}",
            "",
            "## Overview",
            "",
            f"- **Total Tests:** {overall['total_tests']}",
            f"- **Passed:** {overall['passed_tests']}",
            f"- **Failed:** {overall['failed_tests']}",
            f"- **Errors:** {overall['error_tests']}",
            f"- **Skipped:** {overall['skipped_tests']}",
            f"- **Success Rate:** {overall['success_rate']:.1%}",
            f"- **Total Time:** {overall['total_time']:.1f}s",
            "",
            "## Test Suites",
            ""
        ]
        
        # Add test suite details
        for suite_name, suite_data in self.summary_data['suites'].items():
            if suite_data.get('status') == 'completed':
                passed = suite_data.get('tests', 0) - suite_data.get('failures', 0) - suite_data.get('errors', 0) - suite_data.get('skipped', 0)
                
                markdown_lines.extend([
                    f"### {suite_data['name']}",
                    "",
                    f"- **Tests:** {suite_data.get('tests', 0)}",
                    f"- **Passed:** {passed}",
                    f"- **Failed:** {suite_data.get('failures', 0)}",
                    f"- **Errors:** {suite_data.get('errors', 0)}",
                    f"- **Skipped:** {suite_data.get('skipped', 0)}",
                    f"- **Duration:** {suite_data.get('time', 0):.1f}s",
                    ""
                ])
        
        # Add performance results
        perf_data = self.summary_data.get('performance', {})
        if perf_data.get('status') == 'completed' and perf_data.get('benchmarks'):
            markdown_lines.extend([
                "## 📊 Performance Benchmarks",
                ""
            ])
            
            for benchmark in perf_data['benchmarks']:
                markdown_lines.extend([
                    f"### {benchmark['name']}",
                    "",
                    f"- **Mean Time:** {benchmark['mean_time_ms']:.2f}ms",
                    f"- **P95 Time:** {benchmark['p95_time_ms']:.2f}ms",
                    f"- **Min Time:** {benchmark['min_time_ms']:.2f}ms",
                    f"- **Max Time:** {benchmark['max_time_ms']:.2f}ms",
                    f"- **Iterations:** {benchmark['iterations']}",
                    ""
                ])
        
        # Write markdown file
        with open(output_file, 'w') as f:
            f.write('\n'.join(markdown_lines))
        
        print(f"Markdown test summary generated: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate test summary reports")
    parser.add_argument("--unit-results", nargs='+', help="Unit test result XML files")
    parser.add_argument("--integration-results", type=Path, help="Integration test result XML file")
    parser.add_argument("--e2e-results", type=Path, help="E2E test result XML file")
    parser.add_argument("--benchmark-results", type=Path, help="Benchmark results JSON file")
    parser.add_argument("--output", type=Path, default=Path("test-summary.html"), help="Output HTML file")
    parser.add_argument("--markdown", type=Path, help="Output markdown file")
    
    args = parser.parse_args()
    
    generator = TestSummaryGenerator()
    
    # Parse unit test results (handle glob patterns)
    unit_results = []
    if args.unit_results:
        for pattern in args.unit_results:
            unit_results.extend([Path(f) for f in glob.glob(pattern)])
    
    # Aggregate all results
    generator.aggregate_results(
        unit_results=unit_results,
        integration_results=args.integration_results,
        e2e_results=args.e2e_results,
        benchmark_results=args.benchmark_results
    )
    
    # Generate reports
    generator.generate_html_report(args.output)
    
    if args.markdown:
        generator.generate_markdown_report(args.markdown)
    
    # Print summary to console
    overall = generator.summary_data['overall']
    print(f"\n📊 Test Summary:")
    print(f"   Total: {overall['total_tests']}")
    print(f"   Passed: {overall['passed_tests']}")
    print(f"   Failed: {overall['failed_tests']}")
    print(f"   Success Rate: {overall['success_rate']:.1%}")


if __name__ == "__main__":
    main()
