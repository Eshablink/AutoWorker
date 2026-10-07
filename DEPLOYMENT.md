# AutoWorker Deployment Status

## Free-tier deployment

As of 2026-10-07, AutoWorker has a free-tier Render deployment path validated as follows:

| Component | Status | URL / Notes |
|---|---|---|
| React web console | ✅ Live | https://autoworker-web-release.onrender.com |
| Web production build | ✅ Verified | TypeScript + Vite build succeeds on Render |
| FastAPI demo API | ✅ Live | https://autoworker-api-demo.onrender.com |
| Demo storage | ✅ Live | Isolated SQLite runtime; no Redis dependency |
| PostgreSQL production | ⚠️ Not provisioned | A dedicated database is required |
| Redis production | ⚠️ Not provisioned | A dedicated broker is required |

## Demo API vs production API

The no-charge deployment now has a separate AutoWorker demo API. It runs with `AUTOWORKER_ENV=development`, isolated SQLite storage, and no Redis dependency. The frontend is explicitly built against that API instead of relying on a `/api` path on the Render static-site host.

This makes the public operator console functional for staging/demo use without reusing another project's database or broker.

The demo runtime is **not** the production architecture and must not be described as durable PostgreSQL/Redis production infrastructure.

## Why the API is not marked production-live

The API runs Alembic migrations before startup. Its production migration set requires PostgreSQL. Without a dedicated `DATABASE_URL`, the application falls back to SQLite and the PostgreSQL-specific migration fails.

The existing Render PostgreSQL and Redis resources in the workspace belong to other applications. They are intentionally **not reused** because AutoWorker requires isolated infrastructure.

No paid resources were created for this deployment.

## Validated free-tier path

The web console is deployed independently as a Render static site using:

```text
cd apps/web && npm install && npm run build
```

The deployment completed successfully and Render reported the site live.

The repository intentionally does not contain a fabricated or placeholder npm lockfile. The deployment uses `npm install`, matching the repository's current dependency setup.

## Production release gate

Do not claim production-live until all of the following are verified on dedicated infrastructure:

- [ ] PostgreSQL provisioned and migrations pass
- [ ] Redis provisioned and readiness passes
- [ ] `AUTOWORKER_ENV=production`
- [ ] Secure `AUTOWORKER_API_TOKEN` configured
- [ ] Explicit `CORS_ORIGINS` configured for the deployed web origin
- [ ] `/health` passes
- [ ] `/ready` passes
- [ ] Authentication success/failure paths verified
- [ ] Task creation and worker execution verified
- [ ] Redis delivery and durable SQL fallback verified
- [ ] Prometheus metrics and structured logs verified
- [ ] Browser E2E/release smoke verification passes

## Cost constraint

This deployment is intentionally **no-charge**. Paid Render infrastructure must not be provisioned unless the repository owner explicitly changes that requirement.

## Current release classification

**Web staging/live preview:** ✅

**Demo API:** ✅

**Full production system:** 🚧 Blocked by isolated PostgreSQL + Redis availability on the free tier.
