import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from app.config import settings

DEFAULT_TITLE = "新对话"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    db_path = settings.database_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   TEXT NOT NULL,
                role              TEXT NOT NULL,
                content           TEXT NOT NULL,
                reasoning_content TEXT NOT NULL DEFAULT '',
                created_at        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, id);
            """
        )
        # 兼容老库：已存在但缺少 reasoning_content 列时补上
        cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
        if "reasoning_content" not in cols:
            conn.execute(
                "ALTER TABLE messages ADD COLUMN reasoning_content TEXT NOT NULL DEFAULT ''"
            )


def create_conversation(title: str | None = None) -> dict:
    conv_id = uuid.uuid4().hex
    now = _now()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, title or DEFAULT_TITLE, now, now),
        )
    return {"id": conv_id, "title": title or DEFAULT_TITLE, "created_at": now, "updated_at": now}


def get_conversation(conv_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
    return dict(row) if row else None


def list_conversations() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def rename_conversation(conv_id: str, title: str) -> dict | None:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, _now(), conv_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_conversation(conv_id: str) -> bool:
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    return cur.rowcount > 0


def touch_conversation(conv_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (_now(), conv_id)
        )


def add_message(
    conv_id: str, role: str, content: str, reasoning_content: str = ""
) -> dict:
    created_at = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, reasoning_content, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (conv_id, role, content, reasoning_content, created_at),
        )
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    touch_conversation(conv_id)
    return dict(row)


def get_messages(conv_id: str, limit: int | None = None) -> list[dict]:
    if limit is not None:
        sql = (
            "SELECT * FROM ("
            "  SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?"
            ") ORDER BY id ASC"
        )
        params: tuple = (conv_id, limit)
    else:
        sql = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC"
        params = (conv_id,)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def count_messages(conv_id: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE conversation_id = ?", (conv_id,)
        ).fetchone()
    return int(row["c"])


def ensure_conversation(conv_id: str | None, title: str | None = None) -> dict:
    """返回已有会话，否则创建新会话。"""
    if conv_id:
        conv = get_conversation(conv_id)
        if conv is None:
            raise ValueError(f"会话不存在: {conv_id}")
        return conv
    return create_conversation(title)


def auto_title_if_default(conv_id: str, first_message: str) -> None:
    conv = get_conversation(conv_id)
    if conv and conv["title"] == DEFAULT_TITLE:
        title = first_message.strip().replace("\n", " ")[:20]
        if title:
            rename_conversation(conv_id, title)
