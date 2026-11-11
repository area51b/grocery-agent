"""Bot configuration provider backed by the admin store (runtime-admin).

Serves the bot's command questions and suggested questions, applying runtime
edits without a restart. Falls back to the static defaults in
``telegram.commands`` when no admin store exists, so a standalone
``grocery telegram`` behaves exactly as before.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from grocery_agent.telegram.commands import (
    COMMAND_QUESTIONS,
    SUGGESTED_QUESTIONS,
)
from grocery_agent.webapp import admin_store

DEFAULT_TTL_SECONDS = 5.0


class BotConfigProvider:
    """Reads bot configuration from the admin store with a short TTL cache."""

    def __init__(
        self,
        admin_db_path: str | None = None,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ):
        self._path = admin_db_path
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._cached_at: float | None = None
        self._cached: tuple[dict[str, str], list[str]] | None = None

    def questions(self) -> dict[str, str]:
        """Return the command -> question mapping."""
        return self._read()[0]

    def suggestions(self) -> list[str]:
        """Return the suggested questions in display order."""
        return self._read()[1]

    def invalidate(self) -> None:
        """Drop the cached values; the next read reloads the store."""
        with self._lock:
            self._cached = None
            self._cached_at = None

    def _read(self) -> tuple[dict[str, str], list[str]]:
        now = time.monotonic()
        with self._lock:
            if (
                self._cached is not None
                and self._cached_at is not None
                and now - self._cached_at < self._ttl
            ):
                return self._cached

        if not self._path or not Path(self._path).is_file():
            value = (dict(COMMAND_QUESTIONS), list(SUGGESTED_QUESTIONS))
        else:
            conn = admin_store.connect_admin(self._path)
            try:
                value = (
                    admin_store.get_command_questions(conn),
                    admin_store.get_suggested_questions(conn),
                )
            finally:
                conn.close()

        with self._lock:
            self._cached = value
            self._cached_at = time.monotonic()
        return value
