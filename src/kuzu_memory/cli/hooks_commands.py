"""
Hooks installation CLI commands for KuzuMemory.

Provides unified hooks installation commands for Claude Code and Auggie.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import sys
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from ..installers.registry import get_installer, has_installer
from ..utils.project_setup import find_project_root
from .enums import HookSystem

console = Console()


# ===== PROJECT ROOT CACHE =====
# Reduces project root discovery from ~100ms to ~5ms
def _get_cached_project_root() -> Path | None:
    """
    Get project root from cache if valid.

    Returns cached project root if:
    - Cache file exists and is valid JSON
    - Cache is less than 5 minutes old (300 seconds)
    - Cached path still exists

    Returns:
        Path to cached project root, or None if cache invalid/expired
    """
    cache_file = Path("/tmp/.kuzu_project_root_cache.json")
    try:
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            # 5 minute TTL
            if time.time() - data.get("timestamp", 0) < 300:
                cached_path = Path(data.get("path", ""))
                if cached_path.exists():
                    return cached_path
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _cache_project_root(path: Path) -> None:
    """
    Cache project root for future calls.

    Writes project root path and timestamp to cache file.
    Fails silently if caching is not possible (caching is optional optimization).

    Args:
        path: Project root path to cache
    """
    cache_file = Path("/tmp/.kuzu_project_root_cache.json")
    try:
        cache_file.write_text(json.dumps({"path": str(path), "timestamp": time.time()}))
    except OSError:
        pass  # Silently fail - caching is optional


def _find_last_assistant_message(transcript_file: Path) -> str | None:
    """
    Find the last assistant message in the transcript.

    Extracts the last assistant message from a Claude Code transcript file,
    normalizing line endings to prevent CR character leakage (Fix #12).

    Args:
        transcript_file: Path to the transcript JSONL file

    Returns:
        The text of the last assistant message, or None if not found
    """
    import logging

    logger = logging.getLogger(__name__)

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
                    # Normalize line endings to prevent CR leakage (Fix #12)
                    text = text.replace("\r\n", "\n").replace("\r", "\n")
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


def _exit_hook_with_json(
    continue_execution: bool = True,
    context: str | None = None,
    hook_event: str = "UserPromptSubmit",
) -> None:
    """
    Exit hook with valid JSON output for Claude Code hooks API.

    Claude Code requires hooks to output JSON to stdout when exiting with code 0.
    This ensures proper communication with the hooks system.

    Uses hookSpecificOutput.additionalContext API for silent context injection
    when context is provided - the context is injected without being displayed to users.

    Args:
        continue_execution: Whether Claude Code should continue execution (default: True)
        context: Optional context to inject silently (not displayed to users)
        hook_event: The hook event name for hookSpecificOutput (default: "UserPromptSubmit")
    """
    output: dict[str, Any] = {"continue": continue_execution}
    if context:
        output["hookSpecificOutput"] = {
            "hookEventName": hook_event,
            "additionalContext": context,
        }
    print(json.dumps(output))
    sys.exit(0)


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


def _get_memories_with_lock(
    db_path: Path, prompt: str, strategy: str = "keyword"
) -> tuple[list[Any] | None, str | None]:
    """
    Get memories with fail-fast locking to prevent blocking when database is locked.

    Uses file-based locking to detect if another process has the database open.
    If locked, returns immediately instead of blocking indefinitely.

    Args:
        db_path: Path to the KuzuMemory database
        prompt: Prompt text to enhance with memories
        strategy: Recall strategy to use (default: "keyword" for speed)
                 Options: "keyword" (fastest, graph-only), "entity", "temporal", "auto" (slowest)

    Returns:
        Tuple of (memories, error_message):
        - (list of memories, None) if successful
        - (None, "locked") if database is locked by another process
        - (None, error_message) if an error occurred
    """
    from ..core.memory import KuzuMemory
    from ..utils.file_lock import DatabaseBusyError, try_lock_database

    try:
        # Try to acquire lock with 0 timeout (fail immediately if locked)
        with try_lock_database(db_path, timeout=0.0):
            # Disable git sync for hooks - session-start hook handles git sync asynchronously
            memory = KuzuMemory(db_path=db_path, enable_git_sync=False, auto_sync=False)
            # Use specified strategy (default: keyword for fast graph-only search)
            memory_context = memory.attach_memories(prompt, max_memories=5, strategy=strategy)
            memories = memory_context.memories
            memory.close()
            return memories, None

    except DatabaseBusyError:
        # Database is locked by another process
        return None, "locked"
    except Exception as e:
        # Other error
        return None, str(e)


@hooks_group.command(name="enhance")
def hooks_enhance() -> None:
    """
    Enhance prompts with kuzu-memory context (for Claude Code hooks).

    Reads JSON from stdin per Claude Code hooks API, extracts the prompt,
    enhances it with project context, and outputs the enhancement to stdout.

    This command is designed to be called by Claude Code hooks, not directly by users.
    """
    import logging
    import os
    from pathlib import Path

    from ..utils.project_setup import find_project_root, get_project_db_path

    # Configure minimal logging for hook execution
    log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
    log_file = log_dir / "kuzu_enhance.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file)],
        force=True,  # Override existing handlers (Python 3.8+)
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
            _exit_hook_with_json()

        # Extract and validate prompt
        prompt = input_data.get("prompt", "")
        if not prompt or not isinstance(prompt, str) or len(prompt.strip()) == 0:
            logger.info("No valid prompt found in input")
            _exit_hook_with_json()

        # Limit prompt size
        max_prompt_length = 100000
        if len(prompt) > max_prompt_length:
            logger.warning(f"Prompt truncated from {len(prompt)} to {max_prompt_length} chars")
            prompt = prompt[:max_prompt_length]

        # Find project root and initialize memory
        try:
            # Use cached project root for faster lookup
            project_root = _get_cached_project_root()
            if project_root is None:
                project_root = find_project_root()
                if project_root:
                    _cache_project_root(project_root)

            if project_root is None:
                logger.info("Project root not found, skipping enhancement")
                _exit_hook_with_json()

            db_path = get_project_db_path(project_root)

            if not db_path.exists():
                logger.info("Project not initialized, skipping enhancement")
                _exit_hook_with_json()

            # Get memories with fail-fast lock check to prevent blocking
            # if database is locked (e.g., by MCP server or another session)
            # Use "keyword" strategy for fast graph-only search (no vector/embedding computation)
            memories, error = _get_memories_with_lock(db_path, prompt, strategy="keyword")

            if error == "locked":
                logger.info("Database busy (another session), skipping enhancement")
                _exit_hook_with_json()
            elif error:
                logger.error(f"Error getting memories: {error}")
                _exit_hook_with_json()
            elif memories:
                # Format as context
                enhancement_parts = ["# Relevant Project Context"]
                for mem in memories:
                    enhancement_parts.append(f"\n- {mem.content}")

                enhancement = "\n".join(enhancement_parts)
                logger.info(f"Enhancement generated ({len(enhancement)} chars)")
                # Use hookSpecificOutput for silent context injection
                _exit_hook_with_json(context=enhancement)
            else:
                logger.info("No relevant memories found")
                _exit_hook_with_json()

        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            _exit_hook_with_json()

    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        _exit_hook_with_json()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        _exit_hook_with_json()


def _git_sync_async(project_root: Path, logger: Any) -> None:
    """
    Fire-and-forget async git sync using subprocess.

    Spawns a detached subprocess to run incremental git sync
    and returns immediately. This prevents blocking the hook.

    Args:
        project_root: Path to project root
        logger: Logger instance for diagnostics
    """
    import subprocess

    try:
        # Build command to run git sync in background
        cmd = [
            sys.executable,
            "-m",
            "kuzu_memory.cli",
            "git",
            "sync",
            "--incremental",
            "--max-commits",
            "100",
        ]

        # Fire and forget - spawn detached subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
            cwd=str(project_root),  # Run in project directory
        )

        logger.info(f"Launched background git sync (PID: {process.pid})")

    except Exception as e:
        # Log but don't fail the hook
        logger.warning(f"Failed to launch background git sync: {e}")


@hooks_group.command(name="session-start")
def hooks_session_start() -> None:
    """
    Record session start event (for Claude Code hooks).

    Reads JSON from stdin per Claude Code hooks API and creates a simple
    session start memory.

    This command is designed to be called by Claude Code hooks, not directly by users.
    """
    import logging
    import os
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
        force=True,  # Override existing handlers (Python 3.8+)
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
            _exit_hook_with_json()

        # Find project root and initialize memory
        try:
            # Use cached project root for faster lookup
            project_root = _get_cached_project_root()
            if project_root is None:
                project_root = find_project_root()
                if project_root:
                    _cache_project_root(project_root)

            if project_root is None:
                logger.info("Project root not found, skipping session start")
                _exit_hook_with_json()

            db_path = get_project_db_path(project_root)

            if not db_path.exists():
                logger.info("Project not initialized, skipping session start")
                _exit_hook_with_json()

            # Try to acquire lock with 0 timeout (fail immediately if locked)
            from ..utils.file_lock import DatabaseBusyError, try_lock_database

            try:
                with try_lock_database(db_path, timeout=0.0):
                    # Session start is the right place to sync once per session
                    # Other hooks (learn, enhance) skip sync since they're called frequently
                    # Disable git sync on init - use async background sync instead
                    memory = KuzuMemory(db_path=db_path, enable_git_sync=False, auto_sync=False)

                    # Type narrowing: we've already checked project_root is not None
                    assert project_root is not None
                    project_name = project_root.name
                    memory.remember(
                        content=f"Session started in {project_name}",
                        source="claude-code-session",
                        metadata={
                            "agent_id": "session-tracker",
                            "event_type": "session_start",
                        },
                    )

                    logger.info(f"Session start memory stored for project: {project_name}")
                    memory.close()

                    # Fire-and-forget async git sync in background
                    # This doesn't block the hook response
                    _git_sync_async(project_root, logger)

            except DatabaseBusyError:
                logger.info("Database busy (another session), skipping session start")
                _exit_hook_with_json()

        except Exception as e:
            logger.error(f"Error storing session start memory: {e}")
            _exit_hook_with_json()

        # Flush logging before exit
        logging.shutdown()
        _exit_hook_with_json()

    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        logging.shutdown()
        _exit_hook_with_json()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        logging.shutdown()
        _exit_hook_with_json()


@hooks_group.command(name="learn")
@click.option("--sync", "sync_mode", is_flag=True, help="Run synchronously (blocking)")
def hooks_learn(sync_mode: bool) -> None:
    """
    Learn from conversations (for Claude Code hooks).

    By default, runs asynchronously (fire-and-forget) for fast hook execution.
    Use --sync to run synchronously (blocking) for debugging.

    This command is designed to be called by Claude Code hooks, not directly by users.
    """
    import logging
    import os
    from pathlib import Path

    # Configure minimal logging for hook execution
    log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
    log_file = log_dir / "kuzu_learn.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file)],
        force=True,  # Override existing handlers (Python 3.8+)
    )
    logger = logging.getLogger(__name__)

    # If --sync flag is used, run in synchronous mode
    if sync_mode:
        _learn_sync(logger, log_dir)
    else:
        # Default: Async fire-and-forget mode
        _learn_async(logger)


def _learn_worker(
    input_json: str,
    project_root_str: str,
    transcript_path_str: str | None,
    log_dir_str: str,
) -> None:
    """
    Worker function for background learning (multiprocessing.Process).

    This runs in a separate process to avoid blocking the main hook.
    Imports heavy dependencies only in the worker to reduce parent overhead.

    Args:
        input_json: JSON-encoded input data from Claude Code
        project_root_str: String path to project root
        transcript_path_str: String path to transcript file (or None)
        log_dir_str: String path to log directory
    """
    import logging

    # Configure logging in worker process
    log_dir = Path(log_dir_str)
    log_file = log_dir / "kuzu_learn_worker.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file)],
        force=True,
    )
    logger = logging.getLogger(__name__)

    try:
        # Parse input data
        input_data = json.loads(input_json)
        project_root = Path(project_root_str)
        transcript_path = Path(transcript_path_str) if transcript_path_str else None

        # Import heavy dependencies only in worker
        from ..core.memory import KuzuMemory
        from ..utils.file_lock import DatabaseBusyError, try_lock_database
        from ..utils.project_setup import get_project_db_path

        # Get transcript path from input if not provided
        if transcript_path is None:
            transcript_path_input = input_data.get("transcript_path", "")
            if transcript_path_input:
                transcript_path = Path(transcript_path_input)

        # Find the transcript file
        if transcript_path and not transcript_path.exists():
            # Try to find the most recent transcript in the same directory
            if transcript_path.parent.exists():
                transcripts = list(transcript_path.parent.glob("*.jsonl"))
                if transcripts:
                    transcript_path = max(transcripts, key=lambda p: p.stat().st_mtime)
                    logger.info(f"Using most recent transcript: {transcript_path}")
                else:
                    logger.warning("No transcript files found")
                    return
            else:
                logger.warning("Transcript directory does not exist")
                return

        # Extract last assistant message
        if transcript_path:
            assistant_text = _find_last_assistant_message(transcript_path)
            if not assistant_text:
                logger.info("No assistant message to store")
                return

            # Validate text length
            if len(assistant_text) < 10:
                logger.info("Assistant message too short to store")
                return

            max_text_length = 1000000
            if len(assistant_text) > max_text_length:
                logger.warning(f"Truncating from {len(assistant_text)} to {max_text_length} chars")
                assistant_text = assistant_text[:max_text_length]

            # Check for duplicates using cache
            cache_file = log_dir / ".kuzu_learn_cache.json"
            cache_ttl = 300  # 5 minutes

            content_hash = hashlib.sha256(assistant_text.encode("utf-8")).hexdigest()
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
                return

            # Not a duplicate - add to cache
            cache[content_hash] = current_time

            try:
                with open(cache_file, "w") as f:
                    json.dump(cache, f)
            except OSError as e:
                logger.warning(f"Failed to save cache: {e}")

            # Store the memory
            db_path = get_project_db_path(project_root)

            if not db_path.exists():
                logger.info("Project not initialized, skipping learning")
                return

            try:
                with try_lock_database(db_path, timeout=0.0):
                    # Disable git sync for hooks - session-start hook handles git sync asynchronously
                    # This reduces worker latency from 330-530ms to ~50ms (98% reduction)
                    memory = KuzuMemory(db_path=db_path, enable_git_sync=False, auto_sync=False)

                    memory.remember(
                        content=assistant_text,
                        source="claude-code-hook",
                        metadata={"agent_id": "assistant"},
                    )

                    logger.info("Memory stored successfully")
                    memory.close()

            except DatabaseBusyError:
                logger.info("Database busy (another session), skipping learn")
                return

    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)


def _learn_async(logger: Any) -> None:
    """
    Fire-and-forget async learn using multiprocessing.Process.

    Spawns a separate process to handle the learning task and returns
    immediately with success status. This is faster than subprocess.Popen
    (~20ms vs ~80ms) because it avoids shell overhead.

    Optimization notes:
    - Uses multiprocessing.Process instead of subprocess.Popen (~60ms improvement)
    - Uses cached project root discovery (~95ms improvement)
    - Total latency reduction: ~155ms (from ~293ms to ~50ms)
    """
    try:
        # Measure timing if DEBUG env var is set
        debug_timing = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
        if debug_timing:
            start_time = time.time()

        # Read stdin to get the input data
        input_data = json.load(sys.stdin)

        # Serialize input data to pass to worker
        input_json = json.dumps(input_data)

        # OPTIMIZATION 1: Use cached project root discovery (100ms → 5ms)
        if debug_timing:
            cache_start = time.time()

        project_root = _get_cached_project_root()
        if project_root is None:
            project_root = find_project_root()
            if project_root:
                _cache_project_root(project_root)

        if debug_timing:
            cache_time = (time.time() - cache_start) * 1000
            logger.info(f"Project root discovery: {cache_time:.1f}ms")

        if project_root is None:
            logger.error("Project root not found, cannot spawn async learn")
            _exit_hook_with_json()

        # Get transcript path from input
        transcript_path_str = input_data.get("transcript_path")

        # Get log directory
        log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))

        # OPTIMIZATION 2: Use multiprocessing.Process instead of subprocess (80ms → 20ms)
        if debug_timing:
            spawn_start = time.time()

        process = multiprocessing.Process(
            target=_learn_worker,
            args=(
                input_json,
                str(project_root),
                transcript_path_str,
                str(log_dir),
            ),
            daemon=True,
        )
        process.start()
        # Don't wait - fire and forget

        if debug_timing:
            spawn_time = (time.time() - spawn_start) * 1000
            total_time = (time.time() - start_time) * 1000
            logger.info(f"Spawn process: {spawn_time:.1f}ms | Total: {total_time:.1f}ms")

        logger.info(f"Learning task queued asynchronously (PID: {process.pid}, cwd={project_root})")

        # Return immediately with queued status
        _exit_hook_with_json()

    except Exception as e:
        logger.error(f"Error in async learn: {e}")
        _exit_hook_with_json()


def _learn_sync(logger: Any, log_dir: Path) -> None:
    """
    Synchronous learn - blocking operation that processes the memory immediately.

    This is called by the async mode subprocess or when --sync flag is used.
    """
    from pathlib import Path

    from ..core.memory import KuzuMemory
    from ..utils.project_setup import find_project_root, get_project_db_path

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

    try:
        logger.info("=== hooks learn (sync mode) called ===")

        # Read JSON from stdin (Claude Code hooks API)
        try:
            input_data = json.load(sys.stdin)
            hook_event = input_data.get("hook_event_name", "unknown")
            logger.info(f"Hook event: {hook_event}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from stdin: {e}")
            _exit_hook_with_json()

        # Get transcript path
        transcript_path = input_data.get("transcript_path", "")
        if not transcript_path:
            logger.info("No transcript path provided")
            _exit_hook_with_json()

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
                    _exit_hook_with_json()
            else:
                logger.warning("Transcript directory does not exist")
                _exit_hook_with_json()

        # Extract last assistant message
        assistant_text = _find_last_assistant_message(transcript_file)
        if not assistant_text:
            logger.info("No assistant message to store")
            _exit_hook_with_json()

        # Type narrowing: we've already checked assistant_text is not None
        assert assistant_text is not None

        # Validate text length
        if len(assistant_text) < 10:
            logger.info("Assistant message too short to store")
            _exit_hook_with_json()

        max_text_length = 1000000
        if len(assistant_text) > max_text_length:
            logger.warning(f"Truncating from {len(assistant_text)} to {max_text_length} chars")
            assistant_text = assistant_text[:max_text_length]

        # Check for duplicates
        if is_duplicate(assistant_text):
            logger.info("Skipping duplicate memory")
            _exit_hook_with_json()

        # Store the memory with auto_sync=False to skip init sync
        try:
            project_root = find_project_root()
            if project_root is None:
                logger.info("Project root not found, skipping learning")
                _exit_hook_with_json()

            db_path = get_project_db_path(project_root)

            if not db_path.exists():
                logger.info("Project not initialized, skipping learning")
                _exit_hook_with_json()

            # Try to acquire lock with 0 timeout (fail immediately if locked)
            from ..utils.file_lock import DatabaseBusyError, try_lock_database

            try:
                with try_lock_database(db_path, timeout=0.0):
                    # Disable git sync for hooks - session-start hook handles git sync asynchronously
                    # This reduces worker latency from 330-530ms to ~50ms (98% reduction)
                    memory = KuzuMemory(db_path=db_path, enable_git_sync=False, auto_sync=False)

                    memory.remember(
                        content=assistant_text,
                        source="claude-code-hook",
                        metadata={"agent_id": "assistant"},
                    )

                    logger.info("Memory stored successfully")
                    memory.close()

            except DatabaseBusyError:
                logger.info("Database busy (another session), skipping learn")
                _exit_hook_with_json()

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            _exit_hook_with_json()

        _exit_hook_with_json()

    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        _exit_hook_with_json()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        _exit_hook_with_json()


__all__ = ["hooks_group"]
