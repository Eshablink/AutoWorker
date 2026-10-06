# AutoWorker — Autonomous AI Computer Worker Engine

## Mission
Build a production-oriented autonomous AI computer worker that accepts high-level goals, plans work, executes typed tools in controlled environments, handles bounded recovery, verifies outcomes, enforces safety policies, and produces auditable evidence.

## Primary Demonstration
A controlled invoice-processing workflow:
1. Accept a natural-language goal.
2. Discover the source invoice.
3. Extract structured invoice data.
4. Validate extracted fields.
5. Interact with a controlled ERP through a browser worker.
6. Handle validation failures through bounded recovery.
7. Persist/verify the resulting ERP record.
8. Produce structured audit and evidence.
9. Pause for human approval when policy requires it.

## Engineering Principles
- GitHub repository is the source of truth.
- Prefer explicit state machines and typed contracts over opaque autonomous loops.
- LLMs propose decisions; policy and typed tools control side effects.
- No unrestricted shell/OS execution from model-generated strings.
- Side effects require authorization and should be idempotent where possible.
- Never claim implementation without tests.
- Avoid storing or exposing private chain-of-thought; retain concise decision metadata and evidence.
- Keep simulated/test integrations clearly separated from real integrations.

## Delivery
The project must be testable locally, containerized, CI-validated, documented, and deployable. Architecture decisions, progress, and deviations from the original prototype must be recorded in the repository.
