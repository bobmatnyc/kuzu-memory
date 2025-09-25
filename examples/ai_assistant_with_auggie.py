#!/usr/bin/env python3
"""
AI Assistant with Auggie-KuzuMemory Integration.

A practical example of how to integrate KuzuMemory with Auggie rules
in a real AI assistant application.
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Add the src directory to the path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kuzu_memory import KuzuMemory
from kuzu_memory.integrations.auggie import AuggieIntegration, AuggieRule, RuleType, RulePriority


class AugmentedAIAssistant:
    """AI Assistant enhanced with KuzuMemory and Auggie rules."""
    
    def __init__(self, db_path: Path, user_id: str):
        """Initialize the augmented AI assistant."""
        self.user_id = user_id
        self.db_path = db_path
        self.memory = None
        self.auggie = None
        self.conversation_history = []
        
    async def initialize(self):
        """Initialize the memory and Auggie integration."""
        try:
            self.memory = KuzuMemory(db_path=self.db_path)
            self.auggie = AuggieIntegration(
                kuzu_memory=self.memory,
                config={
                    "max_context_memories": 10,
                    "enable_learning": True,
                    "learning_threshold": 0.7
                }
            )
            
            # Add custom rules for better AI assistance
            await self._setup_custom_rules()
            
            print(f"🤖 AI Assistant initialized for user: {self.user_id}")
            print(f"📊 Rules loaded: {len(self.auggie.rule_engine.rules)}")
            
        except Exception as e:
            print(f"❌ Error initializing assistant: {e}")
            raise
    
    async def _setup_custom_rules(self):
        """Set up custom rules for enhanced AI assistance."""
        
        # Rule 1: Enhance coding questions with user's tech stack
        self.auggie.rule_engine.add_rule(AuggieRule(
            id="enhance_coding_with_stack",
            name="Enhance Coding with Tech Stack",
            description="Add user's technology stack context to coding questions",
            rule_type=RuleType.CONTEXT_ENHANCEMENT,
            priority=RulePriority.HIGH,
            conditions={
                "prompt_category": "coding",
                "has_preference_memories": True
            },
            actions={
                "add_context": "Include user's preferred technologies and frameworks",
                "memory_types": ["preference", "decision"],
                "include_tech_stack": True
            }
        ))
        
        # Rule 2: Learn from user corrections aggressively
        self.auggie.rule_engine.add_rule(AuggieRule(
            id="aggressive_correction_learning",
            name="Aggressive Correction Learning",
            description="Learn aggressively from any user corrections",
            rule_type=RuleType.LEARNING_TRIGGER,
            priority=RulePriority.CRITICAL,
            conditions={
                "user_feedback": True
            },
            actions={
                "learn_from_response": {
                    "extract_correction": True,
                    "update_memories": True,
                    "confidence_boost": 0.95,
                    "create_preference": True
                }
            }
        ))
        
        # Rule 3: Personalize responses based on experience level
        self.auggie.rule_engine.add_rule(AuggieRule(
            id="personalize_by_experience",
            name="Personalize by Experience Level",
            description="Adjust response complexity based on user's experience level",
            rule_type=RuleType.PROMPT_MODIFICATION,
            priority=RulePriority.MEDIUM,
            conditions={
                "has_identity_memories": True
            },
            actions={
                "modify_prompt": {
                    "adjust_complexity": True,
                    "include_examples": True,
                    "mention_experience": True
                }
            }
        ))
    
    async def process_message(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a user message with memory enhancement and learning."""
        try:
            # Step 1: Enhance the prompt using Auggie rules and memories
            enhancement = self.auggie.enhance_prompt(
                prompt=user_message,
                user_id=self.user_id,
                context=context
            )
            
            enhanced_prompt = enhancement["enhanced_prompt"]
            
            # Step 2: Simulate AI response (in real implementation, call your AI model here)
            ai_response = await self._simulate_ai_response(enhanced_prompt, enhancement)
            
            # Step 3: Store the interaction in conversation history
            interaction = {
                "user_message": user_message,
                "enhanced_prompt": enhanced_prompt,
                "ai_response": ai_response,
                "enhancement_info": enhancement,
                "timestamp": enhancement["rule_modifications"].get("timestamp")
            }
            self.conversation_history.append(interaction)
            
            return {
                "response": ai_response,
                "enhancement_used": True,
                "context_summary": enhancement["context_summary"],
                "memories_used": len(enhancement.get("memory_context", {}).get("memories", [])),
                "rules_applied": len(enhancement["rule_modifications"].get("executed_rules", []))
            }
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request.",
                "error": str(e)
            }
    
    async def _simulate_ai_response(self, enhanced_prompt: str, enhancement: Dict[str, Any]) -> str:
        """Simulate AI response (replace with actual AI model call)."""
        
        # Extract context for response generation
        memory_context = enhancement.get("memory_context")
        user_preferences = []
        user_tech_stack = []
        user_experience = "experienced"
        
        if memory_context and memory_context.memories:
            for memory in memory_context.memories:
                if memory.memory_type.value == "preference":
                    user_preferences.append(memory.content)
                elif memory.entities:
                    # Extract tech stack from entities
                    tech_keywords = ["python", "javascript", "react", "django", "postgresql", "docker"]
                    for entity in memory.entities:
                        if any(keyword in entity.lower() for keyword in tech_keywords):
                            user_tech_stack.append(entity)
        
        # Generate contextual response based on the enhanced prompt
        original_prompt = enhancement["original_prompt"].lower()
        
        if "python" in original_prompt and "function" in original_prompt:
            response = f"""Here's how to write a Python function"""
            if user_preferences:
                response += f", considering your preference for {user_preferences[0][:50]}"""
            response += f""":\n\n```python
def example_function(param1, param2):
    \"\"\"
    Example function with proper documentation.
    \"\"\"
    # Your code here
    result = param1 + param2
    return result
```\n\nBest practices:"""
            if "test" in str(user_preferences):
                response += "\n- Write unit tests for your function"
            response += "\n- Use type hints for better code clarity\n- Add proper documentation"
            
        elif "database" in original_prompt:
            response = "For database connections, I recommend"
            if "postgresql" in str(user_tech_stack).lower():
                response += " using PostgreSQL with connection pooling"
            else:
                response += " using a connection pool pattern"
            response += ":\n\n```python\nimport psycopg2.pool\n\n# Create connection pool\npool = psycopg2.pool.SimpleConnectionPool(1, 20, database='your_db')\n```"
            
        elif "test" in original_prompt:
            response = "For testing, I recommend"
            if any("pytest" in pref.lower() for pref in user_preferences):
                response += " pytest since you mentioned preferring it"
            else:
                response += " pytest as a comprehensive testing framework"
            response += ":\n\n```python\nimport pytest\n\ndef test_example():\n    assert example_function(2, 3) == 5\n```"
            
        elif "deploy" in original_prompt or "microservice" in original_prompt:
            response = "For microservice deployment"
            if "docker" in str(user_tech_stack).lower():
                response += ", since you're using Docker, here's a deployment approach"
            response += ":\n\n```dockerfile\nFROM python:3.9-slim\nCOPY . /app\nWORKDIR /app\nRUN pip install -r requirements.txt\nCMD ['python', 'app.py']\n```"
            
        else:
            response = f"Based on your background and preferences, here's my recommendation for: {original_prompt}"
            if user_tech_stack:
                response += f"\n\nConsidering your tech stack ({', '.join(user_tech_stack[:3])}), "
            response += "I suggest focusing on solutions that align with your current setup."
        
        return response
    
    async def learn_from_feedback(self, user_feedback: str, last_interaction_index: int = -1) -> Dict[str, Any]:
        """Learn from user feedback on the last interaction."""
        try:
            if not self.conversation_history:
                return {"error": "No conversation history to learn from"}
            
            interaction = self.conversation_history[last_interaction_index]
            
            # Learn from the feedback
            learning_result = self.auggie.learn_from_interaction(
                prompt=interaction["user_message"],
                ai_response=interaction["ai_response"],
                user_feedback=user_feedback,
                user_id=self.user_id,
                context={"interaction_index": last_interaction_index}
            )
            
            return {
                "learning_applied": True,
                "memories_created": len(learning_result.get("extracted_memories", [])),
                "corrections_found": len(learning_result.get("corrections", [])),
                "quality_score": learning_result.get("quality_score", 0)
            }
            
        except Exception as e:
            print(f"❌ Error learning from feedback: {e}")
            return {"error": str(e)}
    
    async def get_user_profile_summary(self) -> Dict[str, Any]:
        """Get a summary of what the assistant knows about the user."""
        try:
            # Get recent memories about the user
            context = self.memory.attach_memories(
                prompt="Tell me about this user's background, preferences, and current work",
                user_id=self.user_id,
                max_memories=15
            )
            
            profile = {
                "total_memories": len(context.memories),
                "identity_info": [],
                "preferences": [],
                "current_work": [],
                "tech_stack": set(),
                "experience_indicators": []
            }
            
            for memory in context.memories:
                if memory.memory_type.value == "identity":
                    profile["identity_info"].append(memory.content)
                elif memory.memory_type.value == "preference":
                    profile["preferences"].append(memory.content)
                elif memory.memory_type.value == "status":
                    profile["current_work"].append(memory.content)
                
                # Extract tech stack from entities
                if memory.entities:
                    tech_keywords = ["python", "javascript", "react", "django", "postgresql", "docker", "kubernetes"]
                    for entity in memory.entities:
                        if any(keyword in entity.lower() for keyword in tech_keywords):
                            profile["tech_stack"].add(entity)
                
                # Look for experience indicators
                content_lower = memory.content.lower()
                if any(word in content_lower for word in ["senior", "lead", "principal", "architect"]):
                    profile["experience_indicators"].append("Senior level")
                elif "junior" in content_lower:
                    profile["experience_indicators"].append("Junior level")
            
            profile["tech_stack"] = list(profile["tech_stack"])
            
            return profile
            
        except Exception as e:
            print(f"❌ Error getting user profile: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Clean up resources."""
        if self.memory:
            self.memory.close()


async def main():
    """Demonstrate the augmented AI assistant."""
    print("🤖 Augmented AI Assistant Demo")
    print("=" * 40)
    
    # Initialize assistant
    assistant = AugmentedAIAssistant(
        db_path=Path("ai_assistant_memories.db"),
        user_id="demo-user"
    )
    
    try:
        await assistant.initialize()
        
        # Simulate a conversation
        conversation_flow = [
            {
                "message": "Hi, I'm Sarah, a senior Python developer at TechCorp. I work with Django and PostgreSQL.",
                "feedback": None
            },
            {
                "message": "How do I write a good Python function?",
                "feedback": None
            },
            {
                "message": "What's the best way to handle database connections in Django?",
                "feedback": None
            },
            {
                "message": "I prefer using pytest for testing. How should I structure my tests?",
                "feedback": None
            },
            {
                "message": "What testing framework should I use?",
                "feedback": "Actually, I already told you I prefer pytest. Please remember that."
            },
            {
                "message": "How do I deploy a Django application?",
                "feedback": None
            }
        ]
        
        print("\n🗣️  Starting Conversation:")
        print("-" * 30)
        
        for i, turn in enumerate(conversation_flow):
            print(f"\n👤 User: {turn['message']}")
            
            # Process the message
            response_data = await assistant.process_message(turn["message"])
            
            print(f"🤖 Assistant: {response_data['response'][:200]}...")
            print(f"📊 Context: {response_data.get('context_summary', 'None')}")
            
            # Handle feedback if provided
            if turn["feedback"]:
                print(f"👤 Feedback: {turn['feedback']}")
                
                learning_result = await assistant.learn_from_feedback(turn["feedback"])
                print(f"🧠 Learning: Created {learning_result.get('memories_created', 0)} memories, "
                      f"found {learning_result.get('corrections_found', 0)} corrections")
        
        # Show user profile summary
        print("\n" + "="*40)
        print("👤 User Profile Summary:")
        print("="*40)
        
        profile = await assistant.get_user_profile_summary()
        
        print(f"📊 Total memories: {profile.get('total_memories', 0)}")
        
        if profile.get("identity_info"):
            print(f"🆔 Identity: {profile['identity_info'][0]}")
        
        if profile.get("preferences"):
            print(f"❤️  Preferences: {len(profile['preferences'])} recorded")
            for pref in profile["preferences"][:2]:
                print(f"   - {pref}")
        
        if profile.get("tech_stack"):
            print(f"🛠️  Tech Stack: {', '.join(profile['tech_stack'])}")
        
        # Show integration statistics
        print("\n" + "="*40)
        print("📈 Integration Statistics:")
        print("="*40)
        
        stats = assistant.auggie.get_integration_statistics()
        print(f"✨ Prompts enhanced: {stats['integration']['prompts_enhanced']}")
        print(f"🧠 Responses learned: {stats['integration']['responses_learned']}")
        print(f"⚙️  Rules triggered: {stats['integration']['rules_triggered']}")
        print(f"💾 Memories created: {stats['integration']['memories_created']}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"💡 The assistant now knows about Sarah's preferences and will provide personalized responses!")
        
    except Exception as e:
        print(f"❌ Error in demo: {e}")
        return 1
    
    finally:
        await assistant.close()
    
    return 0


if __name__ == "__main__":
    asyncio.run(main())
