# File ownership

## Claude Opus owns

- `generator/**`
- Loader-specific migrations
- `generator/tests/**`
- `docs/collaboration/opus/**`
- `docs/LOADER_DESIGN.md`
- `docs/LOADER_TEST_REPORT.md`

## Codex owns

- `benchmarks/**`
- Benchmark-specific helper scripts
- `docs/collaboration/codex/**`
- `docs/BENCHMARK_PLAN.md`
- `docs/BENCHMARK_TEST_REPORT.md`

## Shared — edit only after agreement on Issue #1

- `backend/**`
- Shared database schema
- `compose.yaml`
- `README.md`
- `pyproject.toml`
- `docs/collaboration/SHARED_CONTRACT.md`
- `docs/collaboration/TASK_BOARD.md`
- `docs/collaboration/DECISION_LOG.md`
- `docs/PRD_COMPLIANCE.md`

Cross-owned change requires a GitHub coordination message and explicit approval before editing. The integration owner alone updates the canonical decision log after agreement. Avoid simultaneous shared-file changes. Other paths are unchanged unless ownership is agreed in advance.
