"""
Help and documentation CLI commands for KuzuMemory.

Provides examples, tips, and interactive help for users.
"""

from __future__ import annotations

import sys
from typing import Any

import click

from .cli_utils import rich_confirm, rich_panel, rich_print, rich_prompt


@click.group(invoke_without_command=True)
@click.pass_context
def help_group(ctx: click.Context) -> None:
    """
    ❓ Help system for KuzuMemory.

    Access examples, tips, and detailed help for commands.

    \b
    🎮 COMMANDS:
      examples    Show practical usage examples
      tips        Show helpful tips and best practices
    """
    # If no subcommand provided, show general help
    if ctx.invoked_subcommand is None:
        rich_panel(
            "Welcome to KuzuMemory Help! 🧠\n\n"
            "Available help commands:\n"
            "• kuzu-memory help examples   - Practical usage examples\n"
            "• kuzu-memory help tips       - Best practices and tips\n"
            "\nFor command-specific help, use:\n"
            "• kuzu-memory <command> --help\n"
            "\nQuick start:\n"
            "• kuzu-memory init           - Initialize project\n"
            "• kuzu-memory memory store   - Store a memory\n"
            "• kuzu-memory status         - Check system status",
            title="❓ KuzuMemory Help",
            style="blue",
        )


@help_group.command()
@click.argument("topic", required=False)
@click.pass_context
def examples(ctx: click.Context, topic: str | None) -> None:
    """
    Show practical examples of KuzuMemory usage.

    Displays example commands and usage patterns for different scenarios
    including basic usage, AI integration, and advanced workflows.

    \b
    🎮 USAGE:
      kuzu-memory help examples              # Show all examples
      kuzu-memory help examples basic        # Basic usage examples
      kuzu-memory help examples ai           # AI integration examples
      kuzu-memory help examples advanced     # Advanced usage examples
    """
    try:
        all_examples: dict[str, dict[str, Any]] = {
            "basic": {
                "title": "📝 Basic Usage Examples",
                "examples": [
                    "# Initialize project",
                    "kuzu-memory init",
                    "",
                    "# Store memories",
                    "kuzu-memory memory store 'We use FastAPI with PostgreSQL'",
                    "kuzu-memory memory store 'Deploy using Docker' --source deployment",
                    "",
                    "# Recall information",
                    "kuzu-memory memory recall 'How do we deploy?'",
                    "kuzu-memory memory recall 'database setup' --max-memories 5",
                    "",
                    "# Enhance prompts",
                    "kuzu-memory memory enhance 'How do I structure the API?'",
                    "kuzu-memory memory enhance 'Performance tips' --format plain",
                    "",
                    "# Check system status",
                    "kuzu-memory status",
                    "kuzu-memory status --detailed",
                ],
            },
            "ai": {
                "title": "🤖 AI Integration Examples",
                "examples": [
                    "# Python AI integration",
                    "import subprocess",
                    "",
                    "def enhance_prompt(prompt):",
                    "    result = subprocess.run([",
                    "        'kuzu-memory', 'memory', 'enhance', prompt, '--format', 'plain'",
                    "    ], capture_output=True, text=True)",
                    "    return result.stdout.strip()",
                    "",
                    "def learn_async(content):",
                    "    subprocess.run([",
                    "        'kuzu-memory', 'memory', 'learn', content, '--quiet'",
                    "    ], check=False)  # Fire and forget",
                    "",
                    "# Usage in conversation",
                    "enhanced = enhance_prompt('How do I authenticate users?')",
                    "ai_response = your_ai_model(enhanced)",
                    "learn_async(f'User asked about auth: {ai_response}')",
                ],
            },
            "advanced": {
                "title": "🚀 Advanced Usage Examples",
                "examples": [
                    "# Learning with metadata",
                    "kuzu-memory memory learn 'API rate limit is 1000/hour' \\",
                    '  --metadata \'{"priority": "high", "category": "limits"}\'',
                    "",
                    "# Session-based memories",
                    "kuzu-memory memory store 'Bug in auth module' --session-id bug-123",
                    "kuzu-memory memory learn 'Fixed by updating JWT' --session-id bug-123",
                    "",
                    "# Different recall strategies",
                    "kuzu-memory memory recall 'performance' --strategy keyword",
                    "kuzu-memory memory recall 'user data' --strategy entity",
                    "kuzu-memory memory recall 'recent changes' --strategy temporal",
                    "",
                    "# System diagnostics",
                    "kuzu-memory doctor                # Full diagnostics",
                    "kuzu-memory doctor health         # Quick health check",
                    "kuzu-memory doctor mcp            # MCP-specific diagnostics",
                ],
            },
            "install": {
                "title": "🚀 Installation & Integration Examples",
                "examples": [
                    "# List available integrations",
                    "kuzu-memory install list",
                    "",
                    "# Install Claude Desktop integration",
                    "kuzu-memory install claude-desktop",
                    "",
                    "# Install Claude Code integration",
                    "kuzu-memory install claude-code",
                    "",
                    "# Check installation status",
                    "kuzu-memory install status",
                    "",
                    "# Remove integration",
                    "kuzu-memory install remove claude-desktop",
                ],
            },
        }

        if topic:
            if topic in all_examples:
                example_set = all_examples[topic]
                rich_panel(
                    "\n".join(example_set["examples"]),
                    title=example_set["title"],
                    style="green",
                )
            else:
                rich_print(f"❌ Unknown topic: {topic}", style="red")
                rich_print(f"Available topics: {', '.join(all_examples.keys())}")
        else:
            # Show all examples
            for _topic_name, example_set in all_examples.items():
                rich_panel(
                    "\n".join(example_set["examples"]),
                    title=example_set["title"],
                    style="green",
                )
                rich_print("")  # Add spacing

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Examples display failed: {e}", style="red")
        sys.exit(1)


@help_group.command()
@click.pass_context
def tips(ctx: click.Context) -> None:
    """
    Show helpful tips and best practices for KuzuMemory.

    Provides practical advice on how to get the most out of KuzuMemory
    including usage patterns, performance optimization, and integration tips.
    """
    try:
        tips_content = [
            "🎯 **Getting Started**",
            "   • Initialize projects with 'kuzu-memory init'",
            "   • Store project context: 'kuzu-memory memory store \"We use FastAPI\"'",
            "   • Test enhancement: 'kuzu-memory memory enhance \"How do I deploy?\"'",
            "",
            "⚡ **Performance Tips**",
            "   • Use async learning: 'kuzu-memory memory learn \"info\" --quiet'",
            "   • Keep recalls fast by limiting --max-memories",
            "   • Monitor performance: 'kuzu-memory status --detailed'",
            "",
            "🤖 **AI Integration**",
            "   • Use subprocess calls, not direct imports",
            "   • Always use --quiet flag for learning in AI workflows",
            "   • Enhance prompts before sending to AI models",
            "",
            "📚 **Memory Best Practices**",
            '   • Be specific: "Use PostgreSQL with asyncpg driver" vs "Use database"',
            '   • Include context: "Authentication uses JWT tokens with 24h expiry"',
            "   • Group related memories with --session-id",
            "",
            "🔧 **Installation & Integration**",
            "   • List integrations: 'kuzu-memory install list'",
            "   • Install Claude Desktop: 'kuzu-memory install claude-desktop'",
            "   • Check status: 'kuzu-memory install status'",
            "",
            "🩺 **Troubleshooting**",
            "   • Run diagnostics: 'kuzu-memory doctor'",
            "   • Quick health check: 'kuzu-memory doctor health'",
            "   • Check connection: 'kuzu-memory doctor connection'",
            "   • Auto-fix issues: 'kuzu-memory doctor --fix'",
            "",
            "📊 **Monitoring**",
            "   • System status: 'kuzu-memory status'",
            "   • Detailed stats: 'kuzu-memory status --detailed'",
            "   • Project info: 'kuzu-memory status --project'",
            "   • Health validation: 'kuzu-memory status --validate'",
        ]

        rich_panel(
            "\n".join(tips_content),
            title="💡 KuzuMemory Tips & Best Practices",
            style="blue",
        )

        # Interactive help
        if rich_confirm("\nWould you like specific help with any topic?", default=False):
            topic = rich_prompt(
                "Enter topic (getting-started, performance, ai-integration, install)",
                default="",
            )

            topic_help = {
                "getting-started": [
                    "🚀 Getting Started with KuzuMemory:",
                    "1. Initialize: kuzu-memory init",
                    "2. Store info: kuzu-memory memory store 'Your project details'",
                    "3. Test recall: kuzu-memory memory recall 'your question'",
                    "4. Try enhancement: kuzu-memory memory enhance 'your prompt'",
                    "5. Check status: kuzu-memory status",
                ],
                "performance": [
                    "⚡ Performance Optimization:",
                    "1. Limit recalls: --max-memories 5",
                    "2. Use async learning: --quiet flag",
                    "3. Monitor response times: kuzu-memory status --detailed",
                    "4. Run health checks: kuzu-memory doctor health",
                ],
                "ai-integration": [
                    "🤖 AI Integration Pattern:",
                    "result = subprocess.run(['kuzu-memory', 'memory', 'enhance', prompt, '--format', 'plain'])",
                    "subprocess.run(['kuzu-memory', 'memory', 'learn', content, '--quiet'])",
                    "Always use subprocess calls, never direct imports!",
                ],
                "install": [
                    "🚀 Installation Tips:",
                    "1. List options: kuzu-memory install list",
                    "2. Install integration: kuzu-memory install <ai-system>",
                    "3. Check status: kuzu-memory install status",
                    "4. Remove if needed: kuzu-memory install remove <ai-system>",
                ],
            }

            if topic in topic_help:
                rich_print("\n" + "\n".join(topic_help[topic]))
            else:
                rich_print(
                    "[i]  Topic not found. Available: getting-started, performance, ai-integration, install",
                    style="blue",
                )

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Tips display failed: {e}", style="red")
        sys.exit(1)


__all__ = ["help_group"]
