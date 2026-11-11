"""Slash commands and suggestion buttons for the Telegram bot.

Every command maps to a fixed natural-language question that is answered
through the same agent path as typed messages, so the agent's tool selection
and data-coverage guarantees apply identically.
"""

from __future__ import annotations

# Telegram command name -> the question the agent is asked.
COMMAND_QUESTIONS: dict[str, str] = {
    "spend": "How much did we spend this month in total?",
    "top": "What do we spend the most on?",
    "last": "What was in my most recent order?",
}

# Commonly asked questions offered as tappable suggestion buttons.
SUGGESTED_QUESTIONS: tuple[str, ...] = (
    "How much did we spend this month?",
    "Who spent more this month?",
    "How much did we save from promotions?",
    "What do we spend the most on?",
    "How has the price of eggs changed?",
    "What was in my most recent order?",
)

COMMAND_LABELS: dict[str, str] = {
    "spend": "total spend this month",
    "top": "top spending categories",
    "last": "most recent order",
    "help": "show this help",
}


def help_text() -> str:
    """Build the /help reply: available commands plus how to ask free-form."""
    lines = ["Commands:"]
    for name, label in COMMAND_LABELS.items():
        lines.append(f"/{name} — {label}")
    lines.append("")
    lines.append(
        "Or just type any grocery question — e.g. "
        '"How much did we spend last month?"'
    )
    return "\n".join(lines)
