# Proposal

## Why

Today the agent can only answer questions that fit one of seven fixed tool shapes (totals, by-type, by-month, by-account, exact-name product, promotion savings, promoted items). Any question outside those shapes — "how often do we buy milk?", "which week was our most expensive?", "show me what was in the 12 October order" — is declined. The household wants traditional-application freedom: ask anything about the grocery data and get an answer computed from the store.

## What Changes

- Add a **guarded read-only SQL tool** so the agent can answer *any* question about the normalized store: it writes a `SELECT`, the SQLite engine computes the result, and the model relays it verbatim. This removes the structural question limit while keeping all arithmetic deterministic (in SQL, never in the model).
- Add higher-level tools for the most common question patterns that are currently impossible or awkward:
  - `search_products` — find products by partial/fuzzy name (today only exact-name lookup exists)
  - `product_price_history` — price paid for a product over time, per occurrence
  - `top_products` — most-purchased products ranked by spend, quantity, or count
  - `transaction_details` — list transactions in a period with filters (type, account, store location)
  - `transaction_items` — line items of a single transaction ("what was in that order?")
  - `compare_periods` — spend in two date ranges with the difference computed in code
- Extend the agent's system prompt to describe the full question space and the SQL tool, so the agent reaches for the right tool instead of declining.
- No changes to ingestion, schema, or the data store.

## Capabilities

### New Capabilities
- `guarded-sql-query`: Defines the read-only SQL execution path exposed to the agent — statement restrictions (single `SELECT`), row/time limits, write prevention, and structured result shape — so unrestricted questions stay safe and deterministic.

### Modified Capabilities
- `spending-analysis-tools`: New requirements for product search by partial name, product price history over time, ranked product listings, transaction and line-item browsing, period comparison, and general read-only SQL querying over the normalized store; existing deterministic-computation and coverage-transparency requirements continue to apply to all new tools.
- `insight-agent`: The question-to-tool mapping requirement broadens from seven fixed tools to the expanded toolset including the guarded SQL tool; the agent may compose a question into SQL when no higher-level tool fits, while still never doing arithmetic itself.

## Impact

- `src/grocery_agent/tools/registry.py` — new tool functions registered with the agent
- `src/grocery_agent/store/queries.py` — supporting SQL query functions
- `src/grocery_agent/agent/__init__.py` — tool registration list and system prompt
- `tests/test_tools.py` — tests for the new tools, including SQL tool guardrails
- No schema migration; no ingestion changes; no new dependencies
