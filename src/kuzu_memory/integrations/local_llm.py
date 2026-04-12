"""Local LLM detection and client for kuzu-memory."""
from __future__ import annotations

import json
import logging
import os
import socket
import urllib.request
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

OLLAMA_DEFAULT_HOST = "localhost"
OLLAMA_DEFAULT_PORT = 11434
LM_STUDIO_DEFAULT_PORT = 1234


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
        if models:
            # Prefer smaller/faster models for memory ops
            preferred = next(
                (
                    m
                    for m in models
                    if any(s in m.lower() for s in ("phi", "llama3.2", "qwen", "gemma"))
                ),
                models[0],
            )
            logger.info("Detected Ollama at %s with %d models", ollama_url, len(models))
            return LocalLLMInfo(
                available=True,
                provider="ollama",
                endpoint=ollama_url,
                models=models,
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


def chat_completion(
    endpoint: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float = 30.0,
    max_tokens: int = 512,
) -> str:
    """
    Call OpenAI-compatible /v1/chat/completions (works for Ollama and LM Studio).

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
    url = f"{endpoint.rstrip('/')}/v1/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "stream": False,
        }
    ).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return str(data["choices"][0]["message"]["content"])
