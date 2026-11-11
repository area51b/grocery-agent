# Spec Delta

## Purpose

Defines the authenticated browser-based extraction of Sheng Siong Online transaction history: finding transactions, reading their details and line items, and capturing the raw data for later normalization.

## ADDED Requirements

### Requirement: Authenticated browser session
Ingestion SHALL run inside a browser session that the user authenticates against shengsiong.com.sg, and MUST NOT write Sheng Siong credentials into source code, git, SQLite, logs, prompts, or any LLM context.

#### Scenario: Ingestion without an active session
- **WHEN** ingestion starts and no authenticated browser session is available
- **THEN** the system presents (or connects to) a browser for the user to log in, and extraction begins only after the session is authenticated

#### Scenario: Credentials stay out of the system
- **WHEN** ingestion runs, succeeds, or fails
- **THEN** no credential material appears in the database, logs, captured data, error messages, or any content handed to the LLM

### Requirement: Transaction history discovery
The system SHALL discover all transactions available under the account's Transactions pages, both Online and In-Store, and extract each transaction's ID, date/time, store location, and total.

#### Scenario: Discovery across both transaction types
- **WHEN** discovery runs against an account with both Online and In-Store transactions
- **THEN** every listed transaction is discovered with its transaction ID, date/time, store location, and total recorded

### Requirement: Line item extraction
The system SHALL open each transaction's detail view and extract every line item's product name, quantity, unit price, and line total, plus promotion description and discount amount when present.

#### Scenario: Item with promotion
- **WHEN** a transaction contains an item such as "SUNLIGHT DISHWASH LIQ LIME 800ML, Qty 1 x $2.94, promotion 2 for $5.35, discount -$0.26"
- **THEN** the extracted line item records the product name, quantity 1, unit price 2.94, line total 2.94, the promotion text, and a discount of -0.26

#### Scenario: Item without promotion
- **WHEN** a transaction contains an item with no promotion or discount
- **THEN** the extracted line item records the product name, quantity, unit price, and line total, with the promotion and discount fields absent

### Requirement: Raw data capture
The system SHALL persist the extracted data in raw, as-captured form before any normalization, so that normalization can be corrected or re-run without re-extracting from the website.

#### Scenario: Raw data survives normalization changes
- **WHEN** extraction of a transaction completes
- **THEN** the as-captured transaction data is stored raw, and later normalization changes can be applied to the raw data without visiting the website again

### Requirement: Per-account ingestion runs
Each ingestion run SHALL target exactly one account, identified by the account display name the site shows after login (e.g. "Hi, <display name>"), using that account's own persistent browser profile and login session, and SHALL record that account name on every transaction captured during the run. The household SHALL support up to four accounts, and no account SHALL be handled differently beyond attribution.

#### Scenario: Two household accounts ingested separately
- **WHEN** ingestion runs once for each household member's account, using different browser profiles
- **THEN** every captured transaction carries the account name shown by the site, and each account's login session persists independently

#### Scenario: Account cap
- **WHEN** ingestion runs for a fifth distinct household account
- **THEN** the run is rejected with a clear message and no data is captured

### Requirement: Idempotent ingestion
Running ingestion SHALL NOT create duplicate transactions: a transaction already captured SHALL be identified by its account and transaction ID and skipped or updated, never duplicated.

#### Scenario: Repeated ingestion run
- **WHEN** ingestion runs a second time against the same account
- **THEN** transactions already captured are skipped or updated in place, and the store contains no duplicate transaction records

#### Scenario: Same transaction ID under a different account
- **WHEN** a transaction ID already captured for one account appears during ingestion of another account
- **THEN** it is stored as a separate transaction attributed to the new account, without overwriting the first

### Requirement: Extraction failure isolation
A failure while extracting one transaction SHALL NOT lose or corrupt data already extracted in the same run.

#### Scenario: Detail page fails mid-run
- **WHEN** opening one transaction's detail view fails during ingestion
- **THEN** the failure is reported for that transaction and all successfully extracted transactions from the run remain captured
