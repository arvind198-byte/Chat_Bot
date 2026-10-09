"""
SQLite persistence layer for the Gemini chatbot.

Tables
------
chats    – id, title, created_at, updated_at
messages – id, chat_id (FK → chats.id), role, content, created_at

Every public function opens its own connection via the _connect() context
manager, which enforces foreign keys and ensures the connection is closed
even on error.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

# Always resolve the DB path relative to *this* file so the app never
# creates a second database when launched from a different working directory.
_DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DB_DIR, "chatbot.db")


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

@contextmanager
def _connect():
    """Yield a sqlite3 connection with foreign keys enabled, then close it."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row          # access columns by name
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation & migration
# ---------------------------------------------------------------------------

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
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        """)

        # --- Safe migration: add updated_at if it doesn't exist yet --------
        columns = [row["name"] for row in cur.execute("PRAGMA table_info(chats)")]
        if "updated_at" not in columns:
            # SQLite does not allow non-constant defaults in ALTER TABLE,
            # so we add the column with no default and backfill manually.
            cur.execute("ALTER TABLE chats ADD COLUMN updated_at TIMESTAMP")
            cur.execute("UPDATE chats SET updated_at = created_at WHERE updated_at IS NULL")

        conn.commit()


# ---------------------------------------------------------------------------
# Chat CRUD
# ---------------------------------------------------------------------------

def create_chat(title: str = "New Chat") -> int:
    """Insert a new chat row and return its id."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO chats (title) VALUES (?)",
            (title,),
        )
        conn.commit()
        return cur.lastrowid


def get_chats() -> list[dict]:
    """Return all chats ordered by most-recently updated first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chats ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_chat(chat_id: int) -> Optional[dict]:
    """Return one chat, or ``None`` when it does not exist."""
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
    """Delete a chat and all its messages.

    Messages are deleted explicitly rather than relying on ON DELETE CASCADE
    because the original schema may not have included that clause and SQLite
    does not allow altering foreign-key constraints on existing tables.
    """
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cur = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()
        return cur.rowcount > 0


def save_exchange(
    chat_id: int,
    user_content: str,
    assistant_content: str,
    title: Optional[str] = None,
) -> None:
    """Persist a successful user/assistant exchange atomically."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, 'user', ?)",
            (chat_id, user_content),
        )
        conn.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, 'assistant', ?)",
            (chat_id, assistant_content),
        )
        if title is None:
            conn.execute(
                "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (chat_id,),
            )
        else:
            conn.execute(
                "UPDATE chats SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, chat_id),
            )
        conn.commit()


# ---------------------------------------------------------------------------
# Message CRUD
# ---------------------------------------------------------------------------

def save_message(chat_id: int, role: str, content: str) -> int:
    """Insert a message and bump the parent chat's updated_at timestamp.

    Returns the new message id.
    """
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )
        conn.execute(
            "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (chat_id,),
        )
        conn.commit()
        return cur.lastrowid


def get_messages(chat_id: int) -> list[dict]:
    """Return messages for a chat in chronological (insertion) order."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, chat_id, role, content, created_at "
            "FROM messages WHERE chat_id = ? ORDER BY id ASC",
            (chat_id,),
        ).fetchall()
        return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Standalone usage – initialise the database from the command line.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print("Database initialised successfully!")
