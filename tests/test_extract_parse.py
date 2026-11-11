"""Tests for line-item parsing from captured modal text (task 4.3 calibration)."""

from __future__ import annotations

import pytest

from grocery_agent.ingest.extract import parse_item


def test_normal_item():
    raw = parse_item(["JF Halal Chicken - Large 1.4KG-1.6KG", "Qty: 1 x $11.90", "$11.90"])
    assert raw["product_name"] == "JF Halal Chicken - Large 1.4KG-1.6KG"
    assert raw["qty"] == "1"
    assert raw["unit_price"] == "$11.90"
    assert raw["line_total"] == "$11.90"
    assert "promotion" not in raw


def test_promo_item_with_discount_after_total():
    # Real captured lines: discount appears after the promotion, following
    # the line total. The line total must not be overwritten by the discount.
    raw = parse_item(
        [
            "*TCIF CLEANSER REG 660ML",
            "Qty: 2 x $2.12",
            "$4.24",
            "4 for $6.50",
            "-$0.98",
        ]
    )
    assert raw["qty"] == "2"
    assert raw["unit_price"] == "$2.12"
    assert raw["line_total"] == "$4.24"
    assert raw["promotion"] == "4 for $6.50"
    assert raw["discount"] == "-$0.98"


def test_weighed_item_has_no_qty_line():
    raw = parse_item(["MYS Snake Gourd", "$0.92"])
    assert raw["product_name"] == "MYS Snake Gourd"
    assert raw["qty"] is None
    assert raw["unit_price"] is None
    assert raw["line_total"] == "$0.92"
    assert "promotion" not in raw


def test_empty_item_raises():
    with pytest.raises(ValueError):
        parse_item([])
