from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from .utils.config import get_config
from .tools import read_file, write_file, fetch_url, run_command

cfg = get_config()

app = FastAPI(title="ai_agent_01")


class RunRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}


@app.get("/health")
async def health():
    return {"status": "ok", "base_dir": cfg.agent_base_dir}


@app.get("/tools")
async def tools_list():
    return {"tools": ["file.read", "file.write", "web.fetch", "shell.run"]}


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

    raise HTTPException(status_code=404, detail="tool not found")
