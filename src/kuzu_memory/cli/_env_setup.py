"""
Set environment variables required by kuzu-memory before heavy imports.

This module must be imported before sentence_transformers or tokenizers
are loaded. Placing the side-effect here avoids ruff E402 in commands.py.
"""

from __future__ import annotations

import os

# Prevent the HuggingFace tokenizers Rust thread-pool from printing a
# "this process got forked" warning when the CLI forks child processes
# (e.g. hooks_commands.py).  setdefault does not override an explicit
# user-set value.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
