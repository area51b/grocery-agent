"""Money and timestamp parsing helpers.

Raw captures keep values exactly as the website shows them ("$2.94",
"-$0.26", "2 for $5.35"). Normalization converts monetary text into integer
cents so aggregation is exact.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

_MONEY_CHARS = set("0123456789.-")


def parse_money_cents(text: str) -> int:
    """Parse captured monetary text into integer cents.

    Handles "$2.94", "-$0.26", "$1,234.56", "2.94", "-0.26". Raises ValueError
    for anything that is not recognizably a single monetary value.
    """
    cleaned = "".join(ch for ch in text if ch in _MONEY_CHARS)
    if cleaned in {"", "-", ".", "-."}:
        raise ValueError(f"Not a monetary value: {text!r}")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Not a monetary value: {text!r}") from exc
    return int((amount * 100).to_integral_value())


def parse_quantity(text: str) -> float:
    """Parse a captured quantity ("1", "0.246") into a float."""
    return float(Decimal(str(text).strip().replace("x", "").strip() or "0"))


def parse_timestamp(text: str) -> str:
    """Normalize a captured date/time into ISO 8601 (second precision).

    Accepts common website formats; raises ValueError when unparseable.
    """
    text = text.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d %b %Y, %I:%M%p",
        "%d %b %Y, %I:%M %p",
        "%d %b %Y %I:%M%p",
        "%d %b %Y %I:%M %p",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt).isoformat(sep=" ", timespec="seconds")
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date/time: {text!r}")
