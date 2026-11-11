# Spec Delta

## ADDED Requirements

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
