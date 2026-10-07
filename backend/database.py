import sqlite3
import json
import uuid
import time
import threading

from config import DB_PATH

_lock = threading.Lock()


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                status TEXT NOT NULL,
                score REAL NOT NULL,
                results TEXT NOT NULL
            )
            """
        )


def save_session(results: dict, score: float, status: str) -> str:
    session_id = uuid.uuid4().hex[:12]
    with _lock, _conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at, status, score, results) VALUES (?, ?, ?, ?, ?)",
            (session_id, time.time(), status, score, json.dumps(results)),
        )
    return session_id


def get_session(session_id: str):
    with _lock, _conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "status": row["status"],
        "score": row["score"],
        "results": json.loads(row["results"]),
    }
