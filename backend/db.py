import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import DB_PATH, DEFAULT_SYSTEM_PROMPT, HISTORY_LIMIT


SCHEMA = """
CREATE TABLE IF NOT EXISTS instances (
    name TEXT PRIMARY KEY,
    system_prompt TEXT NOT NULL,
    phone TEXT,
    status TEXT DEFAULT 'disconnected',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_name TEXT NOT NULL,
    jid TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_inst_jid
    ON messages (instance_name, jid, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def upsert_instance(name: str, system_prompt: str | None = None) -> None:
    with conn() as c:
        c.execute(
            """
            INSERT INTO instances (name, system_prompt, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT (name) DO UPDATE SET
                system_prompt = COALESCE(excluded.system_prompt, instances.system_prompt)
            """,
            (name, system_prompt or DEFAULT_SYSTEM_PROMPT, _now()),
        )


def update_instance_status(name: str, status: str) -> None:
    with conn() as c:
        c.execute("UPDATE instances SET status = ? WHERE name = ?", (status, name))


def update_instance_prompt(name: str, prompt: str) -> None:
    with conn() as c:
        c.execute(
            "UPDATE instances SET system_prompt = ? WHERE name = ?", (prompt, name)
        )


def set_instance_enabled(name: str, enabled: bool) -> None:
    with conn() as c:
        c.execute(
            "UPDATE instances SET enabled = ? WHERE name = ?",
            (1 if enabled else 0, name),
        )


def delete_instance(name: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM messages WHERE instance_name = ?", (name,))
        c.execute("DELETE FROM instances WHERE name = ?", (name,))


def get_instance(name: str) -> dict | None:
    with conn() as c:
        row = c.execute(
            "SELECT * FROM instances WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None


def list_instances() -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM instances ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def add_message(instance_name: str, jid: str, role: str, content: str) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO messages (instance_name, jid, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (instance_name, jid, role, content, _now()),
        )


def history(instance_name: str, jid: str, limit: int = HISTORY_LIMIT) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            """
            SELECT role, content FROM messages
            WHERE instance_name = ? AND jid = ?
            ORDER BY id DESC LIMIT ?
            """,
            (instance_name, jid, limit),
        ).fetchall()
        return list(reversed([dict(r) for r in rows]))


def recent_conversations(instance_name: str, limit: int = 20) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            """
            SELECT jid,
                   MAX(created_at) AS last_at,
                   COUNT(*) AS n_messages
            FROM messages
            WHERE instance_name = ?
            GROUP BY jid
            ORDER BY last_at DESC
            LIMIT ?
            """,
            (instance_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]
