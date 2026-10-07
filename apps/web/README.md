# AutoWorker Web Console

The web application is the operator surface for AutoWorker.

## What it does

- Monitor persisted tasks and lifecycle state.
- Inspect action plans, policy decisions, risk level, retries, observations, and errors.
- Review pending human approvals and approve or reject them with an operator note.
- Inspect verification results and evidence references.
- Inspect runtime posture and durable coordination capabilities.
- Refresh automatically against the FastAPI control plane.

## Local development

From the repository root:

~~~bash
cd apps/web
npm install
npm run dev
~~~

The Vite development server runs on port 5173 by default.

Set `VITE_API_URL` when the API is not available through the default `/api` reverse-proxy path.

## Production build

~~~bash
npm run build
~~~

The CI pipeline validates the production TypeScript/Vite build on every relevant push and pull request.
