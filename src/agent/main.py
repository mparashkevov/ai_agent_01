from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any, Dict

from .utils.config import get_config
from .tools import (
    read_file,
    write_file,
    fetch_url,
    run_command,
    build_index,
    query_index,
    pull_model,
    generate,
)

cfg = get_config()

app = FastAPI(title="ai_agent_01")


class RunRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}


@app.get("/health")
async def health():
    return {"status": "ok", "base_dir": cfg.agent_base_dir}


@app.get("/")
async def root():
        """Serve a minimal chat UI for quick local testing and interaction."""
        chat_html = """
        <!doctype html>
        <html>
            <head>
                <meta charset="utf-8" />
                <title>ai_agent_01 — Chat</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 900px; margin: 2rem auto; }
                    #chat { border: 1px solid #ddd; padding: 1rem; height: 60vh; overflow:auto; background:#f9f9f9 }
                    .msg { margin: 0.5rem 0 }
                    .user { color: #0b5cff }
                    .bot { color: #111 }
                    #controls { margin-top: 1rem; display:flex; gap:8px }
                    textarea { flex:1; height:64px }
                </style>
            </head>
            <body>
                <h2>ai_agent_01 — Chat (local)</h2>
                <div id="chat"></div>
                <div id="controls">
                    <textarea id="prompt" placeholder="Type your message..."></textarea>
                    <button id="send">Send</button>
                </div>
                <script>
                    const chat = document.getElementById('chat');
                    const prompt = document.getElementById('prompt');
                    const send = document.getElementById('send');

                    function append(role, text){
                        const el = document.createElement('div');
                        el.className = 'msg';
                        el.innerHTML = `<b class="${role}">${role}:</b> <span>${text.replace(/\n/g,'<br/>')}</span>`;
                        chat.appendChild(el);
                        chat.scrollTop = chat.scrollHeight;
                    }

                    send.addEventListener('click', async ()=>{
                        const value = prompt.value.trim();
                        if(!value) return;
                        append('user', value);
                        prompt.value = '';
                        append('bot', '...');
                        try{
                            const resp = await fetch('/chat', {
                                method: 'POST', headers:{'Content-Type':'application/json'},
                                body: JSON.stringify({prompt: value})
                            });
                            const data = await resp.json();
                            // remove the last '...' placeholder
                            chat.removeChild(chat.lastChild);
                            if(data.ok){
                                append('bot', data.response || '(empty)');
                            } else {
                                append('bot', 'Error: '+(data.error||JSON.stringify(data)) );
                            }
                        }catch(e){
                            chat.removeChild(chat.lastChild);
                            append('bot', 'Network error: '+e.message);
                        }
                    });
                </script>
            </body>
        </html>
        """
        return HTMLResponse(content=chat_html, status_code=200)


class ChatRequest(BaseModel):
        prompt: str
        model: str | None = None
        temperature: float | None = 0.0


@app.post('/chat')
async def chat_endpoint(req: ChatRequest):
        """Simple chat endpoint — sends the prompt to the configured local LLM (Ollama) via `ollama.generate`.

        This endpoint is intentionally minimal: for production use add auth, rate limits, and streaming.
        """
        prompt = req.prompt or ""
        model = req.model
        temp = req.temperature if req.temperature is not None else 0.0
        try:
                ok, out = generate(prompt, model=model, temperature=float(temp))
                if ok:
                        return {"ok": True, "response": out}
                return {"ok": False, "error": out}
        except Exception as e:
                return {"ok": False, "error": str(e)}


@app.get("/tools")
async def tools_list():
    return {
        "tools": [
            "file.read",
            "file.write",
            "web.fetch",
            "shell.run",
            "index.build",
            "index.query",
            "ollama.pull",
            "ollama.generate",
        ]
    }


@app.post("/run")
async def run(req: RunRequest):
    tool = req.tool
    params = req.params or {}

    if tool == "file.read":
        ok, out = read_file(params.get("path", ""))
        if not ok:
            raise HTTPException(status_code=400, detail=out)
        return {"result": out}

    if tool == "file.write":
        ok, out = write_file(params.get("path", ""), params.get("content", ""))
        if not ok:
            raise HTTPException(status_code=400, detail=out)
        return {"result": out}

    if tool == "web.fetch":
        ok, out = fetch_url(params.get("url", ""), timeout=params.get("timeout", 10))
        if not ok:
            raise HTTPException(status_code=400, detail=out)
        return {"result": out}

    if tool == "shell.run":
        ok, out = run_command(params.get("cmd", ""), timeout=params.get("timeout", 30), cwd=params.get("cwd"))
        if not ok:
            raise HTTPException(status_code=400, detail=out)
        return {"result": out}

    if tool == "index.build":
        ok, out = build_index(params.get("index_name", "default"), docs_path=params.get("docs_path"))
        if not ok:
            raise HTTPException(status_code=400, detail=out)
        return {"result": out}

    if tool == "index.query":
        ok, out = query_index(params.get("index_name", "default"), query=params.get("query", ""), top_k=params.get("top_k", 3), docs_path=params.get("docs_path"))
        if not ok:
            raise HTTPException(status_code=400, detail=out)
        return {"result": out}

    if tool == "ollama.pull":
        ok, out = pull_model(params.get("model"))
        if not ok:
            raise HTTPException(status_code=400, detail=out)
        return {"result": out}

    if tool == "ollama.generate":
        ok, out = generate(params.get("prompt", ""), model=params.get("model"), temperature=params.get("temperature", 0.0), max_tokens=params.get("max_tokens", 512))
        if not ok:
            raise HTTPException(status_code=400, detail=out)
        return {"result": out}

    raise HTTPException(status_code=404, detail="tool not found")
