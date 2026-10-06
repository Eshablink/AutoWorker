# AutoWorker Execution Architecture

## Runtime flow

`Task -> Policy -> State Machine -> Worker -> Tool Adapter -> Observation -> Verification -> Audit/Event Stream`

The execution worker is isolated from tool implementations and authorization decisions.

## Event model

Operational events are emitted for task state changes, action execution, approvals, recovery, and verification. Events contain operational metadata only; private chain-of-thought is never persisted or streamed.

The initial event bus is in-process. Production deployment can replace it with Redis Streams, PostgreSQL-backed outbox delivery, or another durable event transport without changing domain contracts.

## Verification

Every successful task must carry a matching successful `VerificationResult`. Verification checks can combine multiple deterministic checks and report a bounded confidence score.

## Persistence boundary

Task state and audit records are persisted through a repository boundary with optimistic concurrency. PostgreSQL/SQLAlchemy is the initial durable adapter.
