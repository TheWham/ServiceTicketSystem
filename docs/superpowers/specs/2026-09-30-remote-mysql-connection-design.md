# Remote MySQL Connection Design

## Goal

Connect the Spring Cloud services to the remote MySQL instance at `120.92.138.195:3306` while retaining the existing AI knowledge base and consultation history.

## Database Boundaries

The remote MySQL instance contains two logical databases:

- `it_ticket_system`: user, ticket, consultation, knowledge article, and other core service tables.
- `it_ai`: `ai_knowledge`, `ai_chat_session`, and `ai_chat_message` used by `ai-service` for RAG, chat history, and human handoff.

The databases remain separate because the Java entities and current service contracts already target these table sets independently. The implementation must not merge the AI tables into the core schema without a separate migration decision.

## Configuration

Core services continue to use the existing profile configuration and receive these runtime variables:

- `MYSQL_HOST=120.92.138.195`
- `MYSQL_PORT=3306`
- `MYSQL_DB=it_ticket_system`
- `MYSQL_USERNAME=root`
- `MYSQL_PASSWORD` supplied at runtime only

`ai-service` uses the same host, port, username, and password, but its database name is independently configurable with `AI_MYSQL_DB` and defaults to `it_ai`. This prevents a shared `MYSQL_DB` value from accidentally pointing the AI mappers at the core schema.

No real password is added to tracked files, examples, generated artifacts, or Nacos import data.

## Schema Initialization

Add an idempotent AI schema script that creates `it_ai` and the three tables required by the current entities, including primary keys, timestamps, indexes for session/message queries, and a foreign-key relationship from messages to sessions where compatible with existing data. The existing `it_ticket_system` initialization remains unchanged.

## Runtime and Verification

Document a PowerShell startup example that sets the runtime variables before launching the Maven services. Verification covers:

1. Static configuration checks for all datasource URLs and placeholders.
2. SQL/schema checks for both databases.
3. A remote connectivity check using the available MySQL client, without printing the password.
4. Service-level startup or focused tests for core persistence and AI session/knowledge persistence when the remote instance is reachable.

If the remote account cannot create databases or tables, the schema script must be run by an administrator first; application startup must not silently fall back to localhost.

## Error Handling and Security

Production startup requires `MYSQL_PASSWORD`; missing credentials fail fast. Logs and verification output must redact credentials. SSL behavior follows the existing profile convention for core services; the AI datasource will expose the same SSL choice through configuration rather than hardcoding a credential or certificate.
