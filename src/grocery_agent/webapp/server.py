"""Single-process web application entry point (web-dashboard capability).

Runs the FastAPI dashboard and, when configured, the Telegram bot's polling
in the same event loop, so one process — and later one container — serves
both. A missing Telegram token disables only the bot: the dashboard keeps
serving (spec: graceful degradation, not process failure).
"""

from __future__ import annotations

import os

import uvicorn

from grocery_agent.agent.env import load_env
from grocery_agent.telegram.bot import (
    build_application,
    parse_allowlist,
    setup_commands,
)
from grocery_agent.webapp import admin_store
from grocery_agent.webapp.app import create_app
from grocery_agent.webapp.bot_config import BotConfigProvider

DEFAULT_WEB_PORT = 8000


def run_webapp() -> int:
    """Entry point for `grocery webapp`. Blocks until interrupted."""
    load_env()
    admin_db_path = admin_store.default_admin_db_path()
    provider = BotConfigProvider(admin_db_path)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    bot_application = None
    if token:
        allowlist = parse_allowlist(os.environ.get("TELEGRAM_ALLOWED_USER_IDS"))
        bot_application = build_application(
            token, allowlist, config_provider=provider
        )
    else:
        print(
            "TELEGRAM_BOT_TOKEN is not set; starting the dashboard without "
            "the Telegram bot."
        )

    app = create_app(
        admin_db_path=admin_db_path,
        config_provider=provider,
        bot_application=bot_application,
    )
    port = int(os.environ.get("GROCERY_WEB_PORT", str(DEFAULT_WEB_PORT)))
    uvicorn.run(app, host="0.0.0.0", port=port)
    return 0
