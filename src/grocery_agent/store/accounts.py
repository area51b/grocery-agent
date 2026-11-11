"""Household account registry.

Accounts are identified by the display name shown on the site (e.g. "Member A"
from the "Hi, <display name>" header) — never by credentials. The household supports
up to MAX_ACCOUNTS accounts; nothing else treats them differently.
"""

from __future__ import annotations

import sqlite3

MAX_ACCOUNTS = 4


def register_account(conn: sqlite3.Connection, name: str) -> None:
    """Register an account, enforcing the household cap.

    Raises ValueError when registering would exceed MAX_ACCOUNTS.
    """
    existing = conn.execute("SELECT COUNT(*) FROM account").fetchone()[0]
    already = conn.execute(
        "SELECT 1 FROM account WHERE name = ?", (name,)
    ).fetchone()
    if not already and existing >= MAX_ACCOUNTS:
        raise ValueError(
            f"Household limit is {MAX_ACCOUNTS} accounts; "
            f"cannot register a {MAX_ACCOUNTS + 1}th ('{name}')."
        )
    conn.execute("INSERT OR IGNORE INTO account (name) VALUES (?)", (name,))
    conn.commit()


def known_accounts(conn: sqlite3.Connection) -> list[str]:
    return [row[0] for row in conn.execute("SELECT name FROM account ORDER BY name")]
