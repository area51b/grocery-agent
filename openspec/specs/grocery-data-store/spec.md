# grocery-data-store Specification

## Purpose

Defines how raw captured transaction data is normalized into a consistent schema and persisted in SQLite, preserving traceability to the raw source.

## Requirements

### Requirement: Normalized transaction data
The system SHALL normalize captured data into a SQLite schema that represents each transaction (ID, date/time, transaction type, store location, total) and each line item (product name, quantity, unit price, line total, promotion, discount) with consistent types and units.

#### Scenario: Normalized item matches its capture
- **WHEN** a captured item with quantity, unit price, line total, promotion text, and discount is normalized
- **THEN** the normalized line item preserves each field with the same value in a consistent typed format

### Requirement: Exact monetary values
The system SHALL store all monetary values as exact numeric values, and MUST NOT store them as binary floating-point.

#### Scenario: Cent-level precision survives storage
- **WHEN** a monetary value such as 5.35 or -0.26 is stored and later queried
- **THEN** the value is returned exactly as captured, with no floating-point drift

### Requirement: Raw source of truth retained
The system SHALL retain the raw captured data in SQLite alongside the normalized data, and each normalized record SHALL trace back to its raw source and transaction ID.

#### Scenario: Traceability from normalized to raw
- **WHEN** any normalized transaction or line item is inspected
- **THEN** it can be traced to the raw captured data and transaction ID it was derived from

### Requirement: Re-normalization from raw
The system SHALL be able to rebuild the normalized store from retained raw data without re-extracting from the website.

#### Scenario: Schema fix applied to existing data
- **WHEN** a normalization rule or schema fix changes
- **THEN** the normalized data is rebuilt from the retained raw data, with no new browser session or website access required

### Requirement: Account attribution
Every normalized transaction and line item SHALL carry the identifier of the account whose ingestion captured it, and transactions SHALL be unique per account and transaction ID.

#### Scenario: Two accounts, no conflation
- **WHEN** both household accounts' transactions are normalized
- **THEN** each row is attributed to its capturing account, and no transaction from one account is merged into the other

### Requirement: Household consolidation
The normalized store SHALL represent purchases from all ingested accounts as one household data set, and household-wide aggregation SHALL combine accounts by default.

#### Scenario: Household totals span both accounts
- **WHEN** transactions from both accounts are ingested and a household-wide aggregate is computed
- **THEN** the result includes purchases from every ingested account, with no special handling per account beyond attribution

### Requirement: Ingestion writes through to the store
Newly captured raw data SHALL be normalized and persisted in the same ingestion flow, so the queryable store is current after each successful run.

#### Scenario: Store reflects the latest run
- **WHEN** an ingestion run completes successfully
- **THEN** all transactions captured by that run are present in the normalized store
