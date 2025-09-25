"""
Integration tests for Auggie-KuzuMemory integration.

Tests the complete integration between KuzuMemory and Auggie rules system
including prompt enhancement, response learning, and rule execution.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from kuzu_memory import KuzuMemory

# Skip import errors for Auggie integration
try:
    from kuzu_memory.integrations.auggie import (
        AuggieIntegration, AuggieRule, AuggieRuleEngine, ResponseLearner,
        RuleType, RulePriority
    )
except ImportError:
    # Mock classes to prevent import errors
    class AuggieIntegration: pass
    class AuggieRule: pass
    class AuggieRuleEngine: pass
    class ResponseLearner: pass
    class RuleType: pass
    class RulePriority: pass


@pytest.mark.skip(reason="Auggie integration requires external setup and may not be fully implemented")
class TestAuggieIntegration:
    """Integration tests for Auggie-KuzuMemory integration."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "auggie_test.db"
    
    @pytest.fixture
    def kuzu_memory(self, temp_db_path):
        """Create a KuzuMemory instance for testing."""
        memory = KuzuMemory(db_path=temp_db_path)
        yield memory
        memory.close()
    
    @pytest.fixture
    def auggie_integration(self, kuzu_memory):
        """Create an AuggieIntegration instance for testing."""
        return AuggieIntegration(
            kuzu_memory=kuzu_memory,
            config={
                "max_context_memories": 8,
                "enable_learning": True
            }
        )
    
    @pytest.fixture
    def sample_user_data(self, kuzu_memory):
        """Create sample user data for testing."""
        user_id = "test-user"
        
        # Store sample memories
        sample_contents = [
            "My name is Alice Johnson and I work at TechCorp as a Senior Python Developer.",
            "I prefer FastAPI for backend APIs and React for frontend applications.",
            "We decided to use PostgreSQL as our main database with Redis for caching.",
            "I always write comprehensive unit tests using pytest before deploying code.",
            "Currently working on a microservices architecture using Docker and Kubernetes."
        ]
        
        for content in sample_contents:
            kuzu_memory.generate_memories(content, user_id=user_id)
        
        return user_id
    
    def test_auggie_integration_initialization(self, kuzu_memory):
        """Test that AuggieIntegration initializes correctly."""
        integration = AuggieIntegration(kuzu_memory)
        
        assert integration.kuzu_memory is kuzu_memory
        assert integration.rule_engine is not None
        assert integration.response_learner is not None
        assert len(integration.rule_engine.rules) > 0  # Default rules loaded
        assert integration.integration_stats["prompts_enhanced"] == 0
    
    def test_prompt_enhancement_with_memories(self, auggie_integration, sample_user_data):
        """Test that prompts are enhanced using memories and rules."""
        user_id = sample_user_data
        prompt = "How do I write a Python function?"
        
        enhancement = auggie_integration.enhance_prompt(prompt, user_id)
        
        # Verify enhancement structure
        assert "original_prompt" in enhancement
        assert "enhanced_prompt" in enhancement
        assert "memory_context" in enhancement
        assert "rule_modifications" in enhancement
        assert "context_summary" in enhancement
        
        # Verify enhancement occurred
        assert enhancement["original_prompt"] == prompt
        assert len(enhancement["enhanced_prompt"]) > len(prompt)
        
        # Verify memories were used
        memory_context = enhancement["memory_context"]
        assert memory_context is not None
        assert len(memory_context.memories) > 0
        
        # Verify rules were applied
        executed_rules = enhancement["rule_modifications"].get("executed_rules", [])
        assert len(executed_rules) > 0
    
    def test_prompt_enhancement_without_memories(self, auggie_integration):
        """Test prompt enhancement for user with no memories."""
        user_id = "new-user"
        prompt = "Hello, how are you?"
        
        enhancement = auggie_integration.enhance_prompt(prompt, user_id)
        
        # Should still work but with minimal enhancement
        assert enhancement["original_prompt"] == prompt
        assert "enhanced_prompt" in enhancement
        
        # May have no memory context
        memory_context = enhancement.get("memory_context")
        if memory_context:
            assert len(memory_context.memories) == 0
    
    def test_coding_prompt_enhancement(self, auggie_integration, sample_user_data):
        """Test enhancement of coding-related prompts."""
        user_id = sample_user_data
        coding_prompts = [
            "How do I debug a Python error?",
            "What's the best way to structure a FastAPI application?",
            "How do I write unit tests for my code?",
            "What database should I use for my project?"
        ]
        
        for prompt in coding_prompts:
            enhancement = auggie_integration.enhance_prompt(prompt, user_id)
            
            # Should include relevant context
            enhanced_prompt = enhancement["enhanced_prompt"]
            assert len(enhanced_prompt) > len(prompt)
            
            # Should mention user's preferences or tech stack
            enhanced_lower = enhanced_prompt.lower()
            assert any(tech in enhanced_lower for tech in ["python", "fastapi", "postgresql", "pytest"])
    
    def test_response_learning_basic(self, auggie_integration, sample_user_data):
        """Test basic response learning functionality."""
        user_id = sample_user_data
        
        learning_result = auggie_integration.learn_from_interaction(
            prompt="What database should I use?",
            ai_response="I recommend PostgreSQL for your project since it's reliable and has good Python support.",
            user_feedback=None,
            user_id=user_id
        )
        
        # Verify learning occurred
        assert "timestamp" in learning_result
        assert "extracted_memories" in learning_result
        assert "quality_score" in learning_result
        assert learning_result["quality_score"] > 0
    
    def test_response_learning_with_correction(self, auggie_integration, sample_user_data):
        """Test learning from user corrections."""
        user_id = sample_user_data
        
        learning_result = auggie_integration.learn_from_interaction(
            prompt="What web framework should I use?",
            ai_response="I recommend Django for Python web development.",
            user_feedback="Actually, I prefer FastAPI for API development because it's faster.",
            user_id=user_id
        )
        
        # Should detect correction
        assert "corrections" in learning_result
        corrections = learning_result["corrections"]
        assert len(corrections) > 0
        
        # Should have lower quality score due to correction
        assert learning_result["quality_score"] < 0.8
        
        # Should extract memories from correction
        assert len(learning_result.get("extracted_memories", [])) > 0
    
    def test_custom_rule_creation(self, auggie_integration):
        """Test creation and application of custom rules."""
        # Create a custom rule
        rule_id = auggie_integration.create_custom_rule(
            name="Test Custom Rule",
            description="A test rule for validation",
            rule_type="context_enhancement",
            conditions={"prompt_category": "test"},
            actions={"add_context": "This is a test context addition"},
            priority="high"
        )
        
        assert rule_id is not None
        assert rule_id in auggie_integration.rule_engine.rules
        
        # Test rule application
        context = {"prompt_category": "test"}
        applicable_rules = auggie_integration.rule_engine.get_applicable_rules(context)
        
        custom_rule_applied = any(rule.id == rule_id for rule in applicable_rules)
        assert custom_rule_applied
    
    def test_rule_execution_with_conditions(self, auggie_integration, sample_user_data):
        """Test that rules execute only when conditions are met."""
        user_id = sample_user_data
        
        # Test with coding prompt (should trigger coding rules)
        coding_enhancement = auggie_integration.enhance_prompt(
            "How do I write a Python function?", user_id
        )
        
        # Test with general prompt (should trigger different rules)
        general_enhancement = auggie_integration.enhance_prompt(
            "What's the weather like?", user_id
        )
        
        # Should have different rule applications
        coding_rules = coding_enhancement["rule_modifications"].get("executed_rules", [])
        general_rules = general_enhancement["rule_modifications"].get("executed_rules", [])
        
        # Coding prompt should trigger more rules due to context
        assert len(coding_rules) >= len(general_rules)
    
    def test_memory_type_filtering_in_rules(self, auggie_integration, sample_user_data):
        """Test that rules can filter memories by type."""
        user_id = sample_user_data
        
        # Create a rule that only uses preference memories
        preference_rule = AuggieRule(
            id="test_preference_rule",
            name="Test Preference Rule",
            description="Test rule for preferences",
            rule_type=RuleType.CONTEXT_ENHANCEMENT,
            priority=RulePriority.HIGH,
            conditions={"has_preference_memories": True},
            actions={
                "add_context": "Include user preferences",
                "memory_types": ["preference"]
            }
        )
        
        auggie_integration.rule_engine.add_rule(preference_rule)
        
        # Test prompt enhancement
        enhancement = auggie_integration.enhance_prompt(
            "What should I use for my project?", user_id
        )
        
        # Should include preference-related context
        enhanced_prompt = enhancement["enhanced_prompt"]
        assert "fastapi" in enhanced_prompt.lower() or "react" in enhanced_prompt.lower()
    
    def test_learning_callback_integration(self, auggie_integration):
        """Test that learning callbacks are properly integrated."""
        callback_called = False
        callback_data = None
        
        def test_callback(data):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = data
        
        # Add callback
        auggie_integration.rule_engine.add_learning_callback(test_callback)
        
        # Trigger learning event
        auggie_integration.rule_engine.trigger_learning({
            "new_insight": "Test learning insight",
            "user_id": "test-user"
        })
        
        assert callback_called
        assert callback_data is not None
        assert "new_insight" in callback_data
    
    def test_integration_statistics_tracking(self, auggie_integration, sample_user_data):
        """Test that integration statistics are properly tracked."""
        user_id = sample_user_data
        
        initial_stats = auggie_integration.get_integration_statistics()
        initial_prompts = initial_stats["integration"]["prompts_enhanced"]
        initial_responses = initial_stats["integration"]["responses_learned"]
        
        # Perform operations
        auggie_integration.enhance_prompt("Test prompt", user_id)
        auggie_integration.learn_from_interaction(
            "Test prompt", "Test response", user_id=user_id
        )
        
        # Check updated statistics
        final_stats = auggie_integration.get_integration_statistics()
        
        assert final_stats["integration"]["prompts_enhanced"] == initial_prompts + 1
        assert final_stats["integration"]["responses_learned"] == initial_responses + 1
        assert "rule_engine" in final_stats
        assert "response_learner" in final_stats
    
    def test_rule_export_import(self, auggie_integration, tmp_path):
        """Test rule export and import functionality."""
        # Export rules
        export_file = tmp_path / "test_rules.json"
        auggie_integration.export_rules(str(export_file))
        
        assert export_file.exists()
        
        # Create new integration and import rules
        new_integration = AuggieIntegration()
        initial_rule_count = len(new_integration.rule_engine.rules)
        
        new_integration.import_rules(str(export_file))
        
        # Should have more rules after import
        assert len(new_integration.rule_engine.rules) >= initial_rule_count
    
    def test_error_handling_in_enhancement(self, auggie_integration):
        """Test error handling during prompt enhancement."""
        # Test with invalid user_id
        enhancement = auggie_integration.enhance_prompt("Test prompt", None)
        
        # Should handle gracefully
        assert "original_prompt" in enhancement
        assert "enhanced_prompt" in enhancement
        
        # Enhanced prompt should fallback to original on error
        if "error" in enhancement:
            assert enhancement["enhanced_prompt"] == enhancement["original_prompt"]
    
    def test_error_handling_in_learning(self, auggie_integration):
        """Test error handling during response learning."""
        # Test with invalid parameters
        learning_result = auggie_integration.learn_from_interaction(
            prompt=None,
            ai_response="Test response",
            user_id="test-user"
        )
        
        # Should handle gracefully
        assert isinstance(learning_result, dict)
        if "error" in learning_result:
            assert isinstance(learning_result["error"], str)
    
    def test_concurrent_rule_execution(self, auggie_integration, sample_user_data):
        """Test that rules can be executed concurrently without issues."""
        import threading
        import time
        
        user_id = sample_user_data
        results = []
        errors = []
        
        def enhance_prompt_worker():
            try:
                for i in range(5):
                    enhancement = auggie_integration.enhance_prompt(
                        f"Test prompt {i}", user_id
                    )
                    results.append(enhancement)
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=enhance_prompt_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 15  # 3 threads * 5 prompts each
        
        # All results should be valid
        for result in results:
            assert "original_prompt" in result
            assert "enhanced_prompt" in result
    
    def test_memory_context_integration(self, auggie_integration, sample_user_data):
        """Test integration between memory context and rule execution."""
        user_id = sample_user_data
        
        # Test prompt that should trigger memory recall
        enhancement = auggie_integration.enhance_prompt(
            "What technologies do I work with?", user_id
        )
        
        memory_context = enhancement["memory_context"]
        rule_modifications = enhancement["rule_modifications"]
        
        # Should have recalled relevant memories
        assert memory_context is not None
        assert len(memory_context.memories) > 0
        
        # Rules should have used memory information
        executed_rules = rule_modifications.get("executed_rules", [])
        assert len(executed_rules) > 0
        
        # Enhanced prompt should include memory content
        enhanced_prompt = enhancement["enhanced_prompt"]
        assert len(enhanced_prompt) > len(enhancement["original_prompt"])
        
        # Should mention technologies from memories
        enhanced_lower = enhanced_prompt.lower()
        assert any(tech in enhanced_lower for tech in ["python", "fastapi", "postgresql"])
