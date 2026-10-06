# Worker Leases & Recovery

Workers use a short-lived lease so a crashed process cannot permanently own a task.

## Lifecycle

1. Worker acquires a task lease.
2. Worker periodically heartbeats before expiry.
3. Successful execution releases the lease.
4. A crashed worker stops heartbeating.
5. Another worker can reclaim the expired lease.
6. Task state remains authoritative in durable persistence.

## Safety

- Lease ownership is identified by worker ID and lease ID.
- Heartbeats from another worker are rejected.
- Expired leases cannot be renewed.
- Lease acquisition is exclusive per task.
- Lease storage is currently in-memory as a reference implementation; production deployment will move this coordination into PostgreSQL/transactional storage.

## Recovery boundary

Lease expiry does not automatically mark a task successful or failed. The recovery coordinator must inspect the durable task state, determine whether the last action is retryable/idempotent, and then transition through the domain state machine.
