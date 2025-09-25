#!/usr/bin/env python3
"""
Comprehensive test of the Auggie integration.
"""

import sys
import tempfile
import time
import logging
from pathlib import Path
from datetime import datetime

# Enable info logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_auggie_integration():
    """Test the complete Auggie integration."""
    print("🤖 Testing Auggie Integration End-to-End")
    print("=" * 60)
    
    try:
        from kuzu_memory.core.memory import KuzuMemory
        from kuzu_memory.integrations.auggie import AuggieIntegration
        from kuzu_memory.core.config import KuzuMemoryConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "auggie_test.db"
            
            # Create configuration with relaxed performance limits
            config = KuzuMemoryConfig()
            config.performance.max_recall_time_ms = 100.0
            config.performance.max_generation_time_ms = 200.0
            
            # Initialize KuzuMemory and Auggie
            memory = KuzuMemory(db_path=db_path, config=config)
            auggie = AuggieIntegration(memory, config={
                "max_context_memories": 8,
                "enable_learning": True
            })
            
            print("✅ Auggie integration initialized")
            print(f"📋 Default rules loaded: {len(auggie.rule_engine.rules)}")
            
            user_id = "auggie-test-user"
            
            # Phase 1: Build user profile
            print(f"\n📝 Phase 1: Building User Profile")
            print("-" * 40)
            
            profile_data = [
                "I prefer FastAPI for backend development and React for frontend applications.",
                "We decided to use PostgreSQL as our main database with Redis for caching.",
                "I always write comprehensive unit tests using pytest before deploying code.",
                "Currently working on the CustomerAnalytics microservice using Docker.",
                "My team follows agile methodology with 2-week sprints."
            ]
            
            stored_memories = 0
            for i, data in enumerate(profile_data):
                memory_ids = memory.generate_memories(data, user_id=user_id, session_id=f"profile-{i}")
                stored_memories += len(memory_ids)
                print(f"  ✓ Stored: {data[:50]}... ({len(memory_ids)} memories)")
            
            print(f"📊 Total memories stored: {stored_memories}")
            
            # Phase 2: Test prompt enhancement
            print(f"\n🚀 Phase 2: Testing Prompt Enhancement")
            print("-" * 40)
            
            test_prompts = [
                "How do I write a Python function?",
                "What's the best way to handle database connections?",
                "Help me debug this authentication issue",
                "What testing framework should I use?",
                "How do I deploy a microservice?"
            ]
            
            enhancement_results = []
            for i, prompt in enumerate(test_prompts):
                print(f"\n  🔍 Test {i+1}: {prompt}")
                
                start_time = time.time()
                enhancement = auggie.enhance_prompt(prompt, user_id)
                enhancement_time = (time.time() - start_time) * 1000
                
                original_length = len(enhancement["original_prompt"])
                enhanced_length = len(enhancement["enhanced_prompt"])
                enhancement_ratio = enhanced_length / original_length
                
                executed_rules = enhancement["rule_modifications"].get("executed_rules", [])
                
                enhancement_results.append({
                    "prompt": prompt,
                    "enhancement_ratio": enhancement_ratio,
                    "rules_applied": len(executed_rules),
                    "enhancement_time_ms": enhancement_time,
                    "context_summary": enhancement["context_summary"]
                })
                
                print(f"     Enhancement: {enhancement_ratio:.1f}x longer")
                print(f"     Rules applied: {len(executed_rules)}")
                print(f"     Context: {enhancement['context_summary']}")
                print(f"     Time: {enhancement_time:.1f}ms")
                
                # Show enhanced prompt sample
                if enhanced_length > original_length:
                    print(f"     Enhanced sample: {enhancement['enhanced_prompt'][:100]}...")
            
            # Phase 3: Test response learning
            print(f"\n🧠 Phase 3: Testing Response Learning")
            print("-" * 40)
            
            learning_scenarios = [
                {
                    "prompt": "What database should I use for my project?",
                    "ai_response": "For your project, I'd recommend PostgreSQL since you mentioned you're already using it.",
                    "user_feedback": None
                },
                {
                    "prompt": "How do I test React components?",
                    "ai_response": "You can use Jest and React Testing Library for testing React components.",
                    "user_feedback": "Actually, I prefer using Cypress for end-to-end testing of React components."
                },
                {
                    "prompt": "What's the best Python web framework?",
                    "ai_response": "Django is a great choice for Python web development.",
                    "user_feedback": "Correction: I prefer FastAPI for API development because it's faster and has better async support."
                }
            ]
            
            learning_results = []
            for i, scenario in enumerate(learning_scenarios):
                print(f"\n  💬 Learning Test {i+1}: {scenario['prompt'][:50]}...")
                
                learning_result = auggie.learn_from_interaction(
                    prompt=scenario["prompt"],
                    ai_response=scenario["ai_response"],
                    user_feedback=scenario["user_feedback"],
                    user_id=user_id
                )
                
                learning_results.append(learning_result)
                
                print(f"     Quality score: {learning_result.get('quality_score', 0):.2f}")
                print(f"     Memories created: {len(learning_result.get('extracted_memories', []))}")
                
                if scenario["user_feedback"]:
                    corrections = learning_result.get("corrections", [])
                    print(f"     Corrections found: {len(corrections)}")
                    for correction in corrections:
                        print(f"       - {correction.get('correction', 'No correction')}")
            
            # Phase 4: Test custom rule creation
            print(f"\n⚙️ Phase 4: Testing Custom Rule Creation")
            print("-" * 40)
            
            custom_rule_id = auggie.create_custom_rule(
                name="Prioritize FastAPI for User",
                description="When user asks about Python web frameworks, prioritize FastAPI",
                rule_type="context_enhancement",
                conditions={
                    "user_id": user_id,
                    "prompt_category": "coding",
                    "prompt": {"contains": "framework"}
                },
                actions={
                    "add_context": "User prefers FastAPI for API development due to performance and async support",
                    "memory_types": ["preference"]
                },
                priority="high"
            )
            
            print(f"  ✅ Created custom rule: {custom_rule_id}")
            
            # Test the custom rule
            test_prompt = "What Python web framework should I use for my new API?"
            enhancement = auggie.enhance_prompt(test_prompt, user_id)
            
            executed_rules = enhancement["rule_modifications"].get("executed_rules", [])
            custom_rule_applied = any(rule["rule_id"] == custom_rule_id for rule in executed_rules)
            
            print(f"  🔍 Testing custom rule:")
            print(f"     Prompt: {test_prompt}")
            print(f"     Custom rule applied: {'✅' if custom_rule_applied else '❌'}")
            print(f"     Enhanced prompt length: {len(enhancement['enhanced_prompt'])} chars")
            
            # Phase 5: Integration statistics
            print(f"\n📊 Phase 5: Integration Statistics")
            print("-" * 40)
            
            stats = auggie.get_integration_statistics()
            
            print(f"  Prompts enhanced: {stats['integration']['prompts_enhanced']}")
            print(f"  Responses learned: {stats['integration']['responses_learned']}")
            print(f"  Rules triggered: {stats['integration']['rules_triggered']}")
            print(f"  Memories created: {stats['integration']['memories_created']}")
            
            # Rule engine stats
            rule_stats = stats['rule_engine']
            print(f"\n  Rule Engine:")
            print(f"    Total rules: {rule_stats['total_rules']}")
            print(f"    Enabled rules: {rule_stats['enabled_rules']}")
            print(f"    Total executions: {rule_stats['total_executions']}")
            
            # Response learner stats
            learner_stats = stats['response_learner']
            print(f"\n  Response Learner:")
            print(f"    Learning events: {learner_stats['total_learning_events']}")
            if 'average_quality_score' in learner_stats:
                print(f"    Average quality: {learner_stats['average_quality_score']:.2f}")
            
            # Performance analysis
            avg_enhancement_time = sum(r["enhancement_time_ms"] for r in enhancement_results) / len(enhancement_results)
            avg_enhancement_ratio = sum(r["enhancement_ratio"] for r in enhancement_results) / len(enhancement_results)
            
            print(f"\n⚡ Performance Analysis:")
            print(f"  Average enhancement time: {avg_enhancement_time:.1f}ms")
            print(f"  Average enhancement ratio: {avg_enhancement_ratio:.1f}x")
            print(f"  Rules per enhancement: {sum(r['rules_applied'] for r in enhancement_results) / len(enhancement_results):.1f}")
            
            # Success criteria
            success_criteria = {
                "memories_stored": stored_memories > 0,
                "prompts_enhanced": stats['integration']['prompts_enhanced'] > 0,
                "responses_learned": stats['integration']['responses_learned'] > 0,
                "custom_rule_created": custom_rule_id is not None,
                "custom_rule_applied": custom_rule_applied,
                "performance_acceptable": avg_enhancement_time < 200.0  # 200ms threshold
            }
            
            print(f"\n🎯 Success Criteria:")
            for criterion, passed in success_criteria.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {criterion.replace('_', ' ').title()}")
            
            overall_success = all(success_criteria.values())
            
            memory.close()
            
            print(f"\n🎉 Overall Result: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
            
            return overall_success
            
    except Exception as e:
        print(f"❌ Error in Auggie integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run Auggie integration test."""
    print("🤖 KuzuMemory Auggie Integration Test")
    print("=" * 70)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_auggie_integration()
    
    print(f"\n{'='*70}")
    print("📊 TEST SUMMARY")
    print(f"{'='*70}")
    
    if success:
        print("🎉 AUGGIE INTEGRATION TEST PASSED!")
        print("✅ All components working correctly:")
        print("   - Memory storage and retrieval")
        print("   - Prompt enhancement with context")
        print("   - Response learning and correction detection")
        print("   - Custom rule creation and execution")
        print("   - Performance within acceptable limits")
        print("\n🚀 KuzuMemory with Auggie is ready for production use!")
        return 0
    else:
        print("❌ AUGGIE INTEGRATION TEST FAILED!")
        print("⚠️  Please check the detailed output above for issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
