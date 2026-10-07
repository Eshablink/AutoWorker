# AutoWorker

**Autonomous AI Computer Worker Engine**

AutoWorker turns high-level operational goals into controlled, verifiable computer actions.

> Status: Phase 4 — autonomous capability layer; hardening pass active.

## Execution model

Goal → Plan → Policy → HITL → Execute → Recover → Verify → Evidence → Audit

The domain state machine is authoritative for lifecycle safety. LLM or agent providers propose work; policy and typed tools control side effects.

## Flagship workflow

1. Accept a natural-language operational goal.
2. Generate structured tool proposals.
3. Extract and validate invoice data with provenance.
4. Evaluate deterministic safety policy and idempotency requirements.
5. Pause for human approval for risky financial actions.
6. Interact with a controlled ERP through typed adapters or Playwright.
7. Handle validation failures with bounded recovery.
8. Verify the resulting ERP record.
9. Store checksum-addressed evidence and audit history.

The repository includes a deterministic simulated ERP for local demonstrations and tests; simulated integrations are separated from real adapters.

## Repository layout

- apps/api — FastAPI control plane and persistence dependency boundary.
- apps/web — React + TypeScript operations dashboard.
- packages/domain — lifecycle state machine and safety invariants.
- packages/agent and packages/planning — structured agent and execution-plan boundaries.
- packages/policy — deterministic authorization rules.
- packages/worker — execution, idempotency, leases, recovery, orchestration.
- packages/tools — browser, document, ERP, and registry contracts.
- packages/memory — task-scoped memory abstraction.
- packages/audit and packages/workflows — evidence plus flagship workflow composition.
- infra/alembic — database migrations.
- tests — automated coverage.

## Local development

Install Python dependencies, run pytest, and run Ruff against packages, apps, and tests. The API exposes /health and /ready. The React dashboard uses /api as its reverse-proxied API base in production.

## Safety guarantees

No private chain-of-thought is persisted. Side-effecting actions require idempotency keys, high-risk operations require explicit HITL approval, approval requests expire, terminal tasks cannot be mutated, and verification is required before completion.

See PROJECT_BRIEF.md, ARCHITECTURE.md, DECISIONS.md, and PROGRESS.md.