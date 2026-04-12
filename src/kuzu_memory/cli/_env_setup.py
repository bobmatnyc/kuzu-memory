"""
Set environment variables required by kuzu-memory before heavy imports.

This module must be imported before sentence_transformers or tokenizers
are loaded. Placing the side-effect here avoids ruff E402 in commands.py.
"""

from __future__ import annotations

import os

# Prevent the HuggingFace tokenizers Rust thread-pool from printing a
# "this process just got forked" warning when the CLI forks child processes
# (e.g. hooks_commands.py).  Force-set (not setdefault) so the value is
# always present regardless of the caller's environment.
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Register an after-fork handler so the env var is also present in any child
# created via os.fork() directly (Python's multiprocessing 'fork' context on
# Linux triggers this path).  The after_in_child callback runs in the child
# process immediately after the fork, before any user code.
if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        after_in_child=lambda: os.environ.__setitem__("TOKENIZERS_PARALLELISM", "false")
    )
