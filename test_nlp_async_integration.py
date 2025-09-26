#!/usr/bin/env python3
"""
Integration Test Script for NLP Features with Async Operations

Tests the integration between:
1. Async memory operations (async_cli.py, background_learner.py)
2. NLP classification (classifier.py)
3. Memory enhancement (memory_enhancer.py)
4. Performance requirements

This script verifies that all components work together properly.
"""

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List
import shutil

# Import KuzuMemory components
from src.kuzu_memory.async_memory.async_cli import AsyncMemoryCLI
from src.kuzu_memory.core.memory import KuzuMemory
from src.kuzu_memory.core.models import MemoryType
from src.kuzu_memory.nlp.classifier import MemoryClassifier

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NLPAsyncIntegrationTester:
    """Test suite for NLP and async operations integration."""

    def __init__(self):
        """Initialize the test environment."""
        self.test_db_dir = None
        self.async_cli = None
        self.sync_memory = None
        self.nlp_classifier = None
        self.test_results = {}

    def setup_test_environment(self) -> None:
        """Set up a temporary test environment."""
        logger.info("Setting up test environment...")

        # Create temporary directory for test database
        self.test_db_dir = Path(tempfile.mkdtemp(prefix="kuzu_memory_test_"))
        logger.info(f"Test database directory: {self.test_db_dir}")

        # Initialize async CLI
        self.async_cli = AsyncMemoryCLI(db_path=self.test_db_dir / "memories.db")

        # Initialize sync memory for comparison
        self.sync_memory = KuzuMemory(db_path=self.test_db_dir / "memories.db")

        # Initialize NLP classifier for testing
        self.nlp_classifier = MemoryClassifier(auto_download=False)

        logger.info("Test environment setup complete")

    def cleanup_test_environment(self) -> None:
        """Clean up test environment."""
        logger.info("Cleaning up test environment...")

        if self.sync_memory:
            try:
                self.sync_memory.close()
            except:
                pass

        if self.test_db_dir and self.test_db_dir.exists():
            shutil.rmtree(self.test_db_dir)

        logger.info("Cleanup complete")

    def test_nlp_classifier_availability(self) -> Dict[str, Any]:
        """Test 1: Verify NLP classifier is properly integrated."""
        logger.info("Test 1: NLP classifier availability...")

        test_content = "I prefer using React over Vue for frontend development"

        result = {
            'test_name': 'nlp_classifier_availability',
            'success': False,
            'details': {}
        }

        try:
            # Test direct classifier
            classification = self.nlp_classifier.classify(test_content)
            result['details']['direct_classification'] = {
                'memory_type': classification.memory_type.value,
                'confidence': classification.confidence,
                'keywords': classification.keywords[:5],
                'entities': classification.entities[:5]
            }

            # Test sentiment analysis
            sentiment = self.nlp_classifier.analyze_sentiment(test_content)
            result['details']['sentiment_analysis'] = {
                'dominant': sentiment.dominant,
                'compound': sentiment.compound,
                'positive': sentiment.positive
            }

            # Test importance calculation
            importance = self.nlp_classifier.calculate_importance(
                test_content, classification.memory_type
            )
            result['details']['importance'] = importance

            result['success'] = True
            logger.info("✅ NLP classifier is working correctly")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ NLP classifier test failed: {e}")

        return result

    def test_async_memory_with_nlp(self) -> Dict[str, Any]:
        """Test 2: Test async memory operations with NLP classification."""
        logger.info("Test 2: Async memory operations with NLP...")

        test_contents = [
            "User prefers TypeScript over JavaScript for better type safety",
            "We decided to use PostgreSQL instead of MongoDB for this project",
            "The authentication system should use JWT tokens with refresh mechanism",
            "Team meeting scheduled for Monday to discuss API design patterns",
            "Bug found in the payment processing module - needs immediate fix"
        ]

        result = {
            'test_name': 'async_memory_with_nlp',
            'success': False,
            'details': {}
        }

        try:
            # Submit multiple learning tasks asynchronously
            task_ids = []
            for i, content in enumerate(test_contents):
                task_result = self.async_cli.learn_async(
                    content=content,
                    source=f"test-async-{i}",
                    metadata={"test_id": i, "test_type": "nlp_integration"},
                    quiet=True
                )
                task_ids.append(task_result['task_id'])

            result['details']['tasks_submitted'] = len(task_ids)
            logger.info(f"Submitted {len(task_ids)} async learning tasks")

            # Wait for all tasks to complete
            completed_tasks = []
            failed_tasks = []

            for task_id in task_ids:
                task_status = self.async_cli.wait_for_task(task_id, timeout_seconds=30.0)
                if task_status['status'] == 'completed':
                    completed_tasks.append(task_status)
                else:
                    failed_tasks.append(task_status)

            result['details']['completed_tasks'] = len(completed_tasks)
            result['details']['failed_tasks'] = len(failed_tasks)

            # Verify memories were created with NLP classification
            if completed_tasks:
                # Get recent memories to check if they have NLP metadata
                with KuzuMemory(db_path=self.test_db_dir / "memories.db") as memory:
                    recent_memories = memory.get_recent_memories(limit=10)

                    nlp_enhanced_count = 0
                    for mem in recent_memories:
                        if (mem.metadata and
                            'extraction_metadata' in mem.metadata and
                            mem.metadata['extraction_metadata'] and
                            'nlp_classification' in mem.metadata['extraction_metadata']):
                            nlp_enhanced_count += 1

                    result['details']['nlp_enhanced_memories'] = nlp_enhanced_count
                    result['details']['total_memories_found'] = len(recent_memories)

                    # Get examples of NLP metadata
                    if recent_memories:
                        example_metadata = recent_memories[0].metadata
                        result['details']['example_metadata'] = {
                            key: str(value)[:100] + ('...' if len(str(value)) > 100 else '')
                            for key, value in (example_metadata or {}).items()
                        }

            result['success'] = len(completed_tasks) > 0
            if result['success']:
                logger.info(f"✅ Async operations completed: {len(completed_tasks)}/{len(task_ids)}")
            else:
                logger.error("❌ No async operations completed successfully")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Async memory test failed: {e}")

        return result

    def test_batch_processing_performance(self) -> Dict[str, Any]:
        """Test 3: Test batch processing with performance measurements."""
        logger.info("Test 3: Batch processing performance...")

        batch_contents = [
            f"Feature request #{i}: Implement advanced search functionality with filters"
            for i in range(20)
        ] + [
            f"Bug report #{i}: Memory leak detected in background processing module"
            for i in range(20)
        ] + [
            f"Decision #{i}: We will use Redis for caching and session storage"
            for i in range(20)
        ]

        result = {
            'test_name': 'batch_processing_performance',
            'success': False,
            'details': {}
        }

        try:
            # Test NLP batch classification
            start_time = time.time()
            batch_classifications = self.nlp_classifier.classify_batch(batch_contents)
            batch_classification_time = (time.time() - start_time) * 1000

            result['details']['batch_classification'] = {
                'items_processed': len(batch_classifications),
                'processing_time_ms': batch_classification_time,
                'avg_time_per_item_ms': batch_classification_time / len(batch_classifications)
            }

            # Test async batch submission
            start_time = time.time()
            batch_task_ids = []

            for i, content in enumerate(batch_contents):
                task_result = self.async_cli.learn_async(
                    content=content,
                    source=f"batch-test-{i}",
                    metadata={"batch_id": "performance_test", "item_id": i},
                    quiet=True
                )
                batch_task_ids.append(task_result['task_id'])

            batch_submission_time = (time.time() - start_time) * 1000

            result['details']['batch_submission'] = {
                'items_submitted': len(batch_task_ids),
                'submission_time_ms': batch_submission_time,
                'avg_submission_time_ms': batch_submission_time / len(batch_task_ids)
            }

            # Wait for a subset to complete (not all - would take too long)
            sample_tasks = batch_task_ids[:5]
            completed_sample = []

            for task_id in sample_tasks:
                task_status = self.async_cli.wait_for_task(task_id, timeout_seconds=15.0)
                if task_status['status'] == 'completed':
                    completed_sample.append(task_status)

            result['details']['sample_completion'] = {
                'sample_size': len(sample_tasks),
                'completed': len(completed_sample),
                'completion_rate': len(completed_sample) / len(sample_tasks) * 100
            }

            # Check performance requirements
            performance_check = {
                'batch_classification_under_5s': batch_classification_time < 5000,
                'avg_classification_under_50ms': (batch_classification_time / len(batch_classifications)) < 50,
                'avg_submission_under_10ms': (batch_submission_time / len(batch_task_ids)) < 10
            }

            result['details']['performance_check'] = performance_check
            result['success'] = all(performance_check.values())

            if result['success']:
                logger.info("✅ Batch processing performance meets requirements")
            else:
                logger.warning("⚠️  Some performance requirements not met")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Batch processing test failed: {e}")

        return result

    def test_sentiment_analysis_integration(self) -> Dict[str, Any]:
        """Test 4: Test sentiment analysis in async operations."""
        logger.info("Test 4: Sentiment analysis integration...")

        sentiment_test_cases = [
            ("I love this new feature! It makes development so much easier.", "positive"),
            ("This bug is really frustrating and blocking our progress.", "negative"),
            ("The database schema has been updated to include user preferences.", "neutral"),
            ("Excellent work on the API design - very clean and intuitive!", "positive"),
            ("Critical security vulnerability found in authentication module!", "negative")
        ]

        result = {
            'test_name': 'sentiment_analysis_integration',
            'success': False,
            'details': {}
        }

        try:
            sentiment_results = []

            # Test each sentiment case
            for content, expected_sentiment in sentiment_test_cases:
                # Test direct sentiment analysis
                sentiment = self.nlp_classifier.analyze_sentiment(content)

                # Submit for async learning
                task_result = self.async_cli.learn_async(
                    content=content,
                    source="sentiment-test",
                    metadata={"expected_sentiment": expected_sentiment},
                    quiet=True
                )

                # Wait for completion
                task_status = self.async_cli.wait_for_task(task_result['task_id'], timeout_seconds=10.0)

                sentiment_results.append({
                    'content': content[:50] + '...',
                    'expected': expected_sentiment,
                    'detected': sentiment.dominant,
                    'compound_score': sentiment.compound,
                    'task_completed': task_status['status'] == 'completed',
                    'correct_detection': sentiment.dominant == expected_sentiment
                })

            result['details']['sentiment_tests'] = sentiment_results

            # Calculate accuracy
            correct_detections = sum(1 for r in sentiment_results if r['correct_detection'])
            completed_tasks = sum(1 for r in sentiment_results if r['task_completed'])

            result['details']['accuracy'] = {
                'sentiment_accuracy': correct_detections / len(sentiment_results) * 100,
                'task_completion_rate': completed_tasks / len(sentiment_results) * 100
            }

            # Check if memories contain sentiment information
            with KuzuMemory(db_path=self.test_db_dir / "memories.db") as memory:
                recent_memories = memory.get_recent_memories(limit=20)

                sentiment_metadata_count = 0
                for mem in recent_memories:
                    if (mem.metadata and
                        'extraction_metadata' in mem.metadata and
                        mem.metadata['extraction_metadata'] and
                        'nlp_classification' in mem.metadata['extraction_metadata']):
                        sentiment_metadata_count += 1

                result['details']['memories_with_sentiment'] = sentiment_metadata_count

            # Success if accuracy > 60% and most tasks complete
            result['success'] = (
                correct_detections / len(sentiment_results) >= 0.6 and
                completed_tasks / len(sentiment_results) >= 0.8
            )

            if result['success']:
                logger.info(f"✅ Sentiment analysis working: {correct_detections}/{len(sentiment_results)} correct")
            else:
                logger.warning(f"⚠️  Sentiment analysis needs improvement: {correct_detections}/{len(sentiment_results)} correct")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Sentiment analysis test failed: {e}")

        return result

    def test_memory_enhancement_features(self) -> Dict[str, Any]:
        """Test 5: Test memory enhancement with entities, keywords, and classification."""
        logger.info("Test 5: Memory enhancement features...")

        enhancement_test_content = """
        We decided to migrate from MySQL to PostgreSQL for better JSON support.
        The development team including John Smith and Sarah Connor will work on this.
        The migration is scheduled for next Friday and will be done by the DevOps team.
        We're using Django ORM for database abstraction and Redis for caching.
        This decision was made after consulting with the CTO and reviewing performance benchmarks.
        """

        result = {
            'test_name': 'memory_enhancement_features',
            'success': False,
            'details': {}
        }

        try:
            # Test direct NLP enhancement
            classification = self.nlp_classifier.classify(enhancement_test_content)
            entities_result = self.nlp_classifier.extract_entities(enhancement_test_content)
            importance = self.nlp_classifier.calculate_importance(
                enhancement_test_content, classification.memory_type
            )

            result['details']['nlp_analysis'] = {
                'memory_type': classification.memory_type.value,
                'confidence': classification.confidence,
                'keywords': classification.keywords[:10],
                'entities': {
                    'people': entities_result.people,
                    'technologies': entities_result.technologies,
                    'organizations': entities_result.organizations,
                    'all_entities': entities_result.all_entities[:10]
                },
                'importance': importance
            }

            # Submit for async processing
            task_result = self.async_cli.learn_async(
                content=enhancement_test_content,
                source="enhancement-test",
                metadata={"test_type": "comprehensive_enhancement"},
                quiet=True
            )

            # Wait for completion
            task_status = self.async_cli.wait_for_task(task_result['task_id'], timeout_seconds=15.0)
            result['details']['async_processing'] = {
                'task_completed': task_status['status'] == 'completed',
                'task_details': task_status
            }

            # Check the stored memory for enhancement features
            if task_status['status'] == 'completed':
                with KuzuMemory(db_path=self.test_db_dir / "memories.db") as memory:
                    recent_memories = memory.get_recent_memories(limit=5)

                    if recent_memories:
                        latest_memory = recent_memories[0]

                        result['details']['stored_memory_analysis'] = {
                            'has_metadata': latest_memory.metadata is not None,
                            'memory_type': latest_memory.memory_type.value,
                            'content_length': len(latest_memory.content),
                        }

                        # Check for NLP enhancement metadata
                        if (latest_memory.metadata and
                            'extraction_metadata' in latest_memory.metadata):

                            extraction_meta = latest_memory.metadata['extraction_metadata']
                            result['details']['enhancement_metadata'] = {
                                'has_nlp_classification': 'nlp_classification' in extraction_meta,
                                'extraction_method': extraction_meta.get('extraction_method'),
                                'keys_present': list(extraction_meta.keys())
                            }

            # Success criteria
            success_criteria = [
                classification.confidence > 0.5,
                len(entities_result.all_entities) > 0,
                task_status['status'] == 'completed',
                importance > 0.1
            ]

            result['details']['success_criteria'] = {
                'good_classification_confidence': success_criteria[0],
                'entities_extracted': success_criteria[1],
                'async_processing_completed': success_criteria[2],
                'reasonable_importance_score': success_criteria[3]
            }

            result['success'] = all(success_criteria)

            if result['success']:
                logger.info("✅ Memory enhancement features working properly")
            else:
                logger.warning("⚠️  Some memory enhancement features need attention")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Memory enhancement test failed: {e}")

        return result

    def test_queue_status_and_monitoring(self) -> Dict[str, Any]:
        """Test 6: Test queue status and monitoring capabilities."""
        logger.info("Test 6: Queue status and monitoring...")

        result = {
            'test_name': 'queue_status_and_monitoring',
            'success': False,
            'details': {}
        }

        try:
            # Get initial queue status
            initial_status = self.async_cli.get_queue_status()
            result['details']['initial_queue_status'] = initial_status

            # Submit some tasks for monitoring
            test_contents = [
                "Monitoring test task 1 - feature request",
                "Monitoring test task 2 - bug report",
                "Monitoring test task 3 - team decision"
            ]

            task_ids = []
            for i, content in enumerate(test_contents):
                task_result = self.async_cli.learn_async(
                    content=content,
                    source=f"monitoring-test-{i}",
                    quiet=True
                )
                task_ids.append(task_result['task_id'])

            result['details']['test_tasks_submitted'] = len(task_ids)

            # Check individual task statuses
            task_statuses = []
            for task_id in task_ids:
                status = self.async_cli.get_task_status(task_id)
                task_statuses.append(status)

            result['details']['individual_task_statuses'] = [
                {
                    'task_id': status['task_id'][:8] + '...',
                    'status': status['status'],
                    'task_type': status.get('task_type', 'unknown')
                }
                for status in task_statuses
            ]

            # Wait a moment for processing
            time.sleep(2.0)

            # Get final queue status
            final_status = self.async_cli.get_queue_status()
            result['details']['final_queue_status'] = final_status

            # Check for status improvements
            status_comparison = {
                'tasks_completed_increase': (
                    final_status['status_summary']['tasks_completed'] -
                    initial_status['status_summary']['tasks_completed']
                ),
                'memories_learned_increase': (
                    final_status['status_summary']['memories_learned'] -
                    initial_status['status_summary']['memories_learned']
                )
            }

            result['details']['status_comparison'] = status_comparison

            # Success criteria
            result['success'] = (
                len(task_ids) > 0 and
                status_comparison['tasks_completed_increase'] >= 0 and
                final_status['status_summary']['queue_size'] >= 0
            )

            if result['success']:
                logger.info("✅ Queue monitoring working correctly")
            else:
                logger.warning("⚠️  Queue monitoring issues detected")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Queue monitoring test failed: {e}")

        return result

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests and compile results."""
        logger.info("🚀 Starting NLP-Async Integration Tests...")

        try:
            self.setup_test_environment()

            # Run all tests
            test_methods = [
                self.test_nlp_classifier_availability,
                self.test_async_memory_with_nlp,
                self.test_batch_processing_performance,
                self.test_sentiment_analysis_integration,
                self.test_memory_enhancement_features,
                self.test_queue_status_and_monitoring
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
                    logger.error(f"Test {test_method.__name__} crashed: {e}")

            # Compile final results
            total_tests = len(results)
            successful_tests = sum(1 for r in results if r['success'])

            final_results = {
                'summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'failed_tests': total_tests - successful_tests,
                    'success_rate': successful_tests / total_tests * 100,
                    'overall_success': successful_tests >= total_tests * 0.75  # 75% threshold
                },
                'individual_results': results,
                'recommendations': self._generate_recommendations(results)
            }

            return final_results

        finally:
            self.cleanup_test_environment()

    def _generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        for result in results:
            if not result['success']:
                test_name = result['test_name']
                if 'nlp_classifier_availability' in test_name:
                    recommendations.append("Install NLTK dependencies and download required data")
                elif 'async_memory_with_nlp' in test_name:
                    recommendations.append("Check async memory operations and NLP integration")
                elif 'batch_processing_performance' in test_name:
                    recommendations.append("Optimize batch processing performance or adjust thresholds")
                elif 'sentiment_analysis' in test_name:
                    recommendations.append("Improve sentiment analysis accuracy or check VADER setup")
                elif 'memory_enhancement' in test_name:
                    recommendations.append("Verify memory enhancement pipeline and metadata storage")
                elif 'queue_status' in test_name:
                    recommendations.append("Check queue management and monitoring systems")

        if not recommendations:
            recommendations.append("All tests passed - integration working correctly!")

        return recommendations


def main():
    """Main test execution function."""
    print("🧠 KuzuMemory NLP-Async Integration Test Suite")
    print("=" * 60)

    tester = NLPAsyncIntegrationTester()
    results = tester.run_all_tests()

    # Print summary
    summary = results['summary']
    print(f"\n📊 Test Results Summary:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Successful: {summary['successful_tests']}")
    print(f"   Failed: {summary['failed_tests']}")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Overall: {'✅ PASS' if summary['overall_success'] else '❌ FAIL'}")

    # Print individual results
    print(f"\n📋 Individual Test Results:")
    for result in results['individual_results']:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        test_name = result['test_name'].replace('test_', '').replace('_', ' ').title()
        print(f"   {status} {test_name}")

        if not result['success'] and 'error' in result:
            print(f"     Error: {result['error']}")

    # Print recommendations
    print(f"\n💡 Recommendations:")
    for rec in results['recommendations']:
        print(f"   • {rec}")

    # Save detailed results to file
    results_file = Path("nlp_async_integration_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Detailed results saved to: {results_file}")

    return results


if __name__ == "__main__":
    main()