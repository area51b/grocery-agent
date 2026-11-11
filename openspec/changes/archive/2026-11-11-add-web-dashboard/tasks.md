# Tasks

## 1. Setup

- [x] 1.1 Add `fastapi`, `uvicorn`, `jinja2`, and `itsdangerous` to `pyproject.toml` and run `uv sync`; verify `uv run python -c "import fastapi, uvicorn, jinja2, itsdangerous; print('ok')"`
- [x] 1.2 Add `ADMIN_PASSWORD` and `ADMIN_SESSION_SECRET` (optional) to `ENV_KEYS` in `src/grocery_agent/agent/env.py` and to `.env.example`; verify `uv run pytest tests/test_env.py -q` passes after extending it with the new keys

## 2. Admin store

- [x] 2.1 Create `src/grocery_agent/webapp/admin_store.py` with the admin SQLite schema (`command`, `suggested_question`, `setting`) in a separate file (default `data/admin.db`), created and seeded on first run from the defaults in `commands.py`; verify with unit tests in `tests/test_admin_store.py` covering first-run seeding and idempotent re-seeding
- [x] 2.2 Implement read/write functions for command questions and suggested questions with validation (non-empty question, suggestion ordering); verify with unit tests for save, rejection of empty values, and that the grocery store file is never opened for write

## 3. Bot config provider

- [x] 3.1 Add a config provider that serves command questions and suggestions from the admin store with a short TTL cache, falling back to the `commands.py` defaults when the admin store is absent; verify with unit tests: defaults without admin store, fresh values after a store edit without restart simulation
- [x] 3.2 Switch `GroceryBot` and the command routing in `src/grocery_agent/telegram/` to read command questions and suggestions through the provider; verify `uv run pytest tests/test_telegram_bot.py -q` passes with the provider defaulting to current behavior

## 4. Web dashboard

- [x] 4.1 Create `src/grocery_agent/webapp/app.py` with a read-only connection factory (`file:...?mode=ro`) feeding `store/queries.py` functions; verify with unit tests that views work against a fixture store and that a missing store file renders a clear message without creating it
- [x] 4.2 Implement the dashboard route rendering aggregate charts (total spend, by month, by account, by type, top products, promotion savings) in a Jinja2 template with Chart.js from `static/`; verify with `TestClient` that the page renders with data and shows an empty-state view for an empty store
- [x] 4.3 Implement date-range and account filters as URL query parameters applied to every aggregate view; verify with `TestClient` that filtered requests change the rendered data and that a filter matching nothing renders empty states, not errors
- [x] 4.4 Implement the coverage view: per-account earliest, latest, and transaction counts, informational only with no ingestion controls; verify with `TestClient` that coverage values render and no ingest action exists in the HTML
- [x] 4.5 Implement password login with `ADMIN_PASSWORD` and a signed session cookie (Starlette `SessionMiddleware`), fail-closed when unset, redirecting unauthenticated requests to the login page; verify with `TestClient` tests: correct login grants access, wrong password refused, unset password refuses all, unauthenticated pages serve no data
- [x] 4.6 Implement the admin routes: edit command questions and suggested questions (with validation), and a settings view listing only non-credential configuration; verify with `TestClient` tests covering a saved edit, rejection of an empty question, and absence of any credential values in rendered HTML

## 5. Single-process entry point

- [x] 5.1 Implement `grocery webapp` in `src/grocery_agent/cli.py`: start uvicorn programmatically and run the Telegram bot polling as an asyncio task in the same process, skipping the bot (with a logged notice) when `TELEGRAM_BOT_TOKEN` is unset; verify with unit tests that the webapp builds without a token and that `uv run grocery webapp --help` prints usage
- [x] 5.2 Add a `TestClient`-level integration test that a running webapp serves the login and dashboard pages and the bot config provider resolves through the admin store; verify `uv run pytest tests/test_webapp.py -q` passes

## 6. Documentation and final check

- [x] 6.1 Update `README.md`: dashboard and admin usage (`uv run grocery webapp`), new `.env` keys, admin store location, and a note that containerization comes later; verify the documented commands run as written
- [x] 6.2 Run the full suite `uv run pytest -q` and confirm all tests pass with no network access
- [x] 6.3 Manual end-to-end check: start `uv run grocery webapp`, log in, exercise filters and charts, edit `/spend` and a suggestion in the admin area, then confirm the running bot uses the edits without restart and `data/grocery.db` is unchanged (compare `sqlite3 data/grocery.db "PRAGMA data_version;"` before and after)

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
