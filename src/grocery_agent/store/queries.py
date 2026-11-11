"""Deterministic query tools over the normalized store.

Every function here computes its results in SQL — the LLM never performs
arithmetic. All aggregates default to ALL ingested accounts (household view);
an optional ``account`` filter attributes spending to one account.

Monetary results are integer cents. ``formatted`` helpers convert cents to
display strings where tools return structured output.
"""

from __future__ import annotations

import sqlite3

from grocery_agent.store.parsing import parse_timestamp


def coverage(conn: sqlite3.Connection) -> dict:
    """Describe the data currently available, per the data-coverage spec."""
    rows = conn.execute(
        """
        SELECT account, MIN(purchased_at), MAX(purchased_at), COUNT(*)
        FROM transaction_record GROUP BY account ORDER BY account
        """
    ).fetchall()
    accounts = [
        {
            "account": account,
            "earliest": earliest,
            "latest": latest,
            "transactions": count,
        }
        for account, earliest, latest, count in rows
    ]
    overall = conn.execute(
        "SELECT MIN(purchased_at), MAX(purchased_at), COUNT(*) FROM transaction_record"
    ).fetchone()
    return {
        "earliest": overall[0],
        "latest": overall[1],
        "transactions": overall[2],
        "accounts": accounts,
    }


def _account_clause(account: str | None, params: list) -> str:
    if account is None:
        return ""
    params.append(account)
    return " AND account = ?"


def _period_clause(start: str | None, end: str | None, params: list) -> str:
    clause = ""
    if start is not None:
        params.append(parse_timestamp(start) if len(start) > 10 else start)
        clause += " AND purchased_at >= ?"
    if end is not None:
        # A date-only end bound must include the whole day.
        end_val = parse_timestamp(end) if len(end) > 10 else end + " 23:59:59"
        params.append(end_val)
        clause += " AND purchased_at <= ?"
    return clause


def _date_bounds(start: str | None, end: str | None) -> tuple[str, str]:
    lo = start or "0000-01-01"
    hi = end or "9999-12-31"
    if len(hi) == 10:  # date-only end: include the whole day
        hi += " 23:59:59"
    return lo, hi


def total_spend_cents(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
    txn_type: str | None = None,
) -> int:
    """Total spend in cents over a period, optionally filtered."""
    lo, hi = _date_bounds(start, end)
    params: list = [lo, hi]
    extra = _account_clause(account, params)
    if txn_type is not None:
        params.append(txn_type)
        extra += " AND txn_type = ?"
    row = conn.execute(
        f"SELECT COALESCE(SUM(total_cents), 0) FROM transaction_record "
        f"WHERE purchased_at >= ? AND purchased_at <= ?{extra}",
        params,
    ).fetchone()
    return row[0]


def spend_by_type_cents(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
) -> list[dict]:
    """Spend split by transaction type (online vs in-store)."""
    lo, hi = _date_bounds(start, end)
    params: list = [lo, hi]
    extra = _account_clause(account, params)
    rows = conn.execute(
        f"SELECT txn_type, COALESCE(SUM(total_cents), 0), COUNT(*) "
        f"FROM transaction_record WHERE purchased_at >= ? AND purchased_at <= ?{extra} "
        f"GROUP BY txn_type ORDER BY txn_type",
        params,
    ).fetchall()
    return [
        {"txn_type": txn_type, "total_cents": total, "transactions": count}
        for txn_type, total, count in rows
    ]


def spend_by_month_cents(
    conn: sqlite3.Connection,
    account: str | None = None,
) -> list[dict]:
    """Spend grouped by calendar month, oldest first."""
    params: list = []
    extra = _account_clause(account, params)
    rows = conn.execute(
        f"SELECT substr(purchased_at, 1, 7) AS month, "
        f"COALESCE(SUM(total_cents), 0), COUNT(*) "
        f"FROM transaction_record WHERE 1=1{extra} "
        f"GROUP BY month ORDER BY month",
        params,
    ).fetchall()
    return [{"month": month, "total_cents": total, "transactions": count} for month, total, count in rows]


def spend_by_account_cents(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
) -> list[dict]:
    """Household spend attributed per account (responsibility view)."""
    lo, hi = _date_bounds(start, end)
    rows = conn.execute(
        "SELECT account, COALESCE(SUM(total_cents), 0), COUNT(*) "
        "FROM transaction_record WHERE purchased_at >= ? AND purchased_at <= ? "
        "GROUP BY account ORDER BY account",
        (lo, hi),
    ).fetchall()
    return [
        {"account": account, "total_cents": total, "transactions": count}
        for account, total, count in rows
    ]


def product_analysis(
    conn: sqlite3.Connection,
    product_name: str,
    account: str | None = None,
) -> dict | None:
    """Aggregate spend, quantity, and prices paid for one product (exact name)."""
    params: list = [product_name]
    extra = _account_clause(account, params)
    totals = conn.execute(
        f"SELECT COALESCE(SUM(line_total_cents), 0), COALESCE(SUM(quantity), 0.0), "
        f"COUNT(*) FROM line_item WHERE product_name = ?{extra}",
        params,
    ).fetchone()
    if totals[2] == 0:
        return None
    prices = conn.execute(
        f"SELECT DISTINCT unit_price_cents FROM line_item "
        f"WHERE product_name = ? AND unit_price_cents IS NOT NULL{extra} "
        f"ORDER BY unit_price_cents",
        params,
    ).fetchall()
    return {
        "product_name": product_name,
        "total_spend_cents": totals[0],
        "total_quantity": totals[1],
        "purchases": totals[2],
        "unit_prices_cents_paid": [price[0] for price in prices],
    }


def promotion_savings_cents(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
) -> int:
    """Sum of discount amounts received on promoted items in a period."""
    lo, hi = _date_bounds(start, end)
    params: list = [lo, hi]
    extra = _account_clause(account, params)
    row = conn.execute(
        f"SELECT COALESCE(SUM(li.discount_cents), 0) FROM line_item li "
        f"JOIN transaction_record t "
        f"ON li.account = t.account AND li.transaction_id = t.transaction_id "
        f"WHERE t.purchased_at >= ? AND t.purchased_at <= ?{extra}",
        params,
    ).fetchone()
    return row[0]


def promoted_items(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
) -> list[dict]:
    """Promoted line items with effective per-unit price paid."""
    lo, hi = _date_bounds(start, end)
    params: list = [lo, hi]
    extra = _account_clause(account, params)
    rows = conn.execute(
        f"SELECT li.product_name, li.quantity, li.unit_price_cents, "
        f"li.line_total_cents, li.promotion_text, li.discount_cents "
        f"FROM line_item li JOIN transaction_record t "
        f"ON li.account = t.account AND li.transaction_id = t.transaction_id "
        f"WHERE t.purchased_at >= ? AND t.purchased_at <= ? "
        f"AND li.promotion_text IS NOT NULL{extra} "
        f"ORDER BY t.purchased_at",
        params,
    ).fetchall()
    result = []
    for name, qty, unit, line_total, promo, discount in rows:
        effective = (
            round((line_total + (discount or 0)) / qty) if qty else None
        )
        result.append(
            {
                "product_name": name,
                "quantity": qty,
                "unit_price_cents": unit,
                "line_total_cents": line_total,
                "promotion_text": promo,
                "discount_cents": discount,
                "effective_unit_price_cents": effective,
            }
        )
    return result


def search_products(
    conn: sqlite3.Connection,
    fragment: str,
    account: str | None = None,
) -> list[dict]:
    """Products whose name contains ``fragment`` (case-insensitive).

    ``%`` and ``_`` in the fragment are matched literally, not as wildcards.
    """
    escaped = fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    params: list = [f"%{escaped}%"]
    extra = _account_clause(account, params)
    rows = conn.execute(
        f"SELECT product_name, COALESCE(SUM(line_total_cents), 0), "
        f"COALESCE(SUM(quantity), 0.0), COUNT(*) "
        f"FROM line_item WHERE product_name LIKE ? ESCAPE '\\'{extra} "
        f"GROUP BY product_name ORDER BY product_name",
        params,
    ).fetchall()
    return [
        {
            "product_name": name,
            "total_spend_cents": total,
            "total_quantity": quantity,
            "purchases": count,
        }
        for name, total, quantity, count in rows
    ]


def product_price_history(
    conn: sqlite3.Connection,
    product_name: str,
    account: str | None = None,
) -> list[dict]:
    """Occurrences of one exact product, chronological, with prices paid."""
    params: list = [product_name]
    extra = _account_clause(account, params)
    rows = conn.execute(
        f"SELECT t.purchased_at, li.quantity, li.unit_price_cents, "
        f"li.line_total_cents, li.promotion_text "
        f"FROM line_item li JOIN transaction_record t "
        f"ON li.account = t.account AND li.transaction_id = t.transaction_id "
        f"WHERE li.product_name = ?{extra} "
        f"ORDER BY t.purchased_at",
        params,
    ).fetchall()
    return [
        {
            "purchased_at": purchased_at,
            "quantity": quantity,
            "unit_price_cents": unit_price,
            "line_total_cents": line_total,
            "promotion_text": promotion,
        }
        for purchased_at, quantity, unit_price, line_total, promotion in rows
    ]


_TOP_PRODUCT_METRICS = {
    "spend": "SUM(li.line_total_cents) DESC",
    "quantity": "COALESCE(SUM(li.quantity), 0) DESC",
    "count": "COUNT(*) DESC",
}


def top_products(
    conn: sqlite3.Connection,
    metric: str = "spend",
    limit: int = 10,
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
) -> list[dict]:
    """Products ranked by spend, quantity, or purchase count."""
    lo, hi = _date_bounds(start, end)
    params: list = [lo, hi]
    extra = _account_clause(account, params)
    order_by = _TOP_PRODUCT_METRICS.get(metric, _TOP_PRODUCT_METRICS["spend"])
    rows = conn.execute(
        f"SELECT li.product_name, COALESCE(SUM(li.line_total_cents), 0), "
        f"COALESCE(SUM(li.quantity), 0.0), COUNT(*) "
        f"FROM line_item li JOIN transaction_record t "
        f"ON li.account = t.account AND li.transaction_id = t.transaction_id "
        f"WHERE t.purchased_at >= ? AND t.purchased_at <= ?{extra} "
        f"GROUP BY li.product_name ORDER BY {order_by}, li.product_name "
        f"LIMIT ?",
        [*params, limit],
    ).fetchall()
    return [
        {
            "product_name": name,
            "total_spend_cents": total,
            "total_quantity": quantity,
            "purchases": count,
        }
        for name, total, quantity, count in rows
    ]


def transaction_details(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
    txn_type: str | None = None,
    account: str | None = None,
) -> list[dict]:
    """Transactions in a period, optionally filtered by type and account."""
    lo, hi = _date_bounds(start, end)
    params: list = [lo, hi]
    extra = _account_clause(account, params)
    if txn_type is not None:
        params.append(txn_type)
        extra += " AND txn_type = ?"
    rows = conn.execute(
        f"SELECT account, transaction_id, purchased_at, txn_type, "
        f"store_location, total_cents "
        f"FROM transaction_record WHERE purchased_at >= ? AND purchased_at <= ?{extra} "
        f"ORDER BY purchased_at",
        params,
    ).fetchall()
    return [
        {
            "account": account_name,
            "transaction_id": transaction_id,
            "purchased_at": purchased_at,
            "txn_type": txn_type_value,
            "store_location": location,
            "total_cents": total,
        }
        for account_name, transaction_id, purchased_at, txn_type_value, location, total in rows
    ]


def transaction_items(
    conn: sqlite3.Connection,
    account: str,
    transaction_id: str,
) -> list[dict] | None:
    """Line items of one transaction, or None when it is not in the store."""
    txn = conn.execute(
        "SELECT purchased_at, txn_type, store_location, total_cents "
        "FROM transaction_record WHERE account = ? AND transaction_id = ?",
        (account, transaction_id),
    ).fetchone()
    if txn is None:
        return None
    rows = conn.execute(
        "SELECT product_name, quantity, unit_price_cents, line_total_cents, "
        "promotion_text, discount_cents FROM line_item "
        "WHERE account = ? AND transaction_id = ? ORDER BY id",
        (account, transaction_id),
    ).fetchall()
    return [
        {
            "product_name": name,
            "quantity": quantity,
            "unit_price_cents": unit_price,
            "line_total_cents": line_total,
            "promotion_text": promotion,
            "discount_cents": discount,
        }
        for name, quantity, unit_price, line_total, promotion, discount in rows
    ]
