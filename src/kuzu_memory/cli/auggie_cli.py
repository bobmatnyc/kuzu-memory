#!/usr/bin/env python3
"""
CLI interface for KuzuMemory Auggie integration.

Provides command-line tools for managing Auggie rules, testing
prompt enhancement, and monitoring integration performance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import KuzuMemory
from ..integrations.auggie import AuggieIntegration


def cmd_enhance_prompt(args: argparse.Namespace) -> int:
    """Enhance a prompt using Auggie integration."""
    try:
        with KuzuMemory(db_path=args.db_path) as memory:
            auggie = AuggieIntegration(memory)

            enhancement = auggie.enhance_prompt(
                prompt=args.prompt, user_id=args.user_id, context={"source": "cli"}
            )

            print("🚀 Prompt Enhancement Results:")
            print("=" * 50)
            print(f"Original: {enhancement['original_prompt']}")
            print(f"Enhanced: {enhancement['enhanced_prompt']}")
            print(f"Context:  {enhancement['context_summary']}")

            if args.verbose:
                print("\n📊 Detailed Information:")
                memory_context = enhancement.get("memory_context") if enhancement else None
                if (
                    memory_context
                    and hasattr(memory_context, "memories")
                    and memory_context.memories
                ):
                    print(f"Memories used: {len(memory_context.memories)}")
                    for i, memory in enumerate(memory_context.memories[:3]):
                        print(f"  {i + 1}. {memory.content[:60]}...")

                executed_rules = enhancement["rule_modifications"].get("executed_rules", [])
                if executed_rules:
                    print(f"Rules applied: {len(executed_rules)}")
                    for rule_info in executed_rules:
                        print(f"  - {rule_info['rule_name']}")

    except Exception as e:
        print(f"❌ Error enhancing prompt: {e}")
        return 1

    return 0


def cmd_learn_response(args: argparse.Namespace) -> int:
    """Learn from an AI response and user feedback."""
    try:
        with KuzuMemory(db_path=args.db_path) as memory:
            auggie = AuggieIntegration(memory)

            learning_result = auggie.learn_from_interaction(
                prompt=args.prompt,
                ai_response=args.response,
                user_feedback=args.feedback,
                user_id=args.user_id,
            )

            print("🧠 Learning Results:")
            print("=" * 30)
            print(f"Quality Score: {learning_result.get('quality_score', 0):.2f}")
            print(f"Memories Created: {len(learning_result.get('extracted_memories', []))}")

            if "corrections" in learning_result:
                corrections = learning_result["corrections"]
                print(f"Corrections Found: {len(corrections)}")
                for correction in corrections:
                    print(f"  - {correction['correction']}")

            if args.verbose:
                print("\n📊 Full Learning Data:")
                print(json.dumps(learning_result, indent=2, default=str))

    except Exception as e:
        print(f"❌ Error learning from response: {e}")
        return 1

    return 0


def cmd_list_rules(args: argparse.Namespace) -> int:
    """List all Auggie rules."""
    try:
        with KuzuMemory(db_path=args.db_path) as memory:
            auggie = AuggieIntegration(memory)

            rules = auggie.rule_engine.rules

            print(f"📋 Auggie Rules ({len(rules)} total):")
            print("=" * 50)

            # Group by rule type
            by_type = {}
            for rule in rules.values():
                rule_type = rule.rule_type.value
                if rule_type not in by_type:
                    by_type[rule_type] = []
                by_type[rule_type].append(rule)

            for rule_type, type_rules in by_type.items():
                print(f"\n🔧 {rule_type.replace('_', ' ').title()} ({len(type_rules)} rules):")

                for rule in sorted(type_rules, key=lambda r: r.priority.value):
                    status = "✅" if rule.enabled else "❌"
                    priority = rule.priority.name
                    executions = rule.execution_count
                    success_rate = rule.success_rate * 100

                    print(f"  {status} {rule.name} [{priority}]")
                    if args.verbose:
                        print(f"      ID: {rule.id}")
                        print(f"      Description: {rule.description}")
                        print(f"      Executions: {executions}, Success: {success_rate:.1f}%")
                        print(f"      Conditions: {rule.conditions}")
                        print(f"      Actions: {rule.actions}")
                        print()

    except Exception as e:
        print(f"❌ Error listing rules: {e}")
        return 1

    return 0


def cmd_create_rule(args: argparse.Namespace) -> int:
    """Create a new custom rule."""
    try:
        with KuzuMemory(db_path=args.db_path) as memory:
            auggie = AuggieIntegration(memory)

            # Parse conditions and actions from JSON
            conditions = json.loads(args.conditions) if args.conditions else {}
            actions = json.loads(args.actions) if args.actions else {}

            rule_id = auggie.create_custom_rule(
                name=args.name,
                description=args.description,
                rule_type=args.rule_type,
                conditions=conditions,
                actions=actions,
                priority=args.priority,
            )

            if rule_id:
                print(f"✅ Created rule: {args.name}")
                print(f"   ID: {rule_id}")
                print(f"   Type: {args.rule_type}")
                print(f"   Priority: {args.priority}")
            else:
                print("❌ Failed to create rule")
                return 1

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in conditions or actions: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error creating rule: {e}")
        return 1

    return 0


def cmd_export_rules(args: argparse.Namespace) -> int:
    """Export rules to a JSON file."""
    try:
        with KuzuMemory(db_path=args.db_path) as memory:
            auggie = AuggieIntegration(memory)

            auggie.export_rules(args.output_file)
            print(f"✅ Rules exported to: {args.output_file}")

    except Exception as e:
        print(f"❌ Error exporting rules: {e}")
        return 1

    return 0


def cmd_import_rules(args: argparse.Namespace) -> int:
    """Import rules from a JSON file."""
    try:
        with KuzuMemory(db_path=args.db_path) as memory:
            auggie = AuggieIntegration(memory)

            initial_count = len(auggie.rule_engine.rules)
            auggie.import_rules(args.input_file)
            final_count = len(auggie.rule_engine.rules)

            imported_count = final_count - initial_count
            print(f"✅ Imported {imported_count} rules from: {args.input_file}")
            print(f"   Total rules now: {final_count}")

    except Exception as e:
        print(f"❌ Error importing rules: {e}")
        return 1

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show integration statistics."""
    try:
        with KuzuMemory(db_path=args.db_path) as memory:
            auggie = AuggieIntegration(memory)

            stats = auggie.get_integration_statistics()

            print("📊 Auggie Integration Statistics:")
            print("=" * 40)

            # Integration stats
            integration_stats = stats["integration"]
            print(f"Prompts Enhanced: {integration_stats['prompts_enhanced']}")
            print(f"Responses Learned: {integration_stats['responses_learned']}")
            print(f"Rules Triggered: {integration_stats['rules_triggered']}")
            print(f"Memories Created: {integration_stats['memories_created']}")

            # Rule engine stats
            rule_stats = stats["rule_engine"]
            print("\nRule Engine:")
            print(f"  Total Rules: {rule_stats['total_rules']}")
            print(f"  Enabled Rules: {rule_stats['enabled_rules']}")
            print(f"  Total Executions: {rule_stats['total_executions']}")

            # Response learner stats
            learner_stats = stats["response_learner"]
            print("\nResponse Learner:")
            print(f"  Learning Events: {learner_stats['total_learning_events']}")
            if "average_quality_score" in learner_stats:
                print(f"  Average Quality: {learner_stats['average_quality_score']:.2f}")

            if args.verbose:
                print("\n🔧 Rule Performance:")
                rule_performance = rule_stats.get("rule_performance", {})

                # Sort by execution count
                sorted_rules = sorted(
                    rule_performance.items(),
                    key=lambda x: x[1]["execution_count"],
                    reverse=True,
                )

                for _rule_id, perf in sorted_rules[:10]:  # Top 10
                    name = perf["name"]
                    count = perf["execution_count"]
                    success = perf["success_rate"] * 100
                    print(f"  {name}: {count} executions, {success:.1f}% success")

    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
        return 1

    return 0


def cmd_test_integration(args: argparse.Namespace) -> int:
    """Test the Auggie integration with sample data."""
    try:
        with KuzuMemory(db_path=args.db_path) as memory:
            auggie = AuggieIntegration(memory)

            print("🧪 Testing Auggie Integration:")
            print("=" * 40)

            # Store sample user data
            user_id = args.user_id
            sample_data = [
                "My name is Test User and I'm a Python developer.",
                "I prefer FastAPI for backend APIs and React for frontend.",
                "We use PostgreSQL as our main database.",
                "I always write unit tests using pytest.",
            ]

            print("📝 Storing sample user data...")
            for data in sample_data:
                memory.generate_memories(data, user_id=user_id)
                print(f"  ✓ {data}")

            # Test prompt enhancement
            print("\n🚀 Testing prompt enhancement...")
            test_prompts = [
                "How do I write a Python function?",
                "What database should I use?",
                "How do I test my code?",
            ]

            for prompt in test_prompts:
                enhancement = auggie.enhance_prompt(prompt, user_id)
                print(f"\n  Prompt: {prompt}")
                print(f"  Enhanced: {len(enhancement['enhanced_prompt'])} chars")
                print(f"  Context: {enhancement['context_summary']}")

            # Test learning
            print("\n🧠 Testing response learning...")
            learning_result = auggie.learn_from_interaction(
                prompt="What framework should I use?",
                ai_response="I recommend Django for Python web development.",
                user_feedback="Actually, I prefer FastAPI as I mentioned before.",
                user_id=user_id,
            )

            print(f"  Quality Score: {learning_result.get('quality_score', 0):.2f}")
            print(f"  Corrections: {len(learning_result.get('corrections', []))}")

            # Show final stats
            stats = auggie.get_integration_statistics()
            print("\n📊 Final Statistics:")
            print(f"  Prompts Enhanced: {stats['integration']['prompts_enhanced']}")
            print(f"  Responses Learned: {stats['integration']['responses_learned']}")

            print("\n✅ Integration test completed successfully!")

    except Exception as e:
        print(f"❌ Error testing integration: {e}")
        return 1

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="KuzuMemory Auggie Integration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("kuzu_memories.db"),
        help="Path to KuzuMemory database",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Enhance prompt command
    enhance_parser = subparsers.add_parser("enhance", help="Enhance a prompt")
    enhance_parser.add_argument("prompt", help="Prompt to enhance")
    enhance_parser.add_argument("--user-id", default="cli-user", help="User ID")
    enhance_parser.set_defaults(func=cmd_enhance_prompt)

    # Learn response command
    learn_parser = subparsers.add_parser("learn", help="Learn from AI response")
    learn_parser.add_argument("prompt", help="Original prompt")
    learn_parser.add_argument("response", help="AI response")
    learn_parser.add_argument("--feedback", help="User feedback")
    learn_parser.add_argument("--user-id", default="cli-user", help="User ID")
    learn_parser.set_defaults(func=cmd_learn_response)

    # List rules command
    list_parser = subparsers.add_parser("rules", help="List all rules")
    list_parser.set_defaults(func=cmd_list_rules)

    # Create rule command
    create_parser = subparsers.add_parser("create-rule", help="Create a new rule")
    create_parser.add_argument("name", help="Rule name")
    create_parser.add_argument("description", help="Rule description")
    create_parser.add_argument(
        "rule_type",
        choices=[
            "context_enhancement",
            "prompt_modification",
            "response_filtering",
            "learning_trigger",
            "memory_prioritization",
        ],
    )
    create_parser.add_argument("--conditions", help="Rule conditions (JSON)")
    create_parser.add_argument("--actions", help="Rule actions (JSON)")
    create_parser.add_argument(
        "--priority", choices=["critical", "high", "medium", "low"], default="medium"
    )
    create_parser.set_defaults(func=cmd_create_rule)

    # Export rules command
    export_parser = subparsers.add_parser("export", help="Export rules to file")
    export_parser.add_argument("output_file", help="Output JSON file")
    export_parser.set_defaults(func=cmd_export_rules)

    # Import rules command
    import_parser = subparsers.add_parser("import", help="Import rules from file")
    import_parser.add_argument("input_file", help="Input JSON file")
    import_parser.set_defaults(func=cmd_import_rules)

    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Show integration statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # Test integration command
    test_parser = subparsers.add_parser("test", help="Test integration with sample data")
    test_parser.add_argument("--user-id", default="test-user", help="User ID for testing")
    test_parser.set_defaults(func=cmd_test_integration)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
