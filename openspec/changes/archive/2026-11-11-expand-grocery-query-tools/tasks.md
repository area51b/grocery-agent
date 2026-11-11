# Tasks

## 1. Guarded SQL tool

- [x] 1.1 Add a read-only connection helper in `store/schema.py` that opens the database via `file:...?mode=ro` URI and installs a deny-writes authorizer; verify a write attempt on the read-only connection raises `sqlite3` error and the DB file is unchanged
- [x] 1.2 Implement `run_sql(sql)` in `tools/registry.py`: single `SELECT` only, row cap with `truncated` flag, wall-clock budget via progress handler, result shape `{columns, rows, row_count, truncated, coverage}`; verify with tests in `tests/test_tools.py` covering a valid query, a rejected `DELETE`, a rejected multi-statement string, and a capped large result
- [x] 1.3 Verify an invalid SQL string returns a structured error result the agent can read, and that `coverage` is present in every result, by asserting against a fixture store

## 2. Product tools

- [x] 2.1 Add `search_products` query to `store/queries.py` (case-insensitive partial match with escaped `%`/`_`, aggregate spend per matching product) and a `search_products` tool in the registry; verify tests cover a partial match, an exact match, and a no-match result
- [x] 2.2 Add `product_price_history` query and tool returning chronological occurrences with date and unit price for a product; verify the test asserts chronological ordering across a fixture store with price changes
- [x] 2.3 Add `top_products` query and tool ranked by spend, quantity, or purchase count over an optional period with account filter; verify the ranking order in tests for each ranking metric

## 3. Transaction and comparison tools

- [x] 3.1 Add `transaction_details` query and tool listing transactions in a period filtered by type and account, returning date, type, store location, and total; verify the tool on a fixture store with two accounts and both txn types
- [x] 3.2 Add `transaction_items` query and tool returning all line items of one identified transaction with quantity, unit price, line total, and promotion text; verify the test matches the fixture store's known items and that an unknown transaction id returns a not-found result
- [x] 3.3 Add `compare_periods` query and tool computing both totals, the difference, and percentage change in Python from integer cents with a zero-denominator guard; verify the test asserts exact difference and one-decimal percentage

## 4. Agent integration

- [x] 4.1 Register all new tools in `agent/__init__.py` `create_react_agent` call and update `_SYSTEM_PROMPT` with the expanded toolset guidance (prefer higher-level tools, SQL fallback, never-mutate rule); verify `build_agent()` constructs successfully and every registry tool appears in the bound tool list
- [x] 4.2 Update `README.md` "Ask spending questions" section with example questions that use the new tools (e.g. "how often do we buy milk?", "what was in my most recent order?"); verify the documented commands run as written

## 5. End-to-end verification

- [x] 5.1 Run the full test suite (`uv run pytest -q`) and confirm all existing and new tests pass
- [x] 5.2 Exercise `uv run grocery ask` end to end with one question per new tool category against the real store and confirm answers include tool-computed values and coverage
