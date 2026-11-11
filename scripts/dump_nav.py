"""Diagnostic: capture the logged-in homepage nav for selector calibration.

Run: uv run python scripts/dump_nav.py <account>
Writes data/diagnostics/home_<account>.png and links_<account>.txt.
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
        page.goto(BASE_URL, wait_until="domcontentloaded")
        ensure_logged_in(page)

        page.screenshot(path=str(out_dir / f"home_{account}.png"), full_page=False)

        lines = ["-- links --"]
        lines += page.eval_on_selector_all(
            "a", "els => els.map(e => (e.innerText || '').trim() + ' | ' + (e.getAttribute('href') || ''))"
        )
        lines += ["-- buttons --"]
        lines += page.eval_on_selector_all(
            "button", "els => els.map(e => (e.innerText || '').trim())"
        )
        lines += ["-- menu/labelled text (spans, li) --"]
        lines += page.eval_on_selector_all(
            "span, li", "els => els.map(e => (e.innerText || '').trim()).filter(t => t && t.length < 60)"
        )
        (out_dir / f"links_{account}.txt").write_text("\n".join(lines))
        print(f"Diagnostics written to {out_dir}")
        return 0
    finally:
        context.close()
        pw.stop()


if __name__ == "__main__":
    raise SystemExit(main())
