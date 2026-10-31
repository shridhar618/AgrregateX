# Frozen shared contract — Phase 01

Status: frozen for parallel implementation. Changes require an Issue #1 proposal, explicit agreement, and integration-owner update here before either agent edits shared code.

## Dataset and source

Only the representative Phase 00 schema is currently available; official organizer schema/generator is NOT VERIFIED. `orders` is one product-bearing row, not a multi-line order header. Fields: `tenant_id int`, `id bigint`, `customer_id int`, `product_id int`, `category_id int`, `ordered_at timestamptz`, `status` (`placed`, `shipped`, `cancelled`), `quantity int`, `unit_price_cents bigint`, `version int`. Tenant/product/customer references are tenant-scoped. Do not claim the organizer's semantics match this model.

## Time and money

All API intervals are timezone-aware, normalized to UTC, half-open `[from,to)`. Empty/invalid ranges are rejected. Daily/hourly buckets use UTC; trend responses include zero buckets. Monetary amounts use integer cents; no floating-point currency. Placed and shipped contribute sales/units. Cancelled rows remain in total order counts and status counts but contribute zero sales/units. Top-N sorts by revenue cents descending, units descending, product ID ascending. These semantics are representative, pending organizer confirmation.

## Rollups

`daily_product`: tenant × UTC day × product × category × status, with signed order count, units, cents.
`hourly_category`: tenant × UTC hour × category × status, with signed order count, units, cents.

Source INSERT/UPDATE/DELETE deltas and both rollups commit atomically. Queries use complete rollup buckets plus exact source rows for partial boundaries; hourly trends use hourly granularity. Exact Top-N aggregates over the full requested range, not daily Top-N lists. Any redesign proposal must preserve correctness under historical changes and transactions.

## API

Base URL `http://localhost:18081`; OpenAPI `/openapi.json`, Swagger `/docs`, health `/health`. Tenant routes require bearer token mapped server-side to trusted tenant ID and path ID equality:

- GET `/tenants/{id}/summary?from=...&to=...`
- GET `/tenants/{id}/orders/count?from=...&to=...`
- GET `/tenants/{id}/trends?from=...&to=...&grain=hour|day`
- GET `/tenants/{id}/top-products?from=...&to=...&limit=...`
- GET `/tenants/{id}/breakdown?from=...&to=...`
- POST `/tenants/{id}/orders` (Idempotency-Key required)
- PATCH/DELETE `/tenants/{id}/orders/{order_id}` (Idempotency-Key required)
- GET `/tenants/{id}/freshness`

Currency response uses `sales_cents`. API validates tenant references and status; duplicate key and identical request replays the result, conflicting reuse returns 409. Admin-only `/monitoring` uses a separate token. Limits: 366-day overall, 31-day hourly range, Top-N <=100, two in-flight per tenant, DB statement timeout 3s.

## Database and benchmarks

Phase 00 used rootless Podman, PostgreSQL 18.6, pg_trickle 0.108.3 installed but extension background workers disabled for AgrregateX. Limits DB 1.8GiB/1.5 CPU and API 300MiB/0.75 CPU. Local host is Fedora 44, i3-1115G4, 7.5GiB RAM. 1M seed-42 representative dataset, 10 tenants, uneven distribution. Full official target requires 1M/10 and 10M/100 matched tests; no 10M data currently exists. Loader is owned by Opus; Codex benchmark suite may consume committed/imported datasets but must not start the 10M loader without an explicit phase instruction and interface coordination.
