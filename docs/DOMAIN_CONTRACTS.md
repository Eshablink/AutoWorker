# AutoWorker Domain Contracts

This document defines the core domain boundary for AutoWorker task execution.

## Aggregate

`Task` is the aggregate root. It owns the task lifecycle, ordered actions, current execution step, verification result, and optimistic-concurrency `version`.

## Task lifecycle

- `CREATED -> PLANNING | CANCELLED`
- `PLANNING -> READY | FAILED | CANCELLED`
- `READY -> RUNNING | CANCELLED`
- `RUNNING -> WAITING_APPROVAL | RECOVERING | VERIFYING | FAILED | CANCELLED`
- `WAITING_APPROVAL -> RUNNING | FAILED | CANCELLED`
- `RECOVERING -> RUNNING | FAILED | CANCELLED`
- `VERIFYING -> COMPLETED | RECOVERING | FAILED | CANCELLED`
- `COMPLETED`, `FAILED`, and `CANCELLED` are terminal.

Terminal tasks cannot be modified through the state-machine transition API.

## Safety invariants

Before execution/resumption:

1. The active `current_step_index` must identify a valid action when actions exist. An empty action list is valid only at index `0`.
2. Side-effecting actions require a non-empty idempotency key.
3. HIGH/CRITICAL policy risk requires approval or denial; it cannot be `ALLOW`.
4. A policy attached to an action must match the current task ID, action ID, and tool ID.
5. Actions requiring approval must have an approval request whose task ID, action ID, and policy decision ID exactly match the current execution context.
6. Approval status must be `APPROVED`.
7. A task cannot become `COMPLETED` without a successful verification result whose task ID matches the task.

## Audit boundary

`AuditEvent` is immutable at the model level and records concise operational metadata. Private model chain-of-thought is intentionally not part of the domain contract. Actions use `decision_summary` and optional `reason_code` instead.

## Persistence boundary

`AbstractTaskRepository` is a protocol boundary for the future PostgreSQL/SQLAlchemy adapter. The state machine owns domain rules; persistence adapters own transactions and optimistic-concurrency enforcement.

The current repository protocol expects a task version to be checked when saving. Database implementation is intentionally deferred to a later milestone.
