"""Normalization: raw captured documents -> normalized SQLite rows.

The raw document format is defined by this project's ingestion capture:
{
    "transaction_id": "SS123456",
    "purchased_at": "12 Oct 2026, 03:30 PM",   # as captured
    "txn_type": "online" | "in-store",
    "store_location": "SHENG SIONG ...",
    "total": "$123.45",                        # as captured
    "items": [
        {
            "product_name": "SUNLIGHT DISHWASH LIQ LIME 800ML",
            "qty": "1",
            "unit_price": "$2.94",
            "line_total": "$2.94",
            "promotion": "2 for $5.35",        # optional
            "discount": "-$0.26"               # optional
        }
    ]
}

Raw values are stored exactly as captured; normalization parses them into
typed columns. See design.md decision 2 and the grocery-data-store spec.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from grocery_agent.store.parsing import parse_money_cents, parse_quantity, parse_timestamp


def _validate_raw(raw: dict) -> None:
    required = {"transaction_id", "purchased_at", "txn_type", "store_location", "total", "items"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"Raw capture missing fields: {sorted(missing)}")
    if raw["txn_type"] not in {"online", "in-store"}:
        raise ValueError(f"Unknown transaction type: {raw['txn_type']!r}")
    if not isinstance(raw["items"], list):
        raise ValueError("Raw capture 'items' must be a list")


def normalize_raw(raw: dict) -> dict:
    """Parse one raw capture into normalized column values (no persistence)."""
    _validate_raw(raw)
    items = []
    for item in raw["items"]:
        unit_price = item.get("unit_price")
        items.append(
            {
                "product_name": str(item["product_name"]),
                # Weighed items show no quantity; it stays NULL.
                "quantity": (
                    parse_quantity(str(item["qty"])) if item.get("qty") is not None else None
                ),
                "unit_price_cents": (
                    parse_money_cents(str(unit_price)) if unit_price else None
                ),
                "line_total_cents": parse_money_cents(str(item["line_total"])),
                "promotion_text": item.get("promotion") or None,
                "discount_cents": (
                    parse_money_cents(str(item["discount"])) if item.get("discount") else None
                ),
            }
        )
    return {
        "transaction_id": str(raw["transaction_id"]),
        "purchased_at": parse_timestamp(str(raw["purchased_at"])),
        "txn_type": raw["txn_type"],
        "store_location": str(raw["store_location"]),
        "total_cents": parse_money_cents(str(raw["total"])),
        "items": items,
    }


def store_raw(conn: sqlite3.Connection, account: str, raw: dict) -> None:
    """Persist a raw capture exactly as provided (idempotent upsert)."""
    _validate_raw(raw)
    conn.execute(
        """
        INSERT INTO raw_transaction (account, transaction_id, captured_at, raw_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(account, transaction_id)
        DO UPDATE SET captured_at = excluded.captured_at, raw_json = excluded.raw_json
        """,
        (
            account,
            str(raw["transaction_id"]),
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            json.dumps(raw, ensure_ascii=False),
        ),
    )


def store_normalized(conn: sqlite3.Connection, account: str, raw: dict) -> None:
    """Normalize one raw capture and upsert it into the normalized tables."""
    norm = normalize_raw(raw)
    conn.execute(
        """
        INSERT INTO transaction_record
            (account, transaction_id, purchased_at, txn_type, store_location, total_cents)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(account, transaction_id) DO UPDATE SET
            purchased_at = excluded.purchased_at,
            txn_type = excluded.txn_type,
            store_location = excluded.store_location,
            total_cents = excluded.total_cents
        """,
        (
            account,
            norm["transaction_id"],
            norm["purchased_at"],
            norm["txn_type"],
            norm["store_location"],
            norm["total_cents"],
        ),
    )
    # Line items are derived data: replace them wholesale for the transaction.
    conn.execute(
        "DELETE FROM line_item WHERE account = ? AND transaction_id = ?",
        (account, norm["transaction_id"]),
    )
    for item in norm["items"]:
        conn.execute(
            """
            INSERT INTO line_item
                (account, transaction_id, product_name, quantity,
                 unit_price_cents, line_total_cents, promotion_text, discount_cents)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account,
                norm["transaction_id"],
                item["product_name"],
                item["quantity"],
                item["unit_price_cents"],
                item["line_total_cents"],
                item["promotion_text"],
                item["discount_cents"],
            ),
        )


def ingest_raw(
    conn: sqlite3.Connection, account: str, raw: dict
) -> None:
    """Capture one raw document and write through to the normalized store."""
    store_raw(conn, account, raw)
    store_normalized(conn, account, raw)
    conn.commit()


def has_transaction(conn: sqlite3.Connection, account: str, transaction_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM raw_transaction WHERE account = ? AND transaction_id = ?",
        (account, transaction_id),
    ).fetchone()
    return row is not None


def renormalize(conn: sqlite3.Connection) -> int:
    """Rebuild all normalized data from retained raw captures.

    Returns the number of transactions rebuilt. No website access is needed.
    """
    rows = conn.execute(
        "SELECT account, raw_json FROM raw_transaction ORDER BY account, transaction_id"
    ).fetchall()
    conn.execute("DELETE FROM line_item")
    conn.execute("DELETE FROM transaction_record")
    for account, raw_json in rows:
        store_normalized(conn, account, json.loads(raw_json))
    conn.commit()
    return len(rows)
