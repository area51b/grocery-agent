"""Tests for the admin configuration store (tasks 2.1-2.2)."""

from __future__ import annotations

import pytest

from grocery_agent.telegram.commands import (
    COMMAND_QUESTIONS,
    SUGGESTED_QUESTIONS,
)
from grocery_agent.webapp import admin_store


@pytest.fixture
def admin_path(tmp_path):
    return str(tmp_path / "admin.db")


@pytest.fixture
def store(admin_path):
    return admin_store.ensure_admin_store(admin_path)


class TestSeeding:
    def test_first_run_seeds_defaults(self, tmp_path):
        conn = admin_store.ensure_admin_store(str(tmp_path / "admin.db"))
        try:
            assert admin_store.get_command_questions(conn) == COMMAND_QUESTIONS
            assert (
                admin_store.get_suggested_questions(conn)
                == list(SUGGESTED_QUESTIONS)
            )
        finally:
            conn.close()

    def test_reopening_is_idempotent(self, admin_path):
        first = admin_store.ensure_admin_store(admin_path)
        admin_store.set_command_question(first, "spend", "edited question")
        first.close()
        reopened = admin_store.ensure_admin_store(admin_path)
        try:
            questions = admin_store.get_command_questions(reopened)
            assert questions["spend"] == "edited question"
            assert admin_store.get_suggested_questions(reopened) == list(
                SUGGESTED_QUESTIONS
            )
        finally:
            reopened.close()


class TestCommandQuestions:
    def test_set_command_question(self, store):
        admin_store.set_command_question(store, "top", "new top question")
        assert (
            admin_store.get_command_questions(store)["top"]
            == "new top question"
        )

    def test_empty_question_rejected(self, store):
        with pytest.raises(ValueError):
            admin_store.set_command_question(store, "top", "   ")
        assert admin_store.get_command_questions(store)["top"] == (
            COMMAND_QUESTIONS["top"]
        )

    def test_unknown_command_rejected(self, store):
        with pytest.raises(ValueError, match="unknown command"):
            admin_store.set_command_question(store, "nonexistent", "question")


class TestSuggestedQuestions:
    def test_replace_list_preserves_order(self, store):
        admin_store.set_suggested_questions(
            store, ["first?", "second?", "third?"]
        )
        assert admin_store.get_suggested_questions(store) == [
            "first?",
            "second?",
            "third?",
        ]

    def test_empty_entry_rejected(self, store):
        with pytest.raises(ValueError):
            admin_store.set_suggested_questions(store, ["ok?", "  "])

    def test_duplicate_rejected(self, store):
        with pytest.raises(ValueError, match="duplicate"):
            admin_store.set_suggested_questions(store, ["same?", "same?"])

    def test_empty_list_allowed(self, store):
        admin_store.set_suggested_questions(store, [])
        assert admin_store.get_suggested_questions(store) == []


class TestGroceryStoreUntouched:
    def test_admin_writes_do_not_touch_grocery_store(self, tmp_path):
        grocery = tmp_path / "grocery.db"
        admin = tmp_path / "admin.db"
        import sqlite3

        g = sqlite3.connect(grocery)
        g.execute("CREATE TABLE t (x INTEGER)")
        g.commit()
        g.close()

        conn = admin_store.ensure_admin_store(str(admin))
        try:
            admin_store.set_command_question(conn, "spend", "q?")
        finally:
            conn.close()

        g = sqlite3.connect(grocery)
        tables = {
            row[0]
            for row in g.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        g.close()
        assert tables == {"t"}
