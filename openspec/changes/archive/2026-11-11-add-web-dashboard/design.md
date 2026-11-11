# Design

## Context

The insight agent already has a deterministic, read-only query layer (`src/grocery_agent/store/queries.py`) that answers every aggregate the dashboard needs — coverage, spend by month/account/type, top products, promotion savings — in integer cents. The Telegram bot (`grocery_agent/telegram/bot.py`) runs as a blocking long-polling process with its command questions and suggestions hardcoded in `commands.py`. Configuration comes from `.env` via the shared `load_env`. See proposal.md for motivation and the delta specs for behavior.

## Goals / Non-Goals

**Goals:**
- One process serving both the web dashboard and the Telegram bot (`grocery webapp`), containerizable later as a single unit.
- Dashboard charts and filters built entirely on the existing query layer, against a read-only store connection.
- Runtime-editable bot configuration in a separate admin SQLite file, applied without restart.
- Password-protected dashboard; zero credential exposure in the UI.

**Non-Goals:**
- Docker/container files (the design enables them, a later change adds them).
- Triggering or scheduling ingestion from the web app.
- Managing the Telegram allowlist or any `.env` value from the UI.
- Multi-admin accounts, roles, or audit logs — a single shared password fits the household scale.

## Decisions

1. **FastAPI + Jinja2 server-rendered templates + vendored Chart.js.**
   The dashboard is server-rendered HTML with filters as URL query parameters — every filtered view is a plain GET, which keeps it testable with `TestClient` and needs no frontend build toolchain. Chart.js is vendored under `static/` (not CDN) so the container runs offline. Alternatives: React SPA (rejected: adds a node toolchain to the container for little benefit on read-heavy pages), or plotting server-side images (rejected: heavier and less interactive).

2. **Single process: uvicorn server + PTB polling on one event loop.**
   `grocery webapp` builds the FastAPI app and starts it with `uvicorn.Server` programmatically; an asyncio startup task initializes the PTB `Application` and calls `updater.start_polling()` instead of the blocking `run_polling()`. If `TELEGRAM_BOT_TOKEN` is missing, the startup task is skipped and the web app runs dashboard-only (spec: bot disabled, not process failure). `grocery telegram` keeps its current standalone path. Alternative: two processes supervised in a container (rejected: user explicitly wants one unit; also two pollers would double Telegram update consumption only if both ran — but process juggling is still worse operationally).

3. **Dashboard reads the store through a read-only connection factory.**
   A small helper opens `sqlite3.connect("file:<path>?mode=ro", uri=True)` per request and reuses `store/queries.py` functions unchanged. Read-only mode guarantees browsing cannot write, and a missing file raises immediately — surfaced as the spec's friendly message. `GROCERY_DB` path resolution matches the tools' behavior.

4. **Admin store: `data/admin.db` with three tables, seeded on first run.**
   `command(name PRIMARY KEY, question)` seeded from `COMMAND_QUESTIONS`; `suggested_question(text, position)` seeded from `SUGGESTED_QUESTIONS`; `setting(key, value)` reserved for future non-credential settings. Writes happen only here; `data/grocery.db` is never opened for write by the web app.

5. **Bot reads config through a provider with a short TTL cache.**
   `commands.py` constants become the fallback defaults; a new provider in the webapp/admin module reads the admin store with a small TTL (e.g. 5 seconds) so runtime edits apply without restart while per-message queries stay cheap. The bot's handler code switches to the provider; when the admin store is absent (standalone `grocery telegram`), it serves defaults — behavior identical to today. Editing is limited to question text and the suggestions list; the command *set* is fixed, matching the spec.

6. **Authentication: shared password + signed session cookie.**
   `ADMIN_PASSWORD` from `.env` checked on a login page; Starlette's `SessionMiddleware` (signed cookie, `itsdangerous`) keeps the app stateless. An `ADMIN_SESSION_SECRET` env value signs the cookie (randomly generated and persisted to the admin store on first run if unset, so restarts keep sessions). Fail-closed: unset/empty `ADMIN_PASSWORD` means the login route always refuses. No per-user accounts.

7. **Secrets never reach templates.**
   The web interface renders no credential values and offers no `.env` editing — credentials stay in the git-ignored file, and there is no settings page that could leak them. The admin area only edits bot questions and suggestions.

8. **Filtering in the query layer's existing terms.**
   Date-range and account filters map to the query layer's existing optional `account` and period parameters (used by `total_spend_cents`, `spend_by_month_cents`, etc.), so no new SQL is written and the dashboard inherits the same guards the tools have.

## Risks / Trade-offs

- [Admin store and grocery store confused by future code] → Separate file, separate connection helpers, and distinct module ownership (`store/` vs `webapp/`); the dashboard's grocery connection is opened read-only at the SQLite level, so even a bug cannot write there.
- [PTB polling inside uvicorn's loop couples web and bot lifecycles] → The bot runs as a managed asyncio task; a bot crash logs the failure and disables only the bot (dashboard keeps serving), matching the graceful-degradation spec scenario.
- [Session cookie theft exposes the dashboard] → Cookie is signed and HTTPS is a deployment concern; the household runs on LAN/tunnel, and the admin area only edits bot questions — no credentials are obtainable from the UI.
- [Chart.js vendored copy needs manual updates] → Acceptable for a household app; pinned version, replaced only deliberately.
- [`grocery webapp` on a machine without ingested data] → Empty-state views and coverage showing zero accounts; no crash (spec scenario).

## Migration Plan

Additive: new subpackage, new admin file, one new CLI subcommand, three new dependencies. `uv sync` then `uv run grocery webapp`; the admin store seeds itself. Rollback is switching back to `grocery telegram` / `grocery ask`; nothing existing changes behavior (the bot's config source falls back to today's defaults).

## Open Questions

None.
