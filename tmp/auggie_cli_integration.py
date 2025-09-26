#!/usr/bin/env python3
"""
Simple Auggie CLI Integration Example

Shows how this Auggie instance can use KuzuMemory CLI commands directly
for persistent project memory and context enhancement.

No HTTP servers, no APIs, just simple CLI calls!
"""

import subprocess
import json
import sys
from pathlib import Path

class AuggieMemoryIntegration:
    """Simple integration using CLI commands only."""
    
    def __init__(self, project_root=None):
        """Initialize with project root directory."""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.kuzu_cmd = self._find_kuzu_command()
    
    def _find_kuzu_command(self):
        """Find the kuzu-memory command to use."""
        # Try different command variations
        commands = [
            './kuzu-memory.sh',  # Development script
            'kuzu-memory',       # Installed via pipx
            'python -m kuzu_memory.cli.commands'  # Direct Python
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(
                    f"{cmd} --help".split(),
                    capture_output=True,
                    cwd=self.project_root,
                    timeout=5
                )
                if result.returncode == 0:
                    return cmd
            except:
                continue
        
        return 'kuzu-memory'  # Fallback
    
    def enhance_prompt(self, user_prompt, format='plain'):
        """
        Enhance a user prompt with project context.
        
        Args:
            user_prompt: The user's original prompt
            format: Output format ('plain', 'json', 'context')
            
        Returns:
            Enhanced prompt string or original if enhancement fails
        """
        try:
            cmd = f"{self.kuzu_cmd} enhance '{user_prompt}' --format {format}".split()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Enhancement failed: {result.stderr}", file=sys.stderr)
                return user_prompt
                
        except Exception as e:
            print(f"Enhancement error: {e}", file=sys.stderr)
            return user_prompt
    
    def store_learning(self, content, source='ai-conversation', metadata=None, quiet=True):
        """
        Store learning from AI conversation.
        
        Args:
            content: What to learn/remember
            source: Source of the learning
            metadata: Optional metadata dict
            quiet: Suppress output
        """
        try:
            cmd = [self.kuzu_cmd, 'learn', content, '--source', source]
            
            if metadata:
                cmd.extend(['--metadata', json.dumps(metadata)])
            
            if quiet:
                cmd.append('--quiet')
            
            subprocess.run(
                cmd,
                cwd=self.project_root,
                timeout=10,
                check=False  # Don't fail if storage fails
            )
            
        except Exception as e:
            print(f"Learning storage error: {e}", file=sys.stderr)
    
    def get_recent_memories(self, count=10, format='json'):
        """
        Get recent project memories.
        
        Args:
            count: Number of recent memories
            format: Output format
            
        Returns:
            List of recent memories or empty list if fails
        """
        try:
            cmd = f"{self.kuzu_cmd} recent --recent {count} --format {format}".split()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10
            )
            
            if result.returncode == 0 and format == 'json':
                return json.loads(result.stdout)
            elif result.returncode == 0:
                return result.stdout.strip().split('\n')
            else:
                return []
                
        except Exception as e:
            print(f"Recent memories error: {e}", file=sys.stderr)
            return []
    
    def process_conversation_turn(self, user_input, ai_response_generator, user_feedback=None):
        """
        Process a complete conversation turn with memory integration.
        
        Args:
            user_input: User's message
            ai_response_generator: Function that takes enhanced prompt and returns AI response
            user_feedback: Optional user feedback/corrections
            
        Returns:
            Dict with conversation results
        """
        # Step 1: Enhance the prompt with project context
        enhanced_prompt = self.enhance_prompt(user_input)
        
        # Step 2: Generate AI response using enhanced prompt
        ai_response = ai_response_generator(enhanced_prompt)
        
        # Step 3: Store the interaction
        interaction_summary = f"Q: {user_input} A: {ai_response}"
        self.store_learning(interaction_summary, source='conversation')
        
        # Step 4: Store user feedback if provided
        if user_feedback:
            feedback_content = f"User feedback on '{user_input}': {user_feedback}"
            self.store_learning(feedback_content, source='feedback')
        
        return {
            'original_prompt': user_input,
            'enhanced_prompt': enhanced_prompt,
            'ai_response': ai_response,
            'user_feedback': user_feedback,
            'context_enhanced': enhanced_prompt != user_input
        }


def simulate_ai_response(prompt):
    """Simulate an AI response (replace with actual AI system)."""
    if 'api' in prompt.lower():
        return "For API development, I recommend using FastAPI with proper error handling and documentation."
    elif 'database' in prompt.lower():
        return "For database operations, use SQLAlchemy with proper connection pooling."
    elif 'test' in prompt.lower():
        return "For testing, use pytest with fixtures and proper test organization."
    else:
        return f"Here's my response to: {prompt}"


def demo_integration():
    """Demonstrate the CLI integration."""
    print("🎯 Auggie CLI Integration Demo")
    print("=" * 50)
    
    # Initialize integration
    memory = AuggieMemoryIntegration()
    
    # Simulate conversation turns
    conversations = [
        {
            'user': 'How do I structure an API endpoint?',
            'feedback': None
        },
        {
            'user': 'What database should I use?',
            'feedback': 'Actually, we already decided on PostgreSQL'
        },
        {
            'user': 'How do I write tests?',
            'feedback': None
        }
    ]
    
    for i, conv in enumerate(conversations, 1):
        print(f"\n💬 Conversation {i}")
        print("-" * 30)
        
        result = memory.process_conversation_turn(
            user_input=conv['user'],
            ai_response_generator=simulate_ai_response,
            user_feedback=conv['feedback']
        )
        
        print(f"👤 User: {result['original_prompt']}")
        if result['context_enhanced']:
            print(f"🧠 Enhanced: {result['enhanced_prompt'][:100]}...")
        print(f"🤖 AI: {result['ai_response']}")
        if result['user_feedback']:
            print(f"📝 Feedback: {result['user_feedback']}")
    
    # Show recent memories
    print(f"\n📋 Recent Project Context")
    print("-" * 30)
    recent = memory.get_recent_memories(count=5)
    for i, mem in enumerate(recent, 1):
        content = mem.get('content', str(mem)) if isinstance(mem, dict) else str(mem)
        print(f"  {i}. {content[:80]}...")


def example_usage():
    """Show example usage patterns."""
    print("\n🔧 Example Usage Patterns")
    print("=" * 50)
    
    memory = AuggieMemoryIntegration()
    
    # Pattern 1: Simple enhancement
    print("\n1. Simple Prompt Enhancement:")
    user_query = "How do I deploy this application?"
    enhanced = memory.enhance_prompt(user_query)
    print(f"   Original: {user_query}")
    print(f"   Enhanced: {enhanced}")
    
    # Pattern 2: Store learning
    print("\n2. Store Learning:")
    memory.store_learning("User prefers Docker for deployment", source='preference')
    print("   ✅ Stored user preference")
    
    # Pattern 3: Get context
    print("\n3. Get Recent Context:")
    recent = memory.get_recent_memories(count=3)
    print(f"   Found {len(recent)} recent memories")


if __name__ == "__main__":
    print("🌟 KuzuMemory CLI Integration")
    print("Simple, direct integration using CLI commands only!")
    print()
    
    try:
        demo_integration()
        example_usage()
        
        print(f"\n🎉 Integration Demo Complete!")
        print("✅ No HTTP servers needed")
        print("✅ No API complexity")
        print("✅ Just simple CLI commands")
        print("✅ Works with any AI system")
        
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
