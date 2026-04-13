"""Local LLM detection and client for kuzu-memory.

Canonical local-LLM interface for kuzu-memory projects.
Supports Ollama and LM Studio via OpenAI-compatible /v1/chat/completions.
Both sync (chat_completion) and streaming (stream_chat_completion) variants.

Env vars:
  OLLAMA_HOST       Override Ollama base URL (default http://localhost:11434)
  OLLAMA_MODEL      Force a specific model, skipping preference selection
  LM_STUDIO_URL     Override LM Studio base URL (default http://localhost:1234)
"""
from __future__ import annotations

import json
import logging
import os
import socket
import urllib.request
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)

OLLAMA_DEFAULT_HOST = "localhost"
OLLAMA_DEFAULT_PORT = 11434
LM_STUDIO_DEFAULT_PORT = 1234

# Embedding-only models that don't support chat completions — excluded from detection.
# These models answer /api/tags but return errors on /v1/chat/completions.
_EMBEDDING_ONLY_PATTERNS = (
    "all-minilm",
    "nomic-embed",
    "mxbai-embed",
    "snowflake-arctic-embed",
    "bge-",
    "gte-",
    "e5-",
    "text-embedding",
)


@dataclass
class LocalLLMInfo:
    """Information about a detected local LLM provider."""

    available: bool
    provider: str  # "ollama" | "lm_studio" | "none"
    endpoint: str
    models: list[str] = field(default_factory=list)
    default_model: str = ""


def _tcp_probe(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a TCP port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


def _ollama_list_models(endpoint: str, timeout: float = 2.0) -> list[str]:
    """Query Ollama /api/tags for available models."""
    try:
        url = f"{endpoint}/api/tags"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _lm_studio_list_models(endpoint: str, timeout: float = 2.0) -> list[str]:
    """Query LM Studio /v1/models for available models."""
    try:
        url = f"{endpoint}/v1/models"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return [m["id"] for m in data.get("data", [])]
    except Exception:
        return []


def detect_local_llm() -> LocalLLMInfo:
    """Probe for available local LLM providers. Returns first available."""
    from urllib.parse import urlparse

    # Check Ollama
    ollama_host = os.environ.get(
        "OLLAMA_HOST", f"http://{OLLAMA_DEFAULT_HOST}:{OLLAMA_DEFAULT_PORT}"
    )
    ollama_url = ollama_host if ollama_host.startswith("http") else f"http://{ollama_host}"
    parsed = urlparse(ollama_url)
    ollama_port = parsed.port or OLLAMA_DEFAULT_PORT
    ollama_hostname = parsed.hostname or OLLAMA_DEFAULT_HOST

    if _tcp_probe(ollama_hostname, ollama_port):
        models = _ollama_list_models(ollama_url)

        # Honour explicit model override before doing any preference logic
        explicit_model = os.environ.get("OLLAMA_MODEL", "")
        if explicit_model:
            logger.info("Using OLLAMA_MODEL override %r at %s", explicit_model, ollama_url)
            return LocalLLMInfo(
                available=True,
                provider="ollama",
                endpoint=ollama_url,
                models=models if models else [explicit_model],
                default_model=explicit_model,
            )

        if models:
            # Filter out embedding-only models (no chat completion support)
            chat_models = [
                m for m in models if not any(p in m.lower() for p in _EMBEDDING_ONLY_PATTERNS)
            ]
            if not chat_models:
                logger.debug("Ollama running but only embedding models found — skipping")
            else:
                # Prefer qwen > gemma3 > gemma4 > gemma2 > gemma > llama3.2 > phi
                # Cross-project benchmark (kuzu-memory + mcp-vector-search) confirms
                # qwen2.5-coder:7b-instruct has the best speed/quality for memory ops.
                # gemma4 benchmarked below qwen despite MoE architecture.
                preferred = next(
                    (
                        m
                        for m in chat_models
                        if any(
                            s in m.lower()
                            for s in (
                                "qwen",
                                "gemma3",
                                "gemma4",
                                "gemma2",
                                "gemma",
                                "llama3.2",
                                "phi",
                            )
                        )
                    ),
                    chat_models[0],
                )
                logger.info(
                    "Detected Ollama at %s: %d chat models (%d total)",
                    ollama_url,
                    len(chat_models),
                    len(models),
                )
                return LocalLLMInfo(
                    available=True,
                    provider="ollama",
                    endpoint=ollama_url,
                    models=chat_models,
                    default_model=preferred,
                )

    # Check LM Studio
    lm_url = os.environ.get("LM_STUDIO_URL", f"http://localhost:{LM_STUDIO_DEFAULT_PORT}")
    parsed_lm = urlparse(lm_url)
    lm_port = parsed_lm.port or LM_STUDIO_DEFAULT_PORT
    lm_hostname = parsed_lm.hostname or "localhost"

    if _tcp_probe(lm_hostname, lm_port):
        models = _lm_studio_list_models(lm_url)
        if models:
            logger.info("Detected LM Studio at %s with %d models", lm_url, len(models))
            return LocalLLMInfo(
                available=True,
                provider="lm_studio",
                endpoint=lm_url,
                models=models,
                default_model=models[0],
            )

    logger.debug("No local LLM detected (Ollama port %d, LM Studio port %d)", ollama_port, lm_port)
    return LocalLLMInfo(available=False, provider="none", endpoint="", models=[], default_model="")


def _build_request(
    endpoint: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    stream: bool,
    temperature: float = 0.1,
) -> urllib.request.Request:
    """Build an OpenAI-compatible /v1/chat/completions request."""
    url = f"{endpoint.rstrip('/')}/v1/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
    ).encode()
    return urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )


def chat_completion(
    endpoint: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float = 30.0,
    max_tokens: int = 512,
) -> str:
    """
    Call OpenAI-compatible /v1/chat/completions (works for Ollama and LM Studio).

    Blocks until the full response is received. Use stream_chat_completion()
    for interactive/display use cases where time-to-first-token matters.

    Args:
        endpoint: Base URL of the local LLM server (e.g. http://localhost:11434).
        model: Model name to use for inference.
        messages: List of message dicts with 'role' and 'content' keys.
        timeout: Request timeout in seconds.
        max_tokens: Maximum tokens in the response.

    Returns:
        The assistant message content string.

    Raises:
        urllib.error.URLError: On connection failure.
        KeyError: If the response format is unexpected.
    """
    req = _build_request(endpoint, model, messages, max_tokens, stream=False)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return str(data["choices"][0]["message"]["content"])


def stream_chat_completion(
    endpoint: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float = 60.0,
    max_tokens: int = 2048,
) -> Generator[str, None, None]:
    """
    Stream an OpenAI-compatible /v1/chat/completions response token-by-token.

    Yields text chunks as they arrive (Server-Sent Events, ``data: {...}`` lines).
    Stops cleanly on ``data: [DONE]``. Safe to break out of early — the HTTP
    connection is closed when the generator is garbage-collected or explicitly
    closed.

    Usage::

        for chunk in stream_chat_completion(endpoint, model, messages):
            print(chunk, end="", flush=True)
        print()  # final newline

    Args:
        endpoint: Base URL (e.g. ``http://localhost:11434``).
        model: Model name.
        messages: Conversation messages.
        timeout: Socket read timeout in seconds (applied per-read, not total).
        max_tokens: Maximum tokens to generate.

    Yields:
        Token/chunk strings as they stream from the model.

    Raises:
        urllib.error.URLError: On connection failure before streaming starts.
    """
    req = _build_request(endpoint, model, messages, max_tokens, stream=True)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw_line in resp:
            line: str = raw_line.decode("utf-8").rstrip("\n\r")
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if payload == "[DONE]":
                return
            try:
                chunk = json.loads(payload)
                delta = chunk["choices"][0].get("delta", {})
                text = delta.get("content")
                if text:
                    yield text
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


def stream_chat_completion_full(
    endpoint: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float = 60.0,
    max_tokens: int = 2048,
) -> str:
    """
    Convenience wrapper: stream internally, return the full concatenated text.

    Useful when you want streaming's faster time-to-first-token behaviour at
    the HTTP level (avoids Ollama's non-streaming response buffering) but still
    need a single string result.

    Args: same as stream_chat_completion.

    Returns:
        Full assistant response as a single string.
    """
    return "".join(stream_chat_completion(endpoint, model, messages, timeout, max_tokens))
