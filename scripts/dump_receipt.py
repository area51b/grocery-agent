"""Diagnostic: dump one in-store receipt page for line-item calibration.

Run: uv run python scripts/dump_receipt.py [account]
"""

from __future__ import annotations

import sys
from pathlib import Path

from grocery_agent.ingest.browser import BASE_URL, ensure_logged_in, open_account_session


def main() -> int:
    account = sys.argv[1] if len(sys.argv) > 1 else "member-a"
    out_dir = Path("data") / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)

    pw, context = open_account_session(account)
    try:
        page = context.new_page()
        page.goto(f"{BASE_URL}account", wait_until="domcontentloaded")
        ensure_logged_in(page)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        # Open the most recent in-store receipt from the transactions listing.
        page.goto(f"{BASE_URL}account", wait_until="domcontentloaded")
        link = page.locator("a[href='/account/order-history']").first
        link.wait_for(state="visible", timeout=15000)
        link.click()
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        card = page.locator("a[href*='/account/in-store-receipt/']").first
        card.wait_for(state="visible", timeout=15000)
        receipt_url = card.get_attribute("href")
        print(f"Opening receipt: {receipt_url}")
        card.click()
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2000)

        page.screenshot(path=str(out_dir / "receipt.png"), full_page=True)
        (out_dir / "receipt.html").write_text(page.content())
        print(f"Receipt diagnostics written to {out_dir}")
        return 0
    finally:
        context.close()
        pw.stop()


if __name__ == "__main__":
    raise SystemExit(main())
