"""Tests for the grocery-data-store capability (tasks 2.1-2.5)."""

from __future__ import annotations

import pytest

from grocery_agent.store import normalize, queries
from grocery_agent.store.schema import connect


@pytest.fixture
def conn(tmp_path):
    return connect(str(tmp_path / "grocery.db"))


class TestSchema:
    def test_schema_creation(self, conn):
        # 2.1: all tables exist with exact-money columns
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"raw_transaction", "transaction_record", "line_item", "meta"} <= tables

    def test_money_columns_are_integer(self, conn):
        columns = {
            row[1]: row[2]
            for row in conn.execute("PRAGMA table_info(line_item)").fetchall()
        }
        assert columns["unit_price_cents"] == "INTEGER"
        assert columns["line_total_cents"] == "INTEGER"
        assert columns["discount_cents"] == "INTEGER"


class TestNormalization:
    def test_item_with_promotion(self, conn):
        # 2.2: the spec's example item, captured exactly as the site shows it
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("promo")))
        row = conn.execute(
            "SELECT product_name, quantity, unit_price_cents, line_total_cents, "
            "promotion_text, discount_cents FROM line_item WHERE product_name "
            "LIKE 'SUNLIGHT%'"
        ).fetchone()
        assert row[0] == "SUNLIGHT DISHWASH LIQ LIME 800ML"
        assert row[1] == 1
        assert row[2] == 294  # $2.94
        assert row[3] == 294  # $2.94
        assert row[4] == "2 for $5.35"
        assert row[5] == -26  # -$0.26

    def test_item_without_promotion(self, conn):
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("plain")))
        row = conn.execute(
            "SELECT promotion_text, discount_cents FROM line_item "
            "WHERE product_name = 'PANDAN LEAVES 100G'"
        ).fetchone()
        assert row == (None, None)

    def test_exact_cents_survive_storage(self, conn):
        # 2.2: 5.35 and -0.26 come back exactly
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("promo")))
        total = conn.execute(
            "SELECT SUM(line_total_cents) FROM line_item"
        ).fetchone()[0]
        discount = conn.execute(
            "SELECT discount_cents FROM line_item WHERE discount_cents IS NOT NULL"
        ).fetchone()[0]
        assert total == 294 + 820
        assert discount == -26

    def test_weighed_item_quantity_is_null(self, conn):
        # Weighed produce shows no Qty on the site; quantity and unit price
        # stay NULL while the line total is preserved.
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("weighed")))
        row = conn.execute(
            "SELECT quantity, unit_price_cents, line_total_cents FROM line_item "
            "WHERE product_name = 'MYS Snake Gourd'"
        ).fetchone()
        assert row == (None, None, 92)

    def test_promo_item_discount_separate_from_total(self, conn):
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("weighed")))
        row = conn.execute(
            "SELECT line_total_cents, promotion_text, discount_cents FROM line_item "
            "WHERE product_name LIKE '%TCIF%'"
        ).fetchone()
        assert row == (424, "4 for $6.50", -98)

    def test_invalid_raw_is_rejected(self, conn):
        with pytest.raises(ValueError):
            normalize.ingest_raw(conn, "member-a", {"transaction_id": "X"})


class TestIdempotency:
    def test_repeated_ingestion_no_duplicates(self, conn):
        # 2.3
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("promo")))
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("promo")))
        count = conn.execute(
            "SELECT COUNT(*) FROM transaction_record"
        ).fetchone()[0]
        assert count == 1

    def test_same_id_different_account_separate(self, conn):
        # 2.3: composite key (account, transaction_id)
        raw = dict(conftest_raw("promo"))
        normalize.ingest_raw(conn, "member-a", raw)
        other = dict(raw)
        other["transaction_id"] = raw["transaction_id"]
        normalize.ingest_raw(conn, "member-b", other)
        count = conn.execute(
            "SELECT COUNT(DISTINCT account) FROM transaction_record"
        ).fetchone()[0]
        assert count == 2


class TestRenormalization:
    def test_rebuild_from_raw_without_website(self, conn):
        # 2.4: wipe normalized data, rebuild from raw, same results
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("promo")))
        before = conn.execute(
            "SELECT total_cents FROM transaction_record"
        ).fetchone()[0]
        conn.execute("DELETE FROM line_item")
        conn.execute("DELETE FROM transaction_record")
        rebuilt = normalize.renormalize(conn)
        assert rebuilt == 1
        after = conn.execute(
            "SELECT total_cents FROM transaction_record"
        ).fetchone()[0]
        assert before == after == 1820

    def test_rebuild_picks_up_new_raw_only(self, conn):
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("promo")))
        normalize.ingest_raw(conn, "member-b", dict(conftest_raw("other")))
        assert normalize.renormalize(conn) == 2


class TestCoverage:
    def test_coverage_reports_range_and_accounts(self, conn):
        # 2.5
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("promo")))
        normalize.ingest_raw(conn, "member-a", dict(conftest_raw("plain")))
        normalize.ingest_raw(conn, "member-b", dict(conftest_raw("other")))
        cov = queries.coverage(conn)
        assert cov["earliest"] == "2026-10-12 15:30:00"
        assert cov["latest"] == "2026-10-20 18:05:00"
        assert cov["transactions"] == 3
        accounts = {a["account"]: a["transactions"] for a in cov["accounts"]}
        assert accounts == {"member-a": 2, "member-b": 1}


def conftest_raw(kind: str) -> dict:
    """Return a mutable copy of a fixture document by kind."""
    from tests.fixtures import (
        RAW_TXN_OTHER_ACCOUNT,
        RAW_TXN_PLAIN,
        RAW_TXN_PROMO,
        RAW_TXN_WEIGHED,
    )

    return {
        "promo": RAW_TXN_PROMO,
        "plain": RAW_TXN_PLAIN,
        "other": RAW_TXN_OTHER_ACCOUNT,
        "weighed": RAW_TXN_WEIGHED,
    }[kind]
