"""Shared fixtures: raw capture documents styled after the real site."""

from __future__ import annotations

import pytest

RAW_TXN_PROMO = {
    "transaction_id": "SS-1001",
    "purchased_at": "12 Oct 2026, 03:30 PM",
    "txn_type": "online",
    "store_location": "SHENG SIONG ONLINE",
    "total": "$18.20",
    "items": [
        {
            "product_name": "SUNLIGHT DISHWASH LIQ LIME 800ML",
            "qty": "1",
            "unit_price": "$2.94",
            "line_total": "$2.94",
            "promotion": "2 for $5.35",
            "discount": "-$0.26",
        },
        {
            "product_name": "MAGGI NOODLES CURRY 5S",
            "qty": "2",
            "unit_price": "$4.10",
            "line_total": "$8.20",
            "promotion": None,
            "discount": None,
        },
    ],
}

RAW_TXN_PLAIN = {
    "transaction_id": "SS-1002",
    "purchased_at": "14 Oct 2026, 10:15 AM",
    "txn_type": "in-store",
    "store_location": "SHENG SIONG ANG MO KIO",
    "total": "$7.90",
    "items": [
        {
            "product_name": "PANDAN LEAVES 100G",
            "qty": "1",
            "unit_price": "$1.50",
            "line_total": "$1.50",
        },
        {
            "product_name": "EGGS FRESH 10S",
            "qty": "1",
            "unit_price": "$6.40",
            "line_total": "$6.40",
        },
    ],
}

RAW_TXN_OTHER_ACCOUNT = {
    "transaction_id": "SS-2001",
    "purchased_at": "20 Oct 2026, 06:05 PM",
    "txn_type": "in-store",
    "store_location": "SHENG SIONG BISHAN",
    "total": "$12.50",
    "items": [
        {
            "product_name": "RICE THAI FRAGRANT 5KG",
            "qty": "1",
            "unit_price": "$12.50",
            "line_total": "$12.50",
        },
    ],
}

# Real-world shapes captured from the live site (2026-11-11, TH06G00400953).
RAW_TXN_WEIGHED = {
    "transaction_id": "TH06G00400953",
    "purchased_at": "25 Oct 2026, 11:09am",
    "txn_type": "in-store",
    "store_location": "BLK 88 TANGLIN HALT ROAD",
    "total": "$23.85",
    "items": [
        {
            "product_name": "CAM English Gourd 400G",
            "qty": "1",
            "unit_price": "$1.20",
            "line_total": "$1.20",
        },
        {
            "product_name": "*TCIF CLEANSER REG 660ML",
            "qty": "2",
            "unit_price": "$2.12",
            "line_total": "$4.24",
            "promotion": "4 for $6.50",
            "discount": "-$0.98",
        },
        {
            "product_name": "MYS Snake Gourd",
            "line_total": "$0.92",
        },
    ],
}


RAW_TXN_NOV8 = {
    "transaction_id": "THA2S01908389",
    "purchased_at": "8 Nov 2026, 7:53pm",
    "txn_type": "in-store",
    "store_location": "BLK 88 TANGLIN HALT ROAD",
    "total": "$96.42",
    "items": [
        {
            "product_name": "FRESH NORWEGIAN SALMON PORTION",
            "line_total": "$96.42",
        },
    ],
}


@pytest.fixture
def sample_raw_documents():
    return [RAW_TXN_PROMO, RAW_TXN_PLAIN, RAW_TXN_OTHER_ACCOUNT]
