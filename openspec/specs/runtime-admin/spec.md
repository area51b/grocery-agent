# runtime-admin Specification

## Purpose

Runtime-editable bot configuration: the dashboard's admin area manages the Telegram bot's slash-command questions and suggested questions, persisted in a separate admin store. The interface exposes no credentials and no `.env` values.

## Requirements

### Requirement: Editing bot command questions
The admin area SHALL allow an authenticated administrator to edit the question each registered slash command maps to, and the change SHALL take effect on the running bot without a restart. The command set itself SHALL NOT be creatable or deletable at runtime.

#### Scenario: Editing a command question
- **WHEN** the administrator changes the question mapped to `/spend` and saves
- **THEN** a user sending `/spend` afterwards receives the agent's answer to the new question, with no application restart

#### Scenario: Invalid question value
- **WHEN** the administrator saves an empty question for a command
- **THEN** the edit is rejected with a validation message and the previous question remains in effect

### Requirement: Editing suggested questions
The admin area SHALL allow the administrator to add, edit, and remove suggested questions shown as tappable buttons, and the changes SHALL take effect on the running bot without a restart.

#### Scenario: Adding a suggestion
- **WHEN** the administrator adds a suggested question and saves
- **THEN** the new suggestion appears as a tappable button on the bot's suggestion keyboard without a restart

#### Scenario: Removing a suggestion
- **WHEN** the administrator removes a suggested question and saves
- **THEN** the suggestion no longer appears on the bot's suggestion keyboard without a restart

### Requirement: Separate admin store
The admin configuration SHALL be persisted in its own SQLite file separate from the grocery data store, seeded with the application's current defaults on first run. Writing admin configuration MUST NOT modify the grocery data store.

#### Scenario: First run seeding
- **WHEN** the application starts and the admin store does not exist
- **THEN** it is created and seeded with the default command questions and suggested questions

#### Scenario: Grocery store untouched by admin edits
- **WHEN** the administrator saves any configuration change
- **THEN** only the admin store changes; the grocery data store is untouched

### Requirement: No credentials in the interface
The web interface SHALL NOT display any credential values (tokens, gateway keys, passwords) and SHALL NOT offer to edit `.env` values.

#### Scenario: Credential values are absent
- **WHEN** any page of the web interface is rendered
- **THEN** no token, gateway key, or password value appears anywhere in the page, and no `.env` editing is offered
