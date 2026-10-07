# AutoWorker Progress

## Current Phase
Phase 10 — Observability + broker hardening

## Completed
- Production-oriented repository, architecture, safety state machine, typed tool boundaries, persistence foundation, worker orchestration, verification, evidence, audit, browser/document/ERP boundaries, React dashboard, Docker, and CI.
- Policy authorization is deterministic; LLM/provider proposals cannot directly authorize side effects.
- Task/action identity, executable action status, policy binding, terminal-state, verification, and idempotency invariants are enforced at the domain boundary.
- Worker execution records started/completed timestamps and fails actions explicitly on executor errors.
- Side-effect classification is authoritative from the registered ToolDefinition.
- Durable idempotency claims now prevent duplicate side-effect execution across worker processes; abandoned claims are intentionally conservative and require reconciliation rather than blind replay.
- Playwright navigation is origin-allowlisted and browser element IDs are constrained to safe selector tokens.
- API readiness fails closed on database errors; request IDs are propagated; production CORS defaults to no origins and rejects wildcard origins.
- Task creation produces durable audit history; dashboard timeline reads persisted task events rather than a static demo stream.
- Persisted task listing is deterministic by creation timestamp with an indexed DB column.
- Human approval requests can expire after 15 minutes; expired approvals are persisted as failed/expired instead of being accepted.
- Verification checks require unique non-empty names and callable callbacks.
- In-process operational event memory is bounded to prevent unbounded growth.
- Operator console exposes task detail, approval inbox, verification state, evidence references, and worker/runtime posture.
- Controlled browser E2E runs in CI against Chromium with PostgreSQL migrations and an invoice-to-ERP integration path.
- Durable task dispatch queue coordinates worker claims on top of persistent leases, with blocked approval states and stale-claim recovery.
- Prometheus request metrics, response timing headers, and structured JSON request logs provide an operational telemetry foundation.
- Redis Streams transport now supports consumer groups, worker distribution, and stale pending-message reclamation while SQL remains authoritative.
- Production task, event, and approval APIs now enforce bearer-token authentication; the operator console can send a bearer token when configured.
- Readiness now checks the configured Redis transport in addition to the database.
- Redis stream/group names, pending reclaim threshold, retention bound, and consumer blocking interval are configurable instead of hard-coded.
- Worker fleets now treat Redis as a low-latency dispatch hint and periodically fall back to the durable SQL queue, preventing missed hints or Redis outages from stalling execution.
- Redis delivery errors are logged without ACKing the message, allowing Redis Streams pending-message reclamation to recover interrupted work.
- Worker, queue, broker, approval-latency, and authentication metrics now expose operational depth beyond request-only telemetry; task/worker IDs are available in structured logs for correlation.
- CI has continuously validated frontend builds and backend tests; the hardening branch is only considered merge-ready when its latest run is green.

## Current Hardening Review
- Durable idempotency now uses atomic database-backed claim/complete semantics before side-effecting execution.
- Orchestrator events can now be persisted through the durable event-outbox sink; delivery is retryable and consumers can deduplicate by event ID.
- The reference worker runtime can now use DB-backed leases with heartbeat renewal and can run continuously through the WorkerLoop.
- Approval lookup is now a normalized indexed projection.
- Browser/document layers contain legacy compatibility modules that should be consolidated only after import usage is mapped.
- Production deployment and isolated infrastructure verification remain before final release.

## Next
- Deploy with a dedicated AutoWorker database and verify production health, authentication, CORS, Redis connectivity, worker execution, and observability end-to-end.
- Only after production verification, document the release posture and remove any remaining deployment-specific placeholders.

## Rule
Update this file after each meaningful milestone. Do not mark work complete until validated.
