"""Browser session management for Sheng Siong ingestion.

One persistent browser profile per account label (design decision 1): each
household account keeps its own login session, and credentials are only ever
typed by the user into the real browser — never into code, storage, or
prompts. Selectors live in ingest.selectors for live calibration.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from grocery_agent.ingest.selectors import LOGIN_INDICATORS, LOGGED_IN_INDICATORS

BASE_URL = "https://shengsiong.com.sg/"
PROFILES_DIR = Path("data") / "profiles"

_LOGIN_WAIT_SECONDS = 300  # five minutes for the user to log in
_POLL_INTERVAL_SECONDS = 2.0


def get_account_name(page: Page) -> str | None:
    """Read the account's display name from the site ("Hi, <display name>" header).

    Returns None when no such element is present. The name becomes the
    account identifier in SQLite; credentials are never touched.
    """
    try:
        elements = page.locator("text=/^Hi, /")
        for i in range(elements.count()):
            text = elements.nth(i).inner_text().strip()
            match = re.match(r"Hi,\s*(.+)$", text)
            if match and match.group(1).strip():
                return match.group(1).strip()
    except Exception:
        pass
    return None


def _has_any(page: Page, selectors: list[str]) -> bool:
    for selector in selectors:
        try:
            if page.locator(selector).first.is_visible():
                return True
        except Exception:
            continue
    return False


def open_account_session(account: str):
    """Launch a headed browser with this account's persistent profile.

    Returns (playwright, browser_context). The caller is responsible for
    closing the context.
    """
    profile_dir = PROFILES_DIR / account
    profile_dir.mkdir(parents=True, exist_ok=True)
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=False,
        viewport={"width": 1280, "height": 900},
    )
    return pw, context


def ensure_logged_in(page: Page) -> None:
    """Navigate to the site and make sure the user is logged in.

    If no session is active, the user logs in manually in the visible
    browser; we poll until login indicators disappear and the logged-in
    markers appear. Credentials are never read or stored by this code.
    """
    page.goto(BASE_URL, wait_until="domcontentloaded")

    if not _has_any(page, LOGIN_INDICATORS) and _has_any(page, LOGGED_IN_INDICATORS):
        return  # persistent session is still valid

    print(
        "\nNo authenticated session found. Please log in to Sheng Siong in the "
        "opened browser window."
    )
    deadline = time.monotonic() + _LOGIN_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(_POLL_INTERVAL_SECONDS)
        if not _has_any(page, LOGIN_INDICATORS) and _has_any(page, LOGGED_IN_INDICATORS):
            print("Login confirmed. Starting extraction...\n")
            return
    raise TimeoutError(
        "Login was not completed in time. Re-run ingestion and log in within "
        f"{_LOGIN_WAIT_SECONDS} seconds."
    )
