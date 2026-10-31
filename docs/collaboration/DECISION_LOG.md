# Accepted shared decisions

Only the integration owner records an accepted decision here after explicit agreement in Issue #1. Proposals and individual workstream choices belong in the agent status/handoff or PR.

## D-001 — Phase 00 transactional rollups as baseline

- Problem: pg_trickle demo forced FULL refresh for two aggregates and 10M behavior is unknown.
- Alternatives: pg_trickle differential tables; transactional PostgreSQL signed-delta rollups.
- Selected: retain AgrregateX synchronous daily/hourly rollups as current baseline pending measured evidence; pg_trickle remains an installed packaged dependency, not the app query path.
- Reason: Phase 00 fixture correctness and 1M tests; extension probe fell back FULL. Not proof that extension cannot scale.
- Owner: Phase 00 integration owner.
- Evidence: `docs/ARCHITECTURE_DECISION.md`, `docs/PROJECT_STATE.md`, 1M benchmark artifacts. 10M write contention is untested.
