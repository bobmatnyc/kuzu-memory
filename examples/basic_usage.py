#!/usr/bin/env python3
"""
Basic usage example for KuzuMemory.

Demonstrates the core functionality of KuzuMemory with
memory generation and recall operations.
"""

import sys
from pathlib import Path

# Add the src directory to the path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kuzu_memory import KuzuMemory


def main():
    """Demonstrate basic KuzuMemory usage."""
    print("KuzuMemory Basic Usage Example")
    print("=" * 40)
    
    # Initialize KuzuMemory with a local database
    db_path = Path("example_memories.db")
    
    try:
        with KuzuMemory(db_path=db_path) as memory:
            print(f"✓ Initialized KuzuMemory with database: {db_path}")
            
            # Example 1: Store personal information
            print("\n1. Storing personal information...")
            personal_info = """
            My name is Alex Chen and I work at DataTech Solutions as a Senior Software Engineer.
            I have 5 years of experience in Python development and machine learning.
            I prefer using FastAPI for backend services and React for frontend applications.
            """
            
            memory_ids = memory.generate_memories(
                content=personal_info,
                user_id="alex-chen",
                session_id="intro-session",
                source="profile_setup"
            )
            
            print(f"✓ Generated {len(memory_ids)} memories from personal information")
            
            # Example 2: Store project information
            print("\n2. Storing project information...")
            project_info = """
            Currently working on the CustomerInsights project using Python and PostgreSQL.
            We decided to use Docker for containerization and AWS for deployment.
            The team includes Sarah (frontend), Mike (DevOps), and myself (backend).
            Project deadline is next month and we're using Agile methodology.
            """
            
            project_memory_ids = memory.generate_memories(
                content=project_info,
                user_id="alex-chen",
                session_id="project-discussion",
                source="team_meeting"
            )
            
            print(f"✓ Generated {len(project_memory_ids)} memories from project information")
            
            # Example 3: Store technical preferences
            print("\n3. Storing technical preferences...")
            tech_preferences = """
            I always use pytest for testing and GitHub Actions for CI/CD.
            For code formatting, I prefer black and isort.
            I never use global variables in production code.
            Remember to always validate input data and handle errors gracefully.
            """
            
            tech_memory_ids = memory.generate_memories(
                content=tech_preferences,
                user_id="alex-chen",
                session_id="tech-discussion",
                source="best_practices"
            )
            
            print(f"✓ Generated {len(tech_memory_ids)} memories from technical preferences")
            
            # Example 4: Recall memories with different prompts
            print("\n4. Recalling memories...")
            
            test_prompts = [
                "What's my name and where do I work?",
                "What programming languages and frameworks do I use?",
                "What project am I working on?",
                "Who are my teammates?",
                "What are my testing preferences?",
                "What database are we using?"
            ]
            
            for i, prompt in enumerate(test_prompts, 1):
                print(f"\n4.{i} Query: {prompt}")
                
                context = memory.attach_memories(
                    prompt=prompt,
                    user_id="alex-chen",
                    max_memories=3
                )
                
                print(f"   Found {len(context.memories)} relevant memories")
                print(f"   Confidence: {context.confidence:.2f}")
                print(f"   Strategy: {context.strategy_used}")
                print(f"   Time: {context.recall_time_ms:.1f}ms")
                
                # Show the enhanced prompt (first 200 characters)
                enhanced_preview = context.enhanced_prompt[:200] + "..." if len(context.enhanced_prompt) > 200 else context.enhanced_prompt
                print(f"   Enhanced prompt preview: {enhanced_preview}")
            
            # Example 5: Test different recall strategies
            print("\n5. Testing different recall strategies...")
            
            test_query = "What technologies and tools do we use in our project?"
            strategies = ["auto", "keyword", "entity", "temporal"]
            
            for strategy in strategies:
                context = memory.attach_memories(
                    prompt=test_query,
                    strategy=strategy,
                    user_id="alex-chen",
                    max_memories=5
                )
                
                print(f"   {strategy:8}: {len(context.memories)} memories, {context.recall_time_ms:.1f}ms")
            
            # Example 6: Show statistics
            print("\n6. Memory system statistics...")
            
            stats = memory.get_statistics()
            
            print(f"   Database path: {stats['system_info']['db_path']}")
            print(f"   Total generate_memories() calls: {stats['performance_stats']['generate_memories_calls']}")
            print(f"   Total attach_memories() calls: {stats['performance_stats']['attach_memories_calls']}")
            print(f"   Average generation time: {stats['performance_stats']['avg_generate_time_ms']:.1f}ms")
            print(f"   Average recall time: {stats['performance_stats']['avg_attach_time_ms']:.1f}ms")
            
            if 'database_stats' in stats.get('storage_stats', {}):
                db_stats = stats['storage_stats']['database_stats']
                print(f"   Total memories stored: {db_stats.get('memory_count', 0)}")
                print(f"   Total entities extracted: {db_stats.get('entity_count', 0)}")
                print(f"   Database size: {db_stats.get('db_size_mb', 0):.1f} MB")
            
            print("\n✓ Example completed successfully!")
            print(f"Database saved at: {db_path.absolute()}")
            print("You can run this example again to see how memories persist.")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure KuzuMemory is properly installed.")
        print("If running from source, ensure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Check that all dependencies are installed and Kuzu is available.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
