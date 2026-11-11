"""Tests for the household account registry (up to 4 accounts)."""

from __future__ import annotations

import pytest

from grocery_agent.store.accounts import MAX_ACCOUNTS, known_accounts, register_account
from grocery_agent.store.schema import connect


@pytest.fixture
def conn(tmp_path):
    return connect(str(tmp_path / "grocery.db"))


def test_register_account(conn):
    register_account(conn, "Member A")
    assert known_accounts(conn) == ["Member A"]


def test_register_duplicate_is_idempotent(conn):
    register_account(conn, "Member A")
    register_account(conn, "Member A")
    assert known_accounts(conn) == ["Member A"]


def test_household_cap_of_four(conn):
    for name in ("A1", "A2", "A3", "A4"):
        register_account(conn, name)
    with pytest.raises(ValueError, match="limit is 4"):
        register_account(conn, "A5")
    assert len(known_accounts(conn)) == MAX_ACCOUNTS
