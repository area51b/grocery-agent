# Design

## Context

The agent (`src/grocery_agent/agent/__init__.py`) is a LangGraph ReAct agent over seven registered tools in `src/grocery_agent/tools/registry.py`, each backed by a SQL function in `src/grocery_agent/store/queries.py`. The normalized store (`transaction_record`, `line_item`, `account`) is richer than what the seven tools expose, so questions outside the fixed shapes are declined. Monetary values are stored as integer cents; the specs require all arithmetic to happen in code, never in the model.

## Goals / Non-Goals

**Goals:**
- Any question answerable from the stored data gets a tool path to an answer
- Keep the determinism guarantee: every number comes from SQL/Python, never from the model
- Keep the store protected from agent-driven writes

**Non-Goals:**
- No schema changes, re-normalization, or ingestion changes
- No write access from the agent, for any purpose
- No new Python dependencies

## Decisions

1. **SQL safety via a read-only connection, not string parsing.** The SQL tool opens the database with a `file:...?mode=ro` URI connection and installs a `sqlite3.Connection.set_authorizer` that denies everything except reads. This is stronger than keyword filtering (which "DROP"-in-a-comment tricks defeat). `sqlite3` executes one statement per call, so multi-statement injection is not possible via `execute`.
2. **Bounded resources per query.** The tool sets a maximum row count (default 200) by appending the limit to the result set after execution (fetch `limit + 1` rows, report `truncated: true` if the extra row exists) and a wall-clock budget enforced with a `set_progress_handler` callback that raises once exceeded. Defaults live as module constants so they are adjustable in one place.
3. **Result shape mirrors existing tools.** The SQL tool returns `{columns, rows, row_count, truncated, coverage}`; every other new tool returns its structured dict plus `coverage`, matching the current registry conventions (integer cents internally, formatted strings at the edge).
4. **Higher-level tools are thin wrappers over `queries.py`.** New query functions follow the existing patterns: `_date_bounds`/`_account_clause` filters, `COALESCE(SUM(...), 0)`, integer cents. `search_products` uses case-insensitive `LIKE` with the fragment escaped; `compare_periods` computes difference and percentage change in Python from integer cents (percentage rounded to one decimal, guarded against a zero denominator).
5. **Agent prompt updated alongside registration.** Each new tool gets a precise docstring (the LLM's primary selection signal), and `_SYSTEM_PROMPT` gains: prefer higher-level tools; use the SQL tool for anything else answerable from the store; never write SQL that mutates data; the read-only connection enforces this regardless.
6. **Alternative considered and rejected:** only adding more fixed tools without the SQL escape hatch — this would re-create the same limitation one step later; every new question shape would need another tool.

## Risks / Trade-offs

- [LLM writes invalid or slow SQL] → Errors are returned as structured tool results the agent can see and retry against; the progress handler bounds worst-case cost; the household dataset is small.
- [Keyword-based tools are easier for the model than raw SQL] → The higher-level tools remain the preferred path; SQL is the fallback, not the default.
- [Percentages introduce floats] → Only derived display values are floats; all source math stays in integer cents, consistent with the exact-monetary-values spec.
- [Large result dumps overflow the model context] → Row cap plus `truncated` flag; the agent can narrow the query and re-run.

## Migration Plan

Additive only: new functions in `queries.py`, new tools in `registry.py`, extended registration list and prompt in `agent/__init__.py`. No data migration; rollback is reverting the module changes.

## Open Questions

None.
