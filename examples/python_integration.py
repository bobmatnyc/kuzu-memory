#!/usr/bin/env python3
"""
Python Integration Example for KuzuMemory

This module demonstrates how to integrate KuzuMemory with Python AI applications.
Uses subprocess calls for reliability and compatibility.
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any


class KuzuMemoryIntegration:
    """
    Python integration for KuzuMemory AI memory system.

    Provides simple, reliable integration using CLI subprocess calls.
    This approach ensures compatibility and avoids import conflicts.
    """

    def __init__(self, project_path: Optional[str] = None, timeout: int = 5):
        """
        Initialize KuzuMemory integration.

        Args:
            project_path: Path to project root (auto-detected if None)
            timeout: Timeout for CLI operations in seconds
        """
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.timeout = timeout

    def enhance_prompt(self, prompt: str, format: str = 'plain',
                      max_memories: int = 5) -> str:
        """
        Enhance a prompt with relevant memory context.

        Args:
            prompt: Original prompt to enhance
            format: Output format ('plain', 'context', 'json')
            max_memories: Maximum memories to include

        Returns:
            Enhanced prompt with context
        """
        try:
            cmd = [
                'kuzu-memory', 'enhance', prompt,
                '--format', format,
                '--max-memories', str(max_memories),
                '--project-root', str(self.project_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True
            )

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            print(f"Warning: Enhancement timed out after {self.timeout}s", file=sys.stderr)
            return prompt
        except subprocess.CalledProcessError as e:
            print(f"Warning: Enhancement failed: {e}", file=sys.stderr)
            return prompt
        except FileNotFoundError:
            print("Error: kuzu-memory command not found", file=sys.stderr)
            return prompt

    def store_learning(self, content: str, source: str = 'ai-conversation',
                      quiet: bool = True, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store learning content asynchronously (non-blocking).

        Args:
            content: Content to learn from
            source: Source identifier
            quiet: Suppress output (recommended for AI workflows)
            metadata: Additional metadata as dict

        Returns:
            True if learning was queued successfully
        """
        try:
            cmd = [
                'kuzu-memory', 'learn', content,
                '--source', source,
                '--project-root', str(self.project_path)
            ]

            if quiet:
                cmd.append('--quiet')

            if metadata:
                cmd.extend(['--metadata', json.dumps(metadata)])

            # Fire and forget - don't check return code
            subprocess.run(cmd, timeout=self.timeout, check=False)
            return True

        except Exception as e:
            print(f"Warning: Learning failed: {e}", file=sys.stderr)
            return False

    def get_project_stats(self) -> Dict[str, Any]:
        """
        Get project memory statistics.

        Returns:
            Dictionary with project statistics
        """
        try:
            cmd = [
                'kuzu-memory', 'stats',
                '--format', 'json',
                '--project-root', str(self.project_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True
            )

            return json.loads(result.stdout)

        except Exception as e:
            print(f"Warning: Stats retrieval failed: {e}", file=sys.stderr)
            return {}


# Example usage functions
def ai_conversation_with_memory(user_input: str, memory: KuzuMemoryIntegration) -> str:
    """
    Example of AI conversation enhanced with memory.

    Args:
        user_input: User's input/question
        memory: KuzuMemory integration instance

    Returns:
        AI response
    """
    # Enhance prompt with memory context
    enhanced_prompt = memory.enhance_prompt(user_input)

    # Send enhanced prompt to your AI system
    ai_response = your_ai_system(enhanced_prompt)

    # Store the learning asynchronously (non-blocking)
    learning_content = f"User asked: {user_input}\nAI responded: {ai_response}"
    memory.store_learning(learning_content, source="conversation")

    return ai_response


def your_ai_system(prompt: str) -> str:
    """
    Placeholder for your AI system integration.
    Replace with actual AI model calls (OpenAI, Anthropic, etc.)
    """
    return f"AI response to: {prompt}"


def main():
    """Example usage of KuzuMemory integration."""
    print("KuzuMemory Python Integration Example")

    # Initialize memory integration
    memory = KuzuMemoryIntegration()

    # Example conversation
    questions = [
        "How do I structure an API endpoint?",
        "What's the best way to handle database connections?",
        "How should I write tests for this project?"
    ]

    for question in questions:
        print(f"\nUser: {question}")
        response = ai_conversation_with_memory(question, memory)
        print(f"AI: {response}")

    # Show project statistics
    print("\nProject Memory Statistics:")
    stats = memory.get_project_stats()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
