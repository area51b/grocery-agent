"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from tests.fixtures import RAW_TXN_OTHER_ACCOUNT, RAW_TXN_PLAIN, RAW_TXN_PROMO


@pytest.fixture
def sample_raw_documents():
    return [RAW_TXN_PROMO, RAW_TXN_PLAIN, RAW_TXN_OTHER_ACCOUNT]
