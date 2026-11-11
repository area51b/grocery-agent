# Spec Delta

## MODIFIED Requirements

### Requirement: Question-to-tool mapping
The agent SHALL interpret natural-language grocery questions and select the appropriate analysis tool(s) to answer them. The agent SHALL prefer the higher-level analysis tools and SHALL fall back to the guarded read-only SQL tool when no higher-level tool fits the question, so any question about the stored data can be answered.

#### Scenario: Spending question selects a tool
- **WHEN** the user asks a question such as "how much did we spend last month?"
- **THEN** the agent invokes the corresponding spending analysis tool and presents the tool's computed result

#### Scenario: Question outside the higher-level tools
- **WHEN** the user asks a question no higher-level tool answers, such as "which store location did we buy the most from?"
- **THEN** the agent answers it by querying the guarded read-only SQL tool and presents the tool's computed result

#### Scenario: Question about data that is not stored
- **WHEN** the user asks about data the store does not contain, such as items bought before any ingestion
- **THEN** the agent states that the data is not available rather than estimating an answer

## ADDED Requirements

### Requirement: Expanded toolset awareness
The agent's instructions SHALL describe the full analysis toolset, including product search, price history, product rankings, transaction browsing, period comparison, and the guarded read-only SQL tool, so the agent knows which questions can be answered and how.

#### Scenario: Agent knows its toolset
- **WHEN** the agent is asked a question within the stored data's reach
- **THEN** it selects a tool that can compute the answer instead of declining because no tool was known
