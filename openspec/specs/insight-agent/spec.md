# insight-agent Specification

## Purpose

Defines the LangGraph agent that maps natural-language questions to the deterministic analysis tools, orchestrates multi-step tool use, and presents grocery insights conversationally.

## Requirements

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

### Requirement: Multi-step orchestration
The agent SHALL be able to combine multiple tool calls to answer compound questions, using the computed outputs of earlier calls as inputs to later steps.

#### Scenario: Compound question
- **WHEN** the user asks a question that requires more than one data result, such as comparing this month's spending to last month's
- **THEN** the agent performs the necessary tool calls and composes an answer from the computed results

### Requirement: No model arithmetic
The agent MUST NOT perform arithmetic, aggregation, or unit conversion on data itself. When no tool provides the value needed to answer, the agent SHALL say so rather than compute or estimate an answer.

#### Scenario: Question outside available data
- **WHEN** the user asks a question the tools cannot answer from stored data
- **THEN** the agent states that the data or capability is not available, without inventing or estimating numbers

### Requirement: Credential and raw-data isolation
The agent SHALL have no access to Sheng Siong credentials, the browser session, or raw captured payloads; its context SHALL contain only the normalized tool results needed to answer the question.

#### Scenario: Context stays clean
- **WHEN** the agent answers any question
- **THEN** no credential material or raw extraction payload is present in the agent's context, prompts, or responses

### Requirement: Answer transparency
The agent's answers SHALL be grounded in tool results and SHALL convey the data coverage the answer is based on when presenting aggregate figures.

#### Scenario: Aggregate answer states its basis
- **WHEN** the agent presents an aggregate figure such as total or monthly spend
- **THEN** the answer reflects the tool's computed value and states the period or data range it covers

### Requirement: Expanded toolset awareness
The agent's instructions SHALL describe the full analysis toolset, including product search, price history, product rankings, transaction browsing, period comparison, and the guarded read-only SQL tool, so the agent knows which questions can be answered and how.

#### Scenario: Agent knows its toolset
- **WHEN** the agent is asked a question within the stored data's reach
- **THEN** it selects a tool that can compute the answer instead of declining because no tool was known
