# AgrregateX — audited state

## Repository

`/home/god/Documents/github/AgrregateX`, independent root Git repo, branch main, zero commits/remotes. All implementation files untracked. No upstream Git history imported; upstream checkout unchanged. `.gitignore` excludes secrets, caches, benchmark outputs, logs, CSV and dumps. Source checkpoint outside repository at `/home/god/Documents/github/AgrregateX-phase00-source.tar.gz`; checksum is in PHASE_STATUS.md.

## Services

Compose `agrregatex`: PostgreSQL running/healthy on localhost 25432 (limit 1800MiB/1.5 CPU); API on 18081 (300MiB/.75 CPU). Both restart unless stopped. `/health` returned HTTP 200. Original demo remains running: DB 15432, dashboard 18080 HTTP 200, generator running. No current crash loop.

## Data and recovery

PostgreSQL 18.6, pg_trickle 0.108.3 installed; extension scheduling disabled, application uses synchronous transactional rollups. Exactly 1,000,000 orders, 10 tenants; tenant 1 401,067, tenant 2 199,325, others 49.3–50.3k. daily_product 82,256 rows / 13,352,960 bytes total; hourly_category 331,361 / 50,257,920 bytes. orders heap/index total 732,889,088 bytes. `orders_time` exists, rollup trigger enabled. No active transaction/lock observed. Volume untouched.

Host at audit: 2.2GiB RAM available, 230GiB disk free. Cancelled loader transaction was building hourly_category. PostgreSQL completed rollback; source and rollups remain at 1M. Logs show substantial WAL/checkpoint writes. No resume checkpoint exists.

## Tests/evidence

Current bounded regression: 150/150. Saved 1M benchmark: 720 requests, zero errors; four API families, tenants 1/2/3/10, day/week/month/boundary ranges. p50 8.76ms, p95 36.68ms, p99 56.51ms, max 67.34ms. Source comparisons 65, zero mismatch; full rollup checks zero. Freshness 30 samples, worst 0.167s. Safety 1,440 ops across three pairs, dashboard 20 req/s/four clients; mean slowdown -3.86%, p95 -27.41% (measurement noise). Security artifact covers four tenants, not 100. No 10M results.
