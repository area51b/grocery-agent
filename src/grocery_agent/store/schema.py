"""SQLite schema and connection management.

Design decisions (see openspec/changes/add-grocery-mvp/design.md):
- Raw captures and normalized data live in one SQLite file.
- All monetary values are stored as INTEGER cents (never floats).
- Transactions are unique per (account, transaction_id); the account label is a
  locally chosen name used only for attribution.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2

DEFAULT_DB = os.path.join("data", "grocery.db")

_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Raw, as-captured data. The source of truth for re-normalization.
CREATE TABLE IF NOT EXISTS raw_transaction (
    account        TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    captured_at    TEXT NOT NULL,          -- ISO 8601 timestamp of the capture run
    raw_json       TEXT NOT NULL,          -- as-captured document, unmodified
    PRIMARY KEY (account, transaction_id)
);

CREATE TABLE IF NOT EXISTS transaction_record (
    account        TEXT    NOT NULL,
    transaction_id TEXT    NOT NULL,
    purchased_at   TEXT    NOT NULL,       -- ISO 8601
    txn_type       TEXT    NOT NULL CHECK (txn_type IN ('online', 'in-store')),
    store_location TEXT    NOT NULL,
    total_cents    INTEGER NOT NULL,
    PRIMARY KEY (account, transaction_id)
);

CREATE TABLE IF NOT EXISTS line_item (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account         TEXT    NOT NULL,
    transaction_id  TEXT    NOT NULL,
    product_name    TEXT    NOT NULL,
    quantity        REAL,                  -- NULL for weighed items (site shows none)
    unit_price_cents INTEGER NULL,         -- NULL when the site shows no unit price
    line_total_cents INTEGER NOT NULL,
    promotion_text  TEXT,                  -- as captured, or NULL when absent
    discount_cents  INTEGER,               -- negative when money off, or NULL when absent
    FOREIGN KEY (account, transaction_id)
        REFERENCES transaction_record (account, transaction_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transaction_purchased_at
    ON transaction_record (purchased_at);
CREATE INDEX IF NOT EXISTS idx_line_item_product
    ON line_item (product_name);

-- Household accounts, identified by the display name shown on the site.
CREATE TABLE IF NOT EXISTS account (
    name TEXT PRIMARY KEY
);
"""


class _Connection(sqlite3.Connection):
    """Connection that records whether a schema migration occurred."""

    schema_migrated: bool = False


def default_db_path() -> str:
    """SQLite path from GROCERY_DB, defaulting to data/grocery.db."""
    return os.environ.get("GROCERY_DB", DEFAULT_DB)


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open a connection with the schema applied and foreign keys enabled.

    If an older schema version is found, the normalized tables are dropped
    and recreated (raw captures are preserved) — the caller is expected to
    re-normalize from raw.
    """
    db_path = db_path or default_db_path()
    parent = Path(db_path).parent
    if str(parent) not in {"", "."}:
        parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, factory=_Connection)
    conn.schema_migrated = False

    version_row = conn.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone() if _table_exists(conn, "meta") else None
    version = int(version_row[0]) if version_row else None

    if version is not None and version < SCHEMA_VERSION:
        # Drop derived tables so the new DDL recreates them; raw survives.
        conn.executescript(
            "DROP TABLE IF EXISTS line_item;"
            "DROP TABLE IF EXISTS transaction_record;"
        )
        conn.schema_migrated = True  # type: ignore[attr-defined]

    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_DDL)
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


# Authorizer action codes that mutate the database. Everything else (SELECT,
# READ, FUNCTION, ...) is allowed on a read-only connection.
_WRITE_ACTION_NAMES = (
    "SQLITE_CREATE_TABLE",
    "SQLITE_CREATE_INDEX",
    "SQLITE_CREATE_TEMP_TABLE",
    "SQLITE_CREATE_TEMP_INDEX",
    "SQLITE_CREATE_TRIGGER",
    "SQLITE_CREATE_TEMP_TRIGGER",
    "SQLITE_CREATE_VIEW",
    "SQLITE_CREATE_VTABLE",
    "SQLITE_DROP_TABLE",
    "SQLITE_DROP_INDEX",
    "SQLITE_DROP_TEMP_TABLE",
    "SQLITE_DROP_TEMP_INDEX",
    "SQLITE_DROP_TRIGGER",
    "SQLITE_DROP_TEMP_TRIGGER",
    "SQLITE_DROP_VIEW",
    "SQLITE_DROP_VTABLE",
    "SQLITE_INSERT",
    "SQLITE_UPDATE",
    "SQLITE_DELETE",
    "SQLITE_ALTER_TABLE",
    "SQLITE_PRAGMA",
    "SQLITE_TRANSACTION",
    "SQLITE_SAVEPOINT",
    "SQLITE_ATTACH",
    "SQLITE_DETACH",
    "SQLITE_REINDEX",
    "SQLITE_ANALYZE",
)
_WRITE_ACTIONS = frozenset(
    getattr(sqlite3, name)
    for name in _WRITE_ACTION_NAMES
    if hasattr(sqlite3, name)
)


def _deny_writes(action, arg1, arg2, db_name, trigger_name):
    """Authorizer callback: SQLITE_OK for reads, SQLITE_DENY for mutations."""
    if action in _WRITE_ACTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def connect_readonly(db_path: str | None = None) -> sqlite3.Connection:
    """Open the store strictly for reading (guarded-sql-query capability).

    The connection is opened with ``mode=ro`` at the SQLite level AND carries
    an authorizer that denies every mutating statement, so agent-supplied SQL
    cannot write to the store even if it tries.
    """
    path = Path(db_path or default_db_path()).resolve()
    if not path.is_file():
        raise sqlite3.OperationalError(f"no database file at {path}")
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    conn.set_authorizer(_deny_writes)
    return conn
