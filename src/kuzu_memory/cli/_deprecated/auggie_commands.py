"""
Auggie integration CLI commands for KuzuMemory.

Contains commands for Auggie-specific functionality including enhance, learn, rules, and stats.
"""

import logging
import sys

import click

from ..integrations.auggie import AuggieIntegration
from ..utils.project_setup import find_project_root
from .cli_utils import rich_panel, rich_print

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def auggie(ctx: click.Context) -> None:
    """
    🤖 Auggie integration commands for enhanced AI memory.

    Provides Auggie-specific functionality for AI conversation enhancement,
    learning from interactions, and rule management.
    """
    # Verify Auggie integration is available
    try:
        from ..core.memory import KuzuMemory
        from ..utils.project_setup import get_project_db_path

        project_root = ctx.obj.get("project_root") or find_project_root()

        # Initialize KuzuMemory instance if not already available
        db_path = get_project_db_path(project_root)
        memory_system = None
        if db_path.exists():
            try:
                memory_system = KuzuMemory(db_path=db_path)
            except Exception as e:
                logger.warning(f"Could not initialize memory system: {e}")

        auggie_integration = AuggieIntegration(
            project_root=project_root, memory_system=memory_system
        )
        ctx.obj["auggie"] = auggie_integration
    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Auggie integration not available: {e}", style="red")
        sys.exit(1)


@auggie.command()
@click.argument("prompt")
@click.option("--user-id", default="cli-user", help="User ID for context")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def enhance(ctx: click.Context, prompt: str, user_id: str, verbose: bool) -> None:
    """
    🚀 Enhance prompt with Auggie-specific memory context.

    Uses Auggie integration to enhance prompts with relevant conversation
    history and project-specific context for better AI responses.

    \b
    🎮 EXAMPLES:
      # Basic enhancement
      kuzu-memory auggie enhance "How do I implement authentication?"

      # Enhanced with user context
      kuzu-memory auggie enhance "Debug this error" --user-id john

      # Verbose output
      kuzu-memory auggie enhance "Performance tips" --verbose
    """
    try:
        auggie = ctx.obj["auggie"]

        # Enhance prompt using Auggie integration
        enhanced_result = auggie.enhance_prompt(prompt, user_id=user_id)

        if not enhanced_result:
            rich_print(f"(i) No enhancement available for: '{prompt}'", style="blue")
            rich_print(prompt)
            return

        if verbose:
            rich_print(f"🔍 Original Prompt: {prompt}")
            rich_print(f"👤 User ID: {user_id}")
            rich_print(f"📚 Memories Used: {enhanced_result.get('memories_count', 0)}")
            rich_print(f"🤖 Auggie Rules Applied: {enhanced_result.get('rules_applied', 0)}")
            rich_print("")

        # Display enhanced prompt
        enhanced_prompt = enhanced_result.get("enhanced_prompt", prompt)
        if enhanced_prompt != prompt:
            rich_panel(enhanced_prompt, title="🚀 Enhanced Prompt", style="green")
        else:
            rich_print(enhanced_prompt)

        if verbose and enhanced_result.get("context"):
            rich_panel(enhanced_result["context"], title="📚 Context Added", style="blue")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Enhancement failed: {e}", style="red")
        sys.exit(1)


@auggie.command()
@click.argument("prompt")
@click.argument("response")
@click.option("--feedback", help="User feedback on the response")
@click.option("--user-id", default="cli-user", help="User ID for context")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed learning data")
@click.pass_context
def learn(
    ctx: click.Context,
    prompt: str,
    response: str,
    feedback: str | None,
    user_id: str,
    verbose: bool,
) -> None:
    """
    🧠 Learn from Auggie conversation interactions.

    Stores conversation data and user feedback for improving future
    AI responses through the Auggie integration system.

    \b
    🎮 EXAMPLES:
      # Basic learning from conversation
      kuzu-memory auggie learn "How to deploy?" "Use Docker with these steps..."

      # Learning with feedback
      kuzu-memory auggie learn "Debug error" "Check logs" --feedback "This helped!"

      # User-specific learning
      kuzu-memory auggie learn "API design" "Use FastAPI" --user-id john
    """
    try:
        auggie = ctx.obj["auggie"]

        # Prepare learning data
        learning_data = {
            "prompt": prompt,
            "response": response,
            "user_id": user_id,
            "feedback": feedback,
        }

        # Learn from conversation using Auggie integration
        learn_result = auggie.learn_from_conversation(learning_data)

        if verbose:
            rich_print(f"👤 User: {user_id}")
            rich_print(f"❓ Prompt: {prompt}")
            rich_print(f"💬 Response: {response[:100]}{'...' if len(response) > 100 else ''}")
            if feedback:
                rich_print(f"📝 Feedback: {feedback}")

        # Show learning results
        if learn_result:
            rich_print("✅ Learning completed successfully", style="green")

            if verbose:
                rich_print(f"   Memory ID: {learn_result.get('memory_id', 'N/A')[:8]}...")
                rich_print(f"   Patterns Extracted: {learn_result.get('patterns_count', 0)}")
                rich_print(f"   Rules Updated: {learn_result.get('rules_updated', 0)}")
        else:
            rich_print("⚠️  Learning completed with no new information stored", style="yellow")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Learning failed: {e}", style="red")
        sys.exit(1)


@auggie.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed rule information")
@click.pass_context
def rules(ctx: click.Context, verbose: bool) -> None:
    """
    📋 Display Auggie rules and their status.

    Shows the current Auggie rules configuration, including active rules,
    rule files, and memory-based rule learning status.

    \b
    🎮 EXAMPLES:
      # Basic rules overview
      kuzu-memory auggie rules

      # Detailed rules information
      kuzu-memory auggie rules --verbose
    """
    try:
        auggie = ctx.obj["auggie"]

        # Get rules information
        rules_info = auggie.get_rules_summary()

        if not rules_info:
            rich_print("(i) No Auggie rules found", style="blue")
            return

        # Display basic rules info
        rich_panel(
            f"Rules Files: {len(rules_info.get('files', []))}\n"
            f"Memory Rules: {len(rules_info.get('memory_rules', []))}\n"
            f"Active Rules: {rules_info.get('active_count', 0)}",
            title="📋 Auggie Rules Summary",
            style="blue",
        )

        if verbose:
            # Show detailed rule information
            rule_files = rules_info.get("files", [])
            if rule_files:
                rich_print("\n📁 Rule Files:")
                for rule_file in rule_files:
                    rich_print(f"   • {rule_file['path']}")
                    rich_print(
                        f"     Rules: {rule_file.get('rule_count', 0)} | "
                        f"Last Modified: {rule_file.get('last_modified', 'Unknown')}"
                    )

            memory_rules = rules_info.get("memory_rules", [])
            if memory_rules:
                rich_print("\n🧠 Memory-Based Rules:")
                for rule in memory_rules:
                    rich_print(f"   • {rule.get('description', 'No description')}")
                    rich_print(
                        f"     Confidence: {rule.get('confidence', 0):.2f} | "
                        f"Uses: {rule.get('usage_count', 0)}"
                    )

            # Rule statistics
            stats = rules_info.get("statistics", {})
            if stats:
                rich_print("\n📊 Rule Statistics:")
                for key, value in stats.items():
                    rich_print(f"   {key.replace('_', ' ').title()}: {value}")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Rules display failed: {e}", style="red")
        sys.exit(1)


@auggie.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed statistics")
@click.pass_context
def stats(ctx: click.Context, verbose: bool) -> None:
    """
    📊 Display Auggie integration statistics.

    Shows comprehensive statistics about Auggie integration usage,
    including conversation counts, learning metrics, and performance data.

    \b
    🎮 EXAMPLES:
      # Basic Auggie statistics
      kuzu-memory auggie stats

      # Detailed statistics
      kuzu-memory auggie stats --verbose
    """
    try:
        auggie = ctx.obj["auggie"]

        # Get Auggie statistics
        stats = auggie.get_integration_stats()

        if not stats:
            rich_print("(i) No Auggie statistics available", style="blue")
            return

        # Display basic statistics
        rich_panel(
            f"Total Conversations: {stats.get('total_conversations', 0)}\n"
            f"Memories Learned: {stats.get('memories_learned', 0)}\n"
            f"Rules Generated: {stats.get('rules_generated', 0)}\n"
            f"Enhancement Rate: {stats.get('enhancement_rate', 0):.1f}%",
            title="📊 Auggie Integration Stats",
            style="green",
        )

        if verbose:
            # Detailed statistics
            user_stats = stats.get("user_stats", {})
            if user_stats:
                rich_print("\n👥 User Activity:")
                for user_id, user_data in user_stats.items():
                    rich_print(f"   {user_id}: {user_data.get('conversations', 0)} conversations")

            performance_stats = stats.get("performance", {})
            if performance_stats:
                rich_print("\n⚡ Performance Metrics:")
                for metric, value in performance_stats.items():
                    if isinstance(value, float):
                        rich_print(f"   {metric.replace('_', ' ').title()}: {value:.2f}ms")
                    else:
                        rich_print(f"   {metric.replace('_', ' ').title()}: {value}")

            # Recent activity
            recent_activity = stats.get("recent_activity", [])
            if recent_activity:
                rich_print("\n🕒 Recent Activity:")
                for activity in recent_activity[:5]:
                    rich_print(
                        f"   • {activity.get('type', 'Unknown')}: {activity.get('description', 'No description')}"
                    )
                    rich_print(f"     {activity.get('timestamp', 'Unknown time')}")

            # Integration health
            health = stats.get("health", {})
            if health:
                rich_print("\n🏥 Integration Health:")
                for component, status in health.items():
                    icon = "✅" if status == "healthy" else "⚠️" if status == "warning" else "❌"
                    rich_print(f"   {component.replace('_', ' ').title()}: {icon} {status}")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Statistics display failed: {e}", style="red")
        sys.exit(1)
