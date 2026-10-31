# AgrregateX — Phase 00 PRD compliance audit

Evidence date 2026-10-31. Representative seed-42 data, not organizer generator. Source: 1,000,000 orders, 10 tenants; largest 401,067, second 199,325. Not the 10M/100 main evaluation.

| Requirement | Status | Evidence/scope |
|---|---|---|
| FR-1 range counts/totals | PASS, bounded | 150/150 regression checks incl. empty/half-open intervals, integer cents. 65 earlier source comparisons at 1M had zero mismatches. |
| FR-2 hourly/daily trends | PASS, bounded | Hour/day, zero periods/boundaries pass; 1M source oracle passed. |
| FR-3 exact period Top-N | PASS, bounded | Exact source comparisons passed at 1M; only tenants 1,2,3,10 sampled. |
| FR-4 status/category | PASS, bounded | Breakdown and placed/cancelled/shipped mutations pass on representative schema. |
| FR-5 tenant isolation | PARTIAL | Path mismatch, RLS and unauthorized action fixtures pass. Saved security artifact covers 4 tenants, not all 100 identities/pairs. Shared backend DB password is a trust boundary. |
| FR-6 insert/update/cancel | PASS, bounded | Insert, update, cancel, delete, replay, rollback and reconciliation pass. 1M source only. |
| FR-7 documented API | PASS, bounded | FastAPI OpenAPI, health and endpoints exercised. |
| Great 1 <200ms at 10M | NOT TESTED | 1M: 720 HTTP requests, zero errors, max 67.34ms; 4 families, tenants, ranges. No 10M. |
| Great 2 freshness <30s | PASS at 1M only | 30 source-commit-to-response samples, worst 0.167s. 10M untested. |
| Great 3 slowdown <10% | PASS for narrow saved experiment only | 3 paired trials, 720 OLTP transactions/arm, dashboard 20 req/s, 4 clients, triggers active. Mean transaction difference -3.86%, p95 -27.41%; negative values are noise, not speedup. Not broad workload or 10M. |
| Great 4 exact correctness | PARTIAL | 1M: 65 source comparisons, zero mismatches; both full rollup EXCEPT ALL checks zero. Four sampled tenants, representative semantics. |
| Great 5 growth <2x | NOT TESTED | No valid 10M result or ratio. |
| Official dataset compatibility | BLOCKED | Organizer schema/generator absent in searched local paths; representative data is not a substitute. |
| Laptop resources | PARTIAL | Fedora 44, i3-1115G4 2C/4T, 7.5GiB RAM; 2.2GiB available and 230GiB disk free at audit. Compose limits DB 1.8GiB/1.5 CPU, API 300MiB/.75 CPU. M1 untested. |
