import os
import subprocess
import requests
from typing import Tuple, Optional

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
    """Call local Ollama HTTP API to generate text. Returns (success, text_or_error)."""
    model = model or OLLAMA_DEFAULT_MODEL
    url = OLLAMA_URL.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        # Ollama may return streaming; for simple usage, read text body
        return True, resp.text
    except Exception as e:
        return False, str(e)
