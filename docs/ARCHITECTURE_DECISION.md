# AgrregateX — architecture decision

## Decision: transactional PostgreSQL signed-delta rollups

The pg_trickle 0.108.3 image remains a packaged PostgreSQL dependency, with extension schedulers disabled for this application. AgrregateX does not use its stream tables in the production query path. No Kafka, Redis or second database is required. The original demo is untouched.

## Evidence and options

The original pinned deployment's `category_revenue` used joined COUNT(DISTINCT), rejected by the installed bounded DISTINCT contract; `product_sales` hit generated SQL errors for an unselected grouping key, then ambiguous name after a trial rewrite. Inspect `pg-trickle-deployment` logs and upstream `src/dvm/parser/validation.rs` and group-rescan aggregate paths. These failures are specific, not proof that every differential query is unsupported.

A new isolated 10,000-row test (`benchmarks/probe.sql`, raw result in results/architecture-probe.txt) removed joins, rounded averages and DISTINCT, grouping one source by tenant, hour, product and status. Admission as DIFFERENTIAL succeeded; historical timestamp/status/quantity mutation reconciled exactly, but the observed manual refresh reported FULL fallback, 28.454 ms. Scheduler/shared memory was disabled for this manual probe; it does NOT measure automatic scheduling or high-rate extension behavior. A configured DIFFERENTIAL label alone is not proof of incremental execution. We have not proved extension performance impossible; a separate tuned extension benchmark could justify a future alternative.

The alternative is compact custom maintenance with two indexed rollups. Small deterministic fixtures passed inserts, cancellations, product/time moves, amount changes, replay, concurrent duplicate events, rollback, and deletion before scaling. All writes and signed deltas commit atomically, with no scheduler, outbox offset, eventual refresh or replay worker to recover. This provides the simplest independently testable correctness/freshness contract. The real write/lock cost is included in operational safety benchmarks in both arms, and is not assumed to be free.

## Data contract

Representative schema models one product-bearing order row (not a multi-line header). Product categories are immutable references; orders retain category_id with a composite FK. Official order-header/item semantics must be adapted after the organizer schema is supplied. Placed and shipped contribute sales and units; cancelled orders remain in total order counts and status counts but contribute zero sales/units. Cents are integer minor units; aggregate sums are signed int64, with bounded input values. Arbitrarily large dataset totals beyond int64 are not supported.

`daily_product`: tenant × UTC day × product × category × status.
`hourly_category`: tenant × UTC hour × category × status.
Both retain gross units/cents for every status; the query excludes cancelled contributions as appropriate. Each INSERT adds the new image, DELETE subtracts the old, UPDATE groups signed old/new images and updates only changed keys. Upsert keys are locked in deterministic order within each rollup; PostgreSQL deadlocks across arbitrary multi-row source transactions remain retryable, not silently dropped. The API returns retryable 503 and clients reuse their idempotency key.

Summary, daily trends, status/category and exact Top-N use complete UTC daily buckets plus at most two disjoint indexed source fragments. Hourly trends use complete hourly buckets and exact hour fragments. Short ranges with no full bucket use only the indexed source interval. All ranges are half-open [from,to); timezone offsets normalize to UTC. Zero trend buckets are generated explicitly. Top-N sums all products over the requested period then sorts by revenue, units and product ID. It never combines precomputed daily Top-N lists.

There are no source full scans on ordinary dashboard paths, but partial-day fragments for a heavy tenant can still be expensive. Product cardinality, tenant skew, range width and concurrency are measured rather than assumed bounded by total order count. Limits: maximum 366-day range, hourly trends 31 days, Top-N <=100, two concurrent requests per tenant, six pooled connections, statement_timeout 3 seconds. These are single API-process limits; multiple replicas would require shared admission control.

## Isolation and durability

Opaque randomly generated tenant tokens map to server-side tenant IDs. Path mismatches are rejected; body models forbid tenant injection; query/header overrides cannot select a different trusted identity. Every SQL query has an explicit tenant predicate plus RLS based on a transaction-local context. API role is neither owner nor superuser and has no BYPASSRLS; it cannot write rollup tables directly. Only the SECURITY DEFINER trigger writes rollups, with pinned search_path and revoked public execution. Schema creation is denied to public. Tokens, DB credentials and raw results are excluded from Git. Admin monitoring uses a separate token; tenant tokens cannot read it.

The backend is the trust boundary for shared DB credentials and transaction-local context. Someone possessing the runtime database password could set arbitrary tenant context; this is not cryptographic database-per-tenant authentication. Do not distribute that password to tenants. Transport binds localhost; remote deployment needs TLS and secret management.

Idempotency records are transactionally unique per tenant/key and fingerprint the method, target and body. A duplicate waits for the original transaction and returns the recorded result; conflicting reuse returns 409. Failed transactions leave neither source changes nor rollup changes nor a successful event marker. Duplicate patches with another key are state assignments and do not add a contribution twice.

## Rebuild and offline import

The representative loader is an administrative offline operation, explicitly blocking source writes, disabling only this project's rollup trigger inside one transaction, loading 100k-row server-side batches, rebuilding both rollups and the covering time index, reenabling the trigger and committing. Any exception/connection loss rolls everything back, including trigger/index DDL. Durability settings remain enabled. It extends 1M to 10M in the same database, not a duplicate 10M copy. Negative IDs reserve generated records; API test IDs are positive.

`database/rebuild.sql` provides the same protected rebuild for existing data. It blocks reads/writes during replacement, and is not an online zero-downtime rebuild. No tenant-accessible rebuild endpoint exists. Normal stop/restart never removes volumes.

## Resource budget and portability

Rootless Podman: PostgreSQL 1800 MiB / 1.5 CPU; API 300 MiB / 0.75 CPU. PostgreSQL shared_buffers 128 MiB, work_mem 4 MiB, maintenance_work_mem 64 MiB, six API connections. Existing workloads remain running. This exact image digest was tested only on x86_64 Fedora; ARM/M1 packaging and performance remain NOT VERIFIED. The SQL/Python design is portable, but a compatible native PostgreSQL image must be validated on M1 before claiming compatibility/performance.
