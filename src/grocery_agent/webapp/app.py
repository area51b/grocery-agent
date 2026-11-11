"""The web application: read-only dashboard and runtime admin area.

Covers the web-dashboard and runtime-admin capabilities:
- all grocery figures come from the deterministic query layer over a
  read-only connection (mode=ro) — browsing never writes to the store;
- the dashboard and admin area require a password login (ADMIN_PASSWORD),
  failing closed when it is unset;
- the admin area edits bot configuration in the separate admin store;
  credentials are never rendered.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from grocery_agent.store import queries
from grocery_agent.store.schema import connect_readonly
from grocery_agent.telegram.bot import setup_commands
from grocery_agent.telegram.commands import COMMAND_LABELS, help_text
from grocery_agent.webapp import admin_store
from grocery_agent.webapp.bot_config import BotConfigProvider

_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATES_DIR = Path(__file__).parent / "templates"

SETTING_SESSION_SECRET = "session_secret"


# --------------------------------------------------------------------------
# Application factory
# --------------------------------------------------------------------------


def create_app(
    admin_db_path: str | None = None,
    config_provider: BotConfigProvider | None = None,
    bot_application=None,
) -> FastAPI:
    """Build the FastAPI app.

    ``bot_application`` (a telegram.ext.Application) is optional: when given,
    its polling starts and stops with the web server's event loop. Without
    one, the app serves the dashboard only (bot disabled, not an error).
    """
    admin_path = admin_db_path or admin_store.default_admin_db_path()
    admin_store.ensure_admin_store(admin_path)
    provider = config_provider or BotConfigProvider(admin_path)
    secret = _session_secret(admin_path)

    app = FastAPI(title="grocery-agent", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=secret)
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    templates = _templates()

    def authenticated(request: Request) -> bool:
        return bool(_session(request).get("admin"))

    def render(name: str, request, **context):
        return templates.TemplateResponse(request, name, context)

    def guard(request: Request):
        """Return a redirect when unauthenticated, else None (fail closed)."""
        if authenticated(request):
            return None
        return RedirectResponse("/login", status_code=303)

    # -- health (unauthenticated, for monitors and uptime checks) -----------

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return FileResponse(
            _STATIC_DIR / "favicon.svg", media_type="image/svg+xml"
        )

    # -- auth ---------------------------------------------------------------

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, error: str = ""):
        return render("login.html", request, error=error)

    @app.post("/login")
    def login(request: Request, password: str = Form("")):
        expected = os.environ.get("ADMIN_PASSWORD", "")
        # Fail closed: an unset or empty password refuses every login.
        if expected and secrets.compare_digest(password, expected):
            _session(request)["admin"] = True
            return RedirectResponse("/", status_code=303)
        return render("login.html", request, error="Incorrect password.")

    @app.post("/logout")
    def logout(request: Request):
        _session(request).clear()
        return RedirectResponse("/login", status_code=303)

    # -- dashboard ----------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, start: str = "", end: str = "", account: str = ""):
        redirect = guard(request)
        if redirect:
            return redirect
        filters = {"start": start, "end": end, "account": account}
        try:
            data = _dashboard_data(start or None, end or None, account or None)
            store_error = ""
        except sqlite3.OperationalError as exc:
            data = None
            store_error = f"Cannot read the grocery store: {exc}"
        return render(
            "dashboard.html",
            request,
            filters=filters,
            accounts=_accounts(data),
            charts=data,
            store_error=store_error,
        )

    @app.get("/coverage", response_class=HTMLResponse)
    def coverage(request: Request):
        redirect = guard(request)
        if redirect:
            return redirect
        try:
            conn = connect_readonly()
            try:
                accounts = queries.coverage(conn)["accounts"]
            finally:
                conn.close()
            store_error = ""
        except sqlite3.OperationalError as exc:
            accounts = []
            store_error = f"Cannot read the grocery store: {exc}"
        return render(
            "coverage.html",
            request,
            accounts=accounts,
            store_error=store_error,
        )

    # -- admin area ---------------------------------------------------------

    def admin_context(request: Request, error: str = "", saved: bool = False):
        return {
            "commands": provider.questions(),
            "command_labels": COMMAND_LABELS,
            "suggestions": provider.suggestions(),
            "error": error,
            "saved": saved,
        }

    @app.get("/admin", response_class=HTMLResponse)
    def admin_page(request: Request, saved: str = ""):
        redirect = guard(request)
        if redirect:
            return redirect
        context = admin_context(request, saved=bool(saved))
        return render("admin.html", request, **context)

    @app.post("/admin/commands")
    def save_command(request: Request, name: str = Form(...), question: str = Form(...)):
        if not authenticated(request):
            return RedirectResponse("/login", status_code=303)
        conn = admin_store.connect_admin(admin_path)
        try:
            admin_store.set_command_question(conn, name, question)
        except ValueError as exc:
            context = admin_context(request, error=str(exc))
            return render("admin.html", request, **context)
        finally:
            conn.close()
        provider.invalidate()
        return RedirectResponse("/admin?saved=1", status_code=303)

    @app.post("/admin/suggestions")
    def save_suggestions(request: Request, suggestions: str = Form("")):
        if not authenticated(request):
            return RedirectResponse("/login", status_code=303)
        texts = [line.strip() for line in suggestions.splitlines()]
        texts = [line for line in texts if line]
        try:
            conn = admin_store.connect_admin(admin_path)
            try:
                admin_store.set_suggested_questions(conn, texts)
            finally:
                conn.close()
        except ValueError as exc:
            context = admin_context(request, error=str(exc))
            return render("admin.html", request, **context)
        provider.invalidate()
        return RedirectResponse("/admin?saved=1", status_code=303)

    # -- admin area ---------------------------------------------------------

    # -- bot lifecycle -------------------------------------------------------

    @app.on_event("startup")
    async def _start_bot() -> None:
        if bot_application is None:
            return
        await bot_application.initialize()
        await setup_commands(bot_application)
        await bot_application.start()
        if bot_application.updater is not None:
            await bot_application.updater.start_polling()

    @app.on_event("shutdown")
    async def _stop_bot() -> None:
        if bot_application is None:
            return
        if bot_application.updater is not None:
            await bot_application.updater.stop()
        await bot_application.stop()
        await bot_application.shutdown()

    return app


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _session(request: Request):
    return request.scope["session"]


def _templates():
    from fastapi.templating import Jinja2Templates

    return Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _session_secret(admin_path: str) -> str:
    """Session-cookie signing key: env value, else generated and persisted."""
    value = os.environ.get("ADMIN_SESSION_SECRET", "")
    if value:
        return value
    conn = admin_store.connect_admin(admin_path)
    try:
        row = conn.execute(
            "SELECT value FROM setting WHERE key = ?",
            (SETTING_SESSION_SECRET,),
        ).fetchone()
        if row:
            return row[0]
        generated = secrets.token_hex(32)
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO setting(key, value) VALUES (?, ?)",
                (SETTING_SESSION_SECRET, generated),
            )
        return generated
    finally:
        conn.close()


def _accounts(data: dict | None) -> list[str]:
    """Account labels for the filter dropdown, from the per-account view."""
    if not data:
        return []
    return [row["account"] for row in data.get("by_account", [])]


def _dashboard_data(
    start: str | None, end: str | None, account: str | None
) -> dict:
    """Compute every dashboard aggregate through the query layer (read-only)."""
    conn = connect_readonly()
    try:
        by_account = queries.spend_by_account_cents(conn, start=start, end=end)
        if account:
            # Projection of the query-layer result, not a recomputation.
            by_account = [row for row in by_account if row["account"] == account]
        return {
            "total": queries.total_spend_cents(
                conn, start=start, end=end, account=account
            ),
            "promo_savings": queries.promotion_savings_cents(
                conn, start=start, end=end, account=account
            ),
            "by_month": queries.spend_by_month_cents(
                conn, account=account, start=start, end=end
            ),
            "by_account": by_account,
            "by_type": queries.spend_by_type_cents(
                conn, start=start, end=end, account=account
            ),
            "top_products": queries.top_products(
                conn, start=start, end=end, account=account, limit=10
            ),
        }
    finally:
        conn.close()
