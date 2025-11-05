"""
Common CLI utilities and formatting functions for KuzuMemory CLI.

Provides Rich-based formatting functions and fallbacks for terminal output.
"""

# Rich imports for beautiful CLI output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Initialize rich console
console = Console() if RICH_AVAILABLE else None


def rich_print(text, style=None, **kwargs):
    """Print with rich formatting if available, fallback to regular print."""
    if RICH_AVAILABLE and console:
        console.print(text, style=style, **kwargs)
    else:
        print(text)


def rich_panel(content, title=None, style="blue"):
    """Create a rich panel if available, fallback to simple formatting."""
    if RICH_AVAILABLE and console:
        console.print(Panel(content, title=title, border_style=style))
    else:
        if title:
            print(f"\n=== {title} ===")
        print(content)
        print("=" * (len(title) + 8) if title else "")


def rich_table(headers, rows, title=None):
    """Create a rich table if available, fallback to simple formatting."""
    if RICH_AVAILABLE and console:
        table = Table(title=title)
        for header in headers:
            table.add_column(header, style="cyan")
        for row in rows:
            table.add_row(*[str(cell) for cell in row])
        console.print(table)
    else:
        if title:
            print(f"\n{title}")
            print("-" * len(title))

        # Simple table formatting
        col_widths = [
            max(len(str(row[i])) for row in [headers, *rows])
            for i in range(len(headers))
        ]

        # Header
        header_row = " | ".join(
            headers[i].ljust(col_widths[i]) for i in range(len(headers))
        )
        print(header_row)
        print("-" * len(header_row))

        # Rows
        for row in rows:
            row_str = " | ".join(
                str(row[i]).ljust(col_widths[i]) for i in range(len(row))
            )
            print(row_str)


def rich_progress_bar(description="Processing..."):
    """Create a rich progress spinner if available."""
    if RICH_AVAILABLE:
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
    else:
        return None


def rich_confirm(message, default=True):
    """Create a rich confirmation prompt if available, fallback to input."""
    if RICH_AVAILABLE and console:
        return Confirm.ask(message, default=default, console=console)
    else:
        default_str = "Y/n" if default else "y/N"
        response = input(f"{message} [{default_str}]: ").strip().lower()
        if not response:
            return default
        return response in ["y", "yes"]


def rich_prompt(message, default=None):
    """Create a rich prompt if available, fallback to input."""
    if RICH_AVAILABLE and console:
        return Prompt.ask(message, default=default, console=console)
    else:
        default_str = f" [{default}]" if default else ""
        response = input(f"{message}{default_str}: ").strip()
        return response if response else default


def format_exception(e, debug=False):
    """Format exceptions for CLI output."""
    if debug:
        import traceback

        return traceback.format_exc()
    else:
        return str(e)


def format_database_size(size_bytes: int) -> str:
    """
    Format database size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "2.3 MB", "450 KB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_performance_stats(
    query_time_ms: float,
    total_memories: int,
    returned_count: int,
    db_size_bytes: int | None = None,
) -> str:
    """
    Format query performance statistics for display.

    Args:
        query_time_ms: Query execution time in milliseconds
        total_memories: Total number of memories in database
        returned_count: Number of memories returned by query
        db_size_bytes: Optional database size in bytes

    Returns:
        Formatted statistics string with appropriate styling
    """
    # Determine performance indicator
    if query_time_ms > 5000:
        time_icon = "🔴"
        time_style = "red bold"
        time_suffix = " (critical)"
    elif query_time_ms > 1000:
        time_icon = "⚠️ "
        time_style = "yellow"
        time_suffix = " (slow)"
    elif query_time_ms > 500:
        time_icon = "⚠️ "
        time_style = "yellow"
        time_suffix = ""
    else:
        time_icon = "📊"
        time_style = "dim"
        time_suffix = ""

    # Format the statistics line
    parts = [
        f"{time_icon} Query: {query_time_ms:.0f}ms{time_suffix}",
        f"Total: {total_memories:,} memories",
        f"Returned: {returned_count}",
    ]

    if db_size_bytes is not None:
        parts.append(f"DB: {format_database_size(db_size_bytes)}")

    stats_line = " | ".join(parts)

    # Add performance tip if slow
    if query_time_ms > 1000:
        tip = "\n💡 Tip: Large databases may need optimization. Consider running 'kuzu-memory optimize' (if available)"
        return (stats_line, time_style, tip)

    return (stats_line, time_style, None)
