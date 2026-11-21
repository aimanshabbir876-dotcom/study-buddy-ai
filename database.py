# database.py
# Saves chats, messages, uploaded-file text and settings in a local SQLite file.
# SQLite is built into Python, so nothing extra needs to be installed.

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# The database file is created next to this script
DB_PATH = Path(__file__).parent / "study_buddy.db"


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
                updated_at TEXT NOT NULL
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


# ---------- Chats ----------

def create_chat(title, mode, language, level):
    """Creates a new chat and returns its id."""
    timestamp = now()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO chats (title, mode, language, level, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, mode, language, level, timestamp, timestamp),
        )
        return cursor.lastrowid


def list_chats():
    """Returns all chats, newest activity first (without the big file text)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, mode, language, level, doc_name, created_at, updated_at "
            "FROM chats ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_chat(chat_id):
    """Returns one chat (including its file text) or None."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    return dict(row) if row else None


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

def get_setting(key, default=None):
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


# ---------- Statistics for the home page ----------

def get_stats():
    with get_connection() as conn:
        chats = conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
        questions = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE role = 'user'"
        ).fetchone()[0]
        files = conn.execute(
            "SELECT COUNT(*) FROM chats WHERE doc_name IS NOT NULL"
        ).fetchone()[0]
    return {"chats": chats, "questions": questions, "files": files}