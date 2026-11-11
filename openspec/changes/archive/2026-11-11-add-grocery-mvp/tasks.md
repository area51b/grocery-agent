# Tasks

## 1. Project setup

- [x] 1.1 Initialize the `uv` Python project (`pyproject.toml`, package skeleton with `ingest`, `store`, `tools`, `agent` modules, CLI entrypoint); verify `uv sync` succeeds and the CLI entrypoint runs
- [x] 1.2 Add dependencies (langgraph, playwright) and dev dependencies (pytest); install Playwright's Chromium; verify a script launches a headed browser and exits cleanly
- [x] 1.3 Initialize git with a `.gitignore` covering `data/`, `.env`, browser profile directories, and raw captures; verify nothing under those paths is tracked

## 2. SQLite store: schema, normalization, queries

- [x] 2.1 Implement the SQLite schema: `raw_transaction` (account label, transaction ID, as-captured JSON), `transaction` (account label, ID, date/time, type online/in-store, store location, total), `line_item` (product name, quantity, unit price, line total, promotion, discount) with all money as integer cents and transactions unique per (account, transaction ID); verify a schema-creation test
- [x] 2.2 Implement normalization from raw JSON to normalized tables; verify with captured-style fixtures covering an item with promotion/discount and an item without, asserting exact cent values
- [x] 2.3 Implement idempotent upsert keyed on (account, transaction ID); verify ingesting the same raw fixture twice leaves no duplicates, and the same transaction ID under a different account label is stored separately
- [x] 2.4 Implement re-normalization: rebuild normalized tables from retained raw rows; verify a fixture normalization change is reflected after rebuild without new raw data
- [x] 2.5 Implement the data-coverage query (earliest and latest ingested transaction dates, counts); verify against fixtures

## 3. Deterministic analysis tools

- [x] 3.1 Implement spending query tools (total over a date range, breakdown by online/in-store, spend over time) over the normalized store; verify computed results against fixture data
- [x] 3.2 Implement product-level query tools (aggregate spend, quantity, unit prices paid per product); verify against fixtures
- [x] 3.3 Implement promotion/discount query tools (total discounts in a period, effective price paid for promoted items); verify against fixtures
- [x] 3.4 Wrap the queries as typed tool functions whose results include the data-coverage range; verify each tool's structured output on fixtures
- [x] 3.5 Implement household consolidation: aggregates span all ingested accounts by default with an optional per-account breakdown; verify a two-account fixture combines totals and reports each account's share

## 4. Ingestion

- [x] 4.1 Implement the per-account persistent browser session: launches a visible Chromium with a profile selected by an account label CLI argument, detects logged-out state, waits for the user to log in manually, and confirms authentication; verify the session persists across two consecutive runs for the same account without re-login, and separately for a second account label
- [x] 4.2 Implement transaction discovery across the Online and In-Store transaction listings, extracting ID, date/time, store location, and total for the run's account; verify a live run records metadata for every listed transaction
- [x] 4.3 Implement detail-page extraction of line items (name, quantity, unit price, line total, promotion, discount) and persist raw JSON, attributed to the run's account, before normalization; verify captured raw data for one transaction matches the page contents
- [x] 4.4 Implement incremental ingestion (skip captured IDs for the run's account) and per-transaction failure isolation; verify a forced failure on one transaction leaves the rest of the run captured and a repeat run duplicates nothing
- [x] 4.5 Wire the full ingest CLI command with the account label argument (discover → extract → raw capture → normalize); verify `grocery ingest --account <label>` on the live site populates raw and normalized tables with the correct attribution

## 5. Insight agent

- [x] 5.1 Configure the LangGraph agent's model access from environment variables (gateway base URL, key, model); verify the agent constructs and completes one model round-trip without any gateway values in source
- [x] 5.2 Bind the analysis tools and implement the `ask` CLI command; verify a spending question returns the tool's computed value with its data range
- [x] 5.3 Enforce the no-arithmetic and credential-isolation behaviors in the agent instructions; verify an unanswerable question is declined without invented numbers and no raw payload appears in the agent's message history

## 6. Integration

- [x] 6.1 End-to-end run on the live site: `grocery ingest` for both household accounts, then `grocery ask` for a household spending question, a product question, and a promotion question; verify answers match direct SQL results and household totals equal the sum of per-account data
- [x] 6.2 Write the README (setup, login flow, ingest and ask commands, environment variables) and verify the documented commands run as written

## Workflow follow-up

- Review the change against the specs, then archive it.
- Verify the archived result.
