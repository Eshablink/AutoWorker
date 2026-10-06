# AutoWorker Execution Architecture

## Flow

`Task -> Action -> Policy -> Worker -> Tool Adapter -> Observation -> Verification`

The worker is intentionally separate from tool implementations.

### Worker responsibilities

- accept an already-planned action
- execute only through an injected `ToolExecutor`
- capture tool output and an operational observation
- move the action to `COMPLETED` only after the executor returns successfully

### Worker non-responsibilities

- deciding whether a tool is authorized
- generating private model reasoning
- owning persistence transactions
- implementing browser, API, OCR, or computer-use mechanics

## Persistence boundary

The domain exposes a repository protocol with optimistic-concurrency semantics. A future PostgreSQL adapter will implement it and atomically persist task state plus audit events.

## Future production extensions

- action execution timeout and cancellation
- retry/recovery policy
- durable worker queue
- heartbeat/lease ownership
- idempotency-key enforcement at the execution adapter
- evidence capture
- structured execution telemetry
