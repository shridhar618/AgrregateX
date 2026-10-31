# AgrregateX agent collaboration

Both developers use the private repository [surajgojanur/AgrregateX](https://github.com/surajgojanur/AgrregateX), its `main` integration branch, and [Issue #1](https://github.com/surajgojanur/AgrregateX/issues/1) as the shared agent message channel. The local Codex shell has no authenticated Git transport; GitHub app actions are used for repository, issue and PR operations. Never place tokens, passwords, or private data in issues or PRs.

## Start work

1. Clone with your authorized GitHub identity and use a feature branch (`feat/resumable-loader` for Opus; `test/prd-benchmark-suite` for Codex).
2. Read `docs/collaboration/SHARED_CONTRACT.md`, `TASK_BOARD.md`, `FILE_OWNERSHIP.md`, current `DECISION_LOG.md`, and your status/handoff documents.
3. Read recent comments on Issue #1. Claim your assignment in the issue before editing owned files.
4. Pull/fetch `main`; avoid rebasing or force-pushing shared history. Keep the Phase 00 1M dataset and existing pg_trickle deployment intact.

## Work and communicate

Work only in assigned paths. At milestones, post a concise message to Issue #1 using the template in TEAM_PROTOCOL.md. If a shared interface needs to change, propose it there and wait for explicit integration-owner agreement before editing. Check recent issue comments before opening a PR.

## Finish

Run the acceptance checks for your work, update only your status and handoff files, push your feature branch, open a PR to `main`, and request review from the other developer/integration owner. Post the PR URL and evidence on Issue #1. Do not merge. Mark the task waiting for review and stop; the integration owner coordinates approval and squash merge.

## Blockers

Post a BLOCKED issue comment with the exact dependency, attempted checks, evidence and requested action. Continue independent work only when it does not assume an unapproved contract change. Do not poll continuously; read the issue at task start and relevant milestones.
