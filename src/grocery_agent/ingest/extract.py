"""Item-level extraction from one transaction's detail modal.

Confirmed DOM (2026-11-11): clicking a listing card opens a "Transaction
Details" modal on the listing page. Item blocks are .purchase-item elements
inside .in-store-receipt-details. Each block's inner_text renders as one of:

    NAME              ->  NAME                 (weighed produce)
    Qty: 1 x $11.90       Qty: 2 x $2.12
    $11.90                $4.24
                          4 for $6.50        (promotion, when present)
                          -$0.98             (discount, when present)

Raw capture keeps every line exactly as shown; parse_item() turns the known
fields into the raw document format and normalization stores them.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page

RECEIPT_DETAILS = ".in-store-receipt-details"
PURCHASE_ITEM = ".purchase-item"

_QTY_RE = re.compile(r"Qty:\s*([0-9.]+)\s*x\s*(\$[0-9,.]+)")
_DISCOUNT_RE = re.compile(r"^-\$")
_MONEY_RE = re.compile(r"^(\$[0-9,.]+|-\$[0-9,.]+)$")


def parse_item(lines: list[str]) -> dict:
    """Parse one purchase-item's text lines into a raw item document."""
    if not lines:
        raise ValueError("Empty purchase item")

    raw_item = {
        "product_name": lines[0],
        "qty": None,        # weighed items show no quantity
        "unit_price": None,
        "line_total": "",
    }
    extra: list[str] = []
    for line in lines[1:]:
        qty_match = _QTY_RE.search(line)
        if qty_match:
            raw_item["qty"] = qty_match.group(1)
            raw_item["unit_price"] = qty_match.group(2)
            continue
        if _DISCOUNT_RE.match(line):
            raw_item["discount"] = line
            continue
        if _MONEY_RE.match(line):
            if not raw_item["line_total"]:
                raw_item["line_total"] = line
            else:
                extra.append(line)
            continue
        extra.append(line)
    if extra:
        # Promotion and/or discount text, kept exactly as captured.
        raw_item["promotion"] = " | ".join(extra)
    return raw_item


def extract_transaction_details(page: Page, transaction_id: str, receipt_url: str) -> dict:
    """Open one transaction's detail modal and capture it as a raw document."""
    card = page.locator(f"a[href='{receipt_url}']").first
    card.click()
    details = page.locator(RECEIPT_DETAILS).first
    details.wait_for(state="visible", timeout=15000)

    items = []
    blocks = page.locator(f"{RECEIPT_DETAILS} {PURCHASE_ITEM}")
    for i in range(blocks.count()):
        text = blocks.nth(i).inner_text()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            items.append(parse_item(lines))

    if not items:
        raise RuntimeError(
            f"No line items extracted for transaction {transaction_id!r}. "
            "Calibrate PURCHASE_ITEM against the live detail modal (task 4.3)."
        )

    # Close the modal so the next card can be opened. Try the close button
    # first, then Escape; verify the modal actually went away.
    for _ in range(3):
        if details.count() == 0 or not details.is_visible():
            break
        try:
            close = page.locator(".in-store-receipt-modal .close-button").first
            if close.count() > 0 and close.is_visible():
                close.click()
            else:
                page.keyboard.press("Escape")
        except Exception:
            page.keyboard.press("Escape")
        try:
            details.wait_for(state="hidden", timeout=3000)
        except Exception:
            page.wait_for_timeout(500)
    if details.count() > 0 and details.is_visible():
        page.keyboard.press("Escape")
        details.wait_for(state="hidden", timeout=5000)

    return {
        "transaction_id": transaction_id,
        "items": items,
    }
