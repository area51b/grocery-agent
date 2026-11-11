# Tasks

## 1. Setup

- [x] 1.1 Add `python-telegram-bot` to `pyproject.toml` dependencies and run `uv sync`; verify `uv run python -c "import telegram; print(telegram.__version__)"` succeeds
- [x] 1.2 Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_IDS` to `ENV_KEYS` in `src/grocery_agent/agent/env.py` and to `.env.example`; verify `uv run pytest tests/ -q -k env` (or add a small env-loading test in `tests/`) passes

## 2. Agent invocation refactor

- [x] 2.1 Add async `answer_question(question: str) -> str` in `src/grocery_agent/agent/__init__.py` that builds the agent, calls `ainvoke`, and returns the final message content; refactor `run_ask` to use it and verify `uv run pytest tests/test_agent.py -q` passes
- [x] 2.2 Add a test asserting `answer_question` returns the final message text from a stubbed agent graph; verify it passes with `uv run pytest tests/test_agent.py -q`

## 3. Telegram bot module

- [x] 3.1 Create `src/grocery_agent/telegram/` with `__init__.py`, `bot.py`, and `commands.py`; verify the package imports with `uv run python -c "from grocery_agent.telegram import bot"`
- [x] 3.2 Implement the command→question mapping and suggestion-button list in `commands.py` (at minimum `/spend`, `/top`, `/last`, `/help`, plus the common-question list); verify each mapping value is a plain question string with a unit test in a new `tests/test_telegram_bot.py`
- [x] 3.3 Implement `bot.py`: build the Telegram `Application` with `concurrent_updates` enabled, register a `MessageHandler` for plain text and `CommandHandler`s for each command, all routed through an allowlist check then `answer_question`; verify with unit tests that a mocked update from a permitted user reaches the answer function
- [x] 3.4 Implement fail-closed access control: reject users not on `TELEGRAM_ALLOWED_USER_IDS` with a generic access-denied notice and no agent call; verify with unit tests covering allowed user, denied user, and unset allowlist
- [x] 3.5 Implement per-user serialization: a per-user `asyncio.Lock` so each user's questions are answered one at a time while different users' questions run in parallel; verify with a unit test that two stubbed concurrent updates from different users overlap, while two from the same user do not
- [x] 3.6 Implement `/start` and `/help`: reply with the command list and set the suggestion `ReplyKeyboard`; verify with a unit test that `/help` sends the command list and keyboard markup
- [x] 3.7 Implement long-reply splitting at 4096 characters on line boundaries; verify with a unit test feeding an oversized stub answer
- [x] 3.8 Implement startup validation: exit with an error naming `TELEGRAM_BOT_TOKEN` when it is missing; verify with a unit test running the bot entry point with the variable unset

## 4. CLI wiring

- [x] 4.1 Add a `grocery telegram` subcommand in `src/grocery_agent/cli.py` that starts the bot (blocking long polling); verify `uv run grocery telegram --help` prints usage and `uv run grocery --help` lists the subcommand

## 5. Documentation and integration check

- [x] 5.1 Add a Telegram section to `README.md` (BotFather token setup, `.env` keys, `uv run grocery telegram`, running under `tmux`/`nohup`) and verify the documented commands run as written
- [x] 5.2 Run the full suite `uv run pytest -q` and confirm all tests, including the new `tests/test_telegram_bot.py`, pass with no network access
- [x] 5.3 Manual end-to-end check with a real token and populated `data/grocery.db`: send `/spend`, tap a suggestion button, and send a free-form question in Telegram; confirm answers match `uv run grocery ask` output for the same questions

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
