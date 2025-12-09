import os
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime

from .config import get_config

cfg = get_config()

_DB_PATH = os.path.join(cfg.agent_base_dir, "agent_sessions.db")


def _conn():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    return conn


def init_db():
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            text TEXT,
            ts TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def create_session(session_id: str) -> None:
    init_db()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO sessions(session_id, created_at) VALUES(?,?)", (session_id, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, text: str) -> None:
    init_db()
    create_session(session_id)
    conn = _conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO messages(session_id, role, text, ts) VALUES(?,?,?,?)", (session_id, role, text, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_history(session_id: str) -> List[Dict]:
    init_db()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT role, text, ts FROM messages WHERE session_id = ? ORDER BY id", (session_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"role": r[0], "text": r[1], "ts": r[2]} for r in rows]


def list_sessions() -> List[Dict]:
    init_db()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT session_id, created_at FROM sessions ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"session_id": r[0], "created_at": r[1]} for r in rows]


def clear_session(session_id: str) -> None:
    init_db()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cur.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
