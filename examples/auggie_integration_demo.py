#!/usr/bin/env python3
"""
Auggie Integration Demo for KuzuMemory.

Demonstrates how KuzuMemory integrates with Auggie's rules system
to provide intelligent memory-driven prompt enhancement and learning.
"""

import sys
from pathlib import Path

# Add the src directory to the path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kuzu_memory import KuzuMemory
from kuzu_memory.integrations.auggie import AuggieIntegration, AuggieRule, RuleType, RulePriority


def main():
    """Demonstrate Auggie integration with KuzuMemory."""
    print("🤖 KuzuMemory + Auggie Integration Demo")
    print("=" * 50)
    
    # Initialize KuzuMemory with Auggie integration
    db_path = Path("auggie_demo_memories.db")
    
    try:
        with KuzuMemory(db_path=db_path) as memory:
            # Initialize Auggie integration
            auggie = AuggieIntegration(
                kuzu_memory=memory,
                config={
                    "max_context_memories": 8,
                    "enable_learning": True
                }
            )
            
            print(f"✅ Initialized KuzuMemory with Auggie integration")
            print(f"📊 Default rules loaded: {len(auggie.rule_engine.rules)}")
            
            # Demo 1: Build user profile through memories
            print("\n" + "="*50)
            print("📝 Demo 1: Building User Profile")
            print("="*50)
            
            user_id = "demo-user"
            
            # Store user profile information
            profile_info = [
                "My name is Sarah Chen and I'm a Senior Software Engineer at TechFlow Inc.",
                "I prefer Python for backend development and React for frontend applications.",
                "I always write comprehensive unit tests before deploying code.",
                "We decided to use PostgreSQL as our main database with Redis for caching.",
                "Currently working on a microservices architecture using Docker and Kubernetes."
            ]
            
            for info in profile_info:
                memory_ids = memory.generate_memories(info, user_id=user_id)
                print(f"  📋 Stored: {info[:60]}... ({len(memory_ids)} memories)")
            
            # Demo 2: Intelligent prompt enhancement
            print("\n" + "="*50)
            print("🚀 Demo 2: Intelligent Prompt Enhancement")
            print("="*50)
            
            test_prompts = [
                "How do I write a Python function?",
                "What's the best way to handle database connections?",
                "Help me debug this authentication issue",
                "What testing framework should I use?",
                "How do I deploy a microservice?"
            ]
            
            for prompt in test_prompts:
                print(f"\n🔍 Original prompt: {prompt}")
                
                # Enhance prompt using Auggie integration
                enhancement = auggie.enhance_prompt(prompt, user_id)
                
                print(f"✨ Enhanced prompt:")
                print(f"   {enhancement['enhanced_prompt'][:200]}...")
                print(f"📊 Context: {enhancement['context_summary']}")
                
                # Show rule applications
                executed_rules = enhancement['rule_modifications'].get('executed_rules', [])
                if executed_rules:
                    print(f"⚙️  Applied rules:")
                    for rule_info in executed_rules:
                        print(f"   - {rule_info['rule_name']}")
            
            # Demo 3: Response learning
            print("\n" + "="*50)
            print("🧠 Demo 3: Learning from AI Responses")
            print("="*50)
            
            # Simulate AI interaction with learning
            learning_scenarios = [
                {
                    "prompt": "What database should I use for my project?",
                    "ai_response": "For your project, I'd recommend PostgreSQL since you mentioned you're already using it at TechFlow Inc. It pairs well with Python and has excellent JSON support for microservices.",
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
            
            for scenario in learning_scenarios:
                print(f"\n💬 Prompt: {scenario['prompt']}")
                print(f"🤖 AI Response: {scenario['ai_response']}")
                
                if scenario['user_feedback']:
                    print(f"👤 User Feedback: {scenario['user_feedback']}")
                
                # Learn from the interaction
                learning_result = auggie.learn_from_interaction(
                    prompt=scenario['prompt'],
                    ai_response=scenario['ai_response'],
                    user_feedback=scenario['user_feedback'],
                    user_id=user_id
                )
                
                print(f"📚 Learning result:")
                print(f"   - Memories extracted: {len(learning_result.get('extracted_memories', []))}")
                print(f"   - Quality score: {learning_result.get('quality_score', 0):.2f}")
                
                if 'corrections' in learning_result:
                    print(f"   - Corrections applied: {len(learning_result['corrections'])}")
            
            # Demo 4: Custom rule creation
            print("\n" + "="*50)
            print("⚙️  Demo 4: Custom Rule Creation")
            print("="*50)
            
            # Create a custom rule for this user
            custom_rule_id = auggie.create_custom_rule(
                name="Prioritize FastAPI for Sarah",
                description="When Sarah asks about Python web frameworks, prioritize FastAPI",
                rule_type="context_enhancement",
                conditions={
                    "user_id": user_id,
                    "prompt_category": "coding",
                    "prompt": {"contains": "web framework"}
                },
                actions={
                    "add_context": "User prefers FastAPI for API development due to performance and async support",
                    "memory_types": ["preference"]
                },
                priority="high"
            )
            
            print(f"✅ Created custom rule: {custom_rule_id}")
            
            # Test the custom rule
            test_prompt = "What Python web framework should I use for my new API?"
            enhancement = auggie.enhance_prompt(test_prompt, user_id)
            
            print(f"\n🔍 Testing custom rule:")
            print(f"   Original: {test_prompt}")
            print(f"   Enhanced: {enhancement['enhanced_prompt'][:200]}...")
            
            executed_rules = enhancement['rule_modifications'].get('executed_rules', [])
            custom_rule_applied = any(rule['rule_id'] == custom_rule_id for rule in executed_rules)
            print(f"   Custom rule applied: {'✅' if custom_rule_applied else '❌'}")
            
            # Demo 5: Statistics and monitoring
            print("\n" + "="*50)
            print("📊 Demo 5: Integration Statistics")
            print("="*50)
            
            stats = auggie.get_integration_statistics()
            
            print(f"Integration Stats:")
            print(f"  - Prompts enhanced: {stats['integration']['prompts_enhanced']}")
            print(f"  - Responses learned: {stats['integration']['responses_learned']}")
            print(f"  - Rules triggered: {stats['integration']['rules_triggered']}")
            print(f"  - Memories created: {stats['integration']['memories_created']}")
            
            print(f"\nRule Engine Stats:")
            print(f"  - Total rules: {stats['rule_engine']['total_rules']}")
            print(f"  - Enabled rules: {stats['rule_engine']['enabled_rules']}")
            print(f"  - Total executions: {stats['rule_engine']['total_executions']}")
            
            print(f"\nResponse Learner Stats:")
            print(f"  - Learning events: {stats['response_learner']['total_learning_events']}")
            print(f"  - Average quality: {stats['response_learner'].get('average_quality_score', 0):.2f}")
            
            # Demo 6: Rule export/import
            print("\n" + "="*50)
            print("💾 Demo 6: Rule Export/Import")
            print("="*50)
            
            # Export rules
            rules_file = Path("demo_auggie_rules.json")
            auggie.export_rules(str(rules_file))
            print(f"✅ Rules exported to {rules_file}")
            
            # Show some rule performance
            print(f"\nTop performing rules:")
            rule_stats = stats['rule_engine']['rule_performance']
            sorted_rules = sorted(
                rule_stats.items(), 
                key=lambda x: x[1]['execution_count'], 
                reverse=True
            )
            
            for rule_id, rule_info in sorted_rules[:3]:
                print(f"  - {rule_info['name']}: {rule_info['execution_count']} executions, "
                      f"{rule_info['success_rate']:.1%} success rate")
            
            print(f"\n🎉 Demo completed successfully!")
            print(f"📁 Database saved at: {db_path.absolute()}")
            print(f"📋 Rules exported to: {rules_file.absolute()}")
            print(f"\n💡 Key Benefits Demonstrated:")
            print(f"   ✅ Intelligent prompt enhancement based on user context")
            print(f"   ✅ Automatic learning from AI responses and user feedback")
            print(f"   ✅ Dynamic rule creation and application")
            print(f"   ✅ Comprehensive monitoring and statistics")
            print(f"   ✅ Rule persistence and sharing")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure KuzuMemory is properly installed.")
        return 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Check that all dependencies are installed and Kuzu is available.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
