from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Path
import uuid
from typing import List, AsyncIterator, Dict, Any, Optional
from pydantic import BaseModel
import os
import asyncio
import json

from llama_index.llms.ollama import Ollama
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool

from .utils.config import get_config
from .utils import session_store
from .tools.weather_tool import weather_tool, WEATHER_TOOL_PROMPT

cfg = get_config()

app = FastAPI(title="ai_agent_01")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize LLM and Agent
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

def get_agent(session_id: str):
    # Initialize Ollama LLM
    llm = Ollama(base_url=OLLAMA_URL, model=OLLAMA_MODEL, request_timeout=300.0)
    
    # Create ReAct Agent
    agent = ReActAgent.from_tools(
        [weather_tool], 
        llm=llm, 
        verbose=True,
        context=WEATHER_TOOL_PROMPT
    )
    return agent

@app.get("/")
async def root():
    """Serve the main chat UI."""
    return FileResponse(os.path.join(static_dir, "index.html"))

class ChatRequest(BaseModel):
    prompt: str
    session_id: str | None = None
    model: str | None = None
    temperature: float | None = 0.0

# Use persistent session store (SQLite)
session_store.init_db()

@app.get("/health")
async def health():
    return {"status": "ok", "base_dir": cfg.agent_base_dir}

@app.post('/chat')
async def chat_endpoint(req: ChatRequest):
    """Session-aware chat."""
    prompt_text = (req.prompt or "").strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="empty prompt")

    sid = req.session_id or str(uuid.uuid4())
    session_store.create_session(sid)
    session_store.save_message(sid, "user", prompt_text)
    
    try:
        agent = get_agent(sid)
        # Run agent
        response = agent.chat(prompt_text)
        out = str(response)
    except Exception as e:
        print(f"Agent error: {e}")
        out = f"Error: {str(e)}"
    
    session_store.save_message(sid, "assistant", out)
    return {"ok": True, "session_id": sid, "response": out, "history": session_store.get_history(sid)}


@app.get('/sessions/{session_id}')
async def get_session(session_id: str = Path(...)):
    """Return session history for given `session_id`."""
    return {"session_id": session_id, "history": session_store.get_history(session_id)}


@app.post('/sessions/{session_id}/clear')
async def clear_session(session_id: str = Path(...)):
    """Clear session history."""
    session_store.clear_session(session_id)
    return {"ok": True, "session_id": session_id}


@app.get('/sessions')
async def list_sessions():
    """Return list of known sessions (persistent)."""
    return {"sessions": session_store.list_sessions()}


@app.websocket('/ws/chat')
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        prompt_text = (data.get('prompt') or '').strip()
        if not prompt_text:
            await websocket.send_json({'type': 'error', 'error': 'empty prompt'})
            await websocket.close()
            return

        sid = data.get('session_id') or str(uuid.uuid4())
        session_store.create_session(sid)
        session_store.save_message(sid, 'user', prompt_text)

        agent = get_agent(sid)
        
        # Stream response
        # Using agent.stream_chat(prompt_text)
        full_resp = ''
        try:
            streaming_response = agent.stream_chat(prompt_text)
            for token in streaming_response.response_gen:
                await websocket.send_json({'type': 'chunk', 'data': token})
                full_resp += token
                
            session_store.save_message(sid, 'assistant', full_resp)
            await websocket.send_json({'type': 'done', 'session_id': sid, 'response': full_resp})
            await websocket.close()
            
        except Exception as e:
            print(f"Streaming error: {e}")
            await websocket.send_json({'type': 'error', 'error': str(e)})
            await websocket.close()
            
    except WebSocketDisconnect:
        return
