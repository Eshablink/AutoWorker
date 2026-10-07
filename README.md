<div align="center">

# AutoWorker

### Autonomous AI Computer Worker Engine

**Turn natural-language goals into controlled, auditable, and verifiable computer work.**

[![CI](https://github.com/Eshablink/AutoWorker/actions/workflows/ci.yml/badge.svg)](https://github.com/Eshablink/AutoWorker/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Web-React%20%2B%20TypeScript-61DAFB?logo=react&logoColor=111827)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/Data-PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Playwright](https://img.shields.io/badge/Browser-Playwright-45BA63?logo=playwright&logoColor=white)](https://playwright.dev/)

</div>

---

## The idea

Most AI demos stop at **"the model generated an answer."**

AutoWorker is designed around a harder problem:

> **How do you let an AI perform real operational work without letting the model directly control risky side effects?**

AutoWorker separates **reasoning, authorization, execution, recovery, verification, and evidence** into explicit layers.

~~~text
Goal
  ↓
Plan
  ↓
Policy
  ├── DENY ───────────────→ Fail safely
  ├── REQUIRE APPROVAL ──→ Human approval
  └── ALLOW
          ↓
       Execute
          ↓
       Recover
          ↓
      Verify independently
          ↓
     Evidence + Audit
~~~

The result is an agent architecture that is easier to inspect, test, secure, and evolve than an unconstrained "LLM + browser" loop.

---

## Recruiter snapshot

| Area | What AutoWorker demonstrates |
|---|---|
| **AI / Agents** | Structured agent-provider boundary, typed tool proposals, bounded planning |
| **Backend** | FastAPI control plane, domain-driven lifecycle state machine, dependency-injected services |
| **Data** | PostgreSQL, SQLAlchemy, Alembic, optimistic concurrency, durable audit history |
| **Automation** | Worker runtime, leases, bounded recovery, idempotency boundaries |
| **Computer Use** | Browser observation/action contracts with Playwright adapter and navigation allowlists |
| **Safety** | Deterministic policy engine, risk classification, HITL approvals, approval expiry |
| **Reliability** | Verification as a separate lifecycle stage, explicit failure states, regression tests |
| **Frontend** | React + TypeScript operations console with live task/audit views |
| **Engineering** | CI, migration validation, Docker Compose, typed contracts, architecture decisions |

### Why it stands out

**AI is not trusted with side effects.** The model proposes; typed tools + deterministic policy decide.

**Execution is stateful.** Tasks move through an explicit lifecycle instead of disappearing inside an opaque loop.

**Success is verified.** A tool returning "click succeeded" is not treated as proof that the business outcome happened.

**Evidence is first-class.** Audit events, verification results, and evidence references make autonomous work inspectable.

---

## Architecture

~~~mermaid
flowchart LR
    U[User Goal] --> API[FastAPI Control Plane]
    API --> R[Task Repository]
    API --> W[React Operations Console]

    R --> O[Worker Orchestrator]
    O --> P[Planner / Agent Provider]
    O --> S[Policy Engine]
    S -->|allow| X[Typed Tool Executor]
    S -->|approval| H[Human Approval]
    S -->|deny| F[Safe Failure]

    H --> X
    X --> B[Browser / Document / ERP Adapters]
    X --> RC[Recovery Coordinator]
    RC --> X

    X --> V[Verification Engine]
    V --> E[Evidence Store]
    V --> A[Audit History]
    A --> W

    R --> DB[(PostgreSQL)]
~~~

### Core boundaries

- **Domain** — task lifecycle, safety invariants, typed contracts
- **Agent / Planning** — structured proposals and bounded execution plans
- **Policy** — deterministic authorization before consequential operations
- **Worker** — execution, leases, recovery, orchestration
- **Tools** — browser, document, ERP, and registry boundaries
- **Verification** — independent proof of the expected resulting state
- **Audit / Evidence** — durable operational trace without private chain-of-thought
- **Web** — operational visibility and task control

---

## Flagship workflow

The primary product story is an **invoice-to-ERP automation workflow**.

~~~text
Natural-language goal
        ↓
Structured plan
        ↓
Invoice extraction + validation
        ↓
Policy evaluation
        ↓
Human approval for risky financial actions
        ↓
Controlled ERP / browser execution
        ↓
Validation-error recovery
        ↓
Independent ERP verification
        ↓
Evidence + audit trail
~~~

A deterministic simulated ERP is included for development and testing so the workflow can be exercised without touching production financial systems.

---

## Safety model

AutoWorker treats safety as an execution boundary, not a prompt instruction.

| Safeguard | Purpose |
|---|---|
| **Deterministic policy** | Every executable action is evaluated before consequential execution |
| **Risk-aware tools** | Registered tools declare risk and side-effect behavior |
| **Human-in-the-loop** | High-risk operations require explicit approval |
| **Approval expiry** | Stale approvals cannot be reused |
| **Idempotency** | Side-effecting operations require idempotency keys |
| **Terminal-state locking** | Completed, failed, and cancelled tasks cannot be casually mutated |
| **Independent verification** | Completion requires a successful verification result |
| **No private chain-of-thought persistence** | Audits store structured operational facts instead |
| **Browser origin allowlists** | Playwright navigation is restricted to approved origins |
| **Optimistic concurrency** | Repository writes protect against stale task updates |

---

## What is implemented today

### Foundation

- Pydantic v2 domain models
- Explicit task state machine
- Typed tool registry and policy engine
- Agent-provider and plan-validation boundaries
- PostgreSQL persistence with SQLAlchemy + Alembic
- Optimistic concurrency controls
- Durable audit-history foundation
- Content-addressed evidence store

### Autonomous execution

- Worker execution boundary
- Process-local idempotency guard
- Worker leases and heartbeats
- Bounded recovery coordinator
- Reference worker runtime
- Separate verification lifecycle
- Simulated ERP invoice workflow
- Playwright browser adapter

### Product surface

- FastAPI task / approval / audit endpoints
- React + TypeScript operations dashboard
- Live task polling
- Persisted audit timeline
- Docker Compose development stack
- CI with backend tests, linting, frontend build, and PostgreSQL migration validation

---

## Quick start

### Option 1 — Docker Compose

~~~bash
git clone https://github.com/Eshablink/AutoWorker.git
cd AutoWorker

docker compose up --build
~~~

Then open:

- **Operations console:** http://localhost:3000
- **API:** http://localhost:8000
- **Health:** http://localhost:8000/health
- **Readiness:** http://localhost:8000/ready

The API container runs database migrations before starting the application.

### Option 2 — Run the backend and frontend separately

Backend:

~~~bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
pytest -q
ruff check packages apps tests

uvicorn apps.api.main:app --reload
~~~

Frontend:

~~~bash
cd apps/web
npm install
npm run dev
~~~

---

## API surface

| Endpoint | Purpose |
|---|---|
| <code>GET /health</code> | Liveness check |
| <code>GET /ready</code> | Database readiness check |
| <code>POST /tasks</code> | Create a task |
| <code>GET /tasks</code> | List recent tasks |
| <code>GET /tasks/{task_id}</code> | Read task state |
| <code>GET /tasks/{task_id}/events</code> | Read persisted audit history |
| <code>POST /approvals/{approval_id}</code> | Approve or reject a pending action |

### Example

Create a task:

~~~bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal":"Process an invoice and verify the ERP record"}'
~~~

Read its lifecycle:

~~~bash
curl http://localhost:8000/tasks/<task-id>
curl http://localhost:8000/tasks/<task-id>/events
~~~

---

## Repository structure

~~~text
AutoWorker/
├── apps/
│   ├── api/                 # FastAPI control plane
│   └── worker/              # Worker application boundary
├── packages/
│   ├── agent/               # Agent-provider contracts
│   ├── planning/            # Execution-plan contracts
│   ├── domain/              # State machine + safety invariants
│   ├── policy/              # Deterministic authorization
│   ├── worker/              # Execution, leases, recovery, runtime
│   ├── tools/               # Browser, document, ERP, registry contracts
│   ├── memory/              # Task-scoped memory abstraction
│   ├── audit/               # Events + evidence
│   ├── verification/        # Business-result verification
│   └── workflows/            # Flagship workflow composition
├── apps/web/                # React + TypeScript console
├── infra/alembic/            # Database migrations
├── tests/
│   └── unit/                # Contract, lifecycle, policy, worker tests
├── docker-compose.yml
├── PROJECT_BRIEF.md
├── ARCHITECTURE.md
├── DECISIONS.md
└── PROGRESS.md
~~~

---

## Engineering decisions

The repository documents architectural trade-offs instead of hiding them.

### 1. Explicit state machine over an unconstrained agent loop

Autonomous execution becomes inspectable and recoverable when lifecycle state is explicit.

### 2. LLM proposes; policy authorizes

The model never receives a direct "do anything" side-effect channel.

### 3. Verification is separate from execution

"Tool succeeded" and "business result is correct" are different claims.

### 4. Evidence over chain-of-thought

The system records useful operational facts without making private reasoning an audit artifact.

### 5. Controlled environments first

The flagship workflow uses simulated / controlled integrations before real financial systems.

See **[ARCHITECTURE.md](ARCHITECTURE.md)** and **[DECISIONS.md](DECISIONS.md)** for the detailed reasoning.

---

## Testing & quality gates

Every meaningful change is expected to pass:

~~~text
Backend
  ✓ pytest
  ✓ Ruff

Data
  ✓ PostgreSQL service
  ✓ Alembic migration validation
  ✓ Legacy-data migration checks

Frontend
  ✓ npm install
  ✓ production build
~~~

CI runs these checks automatically on pushes and pull requests.

---

## Project status

**Current phase:** Phase 4 — Autonomous capability layer

The foundation is intentionally production-oriented, but the project is still under active development.

### Current focus

1. Durable cross-process idempotency
2. Durable event outbox / operational event consistency
3. Real worker dispatch loop and queue integration
4. Rich approval, evidence, and task-detail UX
5. PostgreSQL + controlled-browser end-to-end workflow coverage
6. Deployment hardening and production health verification

The project is **not** presented as a fully autonomous production worker yet; the remaining gaps are documented and treated as engineering work rather than hidden behind a demo.

---

## Roadmap

~~~text
[✓] Domain safety foundation
[✓] Persistence + migrations
[✓] Worker execution boundaries
[✓] Browser / ERP / document contracts
[✓] Verification + evidence
[✓] Operations dashboard
[✓] Worker runtime foundation
[ ] Atomic durable idempotency
[ ] Durable event outbox
[ ] Full multi-worker dispatch
[ ] End-to-end controlled-browser demo
[ ] Production deployment + observability
~~~

---

## Why the project is built this way

AutoWorker is intentionally closer to an **automation platform** than a chatbot demo.

The engineering goal is not just to make an agent act autonomously.

It is to make autonomous work:

**bounded → explainable → recoverable → verifiable → auditable**

That is the bar the rest of the roadmap is designed to meet.

---

<div align="center">

### AutoWorker
**Autonomous execution with explicit control.**

</div>
