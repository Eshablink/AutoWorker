# AutoWorker Progress

## Current Phase
Phase 4 — Autonomous capability layer

## Completed
- Production-oriented repository, architecture, safety state machine, typed tool boundaries, persistence foundation, worker orchestration, verification, evidence, audit, browser/document/ERP boundaries, React dashboard, Docker, and CI.
- Policy authorization is deterministic; LLM/provider proposals cannot directly authorize side effects.
- Task/action identity, executable action status, policy binding, terminal-state, verification, and idempotency invariants are enforced at the domain boundary.
- Worker execution records started/completed timestamps and fails actions explicitly on executor errors.
- Side-effect classification is authoritative from the registered ToolDefinition.
- Process-local idempotency reuse prevents duplicate execution inside a worker process; durable cross-process idempotency remains a production follow-up.
- Playwright navigation is origin-allowlisted and browser element IDs are constrained to safe selector tokens.
- API readiness fails closed on database errors; request IDs are propagated; production CORS defaults to no origins and rejects wildcard origins.
- Task creation produces durable audit history; dashboard timeline reads persisted task events rather than a static demo stream.
- Persisted task listing is deterministic by creation timestamp with an indexed DB column.
- Human approval requests can expire after 15 minutes; expired approvals are persisted as failed/expired instead of being accepted.
- Verification checks require unique non-empty names and callable callbacks.
- In-process operational event memory is bounded to prevent unbounded growth.
- CI has continuously validated frontend builds and backend tests; the hardening branch is only considered merge-ready when its latest run is green.

## Current Hardening Review
- Durable idempotency is still process-local and should be replaced by an atomic database-backed claim/complete design before multi-worker production.
- Orchestrator EventBus events are not yet all persisted automatically; a durable outbox/event sink is the next audit architecture step.
- Approval lookup currently scans task JSON and should become a normalized indexed approval projection at production scale.
- `apps/worker` still needs a durable runtime loop around repository + lease + orchestrator.
- Browser/document layers contain legacy compatibility modules that should be consolidated only after import usage is mapped.
- Full end-to-end validation still needs a real PostgreSQL execution path and controlled browser integration.

## Next
- Finish durable execution coordination (atomic idempotency + worker loop + outbox).
- Complete real approval/audit/evidence task detail flows in the web console.
- Add end-to-end PostgreSQL/browser workflow tests.
- Then deploy with a dedicated AutoWorker database and verify production health before final release.

## Rule
Update this file after each meaningful milestone. Do not mark work complete until validated.
