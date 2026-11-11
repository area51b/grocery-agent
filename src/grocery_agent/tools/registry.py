"""Deterministic analysis tools exposed to the LangGraph agent.

Each tool computes its result entirely in SQL (design decision 5) and returns
a structured dict that includes the data-coverage range, per the
spending-analysis-tools spec. Household aggregates span all ingested accounts
by default; ``account`` narrows to one member's purchases.
"""

from __future__ import annotations

import os
import sqlite3
import time

from grocery_agent.store import queries
from grocery_agent.store.schema import connect, connect_readonly, default_db_path


def connect_store() -> sqlite3.Connection:
    return connect(default_db_path())


# Guarded-SQL limits (see design.md decisions 1-2).
MAX_SQL_ROWS = 200
SQL_TIME_BUDGET_SECONDS = 5.0


def run_sql(sql: str) -> dict:
    """Run one read-only SQL statement against the normalized store.

    The only unrestricted tool: any question answerable from stored data can
    be answered here. Safety comes from the read-only connection (schema
    ``connect_readonly``), not from string parsing. Errors are returned as
    structured results so the agent can read them and retry.
    """
    conn = connect_readonly()
    try:
        deadline = time.monotonic() + SQL_TIME_BUDGET_SECONDS

        def enforce_time_budget() -> int:
            return 1 if time.monotonic() > deadline else 0

        conn.set_progress_handler(enforce_time_budget, 1000)
        try:
            cursor = conn.execute(sql)
            columns = [desc[0] for desc in cursor.description or []]
            rows = cursor.fetchmany(MAX_SQL_ROWS + 1)
        except (sqlite3.Error, sqlite3.Warning) as exc:
            return {
                "error": str(exc),
                "sql": sql,
                "coverage": queries.coverage(conn),
            }
        truncated = len(rows) > MAX_SQL_ROWS
        return {
            "columns": columns,
            "rows": [list(row) for row in rows[:MAX_SQL_ROWS]],
            "row_count": min(len(rows), MAX_SQL_ROWS),
            "truncated": truncated,
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def _format_cents(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) // 100}.{abs(cents) % 100:02d}"


def spend(
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
    txn_type: str | None = None,
) -> dict:
    """Total household spending over an optional period, transaction type, or account."""
    conn = connect_store()
    try:
        total = queries.total_spend_cents(conn, start, end, account, txn_type)
        return {
            "total_cents": total,
            "total": _format_cents(total),
            "start": start,
            "end": end,
            "account": account or "all accounts",
            "txn_type": txn_type or "all types",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def spend_by_type(
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
) -> dict:
    """Household spending split by transaction type (online vs in-store)."""
    conn = connect_store()
    try:
        rows = queries.spend_by_type_cents(conn, start, end, account)
        return {
            "breakdown": [
                {**row, "total": _format_cents(row["total_cents"])} for row in rows
            ],
            "start": start,
            "end": end,
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def spend_by_month(account: str | None = None) -> dict:
    """Household spending grouped by calendar month, oldest first."""
    conn = connect_store()
    try:
        rows = queries.spend_by_month_cents(conn, account)
        return {
            "months": [
                {**row, "total": _format_cents(row["total_cents"])} for row in rows
            ],
            "account": account or "all accounts",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def spend_by_account(start: str | None = None, end: str | None = None) -> dict:
    """Household spending attributed per account (responsibility view)."""
    conn = connect_store()
    try:
        rows = queries.spend_by_account_cents(conn, start, end)
        return {
            "accounts": [
                {**row, "total": _format_cents(row["total_cents"])} for row in rows
            ],
            "start": start,
            "end": end,
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def product_spend(product_name: str, account: str | None = None) -> dict:
    """Aggregate spend, quantity, and prices paid for one product (exact name)."""
    conn = connect_store()
    try:
        result = queries.product_analysis(conn, product_name, account)
        if result is None:
            return {
                "product_name": product_name,
                "found": False,
                "coverage": queries.coverage(conn),
            }
        return {
            "found": True,
            **result,
            "total_spend": _format_cents(result["total_spend_cents"]),
            "unit_prices_paid": [_format_cents(c) for c in result["unit_prices_cents_paid"]],
            "account": account or "all accounts",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def promotion_savings(
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
) -> dict:
    """Total amount saved through promotions in a period."""
    conn = connect_store()
    try:
        discounts = queries.promotion_savings_cents(conn, start, end, account)
        savings = -discounts  # stored discounts are negative; savings are positive
        return {
            "savings_cents": savings,
            "savings": _format_cents(savings),
            "start": start,
            "end": end,
            "account": account or "all accounts",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def promoted_item_details(
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
) -> dict:
    """Promoted line items with the effective per-unit price paid."""
    conn = connect_store()
    try:
        items = queries.promoted_items(conn, start, end, account)
        for item in items:
            item["effective_unit_price"] = _format_cents(
                item["effective_unit_price_cents"]
            )
        return {
            "items": items,
            "start": start,
            "end": end,
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def search_products(fragment: str, account: str | None = None) -> dict:
    """Find products by partial name match with aggregate spend per product."""
    conn = connect_store()
    try:
        matches = [
            {**row, "total_spend": _format_cents(row["total_spend_cents"])}
            for row in queries.search_products(conn, fragment, account)
        ]
        return {
            "query": fragment,
            "found": bool(matches),
            "matches": matches,
            "account": account or "all accounts",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def product_price_history(product_name: str, account: str | None = None) -> dict:
    """Unit price paid for one product on each purchase, chronological."""
    conn = connect_store()
    try:
        occurrences = [
            {
                **row,
                "unit_price": (
                    _format_cents(row["unit_price_cents"])
                    if row["unit_price_cents"] is not None
                    else None
                ),
            }
            for row in queries.product_price_history(conn, product_name, account)
        ]
        return {
            "product_name": product_name,
            "found": bool(occurrences),
            "occurrences": occurrences,
            "account": account or "all accounts",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def top_products(
    metric: str = "spend",
    limit: int = 10,
    start: str | None = None,
    end: str | None = None,
    account: str | None = None,
) -> dict:
    """Products ranked by spend, quantity, or purchase count in a period."""
    conn = connect_store()
    try:
        products = [
            {**row, "total_spend": _format_cents(row["total_spend_cents"])}
            for row in queries.top_products(conn, metric, limit, start, end, account)
        ]
        return {
            "metric": metric,
            "products": products,
            "start": start,
            "end": end,
            "account": account or "all accounts",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def transaction_details(
    start: str | None = None,
    end: str | None = None,
    txn_type: str | None = None,
    account: str | None = None,
) -> dict:
    """Transactions in a period with type/account filters."""
    conn = connect_store()
    try:
        transactions = [
            {**row, "total": _format_cents(row["total_cents"])}
            for row in queries.transaction_details(conn, start, end, txn_type, account)
        ]
        return {
            "transactions": transactions,
            "start": start,
            "end": end,
            "txn_type": txn_type or "all types",
            "account": account or "all accounts",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()


def transaction_items(account: str, transaction_id: str) -> dict:
    """Line items of one identified transaction."""
    conn = connect_store()
    try:
        items = queries.transaction_items(conn, account, transaction_id)
        result = {
            "account": account,
            "transaction_id": transaction_id,
            "coverage": queries.coverage(conn),
        }
        if items is None:
            result["found"] = False
            return result
        return {
            **result,
            "found": True,
            "items": [
                {
                    **row,
                    "unit_price": (
                        _format_cents(row["unit_price_cents"])
                        if row["unit_price_cents"] is not None
                        else None
                    ),
                    "line_total": _format_cents(row["line_total_cents"]),
                }
                for row in items
            ],
        }
    finally:
        conn.close()


def compare_periods(
    start_a: str,
    end_a: str,
    start_b: str,
    end_b: str,
    account: str | None = None,
) -> dict:
    """Compare total spend between two periods; difference computed in code."""
    conn = connect_store()
    try:
        total_a = queries.total_spend_cents(conn, start_a, end_a, account)
        total_b = queries.total_spend_cents(conn, start_b, end_b, account)
        difference = total_a - total_b
        percent_change = (
            round(difference / total_b * 100, 1) if total_b != 0 else None
        )
        return {
            "period_a": {"start": start_a, "end": end_a, "total_cents": total_a, "total": _format_cents(total_a)},
            "period_b": {"start": start_b, "end": end_b, "total_cents": total_b, "total": _format_cents(total_b)},
            "difference_cents": difference,
            "difference": _format_cents(difference),
            "percent_change": percent_change,
            "account": account or "all accounts",
            "coverage": queries.coverage(conn),
        }
    finally:
        conn.close()
