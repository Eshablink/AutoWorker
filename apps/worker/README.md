# Worker Runtime

The worker runtime is the long-running execution boundary for AutoWorker.

It claims an eligible task from the durable dispatch queue under a worker lease, plans CREATED tasks, applies policy to READY tasks, executes RUNNING tasks, and independently verifies results. Repository and execution adapters remain injectable for tests and
production infrastructure.

The runtime supports a persistent task queue with blocked approval states, stale-claim recovery, heartbeat-backed leases, and continuous polling. An external broker can replace or sit in front of the queue while preserving the same state-machine and optimistic-concurrency boundaries.
