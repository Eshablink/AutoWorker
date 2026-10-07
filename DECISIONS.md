# Architecture Decisions

## ADR-001 — Use an explicit execution state machine
**Status:** Accepted

An autonomous worker needs durable, inspectable lifecycle state. A bounded state machine is preferred to an unbounded ReAct loop.

## ADR-002 — LLM does not directly control side effects
**Status:** Accepted

The model may propose an action, but typed tools and the policy engine authorize and execute it.

## ADR-003 — Controlled browser environment
**Status:** Accepted

The flagship workflow will use a controlled browser/test application rather than production ERP/payment systems.

## ADR-004 — Evidence instead of chain-of-thought logging
**Status:** Accepted

Auditability will use structured action metadata, tool results, policy decisions, approvals, screenshots/evidence and verification results. Private chain-of-thought will not be stored as an audit requirement.

## ADR-005 — Build the flagship workflow before broad integrations
**Status:** Accepted

One genuine end-to-end workflow is more valuable than many simulated integrations.


## ADR-006 — Expiring human approvals
**Status:** Accepted

High-risk approval requests created by the orchestrator expire after 15 minutes. Expiration fails the waiting task and is persisted before returning the conflict response. This prevents stale human authorization from being reused.

## ADR-007 — Registry is authoritative for side effects
**Status:** Accepted

The registered ToolDefinition owns the side-effect classification used by policy. Action metadata cannot downgrade a registered side-effecting tool.

## ADR-008 — Bound in-process event memory
**Status:** Accepted

The reference EventBus keeps a bounded recent window. Durable audit persistence remains the source of truth; the in-process bus is not an unbounded event store.

## ADR-009 — Redis is a dispatch hint; SQL is the source of truth
**Status:** Accepted

Redis Streams improves worker delivery latency and cross-process distribution, but the durable SQL dispatch queue remains authoritative. Worker fleets periodically poll SQL even when Redis is configured, so a lost broker hint or temporary Redis outage cannot permanently strand an eligible task.

## ADR-010 — At-least-once broker handling over eager ACK
**Status:** Accepted

A worker ACKs a Redis message only after the runtime returns a result. Processing exceptions intentionally leave the message pending so Redis consumer-group reclamation can retry delivery. Database leases and idempotency remain the final duplicate-execution safety boundaries.
