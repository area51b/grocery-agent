# grocery-agent

Family Grocery Intelligence Agent — analyzes household grocery purchasing
history from Sheng Siong Online and answers spending questions.

Spec-driven development via [OpenSpec](https://openspec.dev); the behavior
specs live in `openspec/specs/`.

## Setup

```sh
uv sync                       # install Python dependencies
uv run playwright install chromium
cp .env.example .env          # then fill in the gateway URL, key, and model
```

## Commands

### Ingest transaction history

```sh
uv run grocery ingest --account a1
uv run grocery ingest --account a2
```

Run once per household account. A headed browser opens — log in to Sheng
Siong manually in that window; the session persists per account under
`data/profiles/<account>/`. Already-captured transactions are skipped, so
re-running only extracts what is new.

### Ask spending questions

```sh
uv run grocery ask "How much did we spend last month?"
uv run grocery ask "Who spent more this month?"
uv run grocery ask "How much did we save from promotions in October?"
```

The agent answers any question the stored data can support — not just totals:

| Question | Tool used |
| --- | --- |
| "How often do we buy milk?" | product search |
| "How has the price of eggs changed?" | price history |
| "What do we spend the most on?" | product ranking |
| "What was in my most recent order?" | transaction browsing |
| "Did we spend more this month than last?" | period comparison |
| "Which store location did we buy the most from?" | ad-hoc read-only SQL |

Answers are computed by deterministic SQL/Python tools over the household
data; the agent relays tool results and states the coverage of the data. The
ad-hoc SQL path runs on a strictly read-only database connection, so the
agent's questions can never modify the store.

### Chat with the agent on Telegram

Instead of the CLI, household members can ask questions in a Telegram chat:

```sh
uv run grocery telegram
```

Setup:

1. Create a bot with [@BotFather](https://t.me/BotFather) in Telegram and copy
   its token.
2. Put the token in `.env` (git-ignored):

   | Variable | Purpose |
   | --- | --- |
   | `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
   | `TELEGRAM_ALLOWED_USER_IDS` | Comma-separated numeric Telegram user IDs allowed to chat |

3. Find your Telegram user ID (e.g. message @userinfobot) and list the IDs of
   every household member who should have access.

The bot is deny-by-default: with `TELEGRAM_ALLOWED_USER_IDS` unset or empty,
nobody can use it. Permitted members can type any question free-form, use the
slash commands (`/spend`, `/top`, `/last`, `/help`), or tap the suggested
questions shown by `/help`. The slash-command menu (what Telegram suggests
when you type `/`) is registered with Telegram at startup. The suggestion
buttons are a reply keyboard: after editing them in the admin area, send
`/help` once and the new keyboard replaces the old one in your Telegram app.
Multiple members can chat at the same time; each person's own questions are
answered one at a time.

The bot runs in the foreground and blocks, so keep it alive with a terminal
multiplexer or run it detached:

```sh
tmux new -s grocery-bot 'uv run grocery telegram'   # or:
nohup uv run grocery telegram > data/telegram.log 2>&1 &
```

### Dashboard and admin web app

Run the analytics dashboard and the Telegram bot as a single web application:

```sh
uv run grocery webapp
```

Then open `http://localhost:8000` (override with `GROCERY_WEB_PORT`) and log
in with the `ADMIN_PASSWORD` from `.env`. The dashboard shows aggregate
charts — total spend, spend by month, by account, by type, top products, and
promotion savings — with date-range and account filters. Every figure is
computed by the same deterministic read-only queries the agent uses; the
store is opened strictly read-only.

The admin area edits the bot's slash-command questions and the suggested
questions shown on `/help`; edits apply to the running bot immediately and
are persisted in a separate admin store (`data/admin.db`). The settings page
shows non-credential configuration only — tokens, keys, and passwords stay in
the git-ignored `.env` and are never displayed. Ingestion is not triggered
from the dashboard; run `grocery ingest` separately as before.

| Variable | Purpose |
| --- | --- |
| `ADMIN_PASSWORD` | Dashboard login password (unset = nobody can log in) |
| `ADMIN_SESSION_SECRET` | Optional cookie-signing key (auto-generated if unset) |
| `GROCERY_WEB_PORT` | Web port (default `8000`) |

The bot's Telegram allowlist stays in `.env` (`TELEGRAM_ALLOWED_USER_IDS`) and
is intentionally not editable from the dashboard.

### Analysis toolset

The agent chooses among these tools (defined in
`src/grocery_agent/tools/registry.py`):

| Tool | Answers questions like |
| --- | --- |
| `spend`, `spend_by_type`, `spend_by_month`, `spend_by_account` | totals, breakdowns, "who spent more?" |
| `product_spend` | "how much do we spend on <exact product>?" |
| `promotion_savings`, `promoted_item_details` | "how much did promotions save us?" |
| `search_products` | "do we ever buy milk?" (partial names) |
| `product_price_history` | "how has the price of eggs changed?" |
| `top_products` | "what do we spend the most on?" |
| `transaction_details` | "which orders did we place in October?" |
| `transaction_items` | "what was in my last order?" |
| `compare_periods` | "did we spend more this month than last?" |
| `run_sql` | anything else answerable from the store |

`run_sql` executes a single read-only `SELECT` against the normalized store
with a row cap (200) and a time budget; writes are blocked at the SQLite
connection level, not by string matching.

## Configuration

Environment variables (set in `.env`, which is git-ignored):

| Variable | Purpose |
| --- | --- |
| `GROCERY_GATEWAY_BASE_URL` | LiteLLM gateway base URL (OpenAI-compatible) |
| `GROCERY_GATEWAY_API_KEY` | Gateway virtual key |
| `GROCERY_MODEL` | Model name served by the gateway |
| `GROCERY_DB` | Optional SQLite path (default `data/grocery.db`) |

Security: Sheng Siong credentials are never stored or read by this
application. You type them only into the real browser during login.

## Development

### Test suite

```sh
uv run pytest -q              # whole suite (no gateway or real data needed)
uv run pytest tests/test_tools.py -q          # analysis tools only
uv run pytest tests/test_agent.py -q          # agent tool registration
uv run pytest "tests/test_tools.py::TestRunSql" -q  # guarded SQL tool tests
```

The suite builds its own temporary SQLite stores from fixtures in
`tests/fixtures.py`; it never touches `data/grocery.db` and never calls the
LLM gateway. `tests/test_agent.py` constructs the agent graph but requires
`GROCERY_GATEWAY_*`/`GROCERY_MODEL` to be set (`.env` is loaded if present).

### Manual end-to-end check

With `data/grocery.db` populated (ingest first if needed) and `.env` filled
in, exercise one question per tool category:

```sh
uv run grocery ask "How often do we buy milk?"                    # search_products
uv run grocery ask "How has the price of eggs changed?"           # product_price_history
uv run grocery ask "What do we spend the most on?"                # top_products
uv run grocery ask "What was in my most recent order?"            # transaction_items
uv run grocery ask "Which store location did we spend the most at?"  # run_sql
```

Check each answer for two things: the numbers come from the store (no
invented figures), and the reply states the data coverage it is based on.

### Inspecting the store directly

```sh
sqlite3 data/grocery.db "SELECT COUNT(*) FROM transaction_record;"
```

