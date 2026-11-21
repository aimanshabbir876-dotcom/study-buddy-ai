# database.py
# Saves chats, messages, uploaded-file text and settings in a local SQLite file.
# SQLite is built into Python, so nothing extra needs to be installed.
# Each chat has an "owner" so that different visitors only see their own chats.

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# The database file is created next to this script
DB_PATH = Path(__file__).parent / "study_buddy.db"

# Owner used for chats that existed before owners were added (and for local use)
DEFAULT_OWNER = "local"


@contextmanager
def get_connection():
    """Opens the database, saves changes, and always closes it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now():
    return datetime.now().isoformat(timespec="microseconds")


def init_db():
    """Creates the tables the first time the app runs."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                mode       TEXT NOT NULL,
                language   TEXT NOT NULL,
                level      TEXT NOT NULL,
                doc_name   TEXT,
                doc_text   TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                owner      TEXT NOT NULL DEFAULT 'local'
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        # Older databases do not have the "owner" column yet, so add it.
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(chats)")]
        if "owner" not in columns:
            conn.execute("ALTER TABLE chats ADD COLUMN owner TEXT NOT NULL DEFAULT 'local'")


# ---------- Chats ----------

def create_chat(title, mode, language, level, owner=DEFAULT_OWNER):
    """Creates a new chat for an owner and returns its id."""
    timestamp = now()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO chats (title, mode, language, level, created_at, updated_at, owner) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, mode, language, level, timestamp, timestamp, owner),
        )
        return cursor.lastrowid


def list_chats(owner=DEFAULT_OWNER):
    """Returns the owner's chats, newest activity first (without the big file text)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, mode, language, level, doc_name, created_at, updated_at "
            "FROM chats WHERE owner = ? ORDER BY updated_at DESC, id DESC",
            (owner,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_chat(chat_id, owner=None):
    """Returns one chat (including its file text) or None.
    If an owner is given, the chat is returned only when it belongs to that owner."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    if row is None:
        return None
    chat = dict(row)
    if owner is not None and chat["owner"] != owner:
        return None
    return chat


def rename_chat(chat_id, new_title):
    with get_connection() as conn:
        conn.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))


def update_chat_settings(chat_id, mode, language, level):
    with get_connection() as conn:
        conn.execute(
            "UPDATE chats SET mode = ?, language = ?, level = ? WHERE id = ?",
            (mode, language, level, chat_id),
        )


def delete_chat(chat_id):
    """Deletes a chat and all of its messages."""
    with get_connection() as conn:
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))


# ---------- Messages ----------

def add_message(chat_id, role, content):
    timestamp = now()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, timestamp),
        )
        conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (timestamp, chat_id))


def get_messages(chat_id):
    """Returns messages in order, as a list like [{"role": "user", "content": "Hi"}]."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_messages(chat_id):
    """Removes the messages of a chat but keeps the chat itself in the history."""
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))


# ---------- Uploaded study material ----------

def set_document(chat_id, doc_name, doc_text):
    """Attaches a file's text to a chat. Pass None, None to remove it."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE chats SET doc_name = ?, doc_text = ? WHERE id = ?",
            (doc_name, doc_text, chat_id),
        )


# ---------- Settings (language, level, dark mode) ----------

def _setting_key(key, owner):
    """Settings of the default owner keep their old names; others get a prefix."""
    return key if owner == DEFAULT_OWNER else f"{owner}:{key}"


def get_setting(key, default=None, owner=DEFAULT_OWNER):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (_setting_key(key, owner),)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key, value, owner=DEFAULT_OWNER):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_setting_key(key, owner), str(value)),
        )


# ---------- Statistics for the home page ----------

def get_stats(owner=DEFAULT_OWNER):
    with get_connection() as conn:
        chats = conn.execute(
            "SELECT COUNT(*) FROM chats WHERE owner = ?", (owner,)
        ).fetchone()[0]
        questions = conn.execute(
            "SELECT COUNT(*) FROM messages m JOIN chats c ON c.id = m.chat_id "
            "WHERE m.role = 'user' AND c.owner = ?",
            (owner,),
        ).fetchone()[0]
        files = conn.execute(
            "SELECT COUNT(*) FROM chats WHERE doc_name IS NOT NULL AND owner = ?", (owner,)
        ).fetchone()[0]
    return {"chats": chats, "questions": questions, "files": files}