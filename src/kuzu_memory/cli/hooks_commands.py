"""
Hooks installation CLI commands for KuzuMemory.

Provides unified hooks installation commands for Claude Code and Auggie.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ..installers.registry import get_installer, has_installer
from ..utils.project_setup import find_project_root
from .enums import HookSystem

console = Console()


@click.group(name="hooks")
def hooks_group() -> None:
    """
    🪝 Hook system entry points for Claude Code integration.

    Provides commands used by Claude Code hooks API for automatic
    prompt enhancement and conversation learning.

    \b
    🎮 COMMANDS:
      enhance    Enhance prompts with project context (called by Claude Code)
      learn      Learn from conversations (called by Claude Code)
      status     Show hooks installation status
      install    Install hooks for a system
      list       List available hook systems

    \b
    🎯 HOOK SYSTEMS:
      claude-code  Claude Code with UserPromptSubmit and PostToolUse hooks
      auggie       Auggie with Augment rules

    Use 'kuzu-memory hooks COMMAND --help' for detailed help.
    """
    pass


@hooks_group.command(name="status")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
@click.option("--verbose", is_flag=True, help="Show detailed information")
def hooks_status(project: str | None, verbose: bool) -> None:
    """
    Show hooks installation status for all systems.

    Checks the installation status of all hook-based systems.

    \b
    🎯 EXAMPLES:
      # Show status for all hook systems
      kuzu-memory hooks status

      # Show detailed status
      kuzu-memory hooks status --verbose
    """
    try:
        # Determine project root
        if project:
            project_root = Path(project)
        else:
            try:
                found_root = find_project_root()
                project_root = found_root if found_root is not None else Path.cwd()
            except Exception:
                project_root = Path.cwd()

        console.print("\n🪝 [bold cyan]Hook Systems Installation Status[/bold cyan]")
        console.print(f"Project: {project_root}\n")

        # Create table for status
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("System", style="cyan", width=15)
        table.add_column("Status", width=15)
        table.add_column("Details", width=40)

        # Check each hook system
        for hook_system in HookSystem:
            system_name = hook_system.value
            if not has_installer(system_name):
                continue

            installer = get_installer(system_name, project_root)
            if not installer:
                continue

            status_info = installer.get_status()
            is_installed = status_info.get("installed", False)

            # Status icon and text
            if is_installed:
                status_str = "[green]✅ Installed[/green]"
                details = "All files present"
            else:
                status_str = "[yellow]❌ Not Installed[/yellow]"
                details = "Run install to set up"

            # Add detailed info if verbose
            if verbose and is_installed:
                files = status_info.get("files", {})
                present_files = [k for k, v in files.items() if v]
                details = f"{len(present_files)} files present"

            table.add_row(hook_system.display_name, status_str, details)

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]❌ Status check failed: {e}[/red]")
        sys.exit(1)


@hooks_group.command(name="install")
@click.argument("system", type=click.Choice([s.value for s in HookSystem]))
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--verbose", is_flag=True, help="Show detailed output")
@click.option("--project", type=click.Path(exists=True), help="Project directory")
def install_hooks(system: str, dry_run: bool, verbose: bool, project: str | None) -> None:
    """
    Install hooks for specified system.

    NOTE: RECOMMENDED: Use 'kuzu-memory install <platform>' instead.
          The unified install command automatically handles MCP + hooks per platform.

    Hooks are automatically updated if already installed (no --force flag needed).

    \b
    🎯 HOOK SYSTEMS:
      claude-code  Install Claude Code hooks (UserPromptSubmit, Stop)
      auggie       Install Auggie rules (treated as hooks)

    \b
    🎯 RECOMMENDED COMMAND:
      kuzu-memory install <platform>
        • Installs MCP + hooks for claude-code
        • Installs rules for auggie
        • No need to think about MCP vs hooks - it does the right thing

    \b
    🎯 EXAMPLES (still supported):
      # Install Claude Code hooks
      kuzu-memory hooks install claude-code

      # Install Auggie rules
      kuzu-memory hooks install auggie
    """
    # Show informational note about unified command
    console.print(
        "\n[blue]Note:[/blue] 'kuzu-memory install <platform>' is now the recommended command."
    )
    console.print("   It automatically installs the right components for each platform.\n")

    try:
        # Determine project root
        if project:
            project_root = Path(project)
        else:
            try:
                found_root = find_project_root()
                if found_root is None:
                    console.print(
                        "[red]❌ Could not find project root. Use --project to specify.[/red]"
                    )
                    sys.exit(1)
                project_root = found_root
            except Exception:
                console.print(
                    "[red]❌ Could not find project root. Use --project to specify.[/red]"
                )
                sys.exit(1)

        # Check if installer exists
        if not has_installer(system):
            console.print(f"[red]❌ Unknown hook system: {system}[/red]")
            console.print("\n💡 Available hook systems:")
            for hook_system in HookSystem:
                console.print(f"  • {hook_system.value} - {hook_system.display_name}")
            sys.exit(1)

        # Get installer
        installer = get_installer(system, project_root)
        if not installer:
            console.print(f"[red]❌ Failed to create installer for {system}[/red]")
            sys.exit(1)

        # Show installation info
        console.print(f"\n🪝 [bold cyan]Installing {installer.ai_system_name}[/bold cyan]")
        console.print(f"📁 Project: {project_root}")
        console.print(f"📋 Description: {installer.description}")

        if dry_run:
            console.print("\n[yellow]🔍 DRY RUN MODE - No changes will be made[/yellow]")

        console.print()

        # Perform installation (always update existing - no force parameter)
        result = installer.install(dry_run=dry_run, verbose=verbose)

        # Show results
        if result.success:
            console.print(f"\n[green]✅ {result.message}[/green]")

            # Show created files
            if result.files_created:
                console.print("\n[cyan]📄 Files created:[/cyan]")
                for file_path in result.files_created:
                    console.print(f"  • {file_path}")

            # Show modified files
            if result.files_modified:
                console.print("\n[yellow]📝 Files modified:[/yellow]")
                for file_path in result.files_modified:
                    console.print(f"  • {file_path}")

            # Show backups
            if result.backup_files and verbose:
                console.print("\n[blue]💾 Backup files:[/blue]")
                for file_path in result.backup_files:
                    console.print(f"  • {file_path}")

            # Show warnings
            if result.warnings:
                console.print("\n[yellow]⚠️  Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  • {warning}")

            # Show next steps
            console.print("\n[green]🎯 Next Steps:[/green]")
            if system == "claude-code":
                console.print("1. Reload Claude Code window or restart")
                console.print("2. Hooks will auto-enhance prompts and learn from responses")
                console.print("3. Check .claude/settings.local.json for configuration")
            elif system == "auggie":
                console.print("1. Open or reload your Auggie workspace")
                console.print("2. Rules will be active for enhanced context")
                console.print("3. Check AGENTS.md and .augment/rules/ for configuration")

        else:
            console.print(f"\n[red]❌ {result.message}[/red]")
            if result.warnings:
                for warning in result.warnings:
                    console.print(f"[yellow]  • {warning}[/yellow]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]❌ Installation failed: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@hooks_group.command(name="list")
def list_hooks() -> None:
    """
    List available hook systems.

    Shows all hook-based systems that can be installed with kuzu-memory.

    \b
    🎯 EXAMPLES:
      # List available hook systems
      kuzu-memory hooks list
    """
    console.print("\n🪝 [bold cyan]Available Hook Systems[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("System", style="cyan", width=15)
    table.add_column("Name", width=15)
    table.add_column("Type", width=15)

    for hook_system in HookSystem:
        system_name = hook_system.value
        display_name = hook_system.display_name

        # Determine type
        if system_name == "claude-code":
            hook_type = "Hooks (Events)"
        elif system_name == "auggie":
            hook_type = "Rules (Markdown)"
        else:
            hook_type = "Unknown"

        table.add_row(system_name, display_name, hook_type)

    console.print(table)

    console.print("\n💡 [dim]Use 'kuzu-memory hooks install <system>' to install[/dim]\n")


@hooks_group.command(name="enhance")
def hooks_enhance() -> None:
    """
    Enhance prompts with kuzu-memory context (for Claude Code hooks).

    Reads JSON from stdin per Claude Code hooks API, extracts the prompt,
    enhances it with project context, and outputs the enhancement to stdout.

    This command is designed to be called by Claude Code hooks, not directly by users.
    """
    import json
    import logging
    import os
    import sys
    from pathlib import Path

    from ..core.memory import KuzuMemory
    from ..utils.project_setup import find_project_root, get_project_db_path

    # Configure minimal logging for hook execution
    log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
    log_file = log_dir / "kuzu_enhance.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file)],
    )
    logger = logging.getLogger(__name__)

    try:
        logger.info("=== hooks enhance called ===")

        # Read JSON from stdin (Claude Code hooks API)
        try:
            input_data = json.load(sys.stdin)
            logger.debug(f"Input keys: {list(input_data.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from stdin: {e}")
            sys.exit(0)

        # Extract and validate prompt
        prompt = input_data.get("prompt", "")
        if not prompt or not isinstance(prompt, str) or len(prompt.strip()) == 0:
            logger.info("No valid prompt found in input")
            sys.exit(0)

        # Limit prompt size
        max_prompt_length = 100000
        if len(prompt) > max_prompt_length:
            logger.warning(f"Prompt truncated from {len(prompt)} to {max_prompt_length} chars")
            prompt = prompt[:max_prompt_length]

        # Find project root and initialize memory
        try:
            project_root = find_project_root()
            if project_root is None:
                logger.info("Project root not found, skipping enhancement")
                sys.exit(0)

            db_path = get_project_db_path(project_root)

            if not db_path.exists():
                logger.info("Project not initialized, skipping enhancement")
                sys.exit(0)

            # Initialize memory and enhance prompt
            memory = KuzuMemory(db_path=db_path)

            # Get relevant memories using attach_memories API
            memory_context = memory.attach_memories(prompt, max_memories=5)
            memories = memory_context.memories

            if memories:
                # Format as context
                enhancement_parts = ["# Relevant Project Context"]
                for mem in memories:
                    enhancement_parts.append(f"\n- {mem.content}")

                enhancement = "\n".join(enhancement_parts)
                logger.info(f"Enhancement generated ({len(enhancement)} chars)")
                print(enhancement)
            else:
                logger.info("No relevant memories found")

            memory.close()

        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(0)


@hooks_group.command(name="session-start")
def hooks_session_start() -> None:
    """
    Record session start event (for Claude Code hooks).

    Reads JSON from stdin per Claude Code hooks API and creates a simple
    session start memory.

    This command is designed to be called by Claude Code hooks, not directly by users.
    """
    import json
    import logging
    import os
    import sys
    from pathlib import Path

    from ..core.memory import KuzuMemory
    from ..utils.project_setup import find_project_root, get_project_db_path

    # Configure minimal logging for hook execution
    log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
    log_file = log_dir / "kuzu_session_start.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file)],
    )
    logger = logging.getLogger(__name__)

    try:
        logger.info("=== hooks session-start called ===")

        # Read JSON from stdin (Claude Code hooks API)
        try:
            input_data = json.load(sys.stdin)
            logger.debug(f"Input keys: {list(input_data.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from stdin: {e}")
            sys.exit(0)

        # Find project root and initialize memory
        try:
            project_root = find_project_root()
            if project_root is None:
                logger.info("Project root not found, skipping session start")
                sys.exit(0)

            db_path = get_project_db_path(project_root)

            if not db_path.exists():
                logger.info("Project not initialized, skipping session start")
                sys.exit(0)

            # Store session start memory
            memory = KuzuMemory(db_path=db_path)

            project_name = project_root.name
            memory.remember(
                content=f"Session started in {project_name}",
                source="claude-code-session",
                metadata={"agent_id": "session-tracker", "event_type": "session_start"},
            )

            logger.info(f"Session start memory stored for project: {project_name}")
            memory.close()

        except Exception as e:
            logger.error(f"Error storing session start memory: {e}")

        # Flush logging before exit
        logging.shutdown()
        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        logging.shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        logging.shutdown()
        sys.exit(0)


@hooks_group.command(name="learn")
def hooks_learn() -> None:
    """
    Learn from conversations (for Claude Code hooks).

    Reads JSON from stdin per Claude Code hooks API, extracts the last assistant
    message from the transcript, and stores it as a memory.

    This command is designed to be called by Claude Code hooks, not directly by users.
    """
    import hashlib
    import json
    import logging
    import os
    import sys
    import time
    from pathlib import Path

    from ..core.memory import KuzuMemory
    from ..utils.project_setup import find_project_root, get_project_db_path

    # Configure minimal logging for hook execution
    log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
    log_file = log_dir / "kuzu_learn.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file)],
    )
    logger = logging.getLogger(__name__)

    # Deduplication cache
    cache_file = log_dir / ".kuzu_learn_cache.json"
    cache_ttl = 300  # 5 minutes

    def is_duplicate(text: str) -> bool:
        """Check if this content was recently stored."""
        try:
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            current_time = time.time()

            cache = {}
            if cache_file.exists():
                try:
                    with open(cache_file) as f:
                        cache = json.load(f)
                except (OSError, json.JSONDecodeError):
                    logger.warning("Failed to load cache, starting fresh")

            # Clean expired entries
            cache = {k: v for k, v in cache.items() if current_time - v < cache_ttl}

            # Check if duplicate
            if content_hash in cache:
                age = current_time - cache[content_hash]
                logger.info(f"Duplicate detected (stored {age:.1f}s ago), skipping")
                return True

            # Not a duplicate - add to cache
            cache[content_hash] = current_time

            try:
                with open(cache_file, "w") as f:
                    json.dump(cache, f)
            except OSError as e:
                logger.warning(f"Failed to save cache: {e}")

            return False
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return False

    def find_last_assistant_message(transcript_file: Path) -> str | None:
        """Find the last assistant message in the transcript."""
        try:
            with open(transcript_file, encoding="utf-8") as f:
                lines = f.readlines()

            if not lines:
                return None

            # Search backwards for assistant messages
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    message = entry.get("message", {})

                    if not isinstance(message, dict) or message.get("role") != "assistant":
                        continue

                    content = message.get("content", [])
                    if not isinstance(content, list):
                        continue

                    # Extract text from content items
                    text_parts = [
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]

                    if text_parts:
                        text = " ".join(text_parts).strip()
                        if text:
                            logger.info(f"Found assistant message ({len(text)} chars)")
                            return text

                except json.JSONDecodeError:
                    continue

            logger.info("No assistant messages found in transcript")
            return None

        except Exception as e:
            logger.error(f"Error reading transcript: {e}")
            return None

    try:
        logger.info("=== hooks learn called ===")

        # Read JSON from stdin (Claude Code hooks API)
        try:
            input_data = json.load(sys.stdin)
            hook_event = input_data.get("hook_event_name", "unknown")
            logger.info(f"Hook event: {hook_event}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from stdin: {e}")
            sys.exit(0)

        # Get transcript path
        transcript_path = input_data.get("transcript_path", "")
        if not transcript_path:
            logger.info("No transcript path provided")
            sys.exit(0)

        # Find the transcript file
        transcript_file = Path(transcript_path)
        if not transcript_file.exists():
            # Try to find the most recent transcript in the same directory
            if transcript_file.parent.exists():
                transcripts = list(transcript_file.parent.glob("*.jsonl"))
                if transcripts:
                    transcript_file = max(transcripts, key=lambda p: p.stat().st_mtime)
                    logger.info(f"Using most recent transcript: {transcript_file}")
                else:
                    logger.warning("No transcript files found")
                    sys.exit(0)
            else:
                logger.warning("Transcript directory does not exist")
                sys.exit(0)

        # Extract last assistant message
        assistant_text = find_last_assistant_message(transcript_file)
        if not assistant_text:
            logger.info("No assistant message to store")
            sys.exit(0)

        # Validate text length
        if len(assistant_text) < 10:
            logger.info("Assistant message too short to store")
            sys.exit(0)

        max_text_length = 1000000
        if len(assistant_text) > max_text_length:
            logger.warning(f"Truncating from {len(assistant_text)} to {max_text_length} chars")
            assistant_text = assistant_text[:max_text_length]

        # Check for duplicates
        if is_duplicate(assistant_text):
            logger.info("Skipping duplicate memory")
            sys.exit(0)

        # Store the memory
        try:
            project_root = find_project_root()
            if project_root is None:
                logger.info("Project root not found, skipping learning")
                sys.exit(0)

            db_path = get_project_db_path(project_root)

            if not db_path.exists():
                logger.info("Project not initialized, skipping learning")
                sys.exit(0)

            memory = KuzuMemory(db_path=db_path)

            memory.remember(
                content=assistant_text,
                source="claude-code-hook",
                metadata={"agent_id": "assistant"},
            )

            logger.info("Memory stored successfully")
            memory.close()

        except Exception as e:
            logger.error(f"Error storing memory: {e}")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(0)


__all__ = ["hooks_group"]
