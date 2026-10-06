# Policy Engine

The policy engine is a deterministic authorization boundary between planning and execution.

## Responsibilities

- Resolve the proposed tool from the typed registry.
- Evaluate baseline risk and side-effecting constraints.
- Produce a domain `PolicyDecision`.
- Require human approval for HIGH and CRITICAL risk.
- Deny side-effecting tools when their registered contract requires an idempotency key and none is supplied.

## Non-responsibilities

The policy engine does not execute tools, call an LLM, automate a browser, or persist state.

## Safety boundary

A `PolicyDecision` is bound to the exact task, action, and registered tool. The task state machine performs a second binding check before execution/resumption.

## Future extensions

- explicit deny rules by tool/category
- tenant/user authorization
- payload-aware limits
- approval expiry
- policy versioning
- audit persistence
