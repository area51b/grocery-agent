# Proposal

## Why

Asking the grocery agent currently requires a terminal session (`uv run grocery ask "..."`). Chatting with the agent from a phone via Telegram is more convenient for household members, and Telegram's command menu plus suggestion buttons make the most common questions one tap away instead of retyping them.

## What Changes

- Add a Telegram bot that forwards a user's message to the existing insight agent (`run_ask` flow) and replies with the agent's answer, so spending questions can be asked in chat instead of the CLI.
- Register slash commands (`/` quick commands) for the most common questions, e.g. `/spend` (total spend this month), `/top` (top spending categories), `/last` (most recent order), `/help`.
- Show commonly asked questions as tappable suggestion buttons (Telegram reply-keyboard / quick-action buttons) when a conversation starts or when `/help` is used.
- Read Telegram bot credentials from `.env` (`TELEGRAM_BOT_TOKEN`, plus an optional `TELEGRAM_ALLOWED_USER_IDS` allowlist), documented in `.env.example` and the README.
- Support multiple household members chatting concurrently: different users' questions are processed in parallel, while each individual user's messages are handled one at a time.
- The `grocery ask` CLI command remains unchanged; the bot is an additional interface.

## Capabilities

### New Capabilities
- `telegram-bot`: The Telegram chat interface to the insight agent — receiving questions, returning agent answers, slash commands, and suggestion buttons for commonly asked questions.

### Modified Capabilities

<!-- None: the insight-agent and analysis-tool capabilities are unchanged; the bot is a new interface over the same agent. -->

## Impact

- **New code**: a Telegram bot module under `src/grocery_agent/` (new `telegram/` subpackage) wired into the CLI as a new subcommand (e.g. `grocery telegram`).
- **Agent integration**: reuses `grocery_agent.agent.build_agent()`; no change to the agent graph, tools, or data store.
- **Dependencies**: a new Telegram bot library dependency (python-telegram-bot) added to `pyproject.toml`.
- **Configuration**: new `TELEGRAM_*` keys in `.env.example`; `agent/env.py` load list extended or the bot loads its own env keys.
- **Docs**: README gains a Telegram setup section.
- **Tests**: unit tests for command routing, allowlist enforcement, and answer formatting using a mocked bot/agent (no network in the suite, consistent with existing test practice).
