# telegram-bot Specification

## Purpose

Provides the Telegram chat interface to the insight agent: household members ask grocery spending questions in a Telegram conversation and receive the agent's answers, with slash commands and suggestion buttons for the most common questions.

## Requirements

### Requirement: Answering questions in chat
The bot SHALL forward any received plain text message to the insight agent and reply with the agent's final answer text. The bot MUST relay the agent's answer verbatim and MUST NOT alter, truncate, or recompute figures.

#### Scenario: Plain text question
- **WHEN** a permitted user sends a message such as "How much did we spend last month?"
- **THEN** the bot replies with the answer produced by the insight agent for that question

#### Scenario: Agent cannot answer
- **WHEN** the agent states that no stored data can answer the question
- **THEN** the bot relays that reply as-is instead of substituting its own estimate

### Requirement: Slash commands for common questions
The bot SHALL register slash commands for commonly asked questions (at minimum `/spend`, `/top`, `/last`, `/help`) and SHALL, on receiving one, answer the mapped question through the insight agent as if it had been typed. `/help` SHALL list the available commands and how to ask free-form questions.

#### Scenario: Command maps to a question
- **WHEN** a permitted user sends `/spend`
- **THEN** the bot replies with the agent's answer to the household's total spend for the current month

#### Scenario: Unknown command
- **WHEN** a permitted user sends a slash command that is not registered
- **THEN** the bot replies with a short usage hint and the list of available commands

### Requirement: Suggestion buttons for common questions
The bot SHALL present commonly asked questions as tappable suggestion buttons when a conversation starts and when `/help` is used. Tapping a suggestion button SHALL have the same effect as sending that question as a message.

#### Scenario: Tapping a suggestion
- **WHEN** a permitted user taps a suggestion button labeled with a common question such as "What do we spend the most on?"
- **THEN** the bot answers it through the insight agent exactly as if the question had been typed

### Requirement: Telegram credentials from environment
The bot SHALL read its Telegram bot token and optional user allowlist from environment variables (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`) loaded from the git-ignored `.env` file at the project root. The bot MUST refuse to start when `TELEGRAM_BOT_TOKEN` is not set, reporting the missing variable.

#### Scenario: Missing bot token
- **WHEN** the bot is started and `TELEGRAM_BOT_TOKEN` is not set in `.env` or the environment
- **THEN** the bot exits with an error naming the missing variable and does not attempt to connect

### Requirement: Access control
The bot SHALL only answer messages from permitted Telegram users, identified by an optional `TELEGRAM_ALLOWED_USER_IDS` allowlist. When the allowlist is empty or unset, the bot SHALL reject all users (fail closed). When a non-permitted user sends a message or command, the bot SHALL NOT forward it to the agent and SHALL NOT reveal household data.

#### Scenario: Permitted user
- **WHEN** a user whose Telegram ID is on the allowlist sends a question
- **THEN** the bot forwards it to the agent and replies with the answer

#### Scenario: Non-permitted user
- **WHEN** a user whose Telegram ID is not on the allowlist sends a message or command
- **THEN** the bot replies with a generic access-denied notice and forwards nothing to the agent

### Requirement: Concurrent multi-user handling
The bot SHALL process questions from different permitted users concurrently, so that one user's in-progress question does not delay another user's answer. All agent queries are read-only, so concurrent processing MUST NOT serialize users behind each other.

#### Scenario: Two users ask at the same time
- **WHEN** two permitted users send questions while no other question is in progress
- **THEN** the bot starts answering both concurrently, and each user receives their own reply

#### Scenario: Same user's messages stay ordered
- **WHEN** a permitted user sends a second message while the agent is still answering their first
- **THEN** the bot answers the first, then handles the second, without running two agent invocations concurrently for that user
