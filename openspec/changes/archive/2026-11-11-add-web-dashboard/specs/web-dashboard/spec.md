# Spec Delta

## Purpose

Provides the read-only web analytics interface to the household grocery data: aggregate charts with filters, data-coverage and ingestion status views, password protection, and the single-process web application that serves the dashboard alongside the Telegram bot.

## ADDED Requirements

### Requirement: Aggregate analytics views
The dashboard SHALL display aggregate views of the household data computed by the existing deterministic query layer: total spend, spend by month, spend by account, spend by type, top products, and promotion savings. Every displayed figure SHALL come from the query layer; the dashboard MUST NOT compute or estimate figures itself.

#### Scenario: Viewing the dashboard
- **WHEN** an authenticated user opens the dashboard with data in the store
- **THEN** the aggregate charts render using the query layer's computed results

#### Scenario: Empty store
- **WHEN** the dashboard is opened before any data has been ingested
- **THEN** the page renders with an empty-state message instead of an error

### Requirement: Filters apply to all views
The dashboard SHALL offer date-range and account filters, and applying a filter SHALL affect every aggregate view on the page. Filters SHALL be optional; with no filters, views cover all ingested data.

#### Scenario: Applying a filter
- **WHEN** an authenticated user selects a date range or account and applies it
- **THEN** every chart and aggregate on the page reflects the filtered data

#### Scenario: Filter matches no data
- **WHEN** the applied filter matches no transactions
- **THEN** the views render empty states rather than errors or zero-only charts

### Requirement: Read-only store access
The dashboard SHALL open the grocery data store with a read-only SQLite connection and SHALL never write to it, even indirectly. If the store file is missing or unreadable, the dashboard SHALL show a clear message and SHALL NOT create or modify the store file.

#### Scenario: Browsing never mutates the store
- **WHEN** an authenticated user browses any dashboard view
- **THEN** the store's modification state is unchanged, including when filters and charts are exercised

#### Scenario: Store file missing
- **WHEN** the configured store file does not exist
- **THEN** the dashboard renders a message naming the problem and the store file is not created

### Requirement: Coverage and ingestion status
The dashboard SHALL show, read-only, the per-account data coverage (earliest and latest transaction, count) and the ingestion status of the store, without offering any control to run ingestion.

#### Scenario: Viewing coverage
- **WHEN** an authenticated user opens the coverage view
- **THEN** per-account earliest, latest, and transaction counts are shown from the store

#### Scenario: No ingestion controls
- **WHEN** the user looks for a way to run ingestion from the dashboard
- **THEN** none exists; the status is informational only

### Requirement: Dashboard access protection
The dashboard and admin area SHALL require authentication with a password from the `ADMIN_PASSWORD` environment variable, granting a session on success. When `ADMIN_PASSWORD` is unset or empty, the application SHALL fail closed: no one may log in. Unauthenticated requests SHALL be redirected to a login page and SHALL receive no data.

#### Scenario: Successful login
- **WHEN** a user submits the correct password on the login page
- **THEN** a session is granted and the dashboard is accessible

#### Scenario: Wrong or missing password
- **WHEN** a user submits a wrong password, or requests a dashboard page unauthenticated
- **THEN** no data is served and the user is returned to the login page

#### Scenario: Password not configured
- **WHEN** `ADMIN_PASSWORD` is unset or empty and a login is attempted
- **THEN** login is refused (fail closed) regardless of the submitted value

### Requirement: Single web application process
The application SHALL offer a single command (`grocery webapp`) that runs the web dashboard and the Telegram bot in one process, with the bot's behavior unchanged from the telegram-bot capability. Stopping the process stops both. The standalone `grocery telegram` command SHALL continue to work as before.

#### Scenario: One process serves both
- **WHEN** the user starts `grocery webapp` with valid configuration
- **THEN** the dashboard is served on its configured port and the Telegram bot answers messages, from the same process

#### Scenario: Missing Telegram configuration
- **WHEN** `grocery webapp` is started without `TELEGRAM_BOT_TOKEN` configured
- **THEN** the dashboard still starts and the application reports that the bot is disabled, instead of failing the whole process
