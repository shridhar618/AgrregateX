# Parallel task board

## Developer A — Claude Opus 5.1

**Phase 01A: Resumable 10M Loader** — ACTIVE after coordination claim on Issue #1.

Goal: design and implement bounded, idempotent, recoverable staging/import and consistent rollup activation. Preserve existing 1M baseline. Do not modify Codex-owned benchmark paths. Dependencies: frozen source/rollup contract and isolated test storage. Acceptance: deterministic checkpoints; safe independent batch commits; duplicate/conflict semantics; error/interruption resume; no inconsistent live summaries; measured phase timings, disk/WAL/RAM; loader report and tests. Cross-interface changes need agreement first.

## Developer B — Codex

**Phase 01B: PRD Benchmark and Acceptance Suite** — ACTIVE after coordination claim on Issue #1.

Goal: exercise the frozen API and provide reproducible HTTP latency, source-oracle correctness, isolation, freshness, OLTP safety, growth comparison and honest PASS/FAIL scoring. Use existing 1M DB for bounded checks; do not launch 10M loader. Dependencies: shared API contract; consume loader output only after Opus publishes a stable resume/import contract. Acceptance: owned benchmark scripts, machine-readable score, PLAN/TEST_REPORT, repeatable bounded test evidence, PR requesting review. Do not edit loader.

## Integration

Neither branch merges itself. Integration owner reviews both PRs and the checklist, resolves approved shared changes, reruns combined checks, and squash-merges after approval.
