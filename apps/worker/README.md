# Worker Runtime

The worker runtime is the long-running execution boundary for AutoWorker.

It can consume task notifications from an external Redis Streams consumer group, then claim the durable task under a database worker lease, plan CREATED tasks, apply policy to READY tasks, execute RUNNING tasks, and independently verify results. Repository and execution adapters remain injectable for tests and
production infrastructure.

The runtime supports a persistent task queue with blocked approval states, stale-claim recovery, heartbeat-backed leases, and continuous polling. An external broker can replace or sit in front of the queue while preserving the same state-machine and optimistic-concurrency boundaries.

## Redis fleet

Use `RedisStreamsTaskBroker.from_url(...)` to connect a worker to Redis. Consumer-group delivery is paired with the SQL dispatch queue and database lease so broker delivery never replaces the durable execution safety boundary.
