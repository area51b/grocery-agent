"""Environment loading for gateway configuration.

The LiteLLM gateway endpoint, key, and model name come from environment
variables (design decision 6) — never from source. A git-ignored ``.env`` at
the project root is read if present. See .env.example for the expected keys.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_KEYS = (
    "GROCERY_GATEWAY_BASE_URL",
    "GROCERY_GATEWAY_API_KEY",
    "GROCERY_MODEL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USER_IDS",
)


def load_env(dotenv_path: Path | None = None) -> None:
    """Populate os.environ from a local .env without overriding existing values."""
    path = dotenv_path or Path(".env")
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key in ENV_KEYS and key not in os.environ:
            os.environ[key] = value
