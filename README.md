<div align="center">

# ⚙️ AutoWorker

### Autonomous AI Computer Worker Engine

**Turn natural-language goals into controlled, auditable, and verifiable computer work.**

[![CI](https://github.com/Eshablink/AutoWorker/actions/workflows/ci.yml/badge.svg)](https://github.com/Eshablink/AutoWorker/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Web-React%2019%20%2B%20TypeScript-61DAFB?logo=react&logoColor=111827)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/Data-PostgreSQL%2017-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Playwright](https://img.shields.io/badge/Browser-Playwright-45BA63?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Repo Size](https://img.shields.io/github/repo-size/Eshablink/AutoWorker)](https://github.com/Eshablink/AutoWorker)
[![Phase](https://img.shields.io/badge/phase-5%20durable%20execution-6f42c1)](PROGRESS.md)

[**Architecture**](ARCHITECTURE.md) · [**Project Brief**](PROJECT_BRIEF.md) · [**Decisions**](DECISIONS.md) · [**Progress**](PROGRESS.md)

</div>

---

## 🎯 What is AutoWorker?

Most AI demos stop at **"the model generated an answer."**

AutoWorker tackles the harder engineering problem:

> **How do you let an AI perform real operational work without giving the model unchecked control over risky side effects?**

The platform separates **planning, authorization, execution, recovery, verification, and evidence** into explicit layers.

~~~text
Natural-language goal
        ↓
Structured plan
        ↓
Policy evaluation
   ├─ DENY ───────────────→ Safe failure
   ├─ APPROVAL ───────────→ Human decision
   └─ ALLOW
        ↓
Controlled execution
        ↓
Recovery / retry
        ↓
Independent verification
        ↓
Evidence + audit trail
~~~

The result is an agent architecture designed to be **inspectable, testable, secure, and evolvable** rather than an unconstrained "LLM + browser" loop.

---

## 🌟 Why AutoWorker stands out

| Capability | What it demonstrates |
|---|---|
| **Agentic AI** | Structured agent-provider boundary, typed action proposals, bounded planning |
| **Backend engineering** | FastAPI control plane, dependency-injected services, explicit domain lifecycle |
| **Data & persistence** | PostgreSQL, SQLAlchemy, Alembic, optimistic concurrency, normalized approval projection |
| **Computer-use automation** | Browser contracts, Playwright adapter, navigation/origin allowlists |
| **Safety engineering** | Deterministic policy, risk classification, HITL approvals, approval expiry |
| **Reliability** | Explicit failures, bounded recovery, idempotency boundaries, independent verification |
| **Auditability** | Durable task history, structured audit events, content-addressed evidence |
| **Frontend** | React + TypeScript operations console with task and audit visibility |
| **Engineering discipline** | CI, migration checks, regression coverage, Docker Compose, architectural decision records |

### The core design principle

**LLM proposes → policy authorizes → tools execute → verification proves → audit records.**

The model is useful, but it is not the final authority over consequential side effects.

---

## 🧩 Feature map

| Area | Included today |
|---|---|
| 🧠 **Planning** | Agent-provider contracts, structured task actions, plan validation boundaries |
| 🛡️ **Policy** | Deterministic allow / deny / approval decisions with risk-aware tools |
| 👷 **Workers** | Reference worker runtime, leases, heartbeats, bounded recovery |
| 🌐 **Computer Use** | Browser action/observation contracts + Playwright adapter |
| 📄 **Documents** | Document/OCR/invoice extraction contracts |
| 🧾 **ERP Automation** | Typed ERP boundary + deterministic simulated ERP |
| ✅ **Verification** | Separate verification lifecycle and composite verification engine |
| 🔐 **Approvals** | Human-in-the-loop approval requests, expiry and safe rejection paths |
| 🧠 **Memory** | Task-scoped memory contract and in-memory implementation |
| 🧾 **Audit / Evidence** | Structured audit trail and content-addressed evidence storage |
| 🖥️ **Operations UI** | React + TypeScript task monitoring and audit timeline |
| 🗄️ **Persistence** | SQLite local default + PostgreSQL / SQLAlchemy / Alembic |
| 🐳 **Infrastructure** | Docker Compose development stack with pgvector PostgreSQL |
| 🧪 **Quality** | Pytest, Ruff, frontend production build, migration validation in CI |
| 📬 **Durable coordination** | Database idempotency claims, task leases + heartbeats, event outbox |

---

## 🏗️ Architecture

~~~mermaid
flowchart LR
    U[User Goal] --> API[FastAPI Control Plane]
    API --> R[Task Repository]
    API --> W[React Operations Console]

    R --> O[Worker Orchestrator]
    O --> P[Planner / Agent Provider]
    O --> S[Policy Engine]

    S -->|deny| F[Safe Failure]
    S -->|approval| H[Human Approval]
    S -->|allow| X[Typed Tool Executor]

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

### Architectural boundaries

- **Domain** — task lifecycle, invariants, typed contracts
- **Agent / Planning** — proposals and execution-plan boundaries
- **Policy** — deterministic authorization before consequential execution
- **Worker** — execution, leases, recovery, runtime coordination
- **Tools** — browser, document, ERP, and registry contracts
- **Verification** — independent checks of expected resulting state
- **Audit / Evidence** — operational facts and evidence, without persisting private chain-of-thought
- **Web** — task control and operational visibility

---

## 🔄 Flagship workflow: Invoice → ERP

The primary product story is a controlled **invoice-to-ERP automation flow**.

~~~text
Natural-language goal
        ↓
Plan actions
        ↓
Extract invoice data
        ↓
Validate required fields
        ↓
Evaluate action policy
        ↓
Request human approval when required
        ↓
Execute controlled ERP / browser action
        ↓
Handle validation failure through bounded recovery
        ↓
Verify ERP state independently
        ↓
Persist evidence + audit trail
~~~

A deterministic simulated ERP is included for development and testing so the workflow can be exercised without touching a production financial system.

---

## 🔐 Safety model

Safety is treated as an **execution boundary**, not merely as a prompt instruction.

| Safeguard | Purpose |
|---|---|
| **Deterministic policy** | Actions are evaluated before consequential execution |
| **Risk-aware tools** | Tool definitions classify risk and side-effect behavior |
| **Human approval** | High-risk operations require explicit human approval |
| **Approval expiry** | Stale approvals cannot be reused |
| **Idempotency** | Side-effecting operations require idempotency boundaries |
| **Terminal-state locking** | Terminal tasks cannot be casually mutated |
| **Independent verification** | Completion requires a matching successful verification |
| **No private reasoning persistence** | Audits contain operational facts, not private chain-of-thought |
| **Browser origin allowlists** | Browser navigation is restricted to approved origins |
| **Optimistic concurrency** | Stale repository writes are rejected |

---

## 📊 Implementation snapshot

| Layer | Status | Notes |
|---|---|---|
| Domain & safety | ✅ Implemented | Typed models, lifecycle state machine, safety invariants |
| Persistence | ✅ Implemented | SQLAlchemy, Alembic, PostgreSQL support, approval projection |
| Worker runtime | ✅ Implemented | Reference runtime, durable leases, heartbeat renewal, recovery, verification lifecycle |
| Durable execution coordination | ✅ Implemented | Atomic idempotency claims, DB-backed leases, retryable event outbox |
| Browser / ERP / document boundaries | ✅ Implemented | Injectable adapters and controlled integrations |
| Audit / evidence | ✅ Implemented | Durable audit foundation + evidence store |
| Operations dashboard | ✅ Implemented | React + TypeScript task/audit views |
| Durable distributed coordination | 🚧 Next | Cross-process idempotency, outbox, multi-worker dispatch |
| Production deployment | 🚧 Next | Deployment hardening and observability |

---

## 🚀 Quick start

### Option A — Docker Compose

**Prerequisites:** Docker + Docker Compose.

~~~bash
git clone https://github.com/Eshablink/AutoWorker.git
cd AutoWorker

docker compose up --build
~~~

Open:

| Service | URL |
|---|---|
| **Operations console** | http://localhost:3000 |
| **API** | http://localhost:8000 |
| **Health** | http://localhost:8000/health |
| **Readiness** | http://localhost:8000/ready |

The API container runs Alembic migrations before starting the application.

### Option B — Backend + frontend locally

#### Backend

~~~bash
python -m venv .venv

# Windows
.venv\\Scripts\\activate

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"

pytest -q
ruff check packages apps tests

uvicorn apps.api.main:app --reload
~~~

#### Frontend

~~~bash
cd apps/web
npm install
npm run dev
~~~

The Vite development server defaults to port 5173.

---

## ⚙️ Configuration

AutoWorker reads configuration from environment variables.

| Variable | Default | Purpose |
|---|---|---|
| <code>AUTOWORKER_ENV</code> | <code>development</code> | Runtime environment name |
| <code>DATABASE_URL</code> | <code>sqlite:///./autoworker.db</code> | SQLAlchemy database connection |
| <code>EVIDENCE_ROOT</code> | <code>./data/evidence</code> | Root directory for stored evidence |
| <code>LLM_API_KEY</code> | unset | Optional agent/LLM provider credential |
| <code>LLM_MODEL</code> | unset | Optional agent/LLM model identifier |
| <code>CORS_ORIGINS</code> | <code>http://localhost:5173</code> outside production | Comma-separated explicit browser origins |

### Production CORS behavior

When <code>AUTOWORKER_ENV=production</code> and <code>CORS_ORIGINS</code> is not supplied, no origins are enabled by default. Wildcard <code>*</code> is rejected.

### Docker database configuration

Docker Compose supplies:

~~~text
postgresql+psycopg://autoworker:autoworker@postgres:5432/autoworker
~~~

For deployment, provide a dedicated database URL instead of reusing a database owned by another application.

---

## 💻 Usage

AutoWorker exposes its control plane through FastAPI.

### Create a task

~~~bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal":"Process an invoice and verify the ERP record"}'
~~~

### Inspect task state

~~~bash
curl http://localhost:8000/tasks/<task-id>
~~~

### Inspect the audit trail

~~~bash
curl http://localhost:8000/tasks/<task-id>/events
~~~

### Health checks

~~~bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
~~~

There is no fabricated <code>TaskRunner</code> API in the README: examples intentionally use the actual HTTP control plane exposed by the repository.

---

## 🔌 API surface

| Method | Endpoint | Purpose |
|---|---|---|
| <code>GET</code> | <code>/health</code> | Liveness check |
| <code>GET</code> | <code>/ready</code> | Database readiness check |
| <code>POST</code> | <code>/tasks</code> | Create a task |
| <code>GET</code> | <code>/tasks</code> | List recent tasks |
| <code>GET</code> | <code>/tasks/{task_id}</code> | Read task state |
| <code>GET</code> | <code>/tasks/{task_id}/events</code> | Read persisted audit history |
| <code>POST</code> | <code>/approvals/{approval_id}</code> | Approve or reject a pending action |

---

## 🧪 Testing & quality gates

The project uses automated checks for every meaningful change.

~~~text
Backend
  ✓ pytest
  ✓ Ruff

Database
  ✓ PostgreSQL service
  ✓ Alembic migration validation
  ✓ Legacy-data migration checks

Frontend
  ✓ npm install
  ✓ TypeScript build
  ✓ Vite production build
~~~

Run locally:

~~~bash
pytest -q
ruff check packages apps tests

cd apps/web
npm install
npm run build
~~~

CI runs these checks automatically on pushes and pull requests.

---

## 📁 Repository structure

~~~text
AutoWorker/
├── apps/
│   ├── api/                  # FastAPI control plane
│   └── worker/               # Worker application boundary
│
├── packages/
│   ├── agent/                # Agent-provider contracts
│   ├── planning/             # Execution-plan contracts
│   ├── domain/               # State machine + safety invariants
│   ├── policy/               # Deterministic authorization
│   ├── worker/               # Execution, leases, recovery, runtime
│   ├── tools/                # Browser, document, ERP, registry contracts
│   ├── memory/               # Task-scoped memory abstraction
│   ├── audit/                # Events + evidence
│   ├── verification/         # Business-result verification
│   └── workflows/            # Workflow composition
│
├── apps/web/                 # React + TypeScript operations console
├── infra/alembic/            # Database migrations
├── tests/unit/               # Domain, policy, worker, persistence, API tests
│
├── docker-compose.yml
├── pyproject.toml
├── PROJECT_BRIEF.md
├── ARCHITECTURE.md
├── DECISIONS.md
└── PROGRESS.md
~~~

---

## 🧠 Engineering decisions

AutoWorker documents the architectural reasoning behind its constraints.

### 1. Explicit state machine over an unconstrained agent loop

Lifecycle state is explicit so execution can be inspected, persisted, and recovered.

### 2. LLM proposes; policy authorizes

The model operates behind typed proposal boundaries instead of a direct unrestricted side-effect channel.

### 3. Verification is separate from execution

"Tool succeeded" and "the business outcome is correct" are different claims.

### 4. Evidence over chain-of-thought

The audit trail records operational facts and evidence references rather than private model reasoning.

### 5. Controlled environments first

The flagship workflow uses simulated / controlled integrations before real financial systems.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [DECISIONS.md](DECISIONS.md) for deeper details.

---

## 📌 Project status

**Status:** 🟢 Production-oriented foundation + durable execution layer complete · 🚧 Product and distributed runtime depth in progress

AutoWorker already has a substantial production-oriented core: explicit task lifecycle control, deterministic policy enforcement, human approvals, durable persistence, worker execution/recovery boundaries, independent verification, audit/evidence handling, browser/ERP contracts, and an operations dashboard.

### What is solid today

| Capability | Status |
|---|---|
| Domain & safety invariants | ✅ Implemented |
| PostgreSQL persistence & migrations | ✅ Implemented |
| Worker execution + recovery foundation | ✅ Implemented |
| HITL approvals + expiry | ✅ Implemented |
| Browser / document / ERP boundaries | ✅ Implemented |
| Verification + audit/evidence | ✅ Implemented |
| React + TypeScript operations console | ✅ Implemented |
| Automated CI + migration regression checks | ✅ Implemented |

### What we are building next

1. **Durable cross-process idempotency** — make side-effect protection reliable across multiple worker processes.
2. **Durable event outbox** — make operational events resilient and consistently delivered.
3. **Multi-worker dispatch** — move from the reference runtime toward real queued/distributed execution.
4. **Broader end-to-end computer-use coverage** — exercise controlled browser workflows against PostgreSQL-backed state.
5. **Production deployment + observability** — harden runtime configuration, health checks, monitoring, and deployment operations.

This is deliberate engineering scope, not a claim that every production concern is already solved.

---

## 🗺️ Roadmap

~~~text
[✓] Domain safety foundation
[✓] Persistence + migrations
[✓] Worker execution boundaries
[✓] Browser / ERP / document contracts
[✓] Verification + evidence
[✓] Operations dashboard
[✓] Worker runtime foundation
[✓] Approval persistence projection
[✓] Atomic durable idempotency
[✓] Durable event outbox
[✓] Database-backed worker leases + heartbeat
[ ] Full multi-worker queue dispatch
[ ] End-to-end controlled-browser demo
[ ] Production deployment + observability
~~~

---

## 🤝 Contributing

Contributions, issue reports, architectural discussion, and experiments are welcome.

For a focused change:

~~~bash
git checkout -b feature/your-change
# make and test your changes

pytest -q
ruff check packages apps tests

git add .
git commit -m "Describe the change"
git push origin feature/your-change
~~~

Then open a Pull Request describing:

- **What changed**
- **Why it changed**
- **How it was tested**
- **Any safety / migration / compatibility implications**

For architecture-level changes, update the relevant documentation in <code>ARCHITECTURE.md</code>, <code>DECISIONS.md</code>, or <code>PROGRESS.md</code>.

---

## 📚 Project documentation

| Document | Purpose |
|---|---|
| [PROJECT_BRIEF.md](PROJECT_BRIEF.md) | Product scope, goals, and requirements |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and boundaries |
| [DECISIONS.md](DECISIONS.md) | Important engineering trade-offs |
| [PROGRESS.md](PROGRESS.md) | Implementation progress and current state |

---

## ⚠️ Current limitations

AutoWorker is **not yet a fully autonomous production deployment**.

The current runtime and adapters intentionally prioritize safe execution boundaries, deterministic testing, controlled integrations, and inspectability. Queue-backed multi-worker dispatch, broader end-to-end computer-use coverage, production observability, and deployment validation remain roadmap work.

---

<div align="center">

### ⚙️ AutoWorker
**Autonomous execution with explicit control.**

Built around a simple idea:

**bounded → recoverable → verifiable → auditable**

</div>
