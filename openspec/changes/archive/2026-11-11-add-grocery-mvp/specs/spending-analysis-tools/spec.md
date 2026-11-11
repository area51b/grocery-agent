# Spec Delta

## Purpose

Defines the deterministic Python/SQL query tools over the normalized grocery data, covering spending, product, and price/promotion analysis, with all arithmetic performed by code rather than a language model.

## ADDED Requirements

### Requirement: Deterministic computation
All financial aggregation and arithmetic SHALL be performed by deterministic Python/SQL code executing against the normalized store. The language model MUST NOT compute, estimate, or correct numeric results itself.

#### Scenario: Totals come from SQL
- **WHEN** a query requires a sum, average, count, or comparison of monetary values or quantities
- **THEN** the result is computed by the tool's SQL/Python code from stored data, and the model only receives and relays the computed result

### Requirement: Spending queries
The tools SHALL answer spending questions over the normalized data, including total spend over a date range, spend broken down by transaction type (online vs in-store), and spend over time.

#### Scenario: Monthly spending breakdown
- **WHEN** the tools are asked for spending in a given month
- **THEN** the result reports total spend for that month, computed from stored line-item and transaction data for transactions within the month

### Requirement: Product-level analysis
The tools SHALL answer per-product questions, including total spend and quantity per product and price paid across occurrences.

#### Scenario: Product spend history
- **WHEN** the tools are asked about a specific product
- **THEN** the result reports aggregate spend, total quantity purchased, and the unit prices paid in the ingested data for matching products

### Requirement: Promotion and discount analysis
The tools SHALL answer price/promotion questions, including total discount amounts received and the effective per-unit price paid for promoted items.

#### Scenario: Discount savings over a period
- **WHEN** the tools are asked how much was saved through promotions in a period
- **THEN** the result reports the summed discount amounts from stored line items in that period, computed by SQL/Python

### Requirement: Household aggregation and per-account breakdown
The tools SHALL compute aggregates over all ingested accounts by default, and SHALL support breaking results down by account so responsibility for spending can be attributed.

#### Scenario: Household question combines accounts
- **WHEN** the tools are asked for household spending over a period
- **THEN** the result combines transactions from every ingested account in that period

#### Scenario: Per-account breakdown
- **WHEN** the tools are asked for spending per account
- **THEN** the result reports each account's share separately, computed from the stored account attribution

### Requirement: Data coverage transparency
The tools SHALL disclose the coverage of the data they queried, including the date range of ingested transactions, so answers are not mistaken for complete history.

#### Scenario: Query over partial history
- **WHEN** a spending question is answered while only some history is ingested
- **THEN** the tool result includes the ingested date range that the answer is based on
