"""Tests for .env loading of gateway and Telegram configuration keys."""

from __future__ import annotations

from grocery_agent.agent.env import load_env


def test_load_env_reads_telegram_keys(tmp_path, monkeypatch):
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USER_IDS"):
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "TELEGRAM_BOT_TOKEN=123:abc\n"
        "TELEGRAM_ALLOWED_USER_IDS=111,222\n"
    )
    load_env(env_file)
    import os

    assert os.environ["TELEGRAM_BOT_TOKEN"] == "123:abc"
    assert os.environ["TELEGRAM_ALLOWED_USER_IDS"] == "111,222"
