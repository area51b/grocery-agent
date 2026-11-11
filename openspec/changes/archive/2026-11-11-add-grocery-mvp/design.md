# Design

## Context

Greenfield Python project; see proposal.md for motivation and the four capability specs for behavioral requirements. Constraints that shape the design: single user on a local Mac, manual CLI-triggered ingestion with interactive browser login, no Sheng Siong API (browser automation only), LLM never does arithmetic or touches credentials, SQLite as the only data store. Python 3.14 with `uv` for project management; LangGraph for orchestration; the LLM is reached through an OpenAI-compatible LiteLLM gateway.

## Goals / Non-Goals

**Goals:**

- One CLI-driven application with two commands: ingest (browser extraction to SQLite) and ask (LangGraph agent over deterministic query tools).
- Raw capture preserved in SQLite so normalization can be re-run without re-scraping.
- Incremental ingestion: discovery collects transaction IDs; only unseen transactions are opened and extracted.
- All arithmetic in SQL/Python; the agent receives computed values only.

**Non-Goals:**

- Unattended/scheduled ingestion, credential storage of any kind, promo-math parsing, fuzzy product matching, purchasing, multi-agent systems, RAG/vector DB, cloud deployment (see proposal).

## Decisions

1. **Playwright, sync API, headed browser with a per-account persistent profile.** Ingestion launches a visible Chromium using a persistent user-data directory chosen per account label (e.g. `--account member-a`), so both household accounts stay logged in independently. First run per account: the user logs in manually; the session persists for later runs, and re-authentication is prompted when expired. Alternatives considered: headless + stored credentials (violates the security principle); reverse-engineered HTTP calls with cookies (fragile and effectively the same auth problem). The interactive login is what keeps credentials entirely outside the codebase.

2. **Raw and normalized data live in one SQLite file.** A `raw_transaction` table stores the as-captured JSON document keyed by account label and transaction ID; normalized tables (`transaction`, `line_item`) are derived from it and every row carries the account label. The label is a locally chosen name (CLI argument), never the Sheng Siong login identity, and its only purpose is attribution of who is responsible for a purchase — nothing else treats accounts differently. Alternative: raw JSON files on disk — rejected because SQLite gives transactional consistency and keeps backup/rollback trivial.

3. **Money as integer cents.** All normalized monetary values (unit price, line total, discount, transaction total) are stored as INTEGER minor units (e.g. 535 for $5.35, -26 for a $0.26 discount). Alternatives: REAL floats (rounding drift — rejected), TEXT decimals (awkward aggregation — rejected). Raw data keeps the original text as captured.

4. **Incremental ingestion keyed on account and transaction ID.** Each run targets one account: discover all listed transactions (online and in-store) with metadata, compare (account, transaction ID) pairs against the store, and only open detail pages for uncaptured transactions. Already-captured transactions are skipped. The composite key deliberately does not assume transaction IDs are globally unique across accounts. This follows from the idempotency requirement and keeps runs fast.

5. **Deterministic tools as plain Python functions over `sqlite3`.** Each tool (spending by period/type, product analysis, promotion/discount totals, data-coverage info) is a typed function returning computed values, registered as a LangGraph tool. Household aggregates span all accounts by default; an optional account dimension supports per-account breakdown. Alternative: an SQL-executing tool the model writes queries for — rejected; the model must not author ad-hoc SQL that could mis-aggregate.

6. **Single LangGraph agent with tool calling.** One ReAct-style agent node binds the query tools and answers in a conversation. Model access via the OpenAI-compatible LiteLLM gateway endpoint, configured through environment variables (base URL, key, model name) — no gateway key in source. The agent's prompts contain tool results only, never raw extraction payloads.

7. **Extraction baseline is DOM scraping; XHR interception is a spike.** MVP selectors read the transaction pages directly. A small spike will check whether the site's own XHR responses (captured via Playwright network events) offer a more stable extraction surface; if so, switching is an internal change invisible to the specs, made easier by raw capture + re-normalization.

8. **Project layout mirrors the capability boundaries.** Modules: `ingest` (browser, discovery, extraction), `store` (schema, normalization, queries), `tools` (tool wrappers over `store` queries), `agent` (LangGraph graph), plus a thin CLI. Tests use captured raw fixtures so normalization and query logic are testable without the website.

## Risks / Trade-offs

- [Site DOM/flow changes break extraction] → Raw capture plus re-normalization limits blast radius to ingestion; failures are isolated per transaction and reported.
- [Anti-automation measures or ToS concerns] → Manual, user-triggered runs at low frequency; interactive login; no headless hammering.
- [Session expiry mid-run] → Ingestion detects the logged-out state and asks the user to re-authenticate in the visible browser, then resumes.
- [LLM misinterprets or relays results incorrectly] → Tools return structured computed values including coverage info; agent instructions require presenting tool values verbatim and declining unavailable computations.
- [Python 3.14 compatibility of Playwright/LangGraph] → Verify at project setup; if needed, pin an older Python via uv.
- [Single SQLite file corrupts or is deleted] → It is derived data plus raw captures; re-ingest rebuilds it. Rollback for schema changes: delete the DB file and re-run ingestion.

## Open Questions

- Definitive product-name normalization rules (case, size suffixes) — start with exact-name matching and refine against real data.
- Whether XHR interception (decision 7) becomes the primary extraction surface.
- Location of the SQLite file by default (proposed: `data/grocery.db`, git-ignored) and CLI command naming.
