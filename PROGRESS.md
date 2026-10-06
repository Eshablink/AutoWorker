# AutoWorker Progress

## Current Phase
Phase 4 — Autonomous capability layer

## Completed
- New GitHub repository and feature-branch workflow established.
- Production-oriented architecture and project documentation added.
- Application/package boundaries scaffolded.
- Pydantic v2 domain contracts implemented.
- Explicit task lifecycle state machine implemented.
- Safety invariants added for terminal states, verification, idempotency, policy binding, and HITL approval binding.
- Private chain-of-thought removed from the domain model; auditable decision summaries are used instead.
- Domain unit tests validated locally: 18 passed.
- Typed tool registry implemented with duplicate/missing-tool protection.
- Deterministic policy engine implemented with risk and idempotency gates.
- Policy engine unit tests added.

## Next
- Harden policy rules with payload-aware authorization and policy versioning.
- Define repository protocol with optimistic-concurrency semantics.
- Add injected worker execution boundary and safety gates.
- Add worker execution unit coverage.
- Add stable domain serialization for durable persistence.
- Introduce persistence adapters with PostgreSQL and optimistic concurrency.
- Build the worker execution loop and API boundary.

## Rule
Update this file after each meaningful milestone. Do not mark work complete until validated.


## Full-stack milestone
- FastAPI task, approval, and event endpoints.
- SQLAlchemy/Alembic durable persistence foundation with PostgreSQL/pgvector infrastructure.
- Worker leases, heartbeat, recovery, orchestration, and verification.
- Operational event bus with no private chain-of-thought.
- React/Vite premium operations dashboard foundation.
- Docker Compose stack for PostgreSQL, API, and web dashboard.


## Capability layer progress
- Typed browser/computer-use session, observation, element-targeting, and action contracts.
- Typed document/OCR/invoice extraction contracts with provenance.
- Task-scoped memory contract and reference in-memory store.
- Structured agent-provider boundary and plan validation contracts.
- Content-addressed evidence store with checksum verification.
- Controlled ERP adapter contract and deterministic simulated ERP.
- Invoice workflow composition with validation, idempotency reuse, and pre-write rejection.
- Live dashboard task API client, polling, task creation control, and production nginx API proxy.
- Durable task listing and audit-history API foundations.
- Database-backed readiness probe and migration-first container startup.
- CI upgraded to current Node 24-compatible GitHub Actions releases.


## Hardening updates
- Policy-denied actions are terminally failed and cannot be forced into RUNNING by the state machine.
- Current action/task identity and executable action status are validated before RUNNING.
- Worker execution has a process-local idempotency store boundary to prevent duplicate side effects during retries.
- Playwright navigation is restricted to an explicit origin allowlist.
- API readiness returns 503 on database failure and request correlation IDs are returned on API responses.
- Environment template now matches runtime settings and includes evidence/provider configuration.
