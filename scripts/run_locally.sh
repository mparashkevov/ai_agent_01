#!/usr/bin/env bash
set -euo pipefail

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

uvicorn src.agent.main:app --host 0.0.0.0 --port 8000
