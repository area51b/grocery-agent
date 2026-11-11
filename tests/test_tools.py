"""Tests for the spending-analysis-tools capability (tasks 3.1-3.5)."""

from __future__ import annotations

import pytest

from grocery_agent.store import normalize
from grocery_agent.tools import registry


@pytest.fixture
def populated_db(tmp_path, monkeypatch):
    """Two accounts ingested: member-a (2 txns) and member-b (1 txn)."""
    db_path = str(tmp_path / "grocery.db")
    monkeypatch.setenv("GROCERY_DB", db_path)
    conn = registry.connect_store()
    from tests.fixtures import (
        RAW_TXN_NOV8,
        RAW_TXN_OTHER_ACCOUNT,
        RAW_TXN_PLAIN,
        RAW_TXN_PROMO,
    )

    normalize.ingest_raw(conn, "member-a", dict(RAW_TXN_PROMO))
    normalize.ingest_raw(conn, "member-a", dict(RAW_TXN_PLAIN))
    normalize.ingest_raw(conn, "member-b", dict(RAW_TXN_OTHER_ACCOUNT))
    normalize.ingest_raw(conn, "member-a", dict(RAW_TXN_NOV8))
    conn.close()
    return db_path


class TestSpendingTools:
    def test_end_date_includes_that_day(self, populated_db):
        # 6.1 regression: THA2S01908389 on 8 Nov 7:53pm must count when the
        # query's range ends on 8 Nov (date-only end bound includes the day).
        result = registry.spend(start="2026-11-08", end="2026-11-08")
        assert result["total_cents"] == 9642

    def test_household_total_combines_accounts(self, populated_db):
        # 3.1 + 3.5: household default spans every account (1820 + 790 + 1250)
        result = registry.spend(start="2026-10-01", end="2026-11-30")
        assert result["total_cents"] == 13502
        assert result["total"] == "$135.02"

    def test_period_filter(self, populated_db):
        result = registry.spend(start="2026-10-13", end="2026-10-31")
        assert result["total_cents"] == 790 + 1250

    def test_breakdown_by_type(self, populated_db):
        # 3.1: online vs in-store
        result = registry.spend_by_type()
        by_type = {row["txn_type"]: row["total_cents"] for row in result["breakdown"]}
        assert by_type == {"online": 1820, "in-store": 11682}

    def test_monthly_breakdown(self, populated_db):
        result = registry.spend_by_month()
        by_month = {row["month"]: row["total_cents"] for row in result["months"]}
        assert by_month == {"2026-10": 3860, "2026-11": 9642}


class TestProductTools:
    def test_product_aggregates(self, populated_db):
        # 3.2
        result = registry.product_spend("MAGGI NOODLES CURRY 5S")
        assert result["found"] is True
        assert result["total_spend_cents"] == 820
        assert result["total_quantity"] == 2
        assert result["unit_prices_cents_paid"] == [410]

    def test_unknown_product_reports_not_found(self, populated_db):
        result = registry.product_spend("NO SUCH PRODUCT")
        assert result["found"] is False


class TestPromotionTools:
    def test_promotion_savings_sum(self, populated_db):
        # 3.3: the only promoted item has a -$0.26 discount, i.e. $0.26 saved
        result = registry.promotion_savings()
        assert result["savings_cents"] == 26
        assert result["savings"] == "$0.26"

    def test_promoted_items_effective_price(self, populated_db):
        result = registry.promoted_item_details()
        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["promotion_text"] == "2 for $5.35"
        assert item["effective_unit_price_cents"] == 294 - 26


class TestAccountAttribution:
    def test_per_account_breakdown(self, populated_db):
        # 3.5: responsibility view
        result = registry.spend_by_account()
        by_account = {row["account"]: row["total_cents"] for row in result["accounts"]}
        assert by_account == {"member-a": 12252, "member-b": 1250}

    def test_account_filter(self, populated_db):
        result = registry.spend(account="member-b")
        assert result["total_cents"] == 1250


class TestCoverageTransparency:
    def test_every_tool_result_includes_coverage(self, populated_db):
        # 3.4: structured results always carry the queried data range
        results = [
            registry.spend(),
            registry.spend_by_type(),
            registry.spend_by_month(),
            registry.spend_by_account(),
            registry.product_spend("MAGGI NOODLES CURRY 5S"),
            registry.promotion_savings(),
            registry.promoted_item_details(),
        ]
        for result in results:
            assert "coverage" in result
            assert result["coverage"]["earliest"] == "2026-10-12 15:30:00"
            assert result["coverage"]["latest"] == "2026-11-08 19:53:00"
            assert result["coverage"]["transactions"] == 4


RAW_TXN_MAGGI_CHEAPER = {
    "transaction_id": "SS-1003",
    "purchased_at": "1 Nov 2026, 10:00 AM",
    "txn_type": "online",
    "store_location": "SHENG SIONG ONLINE",
    "total": "$3.50",
    "items": [
        {
            "product_name": "MAGGI NOODLES CURRY 5S",
            "qty": "1",
            "unit_price": "$3.50",
            "line_total": "$3.50",
        },
    ],
}


class TestRunSql:
    def test_valid_select_returns_rows_and_coverage(self, populated_db):
        result = registry.run_sql("SELECT COUNT(*) AS n FROM transaction_record")
        assert result["columns"] == ["n"]
        assert result["rows"] == [[4]]
        assert result["row_count"] == 1
        assert result["truncated"] is False
        assert "coverage" in result

    def test_delete_is_rejected_and_data_unchanged(self, populated_db):
        result = registry.run_sql("DELETE FROM transaction_record")
        assert "error" in result
        assert "coverage" in result
        # The store itself is unchanged.
        assert registry.run_sql("SELECT COUNT(*) FROM transaction_record")["rows"] == [[4]]

    def test_multi_statement_string_is_rejected(self, populated_db):
        result = registry.run_sql("SELECT 1; DELETE FROM line_item")
        assert "error" in result
        assert registry.run_sql("SELECT COUNT(*) FROM line_item")["rows"] == [[6]]

    def test_row_cap_with_truncation_flag(self, populated_db):
        sql = (
            "WITH RECURSIVE cnt(x) AS ("
            "  SELECT 1 UNION ALL SELECT x + 1 FROM cnt LIMIT 500"
            ") SELECT x FROM cnt"
        )
        result = registry.run_sql(sql)
        assert result["row_count"] == registry.MAX_SQL_ROWS
        assert result["truncated"] is True

    def test_invalid_sql_returns_structured_error(self, populated_db):
        result = registry.run_sql("SELEC nope FROM nothing")
        assert "error" in result
        assert "sql" in result
        assert "coverage" in result

    def test_write_is_blocked_at_the_connection(self, populated_db):
        # 1.1: the read-only connection refuses writes directly.
        import sqlite3

        conn = registry.connect_readonly(populated_db)
        try:
            with pytest.raises(sqlite3.Error):
                conn.execute("INSERT INTO account (name) VALUES ('x')")
        finally:
            conn.close()


class TestProductSearchTools:
    def test_partial_match_finds_fragment(self, populated_db):
        result = registry.search_products("MAGGI")
        assert result["found"] is True
        assert result["matches"][0]["product_name"] == "MAGGI NOODLES CURRY 5S"
        assert result["matches"][0]["total_spend_cents"] == 820

    def test_no_match(self, populated_db):
        result = registry.search_products("CAVIAR")
        assert result["found"] is False
        assert result["matches"] == []

    def test_fragment_wildcards_are_literal(self, populated_db):
        # "_" must not act as a single-character wildcard.
        result = registry.search_products("MAGGI X NOODLES")
        assert result["found"] is False

    def test_price_history_chronological_with_price_changes(self, populated_db):
        # Add a second MAGGI occurrence at a different price.
        from grocery_agent.store import normalize

        conn = registry.connect_store()
        normalize.ingest_raw(conn, "member-a", dict(RAW_TXN_MAGGI_CHEAPER))
        conn.close()

        result = registry.product_price_history("MAGGI NOODLES CURRY 5S")
        assert result["found"] is True
        prices = [occ["unit_price_cents"] for occ in result["occurrences"]]
        assert prices == [410, 350]  # chronological, both prices present
        dates = [occ["purchased_at"] for occ in result["occurrences"]]
        assert dates == sorted(dates)

    def test_price_history_unknown_product(self, populated_db):
        result = registry.product_price_history("NO SUCH PRODUCT")
        assert result["found"] is False

    def test_top_products_by_spend(self, populated_db):
        result = registry.top_products(metric="spend")
        top = result["products"][0]
        assert top["product_name"] == "FRESH NORWEGIAN SALMON PORTION"
        assert top["total_spend_cents"] == 9642

    def test_top_products_by_quantity(self, populated_db):
        result = registry.top_products(metric="quantity")
        top = result["products"][0]
        assert top["product_name"] == "MAGGI NOODLES CURRY 5S"
        assert top["total_quantity"] == 2

    def test_top_products_by_count(self, populated_db):
        result = registry.top_products(metric="count", limit=10)
        counts = {p["product_name"]: p["purchases"] for p in result["products"]}
        assert set(counts.values()) == {1}

    def test_top_products_period_filter(self, populated_db):
        result = registry.top_products(metric="spend", start="2026-11-01")
        assert [p["product_name"] for p in result["products"]] == [
            "FRESH NORWEGIAN SALMON PORTION"
        ]


class TestTransactionTools:
    def test_transaction_details_lists_all(self, populated_db):
        # Two accounts and both txn types are represented.
        result = registry.transaction_details()
        assert len(result["transactions"]) == 4
        assert {t["txn_type"] for t in result["transactions"]} == {"online", "in-store"}
        assert {t["account"] for t in result["transactions"]} == {"member-a", "member-b"}

    def test_transaction_details_filters(self, populated_db):
        result = registry.transaction_details(txn_type="online")
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["total_cents"] == 1820

        result = registry.transaction_details(account="member-b")
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["transaction_id"] == "SS-2001"

    def test_transaction_items_known_transaction(self, populated_db):
        result = registry.transaction_items("member-a", "SS-1001")
        assert result["found"] is True
        names = [item["product_name"] for item in result["items"]]
        assert names == ["SUNLIGHT DISHWASH LIQ LIME 800ML", "MAGGI NOODLES CURRY 5S"]
        assert result["items"][1]["unit_price"] == "$4.10"

    def test_transaction_items_unknown_transaction(self, populated_db):
        result = registry.transaction_items("member-a", "SS-9999")
        assert result["found"] is False

    def test_compare_periods(self, populated_db):
        result = registry.compare_periods(
            "2026-10-01", "2026-10-31", "2026-11-01", "2026-11-30"
        )
        assert result["period_a"]["total_cents"] == 3860
        assert result["period_b"]["total_cents"] == 9642
        assert result["difference_cents"] == 3860 - 9642
        assert result["percent_change"] == round((3860 - 9642) / 9642 * 100, 1)

    def test_compare_periods_zero_denominator(self, populated_db):
        result = registry.compare_periods(
            "2026-12-01", "2026-12-31", "2026-01-01", "2026-01-31"
        )
        assert result["difference_cents"] == 0
        assert result["percent_change"] is None
