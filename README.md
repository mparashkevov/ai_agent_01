ai_agent_01 — Local AI Agent Runner

Lightweight local AI agent scaffold that exposes an HTTP API to run "tools" (file access, web fetch, shell commands) and is ready for Docker deployment.

Quickstart (local):

1. Create a virtual environment and install requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and adjust `AGENT_BASE_DIR` if needed.

3. Run the server:

```bash
uvicorn src.agent.main:app --host 0.0.0.0 --port 8000
```

Docker:

Build and run with Docker:

```bash
docker build -t ai_agent_01:latest .
docker run --rm -p 8000:8000 -v $(pwd):/workspace -e AGENT_BASE_DIR=/workspace ai_agent_01:latest
```

API endpoints:
- `GET /health` — health check
- `GET /tools` — list available tools
- `POST /run` — run a tool with JSON: `{ "tool": "file.read", "params": {...} }`

Security note: This scaffold allows local file and shell access; update `AGENT_BASE_DIR` and add authentication before exposing publicly.

LlamaIndex integration
----------------------
This project includes optional integration with the `llama-index` (LlamaIndex) library to build vector indexes over local documents and run queries.

Prerequisites:
- Set `OPENAI_API_KEY` (or configure the LLM provider you prefer) in the environment if you want to use an LLM-backed query engine.
- Install extra requirements: `pip install -r requirements.txt` (includes `llama-index` and `openai`).

Tools provided:
- `index.build` — build an index from files under a subfolder of `AGENT_BASE_DIR`. Example payload for `/run`:
	`{ "tool": "index.build", "params": { "index_name": "notes", "docs_path": "notes" } }`
- `index.query` — query a saved index. Example payload:
	`{ "tool": "index.query", "params": { "index_name": "notes", "query": "what did I write about deployment?" } }`

Security:
- Indexing and querying use an LLM provider; do not expose API keys in public repos. Restrict network access and require auth before exposing endpoints.
