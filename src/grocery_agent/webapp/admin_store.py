"""Runtime admin configuration store (runtime-admin capability).

Design decisions (see openspec/changes/add-web-dashboard/design.md):
- Admin configuration lives in its own SQLite file (default data/admin.db),
  never in the grocery data store.
- Seeded on first run from the default command questions and suggested
  questions in ``grocery_agent.telegram.commands``.
- Validation rejects empty command questions and empty suggestion entries.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from grocery_agent.telegram.commands import COMMAND_QUESTIONS, SUGGESTED_QUESTIONS

DEFAULT_ADMIN_DB = os.path.join("data", "admin.db")

_DDL = """
CREATE TABLE IF NOT EXISTS command (
    name     TEXT PRIMARY KEY,
    question TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suggested_question (
    text     TEXT PRIMARY KEY,
    position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS setting (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def default_admin_db_path() -> str:
    """Path of the admin store, defaulting to data/admin.db."""
    return os.environ.get("ADMIN_DB", DEFAULT_ADMIN_DB)


def connect_admin(db_path: str | None = None) -> sqlite3.Connection:
    """Open the admin store, creating parent directories and schema."""
    path = db_path or default_admin_db_path()
    parent = Path(path).parent
    if str(parent) not in {"", "."}:
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_DDL)
    return conn


def ensure_admin_store(
    db_path: str | None = None,
    commands: dict[str, str] | None = None,
    suggestions: tuple[str, ...] | list[str] | None = None,
) -> sqlite3.Connection:
    """Open the admin store, seeding defaults when empty (idempotent)."""
    commands = commands if commands is not None else COMMAND_QUESTIONS
    suggestions = suggestions if suggestions is not None else SUGGESTED_QUESTIONS
    conn = connect_admin(db_path)
    with conn:
        if not conn.execute("SELECT 1 FROM command LIMIT 1").fetchone():
            conn.executemany(
                "INSERT OR IGNORE INTO command(name, question) VALUES (?, ?)",
                list(commands.items()),
            )
        if not conn.execute(
            "SELECT 1 FROM suggested_question LIMIT 1"
        ).fetchone():
            conn.executemany(
                "INSERT OR IGNORE INTO suggested_question(text, position) "
                "VALUES (?, ?)",
                [(text, i) for i, text in enumerate(suggestions)],
            )
    return conn


def get_command_questions(conn: sqlite3.Connection) -> dict[str, str]:
    """Return the command -> question mapping."""
    return {
        name: question
        for name, question in conn.execute(
            "SELECT name, question FROM command ORDER BY name"
        )
    }


def get_suggested_questions(conn: sqlite3.Connection) -> list[str]:
    """Return the suggested questions in display order."""
    return [
        text
        for (text,) in conn.execute(
            "SELECT text FROM suggested_question ORDER BY position, text"
        )
    ]


def set_command_question(conn: sqlite3.Connection, name: str, question: str) -> None:
    """Set the question a command maps to. Raises on empty values."""
    if not name or not name.strip():
        raise ValueError("command name is required")
    if not question or not question.strip():
        raise ValueError("question must not be empty")
    with conn:
        cursor = conn.execute(
            "UPDATE command SET question = ? WHERE name = ?",
            (question.strip(), name),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"unknown command: {name}")


def set_suggested_questions(
    conn: sqlite3.Connection, texts: list[str]
) -> None:
    """Replace the suggested-questions list, in the given order."""
    cleaned: list[str] = []
    for text in texts:
        if not text or not text.strip():
            raise ValueError("suggested question must not be empty")
        stripped = text.strip()
        if stripped in cleaned:
            raise ValueError(f"duplicate suggestion: {stripped}")
        cleaned.append(stripped)
    with conn:
        conn.execute("DELETE FROM suggested_question")
        conn.executemany(
            "INSERT INTO suggested_question(text, position) VALUES (?, ?)",
            [(text, i) for i, text in enumerate(cleaned)],
        )
