# Proposal

## Why

Grocery purchasing data for the family lives behind the Sheng Siong Online transaction history page, visible only as one-off web pages. There is no way to answer basic questions — where is the money going, which products cost the most, are promotions actually saving us money — without manually reading past orders. This project builds a family grocery intelligence agent that ingests transaction history, stores it locally, and answers spending questions conversationally.

## What Changes

This is the initial MVP build of a new Python application:

- Add authenticated, browser-based ingestion of Sheng Siong Online transaction history (online and in-store), including transaction metadata and item-level line items.
- Add storage of raw extracted data (as-captured) and a normalized SQLite data store derived from it, consolidating purchases from multiple household Sheng Siong accounts under one data set, attributed by a local per-account label.
- Add deterministic Python/SQL query tools for spending totals, product-level analysis, and price/promotion analysis.
- Add a LangGraph agent that selects and calls those tools and presents results conversationally.
- Enforce architectural principle: the LLM performs reasoning, tool selection, and conversation only — all arithmetic, financial aggregation, and data access is done by deterministic code.
- Enforce security principle: Sheng Siong credentials are never stored in source code, prompts, git history, SQLite, or LLM context; the browser session is authenticated by the user (or a local credential mechanism) outside of the LLM's view.

## Capabilities

### New Capabilities

- `transaction-ingestion`: Authenticated browser-based extraction of Sheng Siong transaction history — discovering transactions (online and in-store), opening individual transaction details, extracting transaction metadata (ID, date/time, store, total) and line items (product name, quantity, unit price, line total, promotion/discount where present), and capturing the raw extracted data.
- `grocery-data-store`: Normalization of raw captured data into a consistent schema and its persistence in SQLite, preserving the raw payload as the ingestion source of truth and consolidating multiple household accounts into one attributed data set.
- `spending-analysis-tools`: Deterministic Python/SQL query tools over the normalized store covering spending aggregation, product-level analysis, and price/promotion analysis. All numeric results come from SQL/Python, never from model arithmetic.
- `insight-agent`: A LangGraph agent that maps natural-language questions to the analysis tools, orchestrates multi-step tool use, and presents results — without ever handling Sheng Siong credentials or performing its own arithmetic on raw data.

### Modified Capabilities

None — this is the initial capability set for a new project.

## Impact

- **New codebase**: Python application (Python 3.14 available locally); no existing code is affected.
- **New dependencies**: Playwright (browser automation), LangGraph (orchestration), SQLite (stdlib, no dependency).
- **External system**: Sheng Siong Online website (shengsiong.com.sg). Ingestion depends on its current DOM/flow; there is no official public API. Site redesigns or anti-automation measures can break ingestion.
- **Local machine only**: single-user desktop deployment; no cloud services, no web hosting.
- **Data sensitivity**: purchase history is personal data, stored locally; credentials are handled entirely outside the application's data flow (browser session or OS-level credential store).
