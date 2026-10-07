# AutoWorker Architecture

## Target System

User / Web Console
→ FastAPI API
→ Task & Job Manager
→ Worker Orchestrator
→ Planner + Execution State Machine
→ Typed Tool Registry
→ Policy Engine
→ Browser / Document / API Workers
→ Verification
→ Audit & Evidence

PostgreSQL is the system-of-record for persistent execution state. Vector retrieval is added only where it has a concrete product purpose.

## Core Boundaries

### Planner
Converts a natural-language goal into a structured, bounded execution plan.

### Execution State Machine
Owns task lifecycle and durable state transitions. Candidate states:
CREATED, PLANNING, READY, RUNNING, WAITING_APPROVAL, RECOVERING, VERIFYING, COMPLETED, FAILED, CANCELLED.

### Tool Registry
Every tool has a typed input/output contract, risk classification, permission requirements, timeout, and execution handler.

### Policy Engine
Evaluates actions before consequential side effects. It can deny, allow, or require human approval.

### Worker Layer
Executes browser, document, and external API operations in controlled environments. Production workers use database-backed task leases with heartbeat renewal so multiple worker processes cannot claim the same task concurrently.

### Recovery
Classifies failures and applies bounded, typed recovery strategies. Side-effecting operations must not be blindly retried.

### Verification
Separates tool success from business success. The expected resulting state must be independently verified.

### Audit
Persists structured execution events, policy decisions, approvals, evidence references, and verification results without leaking secrets or private chain-of-thought. Operational events can be written to a durable outbox before external delivery, with retry state retained for failed publication.

## Original Prototype Evolution
The original design's Goal Planner, ReAct loop, Vision/DOM grounding, Dynamic Memory, Exception Recovery, HITL Guardrail, and DB Verification are retained conceptually but reorganized behind explicit production boundaries.


## Durable Execution Coordination

The execution layer now includes three persistence-backed coordination primitives:

1. **Idempotency claims** — a unique key is atomically claimed before a side-effecting operation. A completed result is reused; an in-progress claim is not blindly replayed.
2. **Task leases** — workers acquire a database lease, renew it with heartbeats, and release it when processing ends. This supports multiple worker processes safely competing for tasks.
3. **Event outbox** — operational events can be appended durably and retried until marked published. Event IDs provide a stable deduplication key for downstream consumers.

## Dispatch & Observability

### Task Dispatch Queue
The persistent dispatch queue records task availability, attempts, claims, blocked approval states, completion, and stale-claim recovery. It is intentionally an execution hint; the database worker lease remains the concurrency authority.

### Operational Telemetry
The API exposes Prometheus-compatible metrics, response timing headers, and structured JSON request logs. HTTP metrics use normalized route templates to avoid high-cardinality path labels.
