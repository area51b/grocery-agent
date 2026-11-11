"""Diagnostic: dump a page's HTML and screenshot for selector calibration.

Run: uv run python scripts/dump_page.py <url_path> <name> [account]
Writes data/diagnostics/<name>.html and <name>.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

from grocery_agent.ingest.browser import BASE_URL, ensure_logged_in, open_account_session


def main() -> int:
    url_path = sys.argv[1] if len(sys.argv) > 1 else "account/order-history"
    name = sys.argv[2] if len(sys.argv) > 2 else "page"
    account = sys.argv[3] if len(sys.argv) > 3 else "member-a"

    out_dir = Path("data") / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)

    pw, context = open_account_session(account)
    try:
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        ensure_logged_in(page)
        # SPA: /account/order-history only renders via in-app navigation.
        # Go to the account page first, then click the Transactions link.
        page.goto(f"{BASE_URL}account", wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        if "order-history" in url_path:
            link = page.locator("a[href='/account/order-history']").first
            link.wait_for(state="visible", timeout=15000)
            link.click()
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # SPA may keep polling; proceed after idle-or-timeout
        page.wait_for_timeout(2000)

        page.screenshot(path=str(out_dir / f"{name}.png"), full_page=True)
        (out_dir / f"{name}.html").write_text(page.content())
        print(f"Diagnostics written: {name}.html / {name}.png in {out_dir}")
        return 0
    finally:
        context.close()
        pw.stop()


if __name__ == "__main__":
    raise SystemExit(main())
