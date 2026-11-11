"""Command-line interface for the grocery agent.

Commands:
    grocery ingest --account <label>   Ingest transaction history for one account.
    grocery ask "<question>"           Ask the insight agent a question.
    grocery telegram                   Run the Telegram bot chat interface.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="grocery",
        description="Family Grocery Intelligence Agent",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest Sheng Siong transaction history for one account.",
    )
    ingest_parser.add_argument(
        "--account",
        required=True,
        help="Local label identifying the household member's account (e.g. 'member-a').",
    )

    ask_parser = subparsers.add_parser(
        "ask",
        help="Ask the insight agent a question about grocery spending.",
    )
    ask_parser.add_argument("question", help="The question to answer.")

    telegram_parser = subparsers.add_parser(
        "telegram",
        help="Run the Telegram bot so household members can chat with the agent.",
    )

    args = parser.parse_args(argv)

    if args.command == "ingest":
        from grocery_agent.ingest import run_ingest

        return run_ingest(args.account)

    if args.command == "ask":
        from grocery_agent.agent import run_ask

        return run_ask(args.question)

    if args.command == "telegram":
        from grocery_agent.telegram.bot import run as run_bot

        return run_bot()

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
