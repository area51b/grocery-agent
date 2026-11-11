"""Tests for the Telegram bot adapter (tasks 3.2-3.8).

All tests use stubbed updates and a stubbed answer function; nothing here
touches the Telegram network or the LLM gateway.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from telegram import ReplyKeyboardMarkup

from grocery_agent.telegram import bot as bot_module
from grocery_agent.telegram.bot import (
    DENIAL_TEXT,
    GroceryBot,
    parse_allowlist,
    run,
    split_reply,
)
from grocery_agent.telegram.commands import (
    COMMAND_QUESTIONS,
    SUGGESTED_QUESTIONS,
    help_text,
)


class StubMessage:
    def __init__(self, text=""):
        self.text = text
        self.sent = []

    async def reply_text(self, text, reply_markup=None):
        self.sent.append((text, reply_markup))


def make_update(user_id, text=""):
    message = StubMessage(text)
    user = SimpleNamespace(id=user_id) if user_id is not None else None
    return SimpleNamespace(effective_user=user, message=message)


class TestCommandMapping:
    def test_commands_map_to_plain_questions(self):
        assert set(COMMAND_QUESTIONS) >= {"spend", "top", "last"}
        for question in COMMAND_QUESTIONS.values():
            assert isinstance(question, str)
            assert question and not question.startswith("/")

    def test_command_handler_answers_mapped_question(self):
        asked = []

        async def answer(question):
            asked.append(question)
            return "answer text"

        bot = GroceryBot({1}, answer)
        handler = bot.command_handler("spend")
        update = make_update(1, "/spend")
        asyncio.run(handler(update, None))
        assert asked == [COMMAND_QUESTIONS["spend"]]
        assert update.message.sent[-1][0] == "answer text"


class TestAllowlist:
    @pytest.mark.asyncio
    async def test_permitted_user_reaches_answer(self):
        asked = []

        async def answer(question):
            asked.append(question)
            return " household answer "

        bot = GroceryBot({7}, answer)
        update = make_update(7, "How much did we spend?")
        await bot.handle_text(update, None)
        assert asked == ["How much did we spend?"]
        assert update.message.sent[-1][0] == " household answer "

    @pytest.mark.asyncio
    async def test_denied_user_gets_generic_notice_and_no_agent_call(self):
        asked = []

        async def answer(question):
            asked.append(question)
            return "should not happen"

        bot = GroceryBot({7}, answer)
        update = make_update(8, "How much did we spend?")
        await bot.handle_text(update, None)
        assert asked == []
        assert update.message.sent == [(DENIAL_TEXT, None)]

    @pytest.mark.asyncio
    async def test_unset_allowlist_denies_everyone(self):
        asked = []

        async def answer(question):
            asked.append(question)
            return "should not happen"

        bot = GroceryBot(set(), answer)  # allowlist unset -> fail closed
        update = make_update(7, "How much did we spend?")
        await bot.handle_text(update, None)
        assert asked == []
        assert update.message.sent == [(DENIAL_TEXT, None)]

    def test_parse_allowlist(self):
        assert parse_allowlist("1, 2,3") == {1, 2, 3}
        assert parse_allowlist("") == set()
        assert parse_allowlist(None) == set()
        assert parse_allowlist("  ") == set()


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_different_users_run_in_parallel(self):
        in_flight = 0
        max_in_flight = 0

        async def answer(question):
            nonlocal in_flight, max_in_flight
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return "done"

        bot = GroceryBot({1, 2}, answer)
        await asyncio.gather(
            bot.handle_text(make_update(1, "q1"), None),
            bot.handle_text(make_update(2, "q2"), None),
        )
        assert max_in_flight == 2

    @pytest.mark.asyncio
    async def test_same_user_serialized(self):
        in_flight = 0
        max_in_flight = 0

        async def answer(question):
            nonlocal in_flight, max_in_flight
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return "done"

        bot = GroceryBot({1}, answer)
        await asyncio.gather(
            bot.handle_text(make_update(1, "q1"), None),
            bot.handle_text(make_update(1, "q2"), None),
        )
        assert max_in_flight == 1


class TestHelpAndSuggestions:
    @pytest.mark.asyncio
    async def test_help_sends_command_list_and_keyboard(self):
        bot = GroceryBot({1}, None)
        update = make_update(1, "/help")
        await bot.handle_help(update, None)
        text, markup = update.message.sent[0]
        assert text == help_text()
        assert isinstance(markup, ReplyKeyboardMarkup)
        buttons = [row[0].text for row in markup.keyboard]
        assert buttons == list(SUGGESTED_QUESTIONS)

    @pytest.mark.asyncio
    async def test_help_denied_for_non_permitted_user(self):
        bot = GroceryBot({1}, None)
        update = make_update(2, "/help")
        await bot.handle_help(update, None)
        assert update.message.sent == [(DENIAL_TEXT, None)]


class TestReplySplitting:
    def test_short_reply_unchanged(self):
        assert split_reply("hello") == ["hello"]

    def test_long_reply_split_on_line_boundaries(self):
        text = "\n".join(f"line {i}" for i in range(1000))
        chunks = split_reply(text, limit=4096)
        assert len(chunks) > 1
        assert all(len(chunk) <= 4096 for chunk in chunks)
        assert "\n".join(chunks) == text

    def test_long_line_split_hard(self):
        text = "x" * 5000
        chunks = split_reply(text, limit=4096)
        assert chunks == ["x" * 4096, "x" * 904]


class TestCommandMenu:
    @pytest.mark.asyncio
    async def test_setup_commands_registers_menu(self):
        registered = []

        class StubTelegramBot:
            async def set_my_commands(self, commands):
                registered.extend(commands)

        app = SimpleNamespace(bot=StubTelegramBot())
        await bot_module.setup_commands(app)
        names = [c.command for c in registered]
        assert names == ["start", "spend", "top", "last", "help"]
        assert all(c.description for c in registered)


class TestStartupValidation:
    def test_missing_token_exits_with_error(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.chdir(tmp_path)  # no .env to load either
        assert run() == 2
