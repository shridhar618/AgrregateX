# Integration checklist

- [ ] Both PRs reviewed by someone other than author.
- [ ] No unapproved cross-owned file changes.
- [ ] Shared contracts remain compatible; accepted changes recorded by integration owner.
- [ ] Loader tests pass, including interruption/resume and duplicate batches.
- [ ] Benchmark tests pass on stable 1M data; 10M results only claimed after actual import.
- [ ] No secrets or credentials committed.
- [ ] No generated datasets, database volumes or large raw results committed.
- [ ] Phase 00 regression suite passes.
- [ ] Original pg_trickle demo remains unaffected.
- [ ] Combined integration checks pass before main is updated.
- [ ] PR approvals recorded; squash merge by integration owner only.
