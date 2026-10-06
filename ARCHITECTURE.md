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
Executes browser, document, and external API operations in controlled environments.

### Recovery
Classifies failures and applies bounded, typed recovery strategies. Side-effecting operations must not be blindly retried.

### Verification
Separates tool success from business success. The expected resulting state must be independently verified.

### Audit
Persists structured execution events, policy decisions, approvals, evidence references, and verification results without leaking secrets or private chain-of-thought.

## Original Prototype Evolution
The original design's Goal Planner, ReAct loop, Vision/DOM grounding, Dynamic Memory, Exception Recovery, HITL Guardrail, and DB Verification are retained conceptually but reorganized behind explicit production boundaries.
