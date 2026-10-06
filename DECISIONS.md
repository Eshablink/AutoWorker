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
