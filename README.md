# AgrregateX — Multi-Tenant Real-Time Aggregation Layer

Exact tenant-scoped counts, sales, hourly/day trends, period Top-N and status/category breakdowns. PostgreSQL transactional signed-delta rollups + FastAPI, independent Git history. No cloud, AI or paid services.

**OFFICIAL DATASET COMPATIBILITY: NOT VERIFIED.** Local benchmarks use the explicitly representative fixed-seed generator; results and failures are in [PRD compliance](docs/PRD_COMPLIANCE.md) and [performance report](docs/PERFORMANCE_REPORT.md). Do not infer official Great compliance from these results.

## Run locally

Requires rootless Podman with Docker-compatible Compose v2+ (or Docker Compose), Git and Python 3.11+ with httpx for host-side test commands. On this tested Fedora machine these are already available. The start script activates the existing user Podman socket. Docker-only hosts should omit that socket command. No privileged installation is performed.

```bash
git clone <your-independent-AgrregateX-repository-url>
cd AgrregateX
./scripts/start.sh
```

Application: http://localhost:18081 · Swagger/OpenAPI: http://localhost:18081/docs · PostgreSQL: 127.0.0.1:25432. Existing pg_trickle demo at port 18080 remains independent.

`start.sh` generates `.env` and `.secrets.json` once with random credentials and restrictive file permissions, builds the small API image, initializes the isolated named volume, and waits for HTTP health. Do not copy `.env.example` unchanged. No credentials are stored in Git. Read your tenant-1 token locally:

```bash
python3 -c "import json; print(json.load(open('.secrets.json'))['tenants']['1'])"
```

Paste it into the simple dashboard. Select a tenant and date interval; every value comes from real SQL. Tokens are explicit local demo credentials, not a production identity provider. An independent admin token gates `/monitoring`; tenant tokens cannot access it.

## API contract

All data routes require `Authorization: Bearer <tenant-token>`. The authenticated tenant must match the path. `from` is inclusive, `to` exclusive, timezone required (UTC outputs). Maximum range 366 days; hourly trends <=31 days. Orders model one product-bearing row. Total orders include cancelled records; sales and sold units exclude cancelled records. Currency is integer cents; no float monetary arithmetic. Top-N ranks by sales cents descending, units descending, product ID ascending.

| Method/path | Purpose |
|---|---|
| GET `/tenants/1/summary?from=...&to=...` | Order count, units, exact sales cents |
| GET `/tenants/1/orders/count?from=...&to=...` | Summary alias matching the PRD example |
| GET `/tenants/1/trends?from=...&to=...&grain=hour` | Hour/day buckets, including zero periods |
| GET `/tenants/1/top-products?from=...&to=...&limit=10` | Exact period-specific Top-N |
| GET `/tenants/1/breakdown?from=...&to=...` | Status and category counts/totals |
| POST `/tenants/1/orders` | Create order; Idempotency-Key required |
| PATCH `/tenants/1/orders/123` | Status, amount, product/customer/time corrections |
| DELETE `/tenants/1/orders/123` | Remove order and its contribution |
| GET `/tenants/1/freshness` | Transactional consistency and observed timestamp |
| GET `/monitoring` | Admin-only pool and actual acceptance results |

Create body: `{"customer_id":1,"product_id":1,"category_id":1,"ordered_at":"2026-10-01T00:00:00Z","status":"placed","quantity":2,"unit_price_cents":1234}`. Customer/product tenant references must exist; representative loader supplies them. PATCH accepts any non-null subset of those fields. Keys reused with different payloads return 409; identical requests replay the same recorded response. Source, event record and rollups commit together. Retry 503 with the same idempotency key. Cross-tenant paths return 403, hidden foreign orders 404, invalid values/references 422. No frontend tenant value is trusted by SQL.

## Load and verify

```bash
# Administrative offline import; blocks this project's source until commit.
python3 generator/load.py 1000000 10
python3 benchmarks/run.py 1000000
python3 benchmarks/freshness.py 1000000
python3 benchmarks/safety.py 1000000
# Extend same dataset, no second 10M copy.
python3 generator/load.py 10000000 100
./scripts/verify.sh --full
```

The generator algorithm is version 1 / seed 42, server-side batches of 100k rows, 90 UTC days, 32 products and 100 customers per tenant. It produces about 40%/20% for tenants 1/2 and spreads the remainder unevenly across others. These are representative dimensions, not organizer schema claims. Negative source IDs reserve generated records. Refuses accidental downscaling, duplicate reload or unrelated positive test records. A failed load rolls back source and trigger/index changes. Allow at least 30 GiB free disk; the container caps memory/CPU. Keep API benchmark traffic off during bulk import. `verify.sh --full` will load missing scales and run real experiments; it is not a dry-run and may take minutes.

## Operations

```bash
./scripts/stop.sh               # preserve volume
./scripts/start.sh
./scripts/restart.sh
# Only this project:
docker compose -p agrregatex logs --tail=100 postgres
docker compose -p agrregatex logs --tail=100 api
podman exec agrregatex-postgres-1 psql -U agrregatex_owner -d agrregatex -c 'SELECT count(*) FROM orders;'
# Protected offline rebuild; same DB, source/rollups replaced atomically.
podman exec -i agrregatex-postgres-1 psql -v ON_ERROR_STOP=1 -U agrregatex_owner -d agrregatex < database/rebuild.sql
```

No normal script deletes a volume. To interrupt a loader, cancel its psql backend/connection and allow rollback; do not delete storage. In-flight writes retry idempotently after restart. There is no asynchronous worker service: maintenance runs in PostgreSQL source transactions. Admin offline rebuild is not zero downtime. No boot autostart guarantee beyond engine restart policies.

## Design and attribution

See [architecture decision](docs/ARCHITECTURE_DECISION.md), [tests](docs/TEST_REPORT.md), [correctness](docs/CORRECTNESS_REPORT.md), and [five-minute demo](docs/DEMO_GUIDE.md). This is independently implemented application/schema/benchmark code, inspired by the Apache-2.0 pg_trickle evaluation. The packaged image includes PostgreSQL 18.6 and pg_trickle 0.108.3; AgrregateX disables extension background scheduling and uses its own transactional rollups. It does not claim authorship of pg_trickle. Original technical names and license attribution remain in LICENSE and NOTICE. No upstream Git history was imported.

ARM/M1 8 GB hardware performance and this image digest's ARM availability are NOT VERIFIED; do not substitute x86 measurements for an M1 test. Production deployment requires HTTPS, secret rotation/storage, authentication lifecycle and multi-instance shared query limits.
