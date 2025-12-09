import os
import subprocess
from typing import Tuple, Optional, AsyncIterator

import httpx

from ..utils.config import get_config

cfg = get_config()

# Defaults
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama-3.1")


def pull_model(model: Optional[str] = None, timeout: int = 300) -> Tuple[bool, str]:
    """Pull a model using the `ollama` CLI. Returns (success, output)."""
    model = model or OLLAMA_DEFAULT_MODEL
    try:
        proc = subprocess.run(["ollama", "pull", model], capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return False, proc.stderr or proc.stdout
        return True, proc.stdout
    except FileNotFoundError:
        return False, "ollama CLI not found; install ollama from https://ollama.com"
    except Exception as e:
        return False, str(e)


def generate(prompt: str, model: Optional[str] = None, temperature: float = 0.0, max_tokens: int = 512) -> Tuple[bool, str]:
    """Call local Ollama HTTP API to generate text synchronously. Returns (success, text_or_error)."""
    model = model or OLLAMA_DEFAULT_MODEL
    url = OLLAMA_URL.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = httpx.post(url, json=payload, timeout=60.0)
        resp.raise_for_status()
        return True, resp.text
    except Exception as e:
        return False, str(e)


async def generate_stream(prompt: str, model: Optional[str] = None, temperature: float = 0.0, max_tokens: int = 512) -> AsyncIterator[str]:
    """Asynchronously stream model output from Ollama. Yields text chunks."""
    model = model or OLLAMA_DEFAULT_MODEL
    url = OLLAMA_URL.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # request streaming if Ollama supports it
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_text():
                if chunk:
                    yield chunk
