#!/usr/bin/env sh
set -e

# Entry point for containerized agent
exec uvicorn src.agent.main:app --host 0.0.0.0 --port 8000
