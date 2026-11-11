# Spec Delta

## Purpose

Defines the LangGraph agent that maps natural-language questions to the deterministic analysis tools, orchestrates multi-step tool use, and presents grocery insights conversationally.

## ADDED Requirements

### Requirement: Question-to-tool mapping
The agent SHALL interpret natural-language grocery questions and select the appropriate analysis tool(s) to answer them.

#### Scenario: Spending question selects a tool
- **WHEN** the user asks a question such as "how much did we spend last month?"
- **THEN** the agent invokes the corresponding spending analysis tool and presents the tool's computed result

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
