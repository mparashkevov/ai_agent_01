from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi import Path
import uuid
from typing import List
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
                    body { font-family: Arial, sans-serif; max-width: 1000px; margin: 2rem auto; }
                    #chat { border: 1px solid #ddd; padding: 1rem; height: 60vh; overflow:auto; background:#f9f9f9 }
                    .msg { margin: 0.5rem 0 }
                    .user { color: #0b5cff }
                    .bot { color: #111 }
                    #controls { margin-top: 1rem; display:flex; gap:8px }
                    textarea { flex:1; height:64px }
                    #meta { margin-bottom: 0.75rem; display:flex; gap:8px; align-items:center }
                    input[type=text] { padding:4px 6px }
                </style>
            </head>
            <body>
                <h2>ai_agent_01 — Chat (local)</h2>
                <div id="meta">
                    <div>Session: <span id="session_id">(new)</span></div>
                    <button id="new_session">New Session</button>
                    <button id="clear_session">Clear Session</button>
                    <label style="margin-left:8px">Docs path: <input id="docs_path" type="text" placeholder="notes"/></label>
                    <label><input id="use_index" type="checkbox"/> Use index</label>
                </div>
                <div id="chat"></div>
                <div id="controls">
                    <textarea id="prompt" placeholder="Type your message..."></textarea>
                    <button id="send">Send</button>
                </div>
                <script>
                    const chat = document.getElementById('chat');
                    const prompt = document.getElementById('prompt');
                    const send = document.getElementById('send');
                    const sessionEl = document.getElementById('session_id');
                    const newBtn = document.getElementById('new_session');
                    const clearBtn = document.getElementById('clear_session');
                    const docsPathEl = document.getElementById('docs_path');
                    const useIndexEl = document.getElementById('use_index');

                    let session_id = null;

                    function append(role, text){
                        const el = document.createElement('div');
                        el.className = 'msg';
                        el.innerHTML = `<b class="${role}">${role}:</b> <span>${text.replace(/\n/g,'<br/>')}</span>`;
                        chat.appendChild(el);
                        chat.scrollTop = chat.scrollHeight;
                    }

                    function setSession(id){
                        session_id = id;
                        sessionEl.textContent = id || '(new)';
                    }

                    newBtn.addEventListener('click', ()=>{ setSession(null); chat.innerHTML=''; append('bot','New session.'); });

                    clearBtn.addEventListener('click', async ()=>{
                        if(!session_id){ append('bot','No session to clear.'); return; }
                        try{
                            await fetch(`/sessions/${session_id}/clear`,{method:'POST'});
                            append('bot','Session cleared.');
                            setSession(null);
                            chat.innerHTML='';
                        }catch(e){ append('bot','Error clearing session: '+e.message); }
                    });

                    send.addEventListener('click', async ()=>{
                        const value = prompt.value.trim();
                        if(!value) return;
                        append('user', value);
                        prompt.value = '';
                        append('bot', '...');
                        try{
                            const body = { prompt: value, session_id: session_id, docs_path: docsPathEl.value || null, use_index: useIndexEl.checked };
                            const resp = await fetch('/chat', {
                                method: 'POST', headers:{'Content-Type':'application/json'},
                                body: JSON.stringify(body)
                            });
                            const data = await resp.json();
                            // remove the last '...' placeholder
                            chat.removeChild(chat.lastChild);
                            if(data.session_id) setSession(data.session_id);
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
    session_id: str | None = None
    model: str | None = None
    temperature: float | None = 0.0
    # If provided, agent will fetch docs from this path and include as context via index.query (or Ollama fallback)
    docs_path: str | None = None
    use_index: bool | None = False


# Simple in-memory session store: { session_id: [ {role:'user'|'assistant', 'text':...}, ... ] }
_sessions = {}


@app.post('/chat')
async def chat_endpoint(req: ChatRequest):
    """Session-aware chat. Keeps simple in-memory conversation history and optionally includes document context
    (via `index.query`) when `use_index` and `docs_path` are provided.

    Returns JSON: `{ ok: bool, session_id: str, response: str, history: [...] }`
    """
    prompt_text = (req.prompt or "").strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="empty prompt")

    sid = req.session_id or str(uuid.uuid4())
    # initialize session if missing
    if sid not in _sessions:
        _sessions[sid] = []

    # append user message
    _sessions[sid].append({"role": "user", "text": prompt_text})

    # build context string from history
    history_lines: List[str] = []
    for m in _sessions[sid]:
        role = m.get("role")
        text = m.get("text", "")
        if role == "user":
            history_lines.append(f"User: {text}")
        else:
            history_lines.append(f"Assistant: {text}")

    context_parts: List[str] = []
    # Optionally query index/docs for context
    if req.use_index and req.docs_path:
        ok_idx, out_idx = query_index(index_name="default", query=prompt_text, docs_path=req.docs_path)
        if ok_idx:
            context_parts.append(f"SearchResults:\n{out_idx}")
        else:
            context_parts.append(f"(index error: {out_idx})")

    # Compose system prompt: history + optional context
    system_prompt = "\n".join(history_lines[-20:])
    if context_parts:
        system_prompt = system_prompt + "\n\nContext:\n" + "\n\n".join(context_parts)

    # Final prompt to model
    final_prompt = system_prompt + "\n\nAssistant:" if system_prompt else f"User: {prompt_text}\nAssistant:"
    # If there is no system prompt (rare), include the current prompt explicitly
    if not system_prompt:
        final_prompt = f"User: {prompt_text}\nAssistant:"

    model = req.model
    temp = float(req.temperature or 0.0)

    try:
        ok, out = generate(final_prompt, model=model, temperature=temp)
        if not ok:
            # model/generator error
            _sessions[sid].append({"role": "assistant", "text": f"(error) {out}"})
            return {"ok": False, "session_id": sid, "error": out, "history": _sessions[sid]}

        # append assistant reply to session
        _sessions[sid].append({"role": "assistant", "text": out})
        return {"ok": True, "session_id": sid, "response": out, "history": _sessions[sid]}
    except Exception as e:
        _sessions[sid].append({"role": "assistant", "text": f"(exception) {str(e)}"})
        return {"ok": False, "session_id": sid, "error": str(e), "history": _sessions[sid]}


@app.get('/sessions/{session_id}')
async def get_session(session_id: str = Path(...)):
    """Return session history for given `session_id`."""
    return {"session_id": session_id, "history": _sessions.get(session_id, [])}


@app.post('/sessions/{session_id}/clear')
async def clear_session(session_id: str = Path(...)):
    """Clear session history."""
    _sessions.pop(session_id, None)
    return {"ok": True, "session_id": session_id}


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
