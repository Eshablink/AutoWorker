# AutoWorker Progress

## Current Phase
Phase 2 — Durable execution foundation

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
