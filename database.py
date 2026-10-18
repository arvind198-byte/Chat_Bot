"""
SQLite persistence layer for the Placement Cell Chatbot.

Tables:
- chats: id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, created_at TIMESTAMP, updated_at TIMESTAMP
- messages: id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, role TEXT, content TEXT, latency_ms INTEGER, tokens_used INTEGER, created_at TIMESTAMP
- feedback: id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER, rating INTEGER, created_at TIMESTAMP
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

_DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DB_DIR, "chatbot.db")


@contextmanager
def _connect():
    """Yield a sqlite3 connection with foreign keys enabled, then close it."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist and apply safe migrations."""
    with _connect() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                latency_ms  INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                rating     INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            )
        """)

        # Safe schema migrations for existing database files
        msg_cols = [row["name"] for row in cur.execute("PRAGMA table_info(messages)")]
        if "latency_ms" not in msg_cols:
            cur.execute("ALTER TABLE messages ADD COLUMN latency_ms INTEGER DEFAULT 0")
        if "tokens_used" not in msg_cols:
            cur.execute("ALTER TABLE messages ADD COLUMN tokens_used INTEGER DEFAULT 0")

        chat_cols = [row["name"] for row in cur.execute("PRAGMA table_info(chats)")]
        if "updated_at" not in chat_cols:
            cur.execute("ALTER TABLE chats ADD COLUMN updated_at TIMESTAMP")
            cur.execute("UPDATE chats SET updated_at = created_at WHERE updated_at IS NULL")

        conn.commit()


def create_chat(title: str = "New Chat") -> int:
    """Insert a new chat and return its id."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO chats (title) VALUES (?)",
            (title,),
        )
        conn.commit()
        return cur.lastrowid


def get_chats() -> list[dict]:
    """Return all chats ordered by most recently updated first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chats ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_chat(chat_id: int) -> Optional[dict]:
    """Return one chat, or None when it does not exist."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone()
        return dict(row) if row else None


def update_chat_title(chat_id: int, title: str) -> None:
    """Set a new title for the given chat."""
    with _connect() as conn:
        conn.execute(
            "UPDATE chats SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, chat_id),
        )
        conn.commit()


def delete_chat(chat_id: int) -> bool:
    """Delete a chat and all its associated messages and feedback."""
    with _connect() as conn:
        # Delete feedback associated with this chat's messages
        conn.execute("""
            DELETE FROM feedback WHERE message_id IN (
                SELECT id FROM messages WHERE chat_id = ?
            )
        """, (chat_id,))
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cur = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()
        return cur.rowcount > 0


class MessageResult(int):
    """An int subclass that carries message metadata."""
    message_id: int
    created_at: Optional[str]

    def __new__(cls, message_id: int, created_at: Optional[str] = None):
        obj = super().__new__(cls, message_id)
        obj.message_id = message_id
        obj.created_at = created_at
        return obj


class ExchangeResult(int):
    """An int subclass that carries exchange metadata."""
    assistant_msg_id: int
    user_msg_id: int
    created_at: Optional[str]
    user_created_at: Optional[str]

    def __new__(
        cls,
        assistant_msg_id: int,
        user_msg_id: int = 0,
        created_at: Optional[str] = None,
        user_created_at: Optional[str] = None,
    ):
        obj = super().__new__(cls, assistant_msg_id)
        obj.assistant_msg_id = assistant_msg_id
        obj.user_msg_id = user_msg_id
        obj.created_at = created_at
        obj.user_created_at = user_created_at
        return obj


def save_exchange(
    chat_id: int,
    user_msg: str,
    bot_msg: str,
    title: Optional[str] = None,
    latency_ms: int = 0,
    tokens_used: int = 0,
) -> ExchangeResult:
    """Persist both the user message and assistant message, returning assistant message id with timestamps."""
    with _connect() as conn:
        cur_user = conn.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, 'user', ?)",
            (chat_id, user_msg),
        )
        user_msg_id = cur_user.lastrowid

        cur_bot = conn.execute(
            "INSERT INTO messages (chat_id, role, content, latency_ms, tokens_used) VALUES (?, 'assistant', ?, ?, ?)",
            (chat_id, bot_msg, latency_ms, tokens_used),
        )
        assistant_msg_id = cur_bot.lastrowid

        user_row = conn.execute("SELECT created_at FROM messages WHERE id = ?", (user_msg_id,)).fetchone()
        bot_row = conn.execute("SELECT created_at FROM messages WHERE id = ?", (assistant_msg_id,)).fetchone()
        user_created_at = user_row["created_at"] if user_row else None
        bot_created_at = bot_row["created_at"] if bot_row else None

        if title is not None:
            conn.execute(
                "UPDATE chats SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, chat_id),
            )
        else:
            conn.execute(
                "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (chat_id,),
            )
        conn.commit()
        return ExchangeResult(
            assistant_msg_id,
            user_msg_id=user_msg_id,
            created_at=bot_created_at,
            user_created_at=user_created_at,
        )


def save_message(chat_id: int, role: str, content: str, latency_ms: int = 0, tokens_used: int = 0) -> MessageResult:
    """Insert a single message and update chat timestamp. Provided for direct operations and test compatibility."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (chat_id, role, content, latency_ms, tokens_used) VALUES (?, ?, ?, ?, ?)",
            (chat_id, role, content, latency_ms, tokens_used),
        )
        msg_id = cur.lastrowid
        row = conn.execute("SELECT created_at FROM messages WHERE id = ?", (msg_id,)).fetchone()
        created_at = row["created_at"] if row else None
        conn.execute(
            "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (chat_id,),
        )
        conn.commit()
        return MessageResult(msg_id, created_at=created_at)


def save_feedback(message_id: int, rating: int) -> int:
    """Store thumbs up (+1) or thumbs down (-1) feedback for an assistant message."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO feedback (message_id, rating) VALUES (?, ?)",
            (message_id, rating),
        )
        conn.commit()
        return cur.lastrowid


def get_messages(chat_id: int) -> list[dict]:
    """Return all messages for a chat with latency and tokens metadata."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, chat_id, role, content, latency_ms, tokens_used, created_at "
            "FROM messages WHERE chat_id = ? ORDER BY id ASC",
            (chat_id,),
        ).fetchall()
        return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with chats, messages, and feedback tables.")
