"""Telegram chat interface to the insight agent (add-telegram-bot capability).

The bot is a thin adapter: it authenticates the Telegram user, maps slash
commands and suggestion buttons to plain questions, and relays the insight
agent's answer verbatim. It holds no household logic of its own.
"""
