# spending-analysis-tools Specification

## Purpose

Defines the deterministic Python/SQL query tools over the normalized grocery data, covering spending, product, and price/promotion analysis, with all arithmetic performed by code rather than a language model.

## Requirements

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

### Requirement: Product search by partial name
The tools SHALL find products by partial name match, so questions about a product can be answered without knowing its exact stored name. The result SHALL include every matching product name and its aggregate spend.

#### Scenario: Partial product name matches
- **WHEN** the tools are asked about a product using a partial name such as "milk"
- **THEN** the result reports each stored product name containing that fragment together with its aggregate spend, instead of reporting that no product was found

#### Scenario: No product matches
- **WHEN** no stored product name matches the search text
- **THEN** the result reports that no product matched, without inventing product names

### Requirement: Product price history
The tools SHALL report the unit price paid for a product on each purchase occurrence over time, so price changes across the ingested history can be traced.

#### Scenario: Price changes across purchases
- **WHEN** the tools are asked how the price of a product changed over time
- **THEN** the result lists each purchase occurrence in chronological order with its date and unit price paid

### Requirement: Ranked product listings
The tools SHALL rank products by aggregate spend, quantity, or purchase count over an optional period, so the household can see its most-bought items.

#### Scenario: Top products by spend
- **WHEN** the tools are asked which products the household spends the most on in a period
- **THEN** the result reports the ranked products with their aggregate spend for that period, computed from stored line items

### Requirement: Transaction browsing
The tools SHALL list transactions over an optional period with filtering by transaction type and account, and SHALL return the line items of a single identified transaction.

#### Scenario: List transactions in a period
- **WHEN** the tools are asked which orders happened in a period
- **THEN** the result reports each transaction in that period with its date, type, store location, and total

#### Scenario: Line items of one transaction
- **WHEN** the tools are asked what was purchased in a specific transaction
- **THEN** the result reports every line item of that transaction with quantity, unit price, line total, and promotion

### Requirement: Period comparison
The tools SHALL compare aggregate spend between two periods and SHALL compute the difference and percentage change in deterministic code.

#### Scenario: Compare two periods
- **WHEN** the tools are asked how spending compared between two periods
- **THEN** the result reports each period's total plus the difference and percentage change, all computed by code
