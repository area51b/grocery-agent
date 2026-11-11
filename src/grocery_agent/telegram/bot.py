"""The Telegram bot: a thin adapter over the insight agent.

Design decisions (see openspec/changes/add-telegram-bot/design.md):
- credentials come from .env via the shared env loader;
- access control is a fail-closed user-ID allowlist;
- different users' questions run concurrently (concurrent_updates), while each
  user's own questions are serialized behind a per-user asyncio.Lock;
- every command and suggestion maps to a plain question answered through the
  same agent path as typed messages; replies are relayed verbatim.
"""

from __future__ import annotations

import asyncio
import os
import sys

from telegram import ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from grocery_agent.agent import answer_question
from grocery_agent.agent.env import load_env
from grocery_agent.telegram.commands import (
    COMMAND_QUESTIONS,
    SUGGESTED_QUESTIONS,
    help_text,
)

TELEGRAM_TEXT_LIMIT = 4096

DENIAL_TEXT = "Sorry, you are not permitted to use this bot."


def parse_allowlist(raw: str | None) -> set[int]:
    """Parse a comma-separated list of numeric Telegram user IDs.

    An unset or empty allowlist yields no permitted users (fail closed).
    """
    if raw is None or not raw.strip():
        return set()
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return ids


def split_reply(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    """Split an agent reply into Telegram-sized chunks on line boundaries."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    return [chunk for chunk in chunks if chunk]


class GroceryBot:
    """Routes Telegram updates to the insight agent, enforcing the allowlist."""

    def __init__(self, allowed_ids: set[int], answer=answer_question):
        self.allowed_ids = allowed_ids
        self._answer = answer
        self._locks: dict[int, asyncio.Lock] = {}

    def is_allowed(self, user_id: int | None) -> bool:
        return user_id is not None and user_id in self.allowed_ids

    async def handle_text(self, update, context) -> None:
        """Answer a typed question (or deny a non-permitted user)."""
        await self._handle(update, update.message.text)

    def command_handler(self, command: str):
        """Build a handler that answers the command's mapped question."""
        question = COMMAND_QUESTIONS[command]

        async def handler(update, context) -> None:
            await self._handle(update, question)

        return handler

    async def handle_help(self, update, context) -> None:
        """Reply with the command list and set the suggestion keyboard."""
        if not await self._permit(update):
            return
        keyboard = ReplyKeyboardMarkup(
            [[question] for question in SUGGESTED_QUESTIONS],
            resize_keyboard=True,
        )
        await update.message.reply_text(help_text(), reply_markup=keyboard)

    async def _handle(self, update, question: str) -> None:
        """Allowlist check, per-user serialization, then the agent call."""
        if not await self._permit(update):
            return
        user_id = update.effective_user.id
        lock = self._locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            reply = await self._answer(question)
        for chunk in split_reply(reply):
            await update.message.reply_text(chunk)

    async def _permit(self, update) -> bool:
        """Check the allowlist; reply with a generic denial when rejected.

        The denial says nothing about the household or the agent, and the
        agent is never invoked for non-permitted users.
        """
        user = update.effective_user
        if self.is_allowed(user.id if user else None):
            return True
        await update.message.reply_text(DENIAL_TEXT)
        return False


def build_application(token: str, allowed_ids: set[int], answer=None) -> Application:
    """Build the Telegram application: commands, text handler, concurrency."""
    bot = GroceryBot(allowed_ids, answer or answer_question)
    app = Application.builder().token(token).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", bot.handle_help))
    app.add_handler(CommandHandler("help", bot.handle_help))
    for name in COMMAND_QUESTIONS:
        app.add_handler(CommandHandler(name, bot.command_handler(name)))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text)
    )
    return app


def run() -> int:
    """Entry point for `grocery telegram`. Blocks on long polling."""
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and "
            "fill it in.",
            file=sys.stderr,
        )
        return 2
    allowed_ids = parse_allowlist(os.environ.get("TELEGRAM_ALLOWED_USER_IDS"))
    app = build_application(token, allowed_ids)
    app.run_polling()
    return 0
