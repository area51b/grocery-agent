# Design

## Context

The insight agent is invoked today only through the CLI (`grocery ask`, `src/grocery_agent/cli.py`), which calls `run_ask(question)` in `src/grocery_agent/agent/__init__.py`. `run_ask` builds (and caches) a LangGraph ReAct agent over the deterministic analysis tools and prints the final message. Configuration comes from a git-ignored `.env` loaded by `grocery_agent/agent/env.py`, which whitelists specific keys (`GROCERY_*`). The test suite never touches the network or the real database. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Chat with the same insight agent from Telegram, reusing the existing agent graph and tools unchanged.
- `/` command shortcuts and tappable suggestions for the most common questions.
- Credentials and an optional user allowlist in `.env`, following the existing env-loading pattern.
- A test suite that exercises command routing, allowlist enforcement, and answer formatting without network access.

**Non-Goals:**
- Multi-user chat platforms other than Telegram.
- Storing conversation history in the data store; the bot keeps no chat transcript beyond what Telegram itself shows.
- Streaming or partial answers; replies are sent once, when the agent finishes.
- Any change to ingestion, the analysis tools, or the agent's prompts.

## Decisions

1. **Library: `python-telegram-bot` (v21+, asyncio).**
   It is the de-facto standard Python Telegram library, asyncio-native (fits LangGraph's async invocation), and its `Application`/handler model makes slash-command routing and reply keyboards straightforward. Alternatives: `aiogram` (equally capable but a second ecosystem convention with no advantage here) or raw long-polling over `httpx` (more code to maintain for updates, commands, and keyboards). Added to `pyproject.toml` as a main dependency.

2. **New `grocery_agent/telegram/` subpackage, started via `grocery telegram` CLI subcommand.**
   A `bot.py` module builds the Telegram `Application`, registers handlers, and runs long polling; `commands.py` holds the command→question mapping and the suggestion list. The CLI gains a `telegram` subcommand so the process lifecycle matches the existing `ingest`/`ask` entry points. The bot runs in the foreground and blocks until interrupted; it is a long-running process by design.

3. **Refactor agent invocation into a reusable, text-in/text-out function.**
   `run_ask` couples the agent call to printing and a process exit code. Add an async `answer_question(question: str) -> str` in `grocery_agent/agent` (wrapping `agent.ainvoke`, returning the final message content). The CLI's `ask` keeps its current behavior on top of it; the bot calls it per message. This is the only change inside the existing agent package.

4. **Credentials via `.env`, extending the existing whitelist.**
   `TELEGRAM_BOT_TOKEN` (required to start) and `TELEGRAM_ALLOWED_USER_IDS` (optional, comma-separated numeric Telegram IDs) are added to `env.py`'s `ENV_KEYS` and to `.env.example`. Reusing the existing `load_env` keeps one loading path; the bot never reads tokens from source or config files. Missing `TELEGRAM_BOT_TOKEN` raises the same style of error message the gateway variables already use.

5. **Access control: allowlist, fail closed.**
   Every update handler first checks `update.effective_user.id` against the allowlist. If `TELEGRAM_ALLOWED_USER_IDS` is unset or empty, no one is permitted — the bot replies with a generic access-denied notice and never invokes the agent. This prevents an accidentally published bot token from leaking household data. Alternative considered (open by default, deny via blocklist) rejected: a household app must be deny-by-default.

6. **Commands and suggestions are plain question strings, not separate code paths.**
   `/spend`, `/top`, `/last` each map to a fixed natural-language question that goes through the same `answer_question` call as typed messages, so the agent's tool selection and data-coverage guarantees apply identically. Suggestions are a `ReplyKeyboard` listing common questions (e.g. "How much did we spend this month?", "What do we spend the most on?", "What was in my most recent order?"), set on `/start` and `/help`. `/help` replies with the command list and sets the keyboard.

7. **Concurrent processing across users, serialized per user.**
   Enable `python-telegram-bot`'s `concurrent_updates` mode so different users' questions run in parallel, and hold a per-user `asyncio.Lock` (a plain dict of user ID → lock) so one person's follow-up message waits until their previous question is answered. This is safe because every agent query is a read-only SELECT against SQLite, which supports concurrent readers; no write path exists. Without concurrency, a spouse asking at the same moment would wait several seconds for the other's LLM round-trips — a poor household experience for no safety gain. Alternative considered (fully sequential updates) rejected: it serializes unrelated users while the data layer needs no serialization.

8. **Long replies are split at Telegram's 4096-character limit** on line boundaries. Agent answers about household spending rarely approach this, but SQL-table excerpts can.

## Risks / Trade-offs

- [Bot process must stay running; a laptop sleep or dropped network silently stops replies] → Document running it under `tmux`/`nohup` or a launchd service in the README; long polling reconnects automatically on transient failures.
- [Token leak exposes the bot publicly] → Fail-closed allowlist (Decision 5); the bot only ever talks to allowlisted users and never answers commands from strangers.
- [`data/grocery.db` accessed concurrently by bot and CLI, or by parallel agent runs] → Safe: all agent queries are read-only SELECTs, and SQLite handles concurrent readers; the `run_sql` connection enforces read-only, so there is no write path to collide.
- [`python-telegram-bot` adds a non-trivial dependency] → Confined to the new subpackage; the core agent and tools stay dependency-clean, and tests mock the bot layer.
- [Fixed command questions may drift from what household members actually ask] → The mapping lives in one module (`commands.py`) as a dict, so adding or rewording entries is a one-line change.

## Migration Plan

Additive change: `uv sync` picks up the new dependency, the user adds `TELEGRAM_BOT_TOKEN` (and optionally the allowlist) to `.env`, and `uv run grocery telegram` starts the bot. Rollback is removing the subcommand usage; nothing about stored data or the existing CLI changes.

## Open Questions

None.
