"""
Command-line interface for KuzuMemory.

Provides CLI commands for init, remember, recall, and stats operations
with user-friendly output and error handling.
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
import click
import logging

from ..core.memory import KuzuMemory
from ..core.config import KuzuMemoryConfig
from ..utils.config_loader import get_config_loader
from ..utils.exceptions import KuzuMemoryError, ConfigurationError, DatabaseError
from ..integrations.auggie import AuggieIntegration
from ..__version__ import __version__

# Set up logging for CLI
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="kuzu-memory")
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config', type=click.Path(exists=True), help='Path to configuration file')
@click.option('--db-path', type=click.Path(), help='Path to database file')
@click.pass_context
def cli(ctx, debug, config, db_path):
    """
    KuzuMemory - Lightweight, embedded graph-based memory system for AI applications.
    
    A fast, offline memory system that stores and retrieves contextual memories
    without requiring LLM calls, using pattern matching and local graph storage.
    """
    # Set up logging level
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('kuzu_memory').setLevel(logging.DEBUG)
    
    # Store common options in context
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['config_path'] = config
    ctx.obj['db_path'] = Path(db_path) if db_path else None


@cli.command()
@click.option('--db-path', type=click.Path(), help='Path to database file')
@click.option('--config-path', type=click.Path(), help='Path to save example configuration')
@click.option('--force', is_flag=True, help='Overwrite existing database')
@click.pass_context
def init(ctx, db_path, config_path, force):
    """Initialize a new KuzuMemory database."""
    try:
        # Determine database path
        final_db_path = Path(db_path) if db_path else ctx.obj.get('db_path') or Path('.kuzu_memory/memories.db')
        
        # Check if database already exists
        if final_db_path.exists() and not force:
            click.echo(f"Database already exists at {final_db_path}")
            click.echo("Use --force to overwrite or specify a different path")
            sys.exit(1)
        
        # Create example configuration if requested
        if config_path:
            config_loader = get_config_loader()
            config_loader.create_example_config(Path(config_path))
            click.echo(f"Example configuration created at {config_path}")
        
        # Initialize KuzuMemory
        click.echo(f"Initializing KuzuMemory database at {final_db_path}...")
        
        with KuzuMemory(db_path=final_db_path) as memory:
            stats = memory.get_statistics()
            
        click.echo("✓ Database initialized successfully")
        click.echo(f"  Database path: {final_db_path}")
        click.echo(f"  Schema version: {stats['system_info']['config_version']}")
        
        if config_path:
            click.echo(f"  Example config: {config_path}")
        
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@cli.command()
@click.argument('content', required=True)
@click.option('--source', default='cli', help='Source of the memory')
@click.option('--user-id', help='User ID for the memory')
@click.option('--session-id', help='Session ID for the memory')
@click.option('--agent-id', default='cli', help='Agent ID for the memory')
@click.option('--metadata', help='Additional metadata as JSON string')
@click.pass_context
def remember(ctx, content, source, user_id, session_id, agent_id, metadata):
    """Store a memory from the provided content."""
    try:
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                click.echo(f"Invalid JSON metadata: {e}", err=True)
                sys.exit(1)
        
        # Load configuration and initialize KuzuMemory
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get('config_path'))
        
        with KuzuMemory(db_path=ctx.obj.get('db_path'), config=config) as memory:
            # Generate memories
            memory_ids = memory.generate_memories(
                content=content,
                metadata=parsed_metadata,
                source=source,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id
            )
            
            if memory_ids:
                click.echo(f"✓ Generated {len(memory_ids)} memories")
                if ctx.obj['debug']:
                    for memory_id in memory_ids:
                        click.echo(f"  Memory ID: {memory_id}")
            else:
                click.echo("No memories extracted from content")
        
    except Exception as e:
        click.echo(f"Error storing memory: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@cli.command()
@click.argument('prompt', required=True)
@click.option('--max-memories', default=10, help='Maximum number of memories to recall')
@click.option('--strategy', default='auto', type=click.Choice(['auto', 'keyword', 'entity', 'temporal']), 
              help='Recall strategy to use')
@click.option('--user-id', help='User ID filter')
@click.option('--session-id', help='Session ID filter')
@click.option('--agent-id', default='cli', help='Agent ID filter')
@click.option('--format', 'output_format', default='enhanced', 
              type=click.Choice(['enhanced', 'plain', 'json', 'memories-only']),
              help='Output format')
@click.pass_context
def recall(ctx, prompt, max_memories, strategy, user_id, session_id, agent_id, output_format):
    """Recall memories relevant to the provided prompt."""
    try:
        # Load configuration and initialize KuzuMemory
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get('config_path'))
        
        with KuzuMemory(db_path=ctx.obj.get('db_path'), config=config) as memory:
            # Attach memories
            context = memory.attach_memories(
                prompt=prompt,
                max_memories=max_memories,
                strategy=strategy,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id
            )
            
            # Output based on format
            if output_format == 'json':
                output = {
                    'original_prompt': context.original_prompt,
                    'enhanced_prompt': context.enhanced_prompt,
                    'memories': [
                        {
                            'id': mem.id,
                            'content': mem.content,
                            'type': mem.memory_type.value,
                            'importance': mem.importance,
                            'confidence': mem.confidence,
                            'created_at': mem.created_at.isoformat(),
                        }
                        for mem in context.memories
                    ],
                    'confidence': context.confidence,
                    'strategy_used': context.strategy_used,
                    'recall_time_ms': context.recall_time_ms,
                }
                click.echo(json.dumps(output, indent=2))
                
            elif output_format == 'memories-only':
                for i, mem in enumerate(context.memories, 1):
                    click.echo(f"{i}. {mem.content}")
                    
            elif output_format == 'plain':
                click.echo(context.to_system_message(format_style='plain'))
                
            else:  # enhanced
                click.echo("Enhanced Prompt:")
                click.echo("=" * 50)
                click.echo(context.enhanced_prompt)
                click.echo("=" * 50)
                click.echo(f"Found {len(context.memories)} memories (confidence: {context.confidence:.2f})")
                click.echo(f"Strategy: {context.strategy_used}, Time: {context.recall_time_ms:.1f}ms")
        
    except Exception as e:
        click.echo(f"Error recalling memories: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed statistics')
@click.option('--format', 'output_format', default='text', 
              type=click.Choice(['text', 'json']), help='Output format')
@click.pass_context
def stats(ctx, detailed, output_format):
    """Show database and performance statistics."""
    try:
        # Load configuration and initialize KuzuMemory
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get('config_path'))
        
        with KuzuMemory(db_path=ctx.obj.get('db_path'), config=config) as memory:
            stats_data = memory.get_statistics()
            
            if output_format == 'json':
                click.echo(json.dumps(stats_data, indent=2, default=str))
            else:
                # Text format
                system_info = stats_data.get('system_info', {})
                perf_stats = stats_data.get('performance_stats', {})
                storage_stats = stats_data.get('storage_stats', {})
                
                click.echo("KuzuMemory Statistics")
                click.echo("=" * 40)
                
                # System info
                click.echo(f"Database Path: {system_info.get('db_path', 'Unknown')}")
                click.echo(f"Initialized: {system_info.get('initialized_at', 'Unknown')}")
                click.echo(f"Config Version: {system_info.get('config_version', 'Unknown')}")
                click.echo()
                
                # Performance stats
                click.echo("Performance:")
                click.echo(f"  attach_memories() calls: {perf_stats.get('attach_memories_calls', 0)}")
                click.echo(f"  generate_memories() calls: {perf_stats.get('generate_memories_calls', 0)}")
                click.echo(f"  Average attach time: {perf_stats.get('avg_attach_time_ms', 0):.1f}ms")
                click.echo(f"  Average generate time: {perf_stats.get('avg_generate_time_ms', 0):.1f}ms")
                click.echo()
                
                # Storage stats
                if 'database_stats' in storage_stats:
                    db_stats = storage_stats['database_stats']
                    click.echo("Database:")
                    click.echo(f"  Memories: {db_stats.get('memory_count', 0)}")
                    click.echo(f"  Entities: {db_stats.get('entity_count', 0)}")
                    click.echo(f"  Sessions: {db_stats.get('session_count', 0)}")
                    click.echo(f"  Size: {db_stats.get('db_size_mb', 0):.1f} MB")
                    click.echo()
                
                if detailed:
                    # Show more detailed statistics
                    click.echo("Detailed Statistics:")
                    click.echo("-" * 20)
                    
                    # Storage details
                    if 'storage_stats' in storage_stats:
                        store_stats = storage_stats['storage_stats']
                        click.echo(f"  Memories stored: {store_stats.get('memories_stored', 0)}")
                        click.echo(f"  Memories skipped: {store_stats.get('memories_skipped', 0)}")
                        click.echo(f"  Memories updated: {store_stats.get('memories_updated', 0)}")
                    
                    # Recall details
                    if 'recall_stats' in stats_data:
                        recall_stats = stats_data['recall_stats']
                        if 'coordinator_stats' in recall_stats:
                            coord_stats = recall_stats['coordinator_stats']
                            click.echo(f"  Total recalls: {coord_stats.get('total_recalls', 0)}")
                            click.echo(f"  Cache hits: {coord_stats.get('cache_hits', 0)}")
                            click.echo(f"  Cache misses: {coord_stats.get('cache_misses', 0)}")
        
    except Exception as e:
        click.echo(f"Error getting statistics: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@cli.command()
@click.option('--force', is_flag=True, help='Force cleanup without confirmation')
@click.pass_context
def cleanup(ctx, force):
    """Clean up expired memories."""
    try:
        # Load configuration and initialize KuzuMemory
        config_loader = get_config_loader()
        config = config_loader.load_config(config_path=ctx.obj.get('config_path'))
        
        if not force:
            click.confirm('This will permanently delete expired memories. Continue?', abort=True)
        
        with KuzuMemory(db_path=ctx.obj.get('db_path'), config=config) as memory:
            cleaned_count = memory.cleanup_expired_memories()
            
            if cleaned_count > 0:
                click.echo(f"✓ Cleaned up {cleaned_count} expired memories")
            else:
                click.echo("No expired memories found")
        
    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@cli.command()
@click.argument('config_path', type=click.Path())
@click.pass_context
def create_config(ctx, config_path):
    """Create an example configuration file."""
    try:
        config_loader = get_config_loader()
        config_loader.create_example_config(Path(config_path))
        click.echo(f"✓ Example configuration created at {config_path}")
        click.echo("Edit this file to customize KuzuMemory settings")
        
    except Exception as e:
        click.echo(f"Error creating configuration: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@cli.group()
@click.pass_context
def auggie(ctx):
    """
    Auggie integration commands for intelligent memory-driven AI interactions.

    Provides commands for managing Auggie rules, enhancing prompts,
    and learning from AI responses.
    """
    pass


@auggie.command()
@click.argument('prompt')
@click.option('--user-id', default='cli-user', help='User ID for context')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def enhance(ctx, prompt, user_id, verbose):
    """Enhance a prompt using Auggie rules and memories."""
    try:
        db_path = ctx.obj.get('db_path', 'kuzu_memories.db')

        with KuzuMemory(db_path=db_path) as memory:
            auggie_integration = AuggieIntegration(memory)

            enhancement = auggie_integration.enhance_prompt(
                prompt=prompt,
                user_id=user_id,
                context={"source": "cli"}
            )

            click.echo("🚀 Prompt Enhancement Results:")
            click.echo("=" * 50)
            click.echo(f"Original: {enhancement['original_prompt']}")
            click.echo(f"Enhanced: {enhancement['enhanced_prompt']}")
            click.echo(f"Context:  {enhancement['context_summary']}")

            if verbose:
                click.echo("\n📊 Detailed Information:")
                memory_context = enhancement.get('memory_context')
                if memory_context and memory_context.memories:
                    click.echo(f"Memories used: {len(memory_context.memories)}")
                    for i, memory in enumerate(memory_context.memories[:3]):
                        click.echo(f"  {i+1}. {memory.content[:60]}...")

                executed_rules = enhancement['rule_modifications'].get('executed_rules', [])
                if executed_rules:
                    click.echo(f"Rules applied: {len(executed_rules)}")
                    for rule_info in executed_rules:
                        click.echo(f"  - {rule_info['rule_name']}")

    except Exception as e:
        click.echo(f"❌ Error enhancing prompt: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@auggie.command()
@click.argument('prompt')
@click.argument('response')
@click.option('--feedback', help='User feedback on the response')
@click.option('--user-id', default='cli-user', help='User ID for context')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed learning data')
@click.pass_context
def learn(ctx, prompt, response, feedback, user_id, verbose):
    """Learn from an AI response and optional user feedback."""
    try:
        db_path = ctx.obj.get('db_path', 'kuzu_memories.db')

        with KuzuMemory(db_path=db_path) as memory:
            auggie_integration = AuggieIntegration(memory)

            learning_result = auggie_integration.learn_from_interaction(
                prompt=prompt,
                ai_response=response,
                user_feedback=feedback,
                user_id=user_id
            )

            click.echo("🧠 Learning Results:")
            click.echo("=" * 30)
            click.echo(f"Quality Score: {learning_result.get('quality_score', 0):.2f}")
            click.echo(f"Memories Created: {len(learning_result.get('extracted_memories', []))}")

            if 'corrections' in learning_result:
                corrections = learning_result['corrections']
                click.echo(f"Corrections Found: {len(corrections)}")
                for correction in corrections:
                    click.echo(f"  - {correction['correction']}")

            if verbose:
                click.echo(f"\n📊 Full Learning Data:")
                click.echo(json.dumps(learning_result, indent=2, default=str))

    except Exception as e:
        click.echo(f"❌ Error learning from response: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@auggie.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed rule information')
@click.pass_context
def rules(ctx, verbose):
    """List all Auggie rules."""
    try:
        db_path = ctx.obj.get('db_path', 'kuzu_memories.db')

        with KuzuMemory(db_path=db_path) as memory:
            auggie_integration = AuggieIntegration(memory)

            rules = auggie_integration.rule_engine.rules

            click.echo(f"📋 Auggie Rules ({len(rules)} total):")
            click.echo("=" * 50)

            # Group by rule type
            by_type = {}
            for rule in rules.values():
                rule_type = rule.rule_type.value
                if rule_type not in by_type:
                    by_type[rule_type] = []
                by_type[rule_type].append(rule)

            for rule_type, type_rules in by_type.items():
                click.echo(f"\n🔧 {rule_type.replace('_', ' ').title()} ({len(type_rules)} rules):")

                for rule in sorted(type_rules, key=lambda r: r.priority.value):
                    status = "✅" if rule.enabled else "❌"
                    priority = rule.priority.name
                    executions = rule.execution_count
                    success_rate = rule.success_rate * 100

                    click.echo(f"  {status} {rule.name} [{priority}]")
                    if verbose:
                        click.echo(f"      ID: {rule.id}")
                        click.echo(f"      Description: {rule.description}")
                        click.echo(f"      Executions: {executions}, Success: {success_rate:.1f}%")
                        click.echo(f"      Conditions: {rule.conditions}")
                        click.echo(f"      Actions: {rule.actions}")
                        click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing rules: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


@auggie.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed statistics')
@click.pass_context
def stats(ctx, verbose):
    """Show Auggie integration statistics."""
    try:
        db_path = ctx.obj.get('db_path', 'kuzu_memories.db')

        with KuzuMemory(db_path=db_path) as memory:
            auggie_integration = AuggieIntegration(memory)

            stats = auggie_integration.get_integration_statistics()

            click.echo("📊 Auggie Integration Statistics:")
            click.echo("=" * 40)

            # Integration stats
            integration_stats = stats['integration']
            click.echo(f"Prompts Enhanced: {integration_stats['prompts_enhanced']}")
            click.echo(f"Responses Learned: {integration_stats['responses_learned']}")
            click.echo(f"Rules Triggered: {integration_stats['rules_triggered']}")
            click.echo(f"Memories Created: {integration_stats['memories_created']}")

            # Rule engine stats
            rule_stats = stats['rule_engine']
            click.echo(f"\nRule Engine:")
            click.echo(f"  Total Rules: {rule_stats['total_rules']}")
            click.echo(f"  Enabled Rules: {rule_stats['enabled_rules']}")
            click.echo(f"  Total Executions: {rule_stats['total_executions']}")

            # Response learner stats
            learner_stats = stats['response_learner']
            click.echo(f"\nResponse Learner:")
            click.echo(f"  Learning Events: {learner_stats['total_learning_events']}")
            if 'average_quality_score' in learner_stats:
                click.echo(f"  Average Quality: {learner_stats['average_quality_score']:.2f}")

            if verbose:
                click.echo(f"\n🔧 Rule Performance:")
                rule_performance = rule_stats.get('rule_performance', {})

                # Sort by execution count
                sorted_rules = sorted(
                    rule_performance.items(),
                    key=lambda x: x[1]['execution_count'],
                    reverse=True
                )

                for rule_id, perf in sorted_rules[:10]:  # Top 10
                    name = perf['name']
                    count = perf['execution_count']
                    success = perf['success_rate'] * 100
                    click.echo(f"  {name}: {count} executions, {success:.1f}% success")

    except Exception as e:
        click.echo(f"❌ Error getting statistics: {e}", err=True)
        if ctx.obj['debug']:
            raise
        sys.exit(1)


if __name__ == '__main__':
    cli()
