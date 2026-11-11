"""Tests for the bot configuration provider (task 3.1)."""

from __future__ import annotations

from grocery_agent.telegram.commands import (
    COMMAND_QUESTIONS,
    SUGGESTED_QUESTIONS,
)
from grocery_agent.webapp import admin_store
from grocery_agent.webapp.bot_config import BotConfigProvider


class TestDefaults:
    def test_defaults_without_admin_store(self):
        provider = BotConfigProvider(None)
        assert provider.questions() == COMMAND_QUESTIONS
        assert provider.suggestions() == list(SUGGESTED_QUESTIONS)

    def test_defaults_when_store_file_missing(self, tmp_path):
        provider = BotConfigProvider(str(tmp_path / "missing.db"))
        assert provider.questions() == COMMAND_QUESTIONS
        assert provider.suggestions() == list(SUGGESTED_QUESTIONS)


class TestRuntimeEdits:
    def test_edits_visible_without_restart(self, tmp_path):
        path = str(tmp_path / "admin.db")
        provider = BotConfigProvider(path, ttl_seconds=0)  # always fresh
        assert provider.questions() == COMMAND_QUESTIONS  # seeded on ensure

        conn = admin_store.ensure_admin_store(path)
        try:
            admin_store.set_command_question(conn, "spend", "edited question")
            admin_store.set_suggested_questions(conn, ["new suggestion?"])
        finally:
            conn.close()

        assert provider.questions()["spend"] == "edited question"
        assert provider.suggestions() == ["new suggestion?"]

    def test_ttl_cache_serves_stale_values(self, tmp_path, monkeypatch):
        path = str(tmp_path / "admin.db")
        provider = BotConfigProvider(path, ttl_seconds=3600)
        assert provider.questions() == COMMAND_QUESTIONS

        conn = admin_store.ensure_admin_store(path)
        try:
            admin_store.set_command_question(conn, "spend", "edited question")
        finally:
            conn.close()

        assert provider.questions()["spend"] == COMMAND_QUESTIONS["spend"]
        provider.invalidate()
        assert provider.questions()["spend"] == "edited question"
