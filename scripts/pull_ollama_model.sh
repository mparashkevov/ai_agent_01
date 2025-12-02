#!/usr/bin/env bash
set -euo pipefail

MODEL=${1:-llama-3.1}

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama CLI not found. Install from https://ollama.com"
  exit 2
fi

echo "Pulling model $MODEL via ollama..."
ollama pull "$MODEL"
echo "Done."
