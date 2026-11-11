"""Debug: print raw .purchase-item texts for one receipt.

Run: uv run python scripts/debug_receipt.py <receipt_id> [account]
"""

from __future__ import annotations

import sys
from pathlib import Path

from grocery_agent.ingest.browser import BASE_URL, ensure_logged_in, open_account_session


def main() -> int:
    receipt_id = sys.argv[1]
    account = sys.argv[2] if len(sys.argv) > 2 else "member-a"

    pw, context = open_account_session(account)
    try:
        page = context.new_page()
        page.goto(f"{BASE_URL}account", wait_until="domcontentloaded")
        ensure_logged_in(page)
        # After (re)login the site may land elsewhere; navigate to /account
        # again and give the SPA time to render.
        page.goto(f"{BASE_URL}account", wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2000)

        link = page.locator("a[href='/account/order-history']").first
        try:
            link.wait_for(state="visible", timeout=30000)
        except Exception:
            page.screenshot(path=str(Path("data/diagnostics/debug_nav_fail.png")))
            raise
        link.click()
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        card = page.locator(f"a[href='/account/in-store-receipt/{receipt_id}']").first
        card.wait_for(state="visible", timeout=15000)
        card.click()
        details = page.locator(".in-store-receipt-details").first
        details.wait_for(state="visible", timeout=15000)
        page.wait_for_timeout(1000)

        blocks = page.locator(".in-store-receipt-details .purchase-item")
        print(f"item blocks: {blocks.count()}")
        for i in range(blocks.count()):
            text = blocks.nth(i).inner_text()
            print(f"--- item {i} ---")
            for line in text.splitlines():
                if line.strip():
                    print(repr(line.strip()))
        return 0
    finally:
        context.close()
        pw.stop()


if __name__ == "__main__":
    raise SystemExit(main())
