"""Transaction history discovery: listing-level metadata extraction.

Confirmed DOM (2026-11-11): the Transactions page renders two swipe panels.
In-Store transactions are cards linking to /account/in-store-receipt/<ID>;
each card holds the ID in <b>, then date/time and store location in the
card title, and "Total: $X" in the card text. Online cards' URL pattern is
pending calibration (no online orders on the first account tested).
"""

from __future__ import annotations

from playwright.sync_api import Page

INSTORE_CARD = "a[href*='/account/in-store-receipt/']"
# Calibrate when an account with online orders is available (task 4.2).
ONLINE_CARD = "a[href*='/account/online-receipt/']"


def _parse_total(text: str) -> str:
    return text.split(":", 1)[-1].strip()


def _parse_card(card) -> dict | None:
    """Extract metadata from one listing card (works for both kinds)."""
    href = card.get_attribute("href") or ""
    transaction_id = href.rstrip("/").split("/")[-1]
    if not transaction_id:
        return None

    title_text = card.locator(".card-title").first.inner_text()
    lines = [line.strip() for line in title_text.splitlines() if line.strip()]
    # lines: [ID, date/time, store location] — store may be absent online.
    date_time = lines[1] if len(lines) > 1 else ""
    store_location = lines[2] if len(lines) > 2 else ""

    total_text = ""
    card_text_locator = card.locator(".card-text").first
    if card_text_locator.count() > 0:
        total_text = card_text_locator.inner_text()

    return {
        "transaction_id": transaction_id,
        "date_time": date_time,
        "store_location": store_location,
        "total": _parse_total(total_text) if total_text else "",
        "receipt_url": href,
    }


def discover_transactions(page: Page) -> dict[str, list[dict]]:
    """Discover listed transactions across both panels of the Transactions page.

    Returns {kind: [metadata]} with kind in {"online", "in-store"}. The
    swipe carousel renders both panels in the DOM, so no tab clicks needed.
    """
    results: dict[str, list[dict]] = {"online": [], "in-store": []}
    seen: set[tuple[str, str]] = set()

    for kind, selector in (("in-store", INSTORE_CARD), ("online", ONLINE_CARD)):
        cards = page.locator(selector)
        for i in range(cards.count()):
            card = cards.nth(i)
            parsed = _parse_card(card)
            if parsed is None:
                continue
            key = (kind, parsed["transaction_id"])
            if key in seen:
                continue
            seen.add(key)
            results[kind].append(parsed)

    if not any(results.values()):
        body_text = page.locator(".content-body").first.inner_text()
        if "No placed orders found" in body_text or "orders found" in body_text:
            return results  # legitimately empty account/tab
        raise RuntimeError(
            "No transaction cards found on the Transactions page. Either the "
            "account has no transactions, or the listing selectors in "
            "ingest.discovery need recalibration (task 4.2)."
        )
    return results
