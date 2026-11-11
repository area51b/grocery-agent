# guarded-sql-query Specification

## Purpose

Lets the agent answer any question about the grocery data by running its own read-only SQL against the normalized store, with guardrails that keep the store safe and results deterministic.

## Requirements

### Requirement: Read-only SQL execution
The system SHALL expose a tool that executes a single SQL statement against the normalized store and returns its result. The tool MUST reject any statement that is not a `SELECT`, including statements that modify schema or data.

#### Scenario: Select query succeeds
- **WHEN** the tool is given a single `SELECT` statement
- **THEN** it executes it against the normalized store and returns the resulting rows

#### Scenario: Write statement is rejected
- **WHEN** the tool is given an `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or other non-`SELECT` statement
- **THEN** the tool returns an error without executing it, and the stored data is unchanged

### Requirement: Query containment
The SQL tool SHALL enforce resource limits on every query: a bounded number of returned rows and a bounded execution time. Reaching a limit SHALL be reported in the result rather than silently truncating.

#### Scenario: Large result is bounded
- **WHEN** a query would return more rows than the configured maximum
- **THEN** the result contains the configured maximum number of rows and indicates that more rows exist

### Requirement: Deterministic SQL results
The SQL tool SHALL return computed values produced by the SQLite engine from stored data. The result SHALL include the data-coverage range of the store, consistent with the other analysis tools.

#### Scenario: SQL answer states its coverage
- **WHEN** the agent answers a question using the SQL tool
- **THEN** the tool result includes the ingested date range the query ran against
