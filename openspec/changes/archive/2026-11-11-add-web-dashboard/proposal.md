# Proposal

## Why

Insights are currently answer-driven: you ask the agent (CLI or Telegram) one question at a time. A dashboard gives an at-a-glance view of the household's grocery data with filters and charts, and a place to adjust bot configuration without editing files. Combining the dashboard and Telegram bot into one web process also sets up simple single-container deployment later.

## What Changes

- Add a web analytics dashboard served by FastAPI: aggregate charts (spend by month, by account, by type, top products, promotion savings) built on the existing deterministic query layer, with date-range and account filters that apply to every view.
- Open the grocery data store strictly read-only (`mode=ro`) from the dashboard so the SQLite store cannot be modified or locked by browsing.
- Show read-only data coverage per account and ingestion status on the dashboard.
- Add a runtime admin area for editing bot slash-command questions and the suggested-questions list, persisted in a separate admin SQLite file (`data/admin.db`); edits apply to the running bot without a restart. The interface exposes no credentials and no `.env` values.
- Ingestion stays outside the dashboard: no ingest triggering from the admin UI.
- Protect the dashboard with a password from `.env` (`ADMIN_PASSWORD`); the Telegram allowlist itself stays in `.env` and is not managed in the UI.
- Run the Telegram bot and the web dashboard in a single process via a new `grocery webapp` command, keeping `grocery telegram` available standalone, so the whole application can later be containerized as one unit.

## Capabilities

### New Capabilities
- `web-dashboard`: The read-only web analytics interface — charts, filters, coverage and ingestion status views, password protection, and the single-process web application entry point.
- `runtime-admin`: Runtime-editable bot configuration (command questions, suggested questions) and view-only settings, persisted in a separate admin store, managed from the dashboard.

### Modified Capabilities

<!-- None: the telegram-bot capability's requirements are unchanged — its commands and suggestions become runtime-configurable, which the spec's "at minimum" wording already accommodates; the ingest, tools, and insight-agent capabilities are untouched. -->

## Impact

- **New code**: a `grocery_agent/webapp/` subpackage (FastAPI app, routes, Jinja2 templates, static assets including a vendored Chart.js) and an admin-store module (new `data/admin.db` managed with its own schema).
- **Changed code**: `commands.py` gains a config-provider seam so command questions and suggestions are read from the admin store with the current constants as defaults; `cli.py` gains a `webapp` subcommand; `pyproject.toml` gains `fastapi`, `uvicorn`, `jinja2`, `itsdangerous`.
- **Data**: one new SQLite file (`data/admin.db`) created and seeded on first run; `data/grocery.db` is opened read-only by the dashboard — no schema changes to the existing store.
- **Docs**: README gains a dashboard/admin section and the new `.env` key.
- **Tests**: FastAPI `TestClient` suites with temporary grocery and admin stores; no network, no real LLM gateway, consistent with existing practice.
- **Deployment**: no Dockerfile in this change; the single-process design is what makes containerization straightforward later.
