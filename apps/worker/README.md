# Worker Runtime

The worker runtime is the long-running execution boundary for AutoWorker.

It claims an eligible task under a worker lease, plans CREATED tasks, applies
policy to READY tasks, executes RUNNING tasks, and independently verifies
results. Repository and execution adapters remain injectable for tests and
production infrastructure.

The reference implementation processes one task per `run_once()`. A production
service can call this from a durable queue/dispatcher while preserving the same
state-machine and optimistic-concurrency boundaries.
